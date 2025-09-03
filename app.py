import os
import logging
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Local imports
from config.langchain_config import validate_config
from agents.tv_agent import hr_agent_simple

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Flask
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per hour", "10 per minute"]
)

@app.route('/')
def index():
    """Serve main page"""
    return app.send_static_file('index.html')

@app.route('/api/health')
@limiter.exempt
def health():
    """Health check endpoint"""
    try:
        logger.info("Health check: healthy")
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0-'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    """Main chat endpoint"""
    try:
        # Get request data
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message required'}), 400
            
        message = data.get('message', '').strip()
        session_id = data.get('sessionId', 'default')
        
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
            
        logger.info(f"New message received: {message[:50]}...")
        logger.info(f"Session ID: {session_id}")
        
        
        # Process message with  agent and specified model
        result = hr_agent_simple.process_message(message, session_id)
        
        # Check for errors
        if 'error' in result:
            logger.error(f"Error processing message: {result.get('details', 'Unknown error')}")
            return jsonify({
                'error': 'Internal server error',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        logger.info("Message processed successfully")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            'error': 'Internal server error',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/upload', methods=['POST'])
@limiter.limit("5 per minute")
def upload_file():
    """File upload endpoint - supports multiple files"""
    try:
        # Check for multiple files first, then single file for backward compatibility
        files = []
        if 'files' in request.files:
            files = request.files.getlist('files')
        elif 'file' in request.files:
            files = [request.files['file']]
        
        if not files or len(files) == 0:
            return jsonify({'error': 'No files provided'}), 400
        
        # Get session ID
        session_id = request.form.get('sessionId', 'default')
        
        uploaded_files = []
        errors = []
        
        for file in files:
            try:
                # Upload file using agent
                result = hr_agent_simple.upload_file(file, session_id)
                
                if result['success']:
                    uploaded_files.append({
                        'name': result['file_info']['original_name'],
                        'type': result['file_info']['file_type'],
                        'size': result['file_info']['file_size']
                    })
                    logger.info(f"File uploaded successfully: {result['file_info']['original_name']}")
                else:
                    errors.append(f"{file.filename}: {result['error']}")
                    
            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {e}")
                errors.append(f"{file.filename}: {str(e)}")
        
        if len(uploaded_files) > 0:
            message = f"Successfully uploaded {len(uploaded_files)} file(s)"
            if len(errors) > 0:
                message += f". {len(errors)} file(s) failed."
            
            return jsonify({
                'success': True,
                'message': message,
                'uploaded_files': uploaded_files,
                'errors': errors,
                'total_uploaded': len(uploaded_files),
                'total_errors': len(errors),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': 'No files could be uploaded',
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}")
        return jsonify({
            'error': 'Error uploading files',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/files/<session_id>', methods=['GET', 'DELETE'])
@limiter.limit("10 per minute")
def handle_session_files(session_id):
    """Handle GET and DELETE for session files"""
    try:
        if request.method == 'GET':
            # Get list of uploaded files for this session
            files = hr_agent_simple.get_uploaded_files(session_id)
            
            file_list = []
            for file_info in files:
                file_list.append({
                    'name': file_info['original_name'],
                    'type': file_info['file_type'],
                    'size': file_info['file_size']
                })
            
            return jsonify({
                'success': True,
                'files': file_list,
                'count': len(file_list),
                'timestamp': datetime.now().isoformat()
            })
            
        elif request.method == 'DELETE':
            # Clear all files for a session
            hr_agent_simple.clear_session_files(session_id)
            
            return jsonify({
                'success': True,
                'message': f'Files cleared for session {session_id}',
                'timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error handling session files: {e}")
        return jsonify({'error': 'Error handling session files'}), 500

@app.route('/api/files/<session_id>/<filename>', methods=['DELETE'])
@limiter.limit("10 per minute")
def delete_individual_file(session_id, filename):
    """Delete individual file from session"""
    try:
        from urllib.parse import unquote
        filename = unquote(filename)
        
        # Get all session files
        session_files = hr_agent_simple.get_uploaded_files(session_id)
        
        # Find and remove the specific file
        file_found = False
        for file_info in session_files:
            if file_info['original_name'] == filename:
                file_path = file_info['file_path']
                if os.path.exists(file_path):
                    os.remove(file_path)
                    file_found = True
                    logger.info(f"Individual file removed: {filename} for session {session_id}")
                    break
        
        if file_found:
            return jsonify({
                'success': True,
                'message': f'File "{filename}" removed successfully',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': f'File "{filename}" not found',
                'timestamp': datetime.now().isoformat()
            }), 404
            
    except Exception as e:
        logger.error(f"Error deleting individual file: {e}")
        return jsonify({'error': 'Error deleting file'}), 500

@app.route('/api/cleanup', methods=['POST'])
@limiter.limit("5 per minute")
def cleanup_old_files():
    """Cleanup old files (older than 1 hour)"""
    try:
        from tools.file_processor import FileProcessor
        file_processor = FileProcessor()
        
        deleted_count = file_processor.cleanup_old_files(max_age_hours=1)
        
        return jsonify({
            'success': True,
            'deleted_files': deleted_count,
            'message': f'Cleaned up {deleted_count} old files',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return jsonify({'error': 'Error during cleanup'}), 500

@app.route('/api/cleanup-session', methods=['POST'])
@limiter.limit("20 per minute")
def cleanup_session_files():
    """Cleanup files for a specific session (called on page refresh/unload)"""
    try:
        session_id = request.form.get('sessionId')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        # Clear session files
        hr_agent_simple.clear_session_files(session_id)
        
        logger.info(f"Session files cleaned up for session: {session_id}")
        
        return jsonify({
            'success': True,
            'message': f'Files cleared for session {session_id}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in session cleanup: {e}")
        return jsonify({'error': 'Error during session cleanup'}), 500

@app.route('/api/new-conversation', methods=['POST'])
@limiter.limit("10 per minute")
def new_conversation():
    """Start new conversation"""
    try:
        data = request.get_json() or {}
        session_id = data.get('sessionId', 'default')
        
        hr_agent_simple.start_new_conversation(session_id)
        
        return jsonify({
            'success': True,
            'message': 'New conversation started',
            'sessionId': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error starting new conversation: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/debug/sessions')
@limiter.exempt
def debug_sessions():
    """Debug endpoint to view active sessions"""
    try:
        sessions_info = {}
        
        # Get info of all sessions ()
        for session_id in ['default']:  # For now only default
            try:
                info = hr_agent_simple.get_conversation_stats(session_id)
                sessions_info[session_id] = info
            except:
                sessions_info[session_id] = {'status': 'inactive'}
        
        return jsonify({
            'active_sessions': sessions_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    return jsonify({
        'error': 'Too many requests. Please wait before trying again.',
        'retry_after': str(e.retry_after) if hasattr(e, 'retry_after') else '60'
    }), 429

@app.errorhandler(500)
def internal_error_handler(e):
    """Handle internal errors"""
    logger.error(f"Internal error: {e}")
    return jsonify({
        'error': 'Internal server error',
        'timestamp': datetime.now().isoformat()
    }), 500

def start_cleanup_thread():
    """Start background thread for periodic file cleanup"""
    def cleanup_worker():
        from tools.file_processor import FileProcessor
        file_processor = FileProcessor()
        
        while True:
            try:
                # Sleep for 30 minutes
                time.sleep(1800)  
                
                # Cleanup files older than 2 hours
                deleted_count = file_processor.cleanup_old_files(max_age_hours=2)
                if deleted_count > 0:
                    logger.info(f"Periodic cleanup: removed {deleted_count} old files")
                    
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                # Continue running even if there's an error
                time.sleep(60)  # Wait 1 minute before retrying
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    logger.info("Periodic file cleanup thread started")

def initialize_app():
    """Initialize application"""
    try:
        # Validate configuration
        if not validate_config():
            raise ValueError("Invalid Azure OpenAI configuration")
        
        logger.info("Configuration validated successfully")
        logger.info("HR  Agent initialized")
        
        # Start periodic cleanup thread
        start_cleanup_thread()
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing application: {e}")
        return False

if __name__ == '__main__':
    print("Starting HAVAS Chatbot ...")
    
    if not initialize_app():
        print("Error during initialization. Check the configuration.")
        exit(1)
    
    # Server configuration
    port = int(os.getenv('PORT', 3000))
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"HAVAS Chatbot  running at http://localhost:{port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info("Available endpoints:")
    logger.info(f"   - Chat: http://localhost:{port}/api/chat")
    logger.info(f"   - Health: http://localhost:{port}/api/health")
    logger.info(f"   - Debug: http://localhost:{port}/api/debug/sessions")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )

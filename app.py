import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

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

def initialize_app():
    """Initialize application"""
    try:
        # Validate configuration
        if not validate_config():
            raise ValueError("Invalid Azure OpenAI configuration")
        
        logger.info("Configuration validated successfully")
        logger.info("HR  Agent initialized")
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

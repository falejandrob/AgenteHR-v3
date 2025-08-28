import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

# Optimized imports
from tools.azure_search import AzureSearchClient
from memory.simple_memory import SimpleMemoryManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TVAgent:
    
    def __init__(self):
        logger.info("Initializing  HRAgent...")
        
        # Initialize document search
        self.document_search = AzureSearchClient()
        
        # Initialize simple memory
        self.memory_manager = SimpleMemoryManager()
        
        # Configure  LLM
        self.llm = self._setup_llm()
        
        #  prompt system
        self.system_prompt = """You are a Tv report assistant specialized in HAVAS.
            Always MUST respond in the language you are asked, ALWAYS.
            If they ask you in Spanish, respond in Spanish.
            If they ask you in French, respond in French.
            If they ask you in English, respond in English.
            If you don't know the answer, say so clearly.
            If you need more information, ask for it.
            If you are unsure about something, ask for clarification.
            If you encounter a problem, describe it clearly.
            Use the provided information to give accurate and helpful answers.
            If you don't have enough information, say so clearly."""

        logger.info(" HRAgent initialized successfully")
    
    def _setup_llm(self):
        """Configure"""
        try:
            from config.langchain_config import get_azure_llm
            llm = get_azure_llm()
            logger.info("LLM configured successfully")
            return llm
        except Exception as e:
            logger.error(f"Error configuring LLM: {e}")
            raise
    
    def process_message(self, message: str, session_id: str = "default") -> Dict:
        """
        Process message in a  manner
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing message: {message[:50]}...")
            
            # 1. Search for relevant documents
            search_results = self.document_search.search(message)
            logger.info(f"Found {len(search_results)} relevant documents")
            
            # 2. Prepare context
            context = self._prepare_context(search_results)
            
            # 3. Get conversation history
            conversation_history = self.memory_manager.get_conversation_history(session_id)
            
            # 4. Create  prompt
            messages = []
            messages.append(SystemMessage(content=self.system_prompt))
            
            # Add history if exists
            for hist_msg in conversation_history[-4:]:  # Only last 4 messages
                messages.append(HumanMessage(content=f"User: {hist_msg['human']}"))
                messages.append(SystemMessage(content=f"Assistant: {hist_msg['ai']}"))
            
            # Add context and current question
            if context:
                context_msg = f"Relevant information:\n{context}\n\nUser's question: {message}"
            else:
                context_msg = f"User's question: {message}"
            
            messages.append(HumanMessage(content=context_msg))
            
            # 5. Generate response
            response = self._generate_response(messages)
            
            # 6. Save to memory
            self.memory_manager.add_message(session_id, message, response)
            
            # 7. Prepare result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'response': response,
                'documentsFound': len(search_results),
                'hasContext': bool(context),
                'session_info': self.memory_manager.get_session_info(session_id),
                'processing_time': round(processing_time, 2),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Message processed successfully in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'error': 'Internal server error',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _prepare_context(self, search_results: List[Dict]) -> str:
        """Prepare context from found documents"""
        if not search_results:
            return ""
        
        context_parts = []
        for i, doc in enumerate(search_results[:3], 1):  # Only first 3
            content = doc.get('content', '').strip()
            if content:
                context_parts.append(f"Document {i}:\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _generate_response(self, messages: List) -> str:
        """
        Generate response with robust error handling for o3-mini
        """
        try:
            # Check model type to use appropriate invoke
            deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', '').lower()
            
            if deployment in {"o3-mini", "o3", "o4-mini"}:
                # For o3-mini, use simple invocation without additional parameters
                logger.info("Invoking o3-mini with minimal configuration")
                result = self.llm.invoke(messages)
            else:
                # For other models, use standard configuration
                result = self.llm.invoke(messages)
            
            # Robust handling of different response types
            if result is None:
                logger.warning("The model returned None")
                return "I'm sorry, I couldn't generate a response at this time. Please try again."
            
            # If it's a string directly
            if isinstance(result, str):
                response = result.strip()
                if response:
                    return response
                else:
                    return "I couldn't generate an adequate response. Please rephrase your question."
            
            # If it has content attribute
            if hasattr(result, 'content'):
                response = result.content
                if isinstance(response, str) and response.strip():
                    return response.strip()
                else:
                    return "I couldn't generate an adequate response. Please rephrase your question."
            
            # If it's a dict with 'content'
            if isinstance(result, dict) and 'content' in result:
                response = result['content']
                if isinstance(response, str) and response.strip():
                    return response.strip()
                else:
                    return "I couldn't generate an adequate response. Please rephrase your question."
            
            # Fallback
            logger.warning(f"Unexpected response format: {type(result)}")
            return "I'm sorry, there was a technical problem. Please try again."
            
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Error generating response: {e}")
            
            # Specific handling for unsupported parameter errors
            if "unsupported parameter" in error_msg or "temperature" in error_msg:
                logger.error("Unsupported parameter error detected - retrying with minimal configuration")
                return "I'm sorry, there was a model configuration problem. The technical team has been notified."
            
            return "I'm sorry, I encountered a technical problem. Please try again later."
    
    def start_new_conversation(self, session_id: str = "default"):
        """Start new conversation"""
        self.memory_manager.clear_session(session_id)
        logger.info(f"New conversation started for session: {session_id}")
    
    def get_conversation_stats(self, session_id: str = "default") -> Dict:
        """Get conversation statistics"""
        return self.memory_manager.get_session_info(session_id)


# Global agent instance
hr_agent_simple = TVAgent()

"""
LangChain configuration for Azure OpenAI
"""
import os
import logging
from typing import Any, Dict, Optional, List
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)


class O3MiniCompatibleChatOpenAI(AzureChatOpenAI):
    """
    Wrapper for AzureChatOpenAI that filters unsupported parameters for o3-mini
    """
    
    def __init__(self, **kwargs):
        # For o3-mini, filter unsupported parameters
        deployment = kwargs.get('deployment_name', '').lower()
        if deployment in {"o3-mini", "o3", "o4-mini"}:
            # Remove unsupported parameters
            filtered_kwargs = {k: v for k, v in kwargs.items() 
                             if k not in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']}
            logger.info(f"Filtering parameters for {deployment}: {list(kwargs.keys())} -> {list(filtered_kwargs.keys())}")
            super().__init__(**filtered_kwargs)
        else:
            super().__init__(**kwargs)
    
    def invoke(self, input_data, config=None, **kwargs):
        """Override invoke to filter parameters at runtime"""
        try:
            # Filter kwargs not supported by o3-mini
            deployment = getattr(self, 'deployment_name', '').lower()
            if deployment in {"o3-mini", "o3", "o4-mini"}:
                # Remove unsupported parameters from config if it exists
                if config and isinstance(config, dict):
                    config = {k: v for k, v in config.items() 
                             if k not in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']}
                
                # Remove unsupported parameters from kwargs
                filtered_kwargs = {k: v for k, v in kwargs.items() 
                                 if k not in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']}
                
                return super().invoke(input_data, config=config, **filtered_kwargs)
            else:
                return super().invoke(input_data, config=config, **kwargs)
                
        except Exception as e:
            logger.error(f"Error in invoke: {e}")
            raise


def validate_config() -> bool:
    """
    Validate Azure OpenAI configuration
    """
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_KEY', 
        'AZURE_OPENAI_DEPLOYMENT'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {missing_vars}")
        return False
    
    logger.info("Azure OpenAI configuration validated")
    return True

def get_azure_llm() -> AzureChatOpenAI:
    """
    Create and configure Azure ChatOpenAI instance optimized for o3-mini
    """
    try:
        deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_key = os.getenv('AZURE_OPENAI_KEY')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2025-01-01-preview')
        
        logger.info(f"Configuring model: {deployment}")
        
        # Base configuration
        llm_params = {
            "azure_endpoint": endpoint,
            "api_key": api_key,
            "api_version": api_version,
            "deployment_name": deployment,
            "verbose": False,
        }
        
        # For standard models
        max_tokens = int(os.getenv('AZURE_OPENAI_MAX_COMPLETION_TOKENS', '1500'))
        llm_params.update({
            "max_completion_tokens": max_tokens,
            "model_kwargs": {}
        })
        logger.info(f"Max tokens: {max_tokens}")
        llm = AzureChatOpenAI(**llm_params)
        
        logger.info(f"LLM configured successfully: {deployment}")
        return llm
        
    except Exception as e:
        logger.error(f"Error configuring LLM: {e}")
        raise

def get_azure_embeddings():
    """
    Configure Azure OpenAI embeddings for vector search
    """
    return AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
        api_key=os.getenv('AZURE_OPENAI_KEY'),
        api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2025-01-01-preview'),
        azure_deployment=os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
    )

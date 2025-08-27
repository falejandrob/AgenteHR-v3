"""
LangChain configuration simplificado para Azure OpenAI
Optimizado para o3-mini reasoning model
"""
import os
import logging
from typing import Any, Dict, Optional, List
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)


class O3MiniCompatibleChatOpenAI(AzureChatOpenAI):
    """
    Wrapper para AzureChatOpenAI que filtra parámetros no soportados por o3-mini
    """
    
    def __init__(self, **kwargs):
        # Para o3-mini, filtrar parámetros no soportados
        deployment = kwargs.get('deployment_name', '').lower()
        if deployment in {"o3-mini", "o3", "o4-mini"}:
            # Remover parámetros no soportados
            filtered_kwargs = {k: v for k, v in kwargs.items() 
                             if k not in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']}
            logger.info(f"🔧 Filtrando parámetros para {deployment}: {list(kwargs.keys())} -> {list(filtered_kwargs.keys())}")
            super().__init__(**filtered_kwargs)
        else:
            super().__init__(**kwargs)
    
    def invoke(self, input_data, config=None, **kwargs):
        """Override invoke para filtrar parámetros en tiempo de ejecución"""
        try:
            # Filtrar kwargs que no son soportados por o3-mini
            deployment = getattr(self, 'deployment_name', '').lower()
            if deployment in {"o3-mini", "o3", "o4-mini"}:
                # Remover parámetros no soportados del config si existe
                if config and isinstance(config, dict):
                    config = {k: v for k, v in config.items() 
                             if k not in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']}
                
                # Remover parámetros no soportados de kwargs
                filtered_kwargs = {k: v for k, v in kwargs.items() 
                                 if k not in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']}
                
                return super().invoke(input_data, config=config, **filtered_kwargs)
            else:
                return super().invoke(input_data, config=config, **kwargs)
                
        except Exception as e:
            logger.error(f"Error en invoke: {e}")
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
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    logger.info("✅ Azure OpenAI configuration validated")
    return True

def get_azure_llm() -> AzureChatOpenAI:
    """
    Create and configure Azure ChatOpenAI instance optimizado para o3-mini
    """
    try:
        deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o-mini')
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_key = os.getenv('AZURE_OPENAI_KEY')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2025-01-01-preview')
        
        logger.info(f"🧠 Configurando modelo: {deployment}")
        
        # Configuración base
        llm_params = {
            "azure_endpoint": endpoint,
            "api_key": api_key,
            "api_version": api_version,
            "deployment_name": deployment,
            "verbose": False,
        }
        
        # Para o3-mini (reasoning model) usar configuración especial
        if deployment and deployment.lower() in {"o3-mini", "o3", "o4-mini"}:
            logger.info("⚡ Modo reasoning model activado - configuración mínima")
            max_completion_tokens = os.getenv('AZURE_OPENAI_MAX_COMPLETION_TOKENS')
            if max_completion_tokens:
                llm_params["model_kwargs"] = {"max_completion_tokens": int(max_completion_tokens)}
                logger.info(f"🎯 Max completion tokens: {max_completion_tokens}")
            
            # Usar la clase compatible con o3-mini
            llm = O3MiniCompatibleChatOpenAI(**llm_params)
            logger.info("🚫 Usando clase compatible con o3-mini (filtros automáticos)")
            
        else:
            # Para modelos estándar
            max_tokens = int(os.getenv('AZURE_OPENAI_MAX_COMPLETION_TOKENS', '1500'))
            llm_params.update({
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "model_kwargs": {}
            })
            logger.info(f"🎯 Max tokens: {max_tokens}")
            llm = AzureChatOpenAI(**llm_params)
        
        logger.info(f"✅ LLM configurado exitosamente: {deployment}")
        return llm
        
    except Exception as e:
        logger.error(f"❌ Error configurando LLM: {e}")
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

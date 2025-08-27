#!/usr/bin/env python3
"""
Script de prueba para validar la configuración del modelo o3-mini
"""
import os
import logging
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_o3_mini_configuration():
    """Test básico de configuración o3-mini"""
    try:
        # Importar configuración
        from config.langchain_config import get_azure_llm, validate_config
        
        logger.info("🧪 Iniciando test de configuración o3-mini...")
        
        # Validar configuración básica
        if not validate_config():
            logger.error("❌ Configuración básica inválida")
            return False
        
        # Crear instancia del LLM
        logger.info("🔧 Creando instancia del LLM...")
        llm = get_azure_llm()
        
        if llm is None:
            logger.error("❌ No se pudo crear la instancia del LLM")
            return False
        
        logger.info(f"✅ LLM creado exitosamente: {type(llm).__name__}")
        
        # Test de invocación simple
        logger.info("🧪 Probando invocación simple...")
        
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="Eres un asistente útil."),
            HumanMessage(content="Hola, ¿cómo estás?")
        ]
        
        # Intento de invocación
        response = llm.invoke(messages)
        
        if response and hasattr(response, 'content') and response.content:
            logger.info(f"✅ Respuesta recibida: {response.content[:100]}...")
            return True
        else:
            logger.error("❌ No se recibió respuesta válida")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        return False

def test_hr_agent():
    """Test básico del HR Agent"""
    try:
        logger.info("🧪 Iniciando test del HR Agent...")
        
        # Importar y crear agente
        from agents.hr_agent import HRAgentSimple
        
        agent = HRAgentSimple()
        
        if agent is None:
            logger.error("❌ No se pudo crear el HR Agent")
            return False
        
        logger.info("✅ HR Agent creado exitosamente")
        
        # Test de mensaje simple
        logger.info("🧪 Probando procesamiento de mensaje...")
        
        result = agent.process_message("Hola, esto es una prueba")
        
        if result and 'response' in result:
            logger.info(f"✅ Mensaje procesado: {result['response'][:100]}...")
            return True
        else:
            logger.error("❌ No se pudo procesar el mensaje")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en test HR Agent: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Iniciando tests de validación...")
    
    # Verificar que existe archivo .env
    env_file = Path(".env")
    if not env_file.exists():
        logger.warning("⚠️ No se encontró archivo .env, usando variables de entorno del sistema")
    
    # Verificar deployment
    deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', '')
    if not deployment:
        logger.error("❌ AZURE_OPENAI_DEPLOYMENT no configurado")
        sys.exit(1)
    
    logger.info(f"🎯 Testing con deployment: {deployment}")
    
    # Ejecutar tests
    test_results = []
    
    # Test 1: Configuración LLM
    test_results.append(("Configuración LLM", test_o3_mini_configuration()))
    
    # Test 2: HR Agent (solo si el primero pasa)
    if test_results[0][1]:
        test_results.append(("HR Agent", test_hr_agent()))
    
    # Reporte final
    logger.info("📊 Resultados de tests:")
    all_passed = True
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  - {test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("🎉 Todos los tests pasaron exitosamente!")
        sys.exit(0)
    else:
        logger.error("💥 Algunos tests fallaron")
        sys.exit(1)

import asyncio
import os
import sys
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types as genai_types

# Asegurarse de que el directorio padre esté en el path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import root_agent

async def main():
    # Establecer valores por defecto si no están en las variables de entorno
    if "GOOGLE_CLOUD_PROJECT" not in os.environ:
        os.environ["GOOGLE_CLOUD_PROJECT"] = "agentspace-demos-466121"
    if "DATASET_ID" not in os.environ:
        os.environ["DATASET_ID"] = "price_shoes_test"
        
    print("Iniciando prueba del agente CalzaIntel...")
    
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent, app_name="calzaintel", session_service=session_service
    )
    
    user_id = "test_user"
    session_id = "test_session"
    
    await session_service.create_session(
        app_name="calzaintel", user_id=user_id, session_id=session_id
    )
    
    query = "Hola! Haz un análisis del inventario y dime qué productos están críticos y cuál es el pedido sugerido."
    print(f"Pregunta: {query}\n")
    print("--- RESPUESTA DEL AGENTE CalzaIntel ---")
    
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=query)]
            ),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text, end="", flush=True)
        print("\n---------------------------------------")
        print("\nPrueba exitosa.")
    except Exception as e:
        import traceback
        print("\nError al ejecutar el agente:")
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import asyncio
import logging
import subprocess
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

from agent import agente_receta
from tools.extraction_tools import procesar_y_guardar_receta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def probar_agente_adk(ruta_pdf: str):
    """
    Prueba el agente de forma nativa utilizando el InMemoryRunner de ADK.
    Simula un flujo completo de conversación donde el usuario solicita al agente
    el procesamiento del archivo PDF.
    """
    print(f"\n=== Iniciando sesión local de ADK con InMemoryRunner ===")
    runner = InMemoryRunner(agent=agente_receta)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id="usuario_local_prueba"
    )
    
    logger.info(f"Sesión ADK creada exitosamente (ID: {session.id})")
    
    ruta_absoluta = os.path.abspath(ruta_pdf)
    mensaje_usuario = f"Por favor, procesa y guarda en BigQuery la receta médica ubicada en la ruta: {ruta_absoluta}"
    print(f"\n👤 Usuario: {mensaje_usuario}")
    
    contenido = Content(
        role="user",
        parts=[Part.from_text(text=mensaje_usuario)]
    )
    
    print("\n🤖 Agente (Analizando intención y ejecutando herramientas automáticamente)...")
    
    async for evento in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=contenido,
    ):
        if evento.content and evento.content.parts:
            for parte in evento.content.parts:
                if parte.text:
                    print(f"\n💬 Respuesta del Agente:\n{parte.text}")

def main():
    """
    Punto de entrada principal para ejecutar pruebas locales.
    """
    print("\n=== Portal ADK: Farmacias Arrocha (Panamá) ===")
    print("Selecciona el modo de prueba local:")
    print("1. Interfaz Web Premium (FastAPI + Interfaz Gráfica en el Navegador) - ¡Recomendado para demostraciones!")
    print("2. Simulación nativa del Agente ADK en Consola (Flujo conversacional con InMemoryRunner)")
    print("3. Validación directa de la Herramienta en Consola (Extracción rápida sin razonamiento LLM de herramientas)")
    print("4. Limpiar Tabla de BigQuery (Vaciar registros de prueba en recetamedicas.prescripciones)")
    print("5. Demostración Ejecutiva para Gerencia (App Web Paralela de Anita Quevedo & José Serrano en puerto 8085)")
    print("6. Probar Cloud Run Function Localmente con Functions Framework (Emulador en puerto 8088)")
    
    try:
        opcion = input("\nIngresa una opción (1, 2, 3, 4, 5 o 6, por defecto 1): ").strip()
    except KeyboardInterrupt:
        sys.exit(0)

    if opcion == "6":
        print("\n🚀 Iniciando emulador local de Cloud Run Function en http://127.0.0.1:8088 ...")
        try:
            subprocess.run(["functions-framework", "--target=procesar_receta_http", "--source=cloud_function.py", "--port=8088"])
        except KeyboardInterrupt:
            print("\nEmulador de Cloud Function detenido.")
            sys.exit(0)
    elif opcion == "5":
        print("\n🚀 Iniciando Demostración Ejecutiva para Gerencia en http://127.0.0.1:8085 ...")
        try:
            subprocess.run([sys.executable, "demo_gerencia.py"])
        except KeyboardInterrupt:
            print("\nServidor de demo gerencial detenido.")
            sys.exit(0)
    elif opcion == "4":
        from limpiar_tabla import limpiar_tabla_prescripciones
        limpiar_tabla_prescripciones()
        sys.exit(0)
    elif not opcion or opcion == "1":
        print("\n🚀 Iniciando el Servidor Web UI ADK...")
        # Iniciar la aplicación web de FastAPI mediante uvicorn
        try:
            subprocess.run([sys.executable, "web_app.py"])
        except KeyboardInterrupt:
            print("\nServidor web detenido.")
            sys.exit(0)
    else:
        if len(sys.argv) < 2:
            print("\n⚠️ Para las opciones de consola, debes proporcionar la ruta del PDF como argumento.")
            print("Ejemplo: python main.py /ruta/a/tu/receta.pdf")
            ruta_pdf = input("\nIngresa la ruta al archivo PDF de prueba: ").strip()
            if not ruta_pdf:
                sys.exit(1)
        else:
            ruta_pdf = sys.argv[1]

        if not os.path.exists(ruta_pdf):
            print(f"\n❌ Error: El archivo {ruta_pdf} no existe.")
            sys.exit(1)

        if opcion == "3":
            print("\n--- Ejecutando Herramienta Directamente ---")
            resultado = procesar_y_guardar_receta(ruta_pdf)
            print(f"\nResultado:\n{resultado}")
        else:
            asyncio.run(probar_agente_adk(ruta_pdf))

if __name__ == "__main__":
    main()

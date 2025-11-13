# Developer: Anita Quevedo - anitaquevedo@google.com
# Equipo PE - LATAM
# Codigo adaptable de: https://github.com/google/adk-samples/blob/main/python/agents/data-science



import requests
import google.auth
from google.auth.transport.requests import Request
import json
import os
import sys

# --- 1. DEFINICIÓN DE VARIABLES ---

# Datos del Proyecto y Ubicación
PROJECT_ID = "agentspace-demos-466121"
PROJECT_NUMBER = "697254066228" 
AS_LOCATION = "global"  # Ubicación de la aplicación (e.g., global, eu, us)
AS_APP = "agentspace-demos-all_1752785371208" # ID del Engine/Application de Agentspace

# Datos del Reasoning Engine (Motor de Razonamiento)
REASONING_ENGINE_ID = "7090728497294868480" 
REASONING_ENGINE_LOCATION = "us-central1" 

# Construcción del nombre del recurso del Reasoning Engine
REASONING_ENGINE = f"projects/{PROJECT_ID}/locations/{REASONING_ENGINE_LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}"

# Datos del Agente a desplegar
AGENT_DISPLAY_NAME = "demo-nl2sql-bq-v1" 
AGENT_DESCRIPTION = (
    "An agent that translates natural language questions into SQL queries. "
    "It understands the user's query, generates the appropriate SQL, "
    "reviews and rewrites it for accuracy, executes it, and can even generate charts from the results."
)

# Endpoint de la API
DISCOVERY_ENGINE_PROD_API_ENDPOINT = "https://discoveryengine.googleapis.com"


def deploy_agent_to_agentspace():
    """
    Ejecuta la llamada POST a la API de Discovery Engine para crear un Agente.
    """
    try:
        # --- 2. AUTENTICACIÓN (Reemplaza gcloud auth print-access-token) ---
        # Usa las Credenciales de Aplicación por Defecto (ADC)
        credentials, _ = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Refrescar y obtener el token de acceso
        auth_request = Request()
        credentials.refresh(auth_request)
        access_token = credentials.token
        print("hola")
        print(access_token)
        # Obtener y mostrar la identidad autenticada
        identity_email = getattr(credentials, 'service_account_email', 'N/A')

        print("hola2")
        print(identity_email)
        if identity_email != 'N/A':
            print(f"✅ Autenticado como Service Account: {identity_email}")
        else:
            print(f"✅ Autenticado usando: {type(credentials).__name__}")
            print("   (Para ver el email exacto de usuario, use 'gcloud auth list' en la terminal.)")
        
    except Exception as e:
        print("❌ Error al obtener credenciales de autenticación.")
        print("Asegúrate de haber corrido 'gcloud auth application-default login' en tu terminal.")
        print(f"Detalle del error: {e}")
        sys.exit(1)

    # --- 3. CONSTRUCCIÓN DE LA URL ---
    # La URL se construye usando las variables definidas
    BASE_URL = (
        f"{DISCOVERY_ENGINE_PROD_API_ENDPOINT}/v1alpha/projects/{PROJECT_NUMBER}/"
        f"locations/{AS_LOCATION}/collections/default_collection/engines/{AS_APP}/"
        f"assistants/default_assistant/agents"
    )

    # --- 4. CONSTRUCCIÓN DEL JSON PAYLOAD (-d) ---
    payload = {
        "displayName": AGENT_DISPLAY_NAME,
        "description": AGENT_DESCRIPTION,
        "icon": {
            "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"
        },
        "adk_agent_definition": {
            "tool_settings": {
                "toolDescription": AGENT_DESCRIPTION,
            },
            "provisioned_reasoning_engine": {
                "reasoningEngine": REASONING_ENGINE, # Usa el nombre del recurso completo
            },
        }
    }

    # --- 5. ENCABEZADOS DE LA PETICIÓN (-H) ---
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        # Este encabezado asegura que las cuotas y la facturación se apliquen al PROJECT_ID correcto
        "x-goog-user-project": PROJECT_ID, 
    }

    # --- 6. EJECUCIÓN DEL POST ---
    print(f"🚀 Intentando desplegar Agente: {AGENT_DISPLAY_NAME}")
    print(f"URL de destino: {BASE_URL}\n")
    
    response = requests.post(BASE_URL, headers=headers, json=payload)

    # --- 7. MANEJO DE LA RESPUESTA ---
    if response.status_code == 200:
        print("✅ ¡Agente desplegado exitosamente! Respuesta de la API:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Error {response.status_code}. El despliegue falló.")
        print("Detalles del error (posibles causas):")
        # Imprime la respuesta detallada de Google para el diagnóstico
        try:
            error_details = response.json()
            print(json.dumps(error_details, indent=2))
        except json.JSONDecodeError:
            print(response.text)
        
        # Recordatorio de soluciones del chat anterior
        print("\n--- Puntos a Revisar ---")
        print("1. **Permisos IAM:** La cuenta que autenticó debe tener el rol 'Discovery Engine Editor'.")
        print("2. **Reasoning Engine:** Verificar que el recurso en:")
        print(f"   {REASONING_ENGINE}")
        print("   exista, esté activo y sea accesible desde el proyecto.")

if __name__ == "__main__":
    # Comando para asegurar la autenticación antes de correr el script
    print("Asegúrate de haber configurado las Credenciales de Aplicación por Defecto (ADC).")
    print("Corre en tu terminal: 'gcloud auth application-default login'")
    print("-" * 50)
    deploy_agent_to_agentspace()
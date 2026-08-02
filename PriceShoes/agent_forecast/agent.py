import os
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
import google.auth
from dotenv import load_dotenv
from google.adk.agents import Agent

try:
    from prompts import AGENT_INSTRUCTION
    from tools import (
        obtener_catalogo_productos,
        ejecutar_pronostico,
        obtener_analisis_inventario,
        obtener_optimizacion_precios,
        simular_impacto_promocion,
        crear_orden_compra
    )
except ModuleNotFoundError:
    from .prompts import AGENT_INSTRUCTION
    from .tools import (
        obtener_catalogo_productos,
        ejecutar_pronostico,
        obtener_analisis_inventario,
        obtener_optimizacion_precios,
        simular_impacto_promocion,
        crear_orden_compra
    )

load_dotenv()

try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
except Exception:
    pass

# Forzar el uso de Vertex AI y configurar ubicación
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

# Crear el agente principal con sus herramientas
root_agent = Agent(
    name="CalzaIntel",
    model="gemini-2.5-flash",
    instruction=AGENT_INSTRUCTION,
    description="Agente inteligente de predicción de demanda y planeación de abastecimiento de Price Shoes.",
    tools=[
        obtener_catalogo_productos,
        ejecutar_pronostico,
        obtener_analisis_inventario,
        obtener_optimizacion_precios,
        simular_impacto_promocion,
        crear_orden_compra
    ]
)

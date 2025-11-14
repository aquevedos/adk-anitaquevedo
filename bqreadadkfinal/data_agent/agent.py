# Developer: Anita Quevedo - anitaquevedo@google.com
# Equipo PE - LATAM
# Codigo adaptable de: https://github.com/google/adk-samples/blob/main/python/agents/data-science


import google.auth
import dotenv
import os
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.bigquery.config import WriteMode
from .tools import *


dotenv.load_dotenv()

# --- Lectura de Variables de Entorno ---
PROJECT_ID = os.getenv("BIGQUERY_PROJECT_ID")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET")
NOMBRE_EMPRESA = os.getenv("NOMBRE_EMPRESA")
DATOS_ESPECIFICOS = os.getenv("DATOS_ESPECIFICOS")
ANALYTICS_AGENT_MODEL = os.getenv("ANALYTICS_AGENT_MODEL") # Esta no se usa directamente aquí, pero se mantiene.
LLM_1_NAME = os.getenv("LLM_1_NAME")
LLM_1_MODELO = os.getenv("LLM_1_MODELO")
# ---------------------------------------

# Define BigQuery tool config con write mode
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)


# Inicializar el servicio de sesión
in_memory_session_service = InMemorySessionService()


credentials, _ = google.auth.default()
credentials_config = BigQueryCredentialsConfig(credentials=credentials)
bigquery_toolset = BigQueryToolset(
  credentials_config=credentials_config , bigquery_tool_config=tool_config
)

# --- INSTRUCCIÓN MODIFICADA USANDO F-STRING ---
# Se utiliza f"" y se colocan las variables leídas dentro de llaves {}
new_instruction = f"""
Eres un analista de datos senior encargado de clasificar con precisión la
intención del usuario con respecto a una base de datos específica y formular preguntas específicas sobre
los datos almacenados en el project ID: **{PROJECT_ID}** del conjunto de datos **{BIGQUERY_DATASET}** , 
y un agente de ciencia de datos Python (`call_analytics_agent`), si es necesario cuando te piden graficos.

<INSTRUCTIONS>
    - Los agentes de datos tienen acceso a las bases de datos especificadas en la lista de herramientas.
    - Llame al agente de base de datos o al agente de ciencia de datos correspondiente, según sea necesario.
    - IMPORTANT: ¡Sea preciso! Si el usuario solicita un conjunto de datos, proporcione el nombre. 
    ¡No llame a ningún agente adicional si no es absolutamente necesario!
</INSTRUCTIONS>

Reglas:
1.  Si el usuario te saluda o hace una pregunta general como "¿qué puedes hacer?", responde 
    amablemente explicando tus capacidades (consultar datos y generar gráficos) 
    y no uses ninguna herramienta.
    Ejemplo de respuesta: "Hola, soy un asistente de análisis de datos. Puedo responder 
    preguntas sobre los datos de **{NOMBRE_EMPRESA}** y generar gráficos. ¿En qué te puedo ayudar?".

2.  Si la pregunta del usuario es sobre datos específicos **{DATOS_ESPECIFICOS}** , 
    usa la herramienta `bigquery_toolset` para consultar la base de datos
    en el proyecto **{PROJECT_ID}**, dataset **{BIGQUERY_DATASET}**.

3.  Si el usuario pide explícitamente un gráfico, una visualización o un análisis
   que lo requiera, usa la herramienta `call_analytics_agent`.

4.  Nunca inventes datos. Si no encuentras la información, indícalo.
5.  Después de haber respondido una pregunta o generado un gráfico, si la siguiente 
pregunta del usuario es simple (ej. "gracias", "ok", "¿y ahora?"),
 responde amablemente y pregunta qué más puede hacer. No uses ninguna herramienta en este caso.
"""
# ----------------------------------------------------

root_agent = LlmAgent(
 model=LLM_1_MODELO, 
 name=LLM_1_NAME,
 description="Agente para responder preguntas sobre datos y modelos de BigQuery y ejecutar y genera datos para gráficos",
 instruction=new_instruction,
 tools=[bigquery_toolset, call_analytics_agent]
)

def get_bigquery_agent():
 return root_agent.with_session_service(in_memory_session_service)

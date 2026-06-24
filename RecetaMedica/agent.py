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
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.genai import types

from prompt import INSTRUCCION_AGENTE_RECETA
from tools.extraction_tools import procesar_y_guardar_receta

load_dotenv()

# Definición del agente siguiendo las buenas prácticas de ADK
agente_receta = LlmAgent(
    name="AgenteRecetaMedica",
    model=os.getenv("GEMINI_MODEL"),
    description="""Agente inteligente desarrollado con ADK para extraer de manera estructurada
los campos de recetas médicas en PDF y almacenar automáticamente la información en BigQuery.""",
    instruction=INSTRUCCION_AGENTE_RECETA,
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    tools=[procesar_y_guardar_receta],
)

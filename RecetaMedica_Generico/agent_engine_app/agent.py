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

from prompt import INSTRUCCION_AGENTE_RECETA_ENGINE
from tools.receta_tools import herramienta_registrar_receta_bq

load_dotenv()

# Agente raíz de Agent Engine estructurado para despliegue en Gemini Enterprise
agente_receta_engine = LlmAgent(
    name="AgenteRecetaMedicaArrocha",
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
    description="Agente de IA Generativa especializado en extracción multimodal de recetas para Farmacias Arrocha.",
    sub_agents=[],
    instruction=INSTRUCCION_AGENTE_RECETA_ENGINE,
    tools=[herramienta_registrar_receta_bq],
)

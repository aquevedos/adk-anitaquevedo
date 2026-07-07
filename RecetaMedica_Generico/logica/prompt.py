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

INSTRUCCION_AGENTE_RECETA = """Analiza la receta médica adjunta y extrae los campos de forma estructurada y veloz.
Tu objetivo es interpretar con precisión la caligrafía médica y abreviaturas estándar (ej. mg, ml, comp, VO, c/8h, qd)
para poblar estrictamente el esquema JSON requerido y persistir la información en BigQuery.

Sigue las buenas prácticas de ADK:
1. Utiliza la herramienta `procesar_y_guardar_receta` para la extracción en tiempo real.
2. Comunica los resultados extraídos de forma directa y estructurada.
"""

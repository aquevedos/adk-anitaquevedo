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
import json
import time
import logging
import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from google.cloud import bigquery

logger = logging.getLogger(__name__)

class MedicamentoPrescrito(BaseModel):
    nombre: str = Field(description="Nombre del fármaco o medicamento")
    dosis: str = Field(description="Dosis prescrita (ej. 500mg)")
    cantidad: str = Field(description="Cantidad prescrita en total")
    sugerencia_etiquetas: int = Field(description="Cantidad de etiquetas sugeridas a imprimir en farmacia")

class RegistrarRecetaArgs(BaseModel):
    numero_receta: str = Field(description="Número correlativo o folio de la receta")
    paciente_nombre: str = Field(description="Nombre del paciente")
    paciente_apellido: str = Field(description="Apellido del paciente")
    paciente_cedula: str = Field(description="Cédula de identidad del paciente")
    medico_nombre: str = Field(description="Nombre completo del doctor prescriptor")
    clinicas_inferidas: List[str] = Field(description="Lista de 3 clínicas posibles asociadas a este doctor")
    medicamentos: List[MedicamentoPrescrito] = Field(description="Listado de medicamentos recetados")

def herramienta_registrar_receta_bq(args: RegistrarRecetaArgs) -> str:
    """
    Herramienta de Agent Engine para persistir en BigQuery los datos extraídos de una receta médica.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "agentspace-demos-466121")
    dataset_id = "recetamedicas"
    table_id = "prescripciones_agent_engine"

    try:
        bq_client = bigquery.Client(project=project_id)
        dataset_ref = bq_client.dataset(dataset_id)
        esquema = [
            bigquery.SchemaField("numero_receta", "STRING"),
            bigquery.SchemaField("paciente_nombre", "STRING"),
            bigquery.SchemaField("paciente_apellido", "STRING"),
            bigquery.SchemaField("paciente_cedula", "STRING"),
            bigquery.SchemaField("medico_nombre", "STRING"),
            bigquery.SchemaField("clinicas_inferidas", "STRING"),
            bigquery.SchemaField("medicamentos_detalle", "STRING"),
            bigquery.SchemaField("fecha_registro", "TIMESTAMP"),
        ]
        table_ref = dataset_ref.table(table_id)
        try:
            tbl = bq_client.get_table(table_ref)
        except Exception:
            table = bigquery.Table(table_ref, schema=esquema)
            bq_client.create_table(table, exists_ok=True)
            time.sleep(4)

        meds_dict = [m.model_dump() for m in args.medicamentos]
        fila = {
            "numero_receta": str(args.numero_receta),
            "paciente_nombre": str(args.paciente_nombre),
            "paciente_apellido": str(args.paciente_apellido),
            "paciente_cedula": str(args.paciente_cedula),
            "medico_nombre": str(args.medico_nombre),
            "clinicas_inferidas": ", ".join(args.clinicas_inferidas),
            "medicamentos_detalle": json.dumps(meds_dict),
            "fecha_registro": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        intento = 0
        errores = None
        while intento < 4:
            try:
                errores = bq_client.insert_rows_json(table_ref, [fila])
                if not errores or not any("not found" in str(e).lower() for e in errores):
                    break
            except Exception as e:
                if "not found" in str(e).lower() and intento < 3:
                    time.sleep(4)
                    intento += 1
                    continue
                raise e
            if errores and any("not found" in str(e).lower() for e in errores) and intento < 3:
                time.sleep(4)
                intento += 1
                continue
            break

        if errores:
            logger.error(f"Error en inserción BQ Agent Engine: {errores}")
            return f"Fallo en almacenamiento BQ: {errores}"

        return f"¡Receta folio {args.numero_receta} de {args.paciente_nombre} {args.paciente_apellido} almacenada con éxito en BigQuery ({project_id}.{dataset_id}.{table_id})!"

    except Exception as ex:
        logger.error(f"Error en herramienta registrar receta: {ex}")
        return f"Excepción en la herramienta: {str(ex)}"

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
import logging
import datetime
import time
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google import genai
from google.genai import types
from google.cloud import bigquery

# Cargar variables de entorno si existen
load_dotenv()

logger = logging.getLogger(__name__)

# Definición de esquemas con Pydantic para la salida estructurada de Gemini
class Medicamento(BaseModel):
    nombre: Optional[str] = Field(description="Nombre del medicamento prescrito")
    dosis: Optional[str] = Field(description="Dosis indicada (ej. 500mg, 1 tableta, 5ml)")
    frecuencia: Optional[str] = Field(description="Frecuencia de consumo (ej. cada 8 horas, 1 vez al día)")
    duracion: Optional[str] = Field(description="Duración del tratamiento (ej. por 5 días, 1 semana)")

class RecetaEstructurada(BaseModel):
    nombre_paciente: Optional[str] = Field(description="Nombre completo del paciente")
    nombre_medico: Optional[str] = Field(description="Nombre completo del médico que prescribe")
    id_medico: Optional[str] = Field(description="Número de colegiatura, cédula profesional o ID del médico")
    fecha: Optional[str] = Field(description="Fecha de la receta en formato YYYY-MM-DD")
    diagnostico: Optional[str] = Field(description="Diagnóstico o condición médica mencionada")
    clinicas_sugeridas: Optional[List[str]] = Field(description="Lista de 3 clínicas posibles inferidas según el historial de consultorios del doctor (ej. Clínica Internacional, Hospital Delgado, Centro Médico ABC)")
    medicamentos: Optional[List[Medicamento]] = Field(description="Lista de medicamentos recetados")
    notas_adicionales: Optional[str] = Field(description="Instrucciones generales o notas adicionales en la receta")


def procesar_y_guardar_receta(ruta_pdf: str) -> str:
    """
    Extrae los campos estructurados de una receta médica en formato PDF utilizando Gemini
    y guarda los datos extraídos en una tabla de BigQuery en el dataset especificado,
    siguiendo las buenas prácticas de ADK.

    Args:
        ruta_pdf (str): Ruta local absoluta o relativa al archivo PDF de la receta médica.

    Returns:
        str: Mensaje detallando el resultado de la extracción y el almacenamiento en BigQuery.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    dataset_id = "recetamedicas"
    table_id = "prescripciones"

    if not os.path.exists(ruta_pdf):
        return f"Error: El archivo PDF especificado no existe en la ruta: {ruta_pdf}"

    try:
        # Conectamos de forma segura corporativa con Gemini Enterprise Agent Platform utilizando ADC
        client = genai.Client(enterprise=True, project=project_id, location=location)

        # Leer el contenido binario del PDF para un procesamiento multimodal fidedigno
        with open(ruta_pdf, "rb") as f:
            pdf_bytes = f.read()

        pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        
        prompt_text = types.Part.from_text(
            text="""Analiza la receta médica adjunta (PDF/imagen).
Interpreta la caligrafía médica y abreviaturas estándar (ej. mg, ml, comp, VO, c/8h, qd) para extraer con precisión:
1. Nombre completo del paciente.
2. Nombre del médico y su colegiatura o cédula.
3. Fecha de expedición de la receta.
4. Diagnóstico o indicación general.
5. Inferencia clínica: A partir del médico, infiere y lista 3 clínicas prestigiosas posibles donde atienda este doctor (ej. Clínica Internacional, Hospital Delgado, Centro Médico ABC).
6. Lista de medicamentos recetados, desglosando: nombre del fármaco, dosis, frecuencia y duración.

Devuelve la información estrictamente estructurada bajo el esquema JSON solicitado."""
        )

        # Configurar la generación de contenido para forzar una salida estructurada (JSON Schema)
        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=RecetaEstructurada,
        )

        # Utilizar el modelo de razonamiento configurado en el entorno (.env)
        model_name = os.getenv("GEMINI_MODEL")
        
        response = client.models.generate_content(
            model=model_name,
            contents=[pdf_part, prompt_text],
            config=config
        )

        if not response.text:
            return "Error: No se recibió texto de respuesta por parte del modelo Gemini."

        # Parsear la respuesta validada por el esquema
        datos = json.loads(response.text)

        # Guardar la información extraída en BigQuery
        bq_client = bigquery.Client(project=project_id)
        
        # Verificar y crear el dataset si no existe
        dataset_ref = bq_client.dataset(dataset_id)
        try:
            bq_client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            bq_client.create_dataset(dataset, exists_ok=True)
            logger.info(f"Dataset {dataset_id} creado exitosamente en el proyecto {project_id}.")

        # Definir el esquema de la tabla en BigQuery
        esquema = [
            bigquery.SchemaField("nombre_paciente", "STRING", description="Nombre del paciente"),
            bigquery.SchemaField("nombre_medico", "STRING", description="Nombre del médico"),
            bigquery.SchemaField("id_medico", "STRING", description="ID o colegiatura del médico"),
            bigquery.SchemaField("fecha", "STRING", description="Fecha de la receta"),
            bigquery.SchemaField("diagnostico", "STRING", description="Diagnóstico médico"),
            bigquery.SchemaField("clinicas_sugeridas", "STRING", description="Clínicas sugeridas por IA"),
            bigquery.SchemaField("medicamentos", "RECORD", mode="REPEATED", description="Lista de medicamentos", fields=[
                bigquery.SchemaField("nombre", "STRING", description="Nombre del medicamento"),
                bigquery.SchemaField("dosis", "STRING", description="Dosis indicada"),
                bigquery.SchemaField("frecuencia", "STRING", description="Frecuencia de uso"),
                bigquery.SchemaField("duracion", "STRING", description="Duración del tratamiento"),
            ]),
            bigquery.SchemaField("notas_adicionales", "STRING", description="Instrucciones adicionales"),
            bigquery.SchemaField("fecha_extraccion", "TIMESTAMP", description="Fecha y hora de extracción"),
            bigquery.SchemaField("archivo_origen", "STRING", description="Nombre del archivo PDF procesado"),
        ]

        table_ref = dataset_ref.table(table_id)
        try:
            tbl = bq_client.get_table(table_ref)
            if len(tbl.schema) < len(esquema):
                tbl.schema = esquema
                bq_client.update_table(tbl, ["schema"])
                logger.info("Esquema de BigQuery actualizado con las nuevas columnas.")
                time.sleep(3)
        except Exception:
            table = bigquery.Table(table_ref, schema=esquema)
            bq_client.create_table(table, exists_ok=True)
            logger.info(f"Tabla {table_id} creada exitosamente en el dataset {dataset_id}. Esperando buffer...")
            time.sleep(4)

        # Preparar los registros anidados de medicamentos para BigQuery
        medicamentos_bq = []
        for med in datos.get("medicamentos", []):
            medicamentos_bq.append({
                "nombre": med.get("nombre", ""),
                "dosis": med.get("dosis", ""),
                "frecuencia": med.get("frecuencia", ""),
                "duracion": med.get("duracion", ""),
            })

        fila = {
            "nombre_paciente": datos.get("nombre_paciente", ""),
            "nombre_medico": datos.get("nombre_medico", ""),
            "id_medico": datos.get("id_medico", ""),
            "fecha": datos.get("fecha", ""),
            "diagnostico": datos.get("diagnostico", ""),
            "clinicas_sugeridas": ", ".join(datos.get("clinicas_sugeridas", [])),
            "medicamentos": medicamentos_bq,
            "notas_adicionales": datos.get("notas_adicionales", ""),
            "fecha_extraccion": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "archivo_origen": os.path.basename(ruta_pdf),
        }

        intento = 0
        max_intentos = 4
        errores = None
        while intento < max_intentos:
            try:
                errores = bq_client.insert_rows_json(table_ref, [fila])
                if not errores or not any("not found" in str(e).lower() for e in errores):
                    break
            except Exception as e:
                if "not found" in str(e).lower() and intento < max_intentos - 1:
                    logger.info(f"Esperando inicialización del buffer de streaming de BQ (intento {intento+1}/{max_intentos})...")
                    time.sleep(3)
                    intento += 1
                    continue
                raise e
            if errores and any("not found" in str(e).lower() for e in errores) and intento < max_intentos - 1:
                logger.info(f"Reintentando inserción por propagación de tabla en BQ (intento {intento+1}/{max_intentos})...")
                time.sleep(3)
                intento += 1
                continue
            break

        if errores:
            return f"Extracción exitosa pero falló la inserción en BigQuery: {errores}"

        nombre_paciente = datos.get("nombre_paciente", "Desconocido")
        return f"Receta procesada exitosamente. Datos extraídos del paciente '{nombre_paciente}' guardados en BigQuery ({project_id}.{dataset_id}.{table_id})."

    except Exception as e:
        logger.error(f"Error procesando la receta médica: {e}")
        return f"Error al procesar y guardar la receta médica: {str(e)}"

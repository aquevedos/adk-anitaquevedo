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
from concurrent.futures import ThreadPoolExecutor
from google import genai
from google.genai import types
from google.cloud import bigquery
import functions_framework

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_template(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "templates", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

LOGIN_HTML_SERVERLESS_TEMPLATE = load_template("login.html")
HTML_SERVERLESS_TEMPLATE = load_template("dashboard_serverless.html")

def extraer_sincrono_cloud(archivo_bytes, nombre_archivo, mime_type, prompt, model_name, project_id, location):
    """Función síncrona ejecutada en un hilo aislado del ThreadPoolExecutor para inferencia paralela."""
    client = genai.Client(enterprise=True, project=project_id, location=location)
    pdf_part = types.Part.from_bytes(data=archivo_bytes, mime_type=mime_type)
    res_gen = client.models.generate_content(
        model=model_name,
        contents=[pdf_part, prompt],
        config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")
    )
    if not res_gen.text:
        return {"archivo": nombre_archivo, "status": "error", "message": "El modelo Gemini no retornó datos."}
    datos = json.loads(res_gen.text)
    meds = datos.get("medicamentos", [])
    fila = {
        "numero_receta": str(datos.get("numero_receta", "")),
        "paciente_nombre": str(datos.get("paciente_nombre", "")),
        "paciente_apellido": str(datos.get("paciente_apellido", "")),
        "paciente_cedula": str(datos.get("paciente_cedula", "")),
        "medico_nombre": str(datos.get("medico_nombre", "")),
        "clinicas_inferidas": ", ".join(datos.get("clinicas_inferidas", [])),
        "medicamentos_detalle": json.dumps(meds),
        "fecha_registro": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "archivo_origen": nombre_archivo,
    }
    return {
        "archivo": nombre_archivo,
        "status": "success",
        "message": f"¡Fila insertada exitosamente en {project_id}.recetamedicas.prescripciones_cloud_run!",
        "data": {
            "paciente_nombre": fila["paciente_nombre"],
            "paciente_apellido": fila["paciente_apellido"],
            "paciente_cedula": fila["paciente_cedula"],
            "medico_nombre": fila["medico_nombre"],
            "numero_receta": fila["numero_receta"],
            "clinicas_inferidas_sugeridas": datos.get("clinicas_inferidas", []),
            "medicamentos": meds,
        },
        "fila_bq": fila
    }

@functions_framework.http
def procesar_receta_http(request):
    """
    Punto de entrada HTTP Serverless para Google Cloud Run Functions (2nd Gen).
    Atiende solicitudes GET devolviendo el portal web premium de Farmacias Arrocha.
    Atiende solicitudes POST ejecutando la extracción multimodal o comandos de gestión en BigQuery.
    """
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    session_token = request.cookies.get("session_token")

    if request.method == 'GET':
        headers_html = {'Content-Type': 'text/html; charset=utf-8', 'Access-Control-Allow-Origin': '*'}
        if session_token == "admin_session_token":
            return (HTML_SERVERLESS_TEMPLATE, 200, headers_html)
        return (LOGIN_HTML_SERVERLESS_TEMPLATE, 200, headers_html)

    if request.method != 'POST':
        return (json.dumps({"status": "error", "message": "Sólo se permite el método POST o GET."}), 405, headers)

    # Autenticación para peticiones POST
    if 'action' in request.form and request.form['action'] == 'login':
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin":
            headers_cookie = {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json',
                'Set-Cookie': 'session_token=admin_session_token; HttpOnly; Secure; SameSite=Lax; Path=/'
            }
            return (json.dumps({"status": "success", "message": "Inicio de sesión exitoso"}), 200, headers_cookie)
        else:
            return (json.dumps({"status": "error", "message": "Usuario o contraseña incorrectos"}), 401, headers)

    if 'action' in request.form and request.form['action'] == 'logout':
        headers_cookie = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
            'Set-Cookie': 'session_token=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0'
        }
        return (json.dumps({"status": "success", "message": "Sesión cerrada correctamente"}), 200, headers_cookie)

    # Validar sesión para el resto de peticiones POST
    if session_token != "admin_session_token":
        return (json.dumps({"status": "error", "message": "No autorizado. Inicie sesión."}), 401, headers)

    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "agentspace-demos-466121")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        dataset_id = "recetamedicas"
        table_id = "prescripciones_cloud_run"

        bq_client = bigquery.Client(project=project_id)

        # Verificar si es una petición de purga de tabla
        if 'action' in request.form and request.form['action'] == 'limpiar':
            query = f"DROP TABLE IF EXISTS `{project_id}.{dataset_id}.{table_id}`"
            bq_client.query(query).result()
            return (json.dumps({"status": "success", "message": f"Tabla {table_id} eliminada exitosamente en BQ."}), 200, headers)

        # Verificar si es una petición de confirmación de clínica
        if 'action' in request.form and request.form['action'] == 'confirmar':
            archivo_arc = request.form.get('archivo', 'Desconocido')
            clinica_sel = request.form.get('clinica', 'Desconocida')
            table_ref = bq_client.dataset(dataset_id).table(table_id)
            fila_audit = {
                "numero_receta": "AUDITORÍA",
                "paciente_nombre": "CONFIRMACIÓN CLÍNICA",
                "paciente_apellido": clinica_sel,
                "paciente_cedula": "VALIDADO",
                "medico_nombre": "USUARIO",
                "clinicas_inferidas": clinica_sel,
                "medicamentos_detalle": json.dumps([{"nombre": f"Clínica confirmada para: {archivo_arc}", "cantidad": 1}]),
                "fecha_registro": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "archivo_origen": archivo_arc,
            }
            bq_client.insert_rows_json(table_ref, [fila_audit])
            return (json.dumps({"status": "success", "message": f"Clínica '{clinica_sel}' confirmada exitosamente en BQ."}), 200, headers)

        # Procesamiento de lote de archivos (extracción multimodal)
        archivos = request.files.getlist('archivos') or request.files.getlist('archivo')
        if not archivos:
            return (json.dumps({"status": "error", "message": "No se encontraron archivos en la petición."}), 400, headers)

        client = genai.Client(enterprise=True, project=project_id, location=location)
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
            bigquery.SchemaField("archivo_origen", "STRING"),
        ]
        table_ref = dataset_ref.table(table_id)
        try:
            tbl = bq_client.get_table(table_ref)
        except Exception:
            table = bigquery.Table(table_ref, schema=esquema)
            bq_client.create_table(table, exists_ok=True)
            time.sleep(4)

        prompt = types.Part.from_text(
            text="""Eres un agente experto en Farmacias Arrocha. Analiza la receta médica adjunta.
Extrae con altísima precisión:
1. Datos del paciente (nombre, apellido, cédula).
2. Número de receta o folio.
3. Nombre del médico prescriptor.
4. Infiere y lista 3 clínicas prestigiosas posibles asociadas a este doctor (ej. Clínica Arrocha Central, Centro Médico ABC, Hospital Internacional).
5. Lista de medicamentos recetados (nombre, dosis, cantidad recetada, sugerencia de etiquetas para farmacia).

Devuelve un objeto JSON estructurado con estas claves:
- numero_receta (string)
- paciente_nombre (string)
- paciente_apellido (string)
- paciente_cedula (string)
- medico_nombre (string)
- clinicas_inferidas (array de strings)
- medicamentos (array de objetos con claves: nombre, dosis, cantidad_recetada, sugerencia_etiquetas)"""
        )

        tareas = []
        for archivo in archivos:
            archivo_bytes = archivo.read()
            nombre_archivo = archivo.filename or f"receta_{time.time()}.pdf"
            mime_type = "application/pdf" if nombre_archivo.lower().endswith(".pdf") else "image/jpeg"
            tareas.append((archivo_bytes, nombre_archivo, mime_type, prompt, model_name, project_id, location))

        # Procesar todas las extracciones simultáneamente usando un pool de hilos
        with ThreadPoolExecutor(max_workers=10) as executor:
            resultados_lote = list(executor.map(lambda args: extraer_sincrono_cloud(*args), tareas))

        # Extraer las filas para inserción masiva en BigQuery
        filas_bq = [r.pop("fila_bq") for r in resultados_lote if r.get("status") == "success" and "fila_bq" in r]

        if filas_bq:
            intento = 0
            errores = None
            while intento < 4:
                try:
                    errores = bq_client.insert_rows_json(table_ref, filas_bq)
                    if not errores or not any("not found" in str(e).lower() for e in errores):
                        break
                except Exception as e:
                    if "not found" in str(e).lower() and intento < 3:
                        logger.info(f"Esperando inicialización del buffer de streaming en BQ (intento {intento+1}/4)...")
                        time.sleep(4)
                        intento += 1
                        continue
                    raise e
                if errores and any("not found" in str(e).lower() for e in errores) and intento < 3:
                    logger.info(f"Reintentando inserción por retardo en metadatos BQ (intento {intento+1}/4)...")
                    time.sleep(4)
                    intento += 1
                    continue
                break

            if errores:
                logger.error(f"Error en inserción masiva BQ en Cloud Run: {errores}")
                for res in resultados_lote:
                    if res.get("status") == "success":
                        res["message"] = f"Extracción exitosa pero falló inserción BQ: {errores}"
                        res["status"] = "error"

        return (json.dumps(resultados_lote), 200, headers)

    except Exception as e:
        logger.error(f"Error en Cloud Run Function: {e}")
        return (json.dumps({"status": "error", "message": str(e)}), 500, headers)

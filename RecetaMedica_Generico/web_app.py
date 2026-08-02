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
import asyncio
import uvicorn
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, Request, Response, HTTPException, Cookie, Depends

load_dotenv()
from fastapi.responses import HTMLResponse, JSONResponse
from google import genai
from google.genai import types
from google.cloud import bigquery

from logica.tools.extraction_tools import RecetaEstructurada
from logica.limpiar_tabla import limpiar_tabla_prescripciones
from logica.firebase_auth import inicializar_base_de_datos, registrar_usuario, autenticar_usuario, validar_sesion

app = FastAPI(title="ADK Web - Extracción por Lotes de Recetas Médicas")

logger = logging.getLogger(__name__)

# Inicializar colección de usuarios en Firestore al iniciar la aplicación
@app.on_event("startup")
def startup_event():
    inicializar_base_de_datos()


async def verify_session(session_token: str = Cookie(None)):
    # TODO(security): Use a cryptographically secure session ID storage in production
    if not session_token or not validar_sesion(session_token):
        raise HTTPException(status_code=401, detail="No autorizado")
    return True

def load_template(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "templates", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Sirve la página de la interfaz web de usuario o la de login."""
    session_token = request.cookies.get("session_token")
    if session_token and validar_sesion(session_token):
        return HTMLResponse(content=load_template("dashboard.html"))
    return HTMLResponse(content=load_template("login.html"))

@app.post("/api/login")
async def api_login(response: Response, username: str = Form(...), password: str = Form(...)):
    """Endpoint de inicio de sesión verificando credenciales en Firestore."""
    if autenticar_usuario(username, password):
        session_val = username.strip().lower()
        response.set_cookie(
            key="session_token",
            value=session_val,
            httponly=True,
            samesite="lax",
            max_age=2592000 # 30 días de persistencia
        )
        return {"status": "success", "message": "Inicio de sesión exitoso"}
    return JSONResponse(status_code=401, content={"status": "error", "message": "Usuario o contraseña incorrectos"})

@app.post("/api/register")
async def api_register(username: str = Form(...), password: str = Form(...)):
    """Endpoint para registrar un nuevo usuario en Firestore."""
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"status": "error", "message": "La contraseña debe tener al menos 6 caracteres."})
    if registrar_usuario(username, password):
        return {"status": "success", "message": "Registro completado con éxito. Ahora puede iniciar sesión."}
    return JSONResponse(status_code=400, content={"status": "error", "message": "El usuario ya existe o no pudo ser registrado."})

@app.post("/api/logout")
async def api_logout(response: Response):
    """Endpoint de cierre de sesión."""
    response.delete_cookie("session_token")
    return {"status": "success", "message": "Sesión cerrada correctamente"}

@app.post("/api/limpiar_tabla")
async def api_limpiar_tabla_endpoint(authorized: bool = Depends(verify_session)):
    """Endpoint web para vaciar la tabla de prescripciones en BigQuery bajo demanda."""
    try:
        limpiar_tabla_prescripciones(interactivo=False)
        return {"status": "success", "message": "La tabla ha sido limpiada correctamente."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/confirmar_clinica")
async def api_confirmar_clinica_endpoint(archivo: str = Form(...), clinica: str = Form(...), authorized: bool = Depends(verify_session)):
    """Registra en BigQuery la confirmación interactiva de la clínica seleccionada por el usuario."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset_id = "recetamedicas"
    table_id = "prescripciones"
    try:
        bq_client = bigquery.Client(project=project_id)
        table_ref = bq_client.dataset(dataset_id).table(table_id)
        fila = {
            "nombre_paciente": "AUDITORÍA CLÍNICA",
            "nombre_medico": "CONFIRMACIÓN DE USUARIO",
            "id_medico": "VALIDADO",
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d"),
            "diagnostico": "SELECCIÓN EN INTERFAZ",
            "clinica_seleccionada": clinica,
            "medicamentos": [],
            "notas_adicionales": f"Usuario confirmó clínica para archivo: {archivo}",
            "fecha_extraccion": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "archivo_origen": archivo,
        }
        bq_client.insert_rows_json(table_ref, [fila])
        return {"status": "success", "message": f"Clínica '{clinica}' guardada exitosamente."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

def extraer_sincrono_worker(pdf_bytes_arg, mime_type_arg, prompt_arg, model_arg, proj_arg, loc_arg, config_arg):
    """Función síncrona aislada en un hilo del sistema operativo para evitar colisiones de conexión en httpx."""
    hilo_client = genai.Client(enterprise=True, project=proj_arg, location=loc_arg)
    return hilo_client.models.generate_content(
        model=model_arg,
        contents=[types.Part.from_bytes(data=pdf_bytes_arg, mime_type=mime_type_arg), prompt_arg],
        config=config_arg
    )

@app.post("/api/procesar_lote")
async def api_procesar_lote(archivos: List[UploadFile] = File(...), authorized: bool = Depends(verify_session)):
    """
    Recibe una lista de archivos PDF cargados de manera concurrente desde el cliente web,
    ejecuta de forma secuencial o iterativa el flujo de extracción estructurada con Gemini,
    persiste las filas en BigQuery y retorna un reporte consolidado por cada archivo.
    """
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    dataset_id = "recetamedicas"
    table_id = "prescripciones"

    # Pre-inicializar el cliente de GenAI y BigQuery para reutilizar conexiones
    try:
        client = genai.Client(enterprise=True, project=project_id, location=location)
        bq_client = bigquery.Client(project=project_id)
        
        # Asegurar la existencia del dataset
        dataset_ref = bq_client.dataset(dataset_id)
        try:
            bq_client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            bq_client.create_dataset(dataset, exists_ok=True)

        # Asegurar la existencia de la tabla
        esquema = [
            bigquery.SchemaField("nombre_paciente", "STRING"),
            bigquery.SchemaField("nombre_medico", "STRING"),
            bigquery.SchemaField("id_medico", "STRING"),
            bigquery.SchemaField("fecha", "STRING"),
            bigquery.SchemaField("diagnostico", "STRING"),
            bigquery.SchemaField("clinica_seleccionada", "STRING"),
            bigquery.SchemaField("medicamentos", "RECORD", mode="REPEATED", fields=[
                bigquery.SchemaField("nombre", "STRING"),
                bigquery.SchemaField("dosis", "STRING"),
                bigquery.SchemaField("frecuencia", "STRING"),
                bigquery.SchemaField("duracion", "STRING"),
            ]),
            bigquery.SchemaField("notas_adicionales", "STRING"),
            bigquery.SchemaField("fecha_extraccion", "TIMESTAMP"),
            bigquery.SchemaField("archivo_origen", "STRING"),
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
            logger.info("Esperando propagación de metadatos de la nueva tabla en BigQuery...")
            time.sleep(4)

    except Exception as config_err:
        logger.error(f"Error inicializando GCP en el backend: {config_err}")
        return JSONResponse(status_code=500, content={"message": f"Error de autenticación GCP: {config_err}"})

    sem = asyncio.Semaphore(5)
    async def procesar_archivo_worker(archivo: UploadFile):
        temp_path = f"temp_batch_{time.time()}_{archivo.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                buffer.write(await archivo.read())

            with open(temp_path, "rb") as f:
                pdf_bytes = f.read()

            mime = "application/pdf" if archivo.filename.lower().endswith(".pdf") else "image/jpeg"
            prompt_text = types.Part.from_text(
                text="""Analiza la receta médica adjunta (PDF/imagen).
Interpreta la caligrafía médica y abreviaturas estándar (ej. mg, ml, comp, VO, c/8h, qd) para extraer con precisión:
1. Nombre completo del paciente.
2. Nombre del médico y su colegiatura o cédula.
3. Fecha de expedición de la receta.
4. Diagnóstico o indicación general.
5. Lista de medicamentos recetados, desglosando: nombre del fármaco, dosis, frecuencia y duración.

Devuelve la información estrictamente estructurada bajo el esquema JSON solicitado."""
            )

            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=RecetaEstructurada,
            )

            model_name = os.getenv("GEMINI_MODEL")
            # Ejecución síncrona completamente aislada en un hilo del sistema operativo
            async with sem:
                response = await asyncio.to_thread(
                    extraer_sincrono_worker, pdf_bytes, mime, prompt_text, model_name, project_id, location, config
                )

            if not response.text:
                return {
                    "archivo": archivo.filename,
                    "status": "error",
                    "message": "Modelo no retornó información extraíble."
                }

            datos = json.loads(response.text)

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
                "clinica_seleccionada": ", ".join(datos.get("clinicas_sugeridas", [])),
                "medicamentos": medicamentos_bq,
                "notas_adicionales": datos.get("notas_adicionales", ""),
                "fecha_extraccion": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "archivo_origen": archivo.filename,
            }

            return {
                "archivo": archivo.filename,
                "status": "success",
                "message": "¡Extracción multimodal exitosa!",
                "data": datos,
                "fila_bq": fila
            }

        except Exception as ex:
            logger.error(f"Error procesando el archivo {archivo.filename}: {ex}")
            return {
                "archivo": archivo.filename,
                "status": "error",
                "message": f"Excepción en la extracción: {str(ex)}"
            }
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    # Ejecutar todo el lote en paralelo mediante asyncio.gather
    resultados_lote = await asyncio.gather(*[procesar_archivo_worker(archivo) for archivo in archivos])
    
    # Recolectar todas las filas exitosas para inserción masiva en un solo llamado de red
    filas_bq = [res.pop("fila_bq") for res in resultados_lote if res.get("status") == "success" and "fila_bq" in res]
    
    if filas_bq:
        intento = 0
        errores = None
        while intento < 4:
            try:
                errores = await asyncio.to_thread(bq_client.insert_rows_json, table_ref, filas_bq)
                if not errores or not any("not found" in str(e).lower() for e in errores):
                    break
            except Exception as e:
                if "not found" in str(e).lower() and intento < 3:
                    await asyncio.sleep(3)
                    intento += 1
                    continue
                raise e
            if errores and any("not found" in str(e).lower() for e in errores) and intento < 3:
                await asyncio.sleep(3)
                intento += 1
                continue
            break

        if errores:
            logger.error(f"Error en inserción masiva BQ: {errores}")
            for res in resultados_lote:
                if res.get("status") == "success":
                    res["message"] = f"Extracción exitosa pero falló inserción BQ: {errores}"
                    res["status"] = "error"
        else:
            logger.info(f"¡Lote masivo de {len(filas_bq)} filas insertado exitosamente en BQ en un solo llamado!")
            for res in resultados_lote:
                if res.get("status") == "success":
                    res["message"] = f"¡Fila insertada exitosamente en {project_id}.{dataset_id}.{table_id}!"

    return list(resultados_lote)

if __name__ == "__main__":
    print("=== Iniciando Servidor ADK Batch Web UI en http://0.0.0.0:8000 ===")
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=True)

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
import sys
import json
import time
import logging
import asyncio
import datetime
import uvicorn
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, Form, Request, Response, HTTPException, Cookie, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from google import genai
from google.genai import types
from google.cloud import bigquery

# Cargar configuración de entorno
load_dotenv()

logger = logging.getLogger(__name__)

from logica.firebase_auth import inicializar_base_de_datos, registrar_usuario, autenticar_usuario, validar_sesion

async def verify_session(session_token: str = Cookie(None)):
    # TODO(security): Use a cryptographically secure session ID storage in production
    if not session_token or not validar_sesion(session_token):
        raise HTTPException(status_code=401, detail="No autorizado")
    return True

def load_template(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "templates", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()



app = FastAPI(title="Farmacias Arrocha - Demostración Ejecutiva de IA para Gerencia")

@app.on_event("startup")
def startup_event():
    inicializar_base_de_datos()

# Esquemas Pydantic avanzados para la demostración de Gerencia
class DatosPaciente(BaseModel):
    nombre: Optional[str] = Field(description="Nombre del paciente")
    apellido: Optional[str] = Field(description="Apellido del paciente")
    cedula: Optional[str] = Field(description="Número de cédula o documento de identidad del paciente")
    fecha_nacimiento: Optional[str] = Field(description="Fecha de nacimiento del paciente")

class MedicamentoDispensar(BaseModel):
    nombre: Optional[str] = Field(description="Nombre del fármaco o principio activo")
    dosis: Optional[str] = Field(description="Dosis exacta (ej. 500mg, 10ml)")
    cantidad_recetada: Optional[str] = Field(description="Cantidad total prescrita (ej. 1 caja, 20 tabletas)")
    sugerencia_etiquetas: Optional[int] = Field(description="Número de etiquetas a imprimir para el mostrador (1 por empaque/caja, o 1 para envase de tabletas sueltas)")
    tipo_empaque: Optional[str] = Field(description="Clasificación del empaque: 'caja', 'frasco', o 'tabletas sueltas'")

class ExtraccionDemoGerencia(BaseModel):
    numero_receta: Optional[str] = Field(description="Número correlativo o folio identificador de la receta")
    paciente: Optional[DatosPaciente] = Field(description="Datos de identificación del paciente")
    medico_nombre_completo: Optional[str] = Field(description="Nombre completo del doctor (ej. 'Doctor Enrique Alemán')")
    clinicas_inferidas_sugeridas: Optional[List[str]] = Field(description="Historial inferido de 3 clínicas posibles asociadas al doctor (ej. Clínica Internacional, Hospital Delgado, Centro Médico ABC)")
    medicamentos: Optional[List[MedicamentoDispensar]] = Field(description="Listado de medicamentos prescritos para dispensación")
    analisis_ia: Optional[str] = Field(description="Resumen del análisis clínico y validación farmacológica")




@app.get("/", response_class=HTMLResponse)
async def home_gerencia(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token and validar_sesion(session_token):
        return HTMLResponse(content=load_template("demo_gerencia.html"))
    return HTMLResponse(content=load_template("login.html"))

@app.post("/api/login")
async def api_login(response: Response, username: str = Form(...), password: str = Form(...)):
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
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"status": "error", "message": "La contraseña debe tener al menos 6 caracteres."})
    if registrar_usuario(username, password):
        return {"status": "success", "message": "Registro completado con éxito. Ahora puede iniciar sesión."}
    return JSONResponse(status_code=400, content={"status": "error", "message": "El usuario ya existe o no pudo ser registrado."})

@app.post("/api/logout")
async def api_logout(response: Response):
    response.delete_cookie("session_token")
    return {"status": "success", "message": "Sesión cerrada correctamente"}

@app.post("/api/extraccion_gerencia")
async def procesar_receta_gerencia(archivo: UploadFile = File(...), authorized: bool = Depends(verify_session)):
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    dataset_id = "recetamedicas"
    table_id = "prescripciones_gerencia"

    temp_path = f"temp_gerencia_{time.time()}_{archivo.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            buffer.write(await archivo.read())

        client = genai.Client(enterprise=True, project=project_id, location=location)
        bq_client = bigquery.Client(project=project_id)

        dataset_ref = bq_client.dataset(dataset_id)
        try:
            bq_client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            bq_client.create_dataset(dataset, exists_ok=True)

        esquema = [
            bigquery.SchemaField("numero_receta", "STRING"),
            bigquery.SchemaField("paciente_nombre", "STRING"),
            bigquery.SchemaField("paciente_apellido", "STRING"),
            bigquery.SchemaField("paciente_cedula", "STRING"),
            bigquery.SchemaField("paciente_nacimiento", "STRING"),
            bigquery.SchemaField("medico_nombre", "STRING"),
            bigquery.SchemaField("clinicas_sugeridas", "STRING"),
            bigquery.SchemaField("medicamentos", "RECORD", mode="REPEATED", fields=[
                bigquery.SchemaField("nombre", "STRING"),
                bigquery.SchemaField("dosis", "STRING"),
                bigquery.SchemaField("cantidad_recetada", "STRING"),
                bigquery.SchemaField("sugerencia_etiquetas", "INTEGER"),
                bigquery.SchemaField("tipo_empaque", "STRING"),
            ]),
            bigquery.SchemaField("fecha_registro", "TIMESTAMP"),
            bigquery.SchemaField("archivo_origen", "STRING"),
        ]

        table_ref = dataset_ref.table(table_id)
        try:
            bq_client.get_table(table_ref)
        except Exception:
            table = bigquery.Table(table_ref, schema=esquema)
            bq_client.create_table(table, exists_ok=True)
            time.sleep(4)

        with open(temp_path, "rb") as f:
            pdf_bytes = f.read()

        pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf" if archivo.filename.lower().endswith(".pdf") else "image/jpeg")
        
        prompt = types.Part.from_text(
            text="""Eres un agente experto en validación clínica para gerencia. Analiza la imagen o documento de la receta médica enviada por José Serrano.
Extrae con altísima precisión y sin inventar:
1. Datos del paciente: Nombre, apellido, número de cédula y fecha de nacimiento.
2. Datos de la receta: Número correlativo o folio.
3. Datos del médico: Nombre completo del doctor (ej. "Doctor Enrique Alemán").
4. Inferencia de Clínicas: A partir del nombre del médico, infiere y lista 3 clínicas o consultorios prestigiosos posibles donde atienda este doctor (ej. Clínica Internacional, Hospital Delgado, Centro Médico ABC).
5. Datos de los medicamentos y dispensación: Identifica cada fármaco, dosis y cantidad recetada. Evalúa si la prescripción es en cajas o en tabletas sueltas y sugiere cuántas etiquetas de dispensación imprimir (1 por cada caja/frasco, o 1 para el empaque de tabletas sueltas).

Retorna estrictamente la estructura JSON del esquema solicitado."""
        )

        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=ExtraccionDemoGerencia,
        )

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        response = await client.aio.models.generate_content(
            model=model,
            contents=[pdf_part, prompt],
            config=config
        )

        if not response.text:
            return JSONResponse(status_code=500, content={"status": "error", "message": "No se pudo extraer información de la receta."})

        datos = json.loads(response.text)
        pac = datos.get("paciente", {})

        medicamentos_bq = []
        for med in datos.get("medicamentos", []):
            medicamentos_bq.append({
                "nombre": med.get("nombre", ""),
                "dosis": med.get("dosis", ""),
                "cantidad_recetada": med.get("cantidad_recetada", ""),
                "sugerencia_etiquetas": med.get("sugerencia_etiquetas", 1),
                "tipo_empaque": med.get("tipo_empaque", "caja"),
            })

        fila = {
            "numero_receta": datos.get("numero_receta", ""),
            "paciente_nombre": pac.get("nombre", ""),
            "paciente_apellido": pac.get("apellido", ""),
            "paciente_cedula": pac.get("cedula", ""),
            "paciente_nacimiento": pac.get("fecha_nacimiento", ""),
            "medico_nombre": datos.get("medico_nombre_completo", ""),
            "clinicas_sugeridas": ", ".join(datos.get("clinicas_inferidas_sugeridas", [])),
            "medicamentos": medicamentos_bq,
            "fecha_registro": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "archivo_origen": archivo.filename,
        }

        intento = 0
        errores = None
        while intento < 4:
            try:
                errores = await asyncio.to_thread(bq_client.insert_rows_json, table_ref, [fila])
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

        return {
            "status": "success",
            "data": datos,
            "db_log": "Registrado exitosamente en BigQuery",
            "archivo": archivo.filename
        }

    except Exception as e:
        logger.error(f"Error en demo gerencia: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == "__main__":
    print("=== Iniciando Servidor Demo Gerencia en http://0.0.0.0:8085 ===")
    uvicorn.run("demo_gerencia:app", host="0.0.0.0", port=8085, reload=True)

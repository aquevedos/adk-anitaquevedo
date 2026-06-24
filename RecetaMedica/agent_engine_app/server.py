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
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from google import genai
from google.genai import types

from agent import agente_receta_engine
from tools.receta_tools import RegistrarRecetaArgs, herramienta_registrar_receta_bq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Engine Service - Farmacias Arrocha")

@app.post("/query")
async def agent_engine_query(request: Request):
    """
    Endpoint estándar de Agent Engine para invocar al agente desde Gemini Enterprise.
    """
    data = await request.json()
    prompt = data.get("query", "") or data.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="El campo 'query' es requerido.")
    
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "agentspace-demos-466121")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(enterprise=True, project=project_id, location=location)
        
        response = client.models.generate_content(
            model=agente_receta_engine.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        return JSONResponse(content={"status": "success", "response": response.text})
    
    except Exception as e:
        logger.error(f"Error en Agent Engine Query: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/extract_image")
async def agent_engine_extract(archivo: UploadFile = File(...)):
    """
    Endpoint auxiliar de Agent Engine para procesar imágenes y llamar a la herramienta de BQ.
    """
    bytes_data = await archivo.read()
    mime = "application/pdf" if archivo.filename.lower().endswith(".pdf") else "image/jpeg"
    
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "agentspace-demos-466121")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        client = genai.Client(enterprise=True, project=project_id, location=location)
        
        pdf_part = types.Part.from_bytes(data=bytes_data, mime_type=mime)
        prompt_part = types.Part.from_text(text=agente_receta_engine.instruction)
        
        res_gen = client.models.generate_content(
            model=agente_receta_engine.model,
            contents=[pdf_part, prompt_part],
            config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")
        )
        
        if not res_gen.text:
            raise Exception("No se obtuvo texto del modelo.")
        
        datos = json.loads(res_gen.text)
        
        # Formatear e invocar la herramienta nativa de registro
        args = RegistrarRecetaArgs(
            numero_receta=str(datos.get("numero_receta", f"ARC-{time.time() or '01'}")),
            paciente_nombre=str(datos.get("paciente_nombre", "Desconocido")),
            paciente_apellido=str(datos.get("paciente_apellido", "")),
            paciente_cedula=str(datos.get("paciente_cedula", "N/A")),
            medico_nombre=str(datos.get("medico_nombre", "Doctor Arrocha")),
            clinicas_inferidas=datos.get("clinicas_inferidas", ["Clínica Arrocha Central"]),
            medicamentos=[]
        )
        
        resultado_tool = herramienta_registrar_receta_bq(args)
        
        return JSONResponse(content={
            "status": "success",
            "extraction": datos,
            "tool_execution": resultado_tool,
            "agent": agente_receta_engine.name
        })
        
    except Exception as e:
        logger.error(f"Error en Agent Engine Extract: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

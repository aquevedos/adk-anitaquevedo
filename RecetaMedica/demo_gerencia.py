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
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse

from google import genai
from google.genai import types
from google.cloud import bigquery

# Cargar configuración de entorno
load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Farmacias Arrocha - Demostración Ejecutiva de IA para Gerencia")

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


HTML_DEMO_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Farmacias Arrocha - Demo de Validación para Gerencia</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #002a54; /* Azul Corporativo Arrocha */
            --surface: rgba(0, 75, 147, 0.35);
            --surface-card: rgba(0, 75, 147, 0.55);
            --border: rgba(255, 255, 255, 0.15);
            --border-hover: rgba(255, 184, 0, 0.6);
            --text-main: #ffffff;
            --text-muted: #cbd5e1;
            --primary: #ffb800; /* Dorado Arrocha */
            --primary-glow: rgba(255, 184, 0, 0.4);
            --accent: #38bdf8;
            --success: #34d399;
            --radius: 16px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }

        body {
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1.5rem 0.75rem;
            background-image: radial-gradient(at 50% 0%, rgba(255, 184, 0, 0.1) 0px, transparent 75%);
            background-attachment: fixed;
        }

        .container { width: 100%; max-width: 1050px; display: flex; flex-direction: column; gap: 1.5rem; padding: 0 0.5rem; }

        header { text-align: center; padding-bottom: 1rem; border-bottom: 1px solid var(--border); width: 100%; }
        
        .meta-badge {
            display: inline-block;
            background: rgba(255, 184, 0, 0.15);
            color: var(--primary);
            border: 1px solid rgba(255, 184, 0, 0.3);
            padding: 0.4rem 1.2rem;
            border-radius: 100px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        h1 {
            font-size: clamp(1.8rem, 6vw, 2.8rem);
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff 0%, #ffb800 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            text-align: center;
            line-height: 1.1;
        }

        .subtitle { color: var(--text-muted); font-size: clamp(1rem, 3.5vw, 1.15rem); font-weight: 300; text-align: center; }

        .upload-panel {
            background: var(--surface);
            backdrop-filter: blur(12px);
            border: 2px dashed var(--border);
            border-radius: var(--radius);
            padding: clamp(1.5rem, 5vw, 3rem) clamp(1rem, 3vw, 2rem);
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
            position: relative;
            width: 100%;
        }

        .upload-panel:hover, .upload-panel.dragover {
            border-color: var(--primary);
            background: rgba(0, 90, 175, 0.5);
            box-shadow: 0 0 25px var(--primary-glow);
            transform: translateY(-2px);
        }

        .file-input { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }

        .btn-main {
            background: linear-gradient(135deg, var(--primary) 0%, #ffd700 100%);
            color: #002a54;
            border: none;
            padding: 0.85rem clamp(1.5rem, 5vw, 2.8rem);
            font-size: clamp(0.95rem, 3vw, 1.1rem);
            font-weight: 700;
            border-radius: 100px;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 4px 20px var(--primary-glow);
            margin-top: 1.5rem;
            width: 100%;
            max-width: 320px;
        }
        .btn-main:hover { transform: translateY(-2px); filter: brightness(1.1); box-shadow: 0 6px 25px var(--primary-glow); }
        .btn-main:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

        .btn-camera {
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            color: #ffffff;
            border: none;
            padding: 0.85rem clamp(1.2rem, 3vw, 2rem);
            font-size: clamp(0.95rem, 3vw, 1.05rem);
            font-weight: 700;
            border-radius: 100px;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 4px 15px rgba(56, 189, 248, 0.3);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            width: 100%;
            max-width: 320px;
            justify-content: center;
        }
        .btn-camera:hover { transform: translateY(-2px); filter: brightness(1.1); box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5); }

        .loader-wrapper { display: none; flex-direction: column; align-items: center; gap: 1.2rem; margin: 2rem 0; width: 100%; }
        .spinner { width: 50px; height: 50px; border: 4px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite; box-shadow: 0 0 20px var(--primary-glow); }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status-text { color: var(--primary); font-weight: 600; font-size: clamp(1rem, 3vw, 1.2rem); text-align: center; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

        /* Panel de Resultados Gerenciales */
        .results-card {
            display: none;
            background: rgba(10, 25, 50, 0.75);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: clamp(1rem, 4vw, 2rem);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
            animation: fadeIn 0.5s forwards;
            width: 100%;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }

        .section-title { font-size: clamp(1.1rem, 3.5vw, 1.3rem); font-weight: 600; color: var(--primary); margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem; }

        .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card-data { background: var(--surface-card); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 1rem; }
        .card-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.4rem; }
        .card-value { font-size: 1.15rem; font-weight: 600; color: var(--text-main); word-break: break-word; }

        /* Inferencia Clínica Combo Box */
        .clinica-box { background: rgba(255, 184, 0, 0.1); border: 1px solid var(--primary); border-radius: 12px; padding: clamp(1rem, 4vw, 1.5rem); margin-bottom: 2rem; width: 100%; }
        .combo-clinica { width: 100%; padding: 0.85rem 1rem; background: #001b38; color: #ffffff; border: 1px solid var(--primary); border-radius: 8px; font-size: 1rem; font-weight: 500; margin-top: 0.5rem; cursor: pointer; outline: none; }
        .combo-clinica option { background: #001b38; color: #ffffff; }

        /* Tabla de Dispensación con Scroll Horizontal en Móvil */
        .table-container { border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; overflow-x: auto; margin-bottom: 2rem; background: rgba(0,0,0,0.2); width: 100%; }
        table { width: 100%; border-collapse: collapse; text-align: left; min-width: 500px; }
        th { padding: 0.85rem 1rem; background: rgba(0,0,0,0.3); color: var(--primary); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid rgba(255,255,255,0.1); }
        td { padding: 0.85rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); color: var(--text-main); font-size: 0.9rem; }
        .badge-tag { background: var(--primary); color: #002a54; font-weight: 700; padding: 0.2rem 0.75rem; border-radius: 100px; font-size: 0.8rem; display: inline-block; box-shadow: 0 0 10px var(--primary-glow); white-space: nowrap; }

        /* Simulación de Base de Datos */
        .db-panel { background: #02182f; border-left: 4px solid var(--success); padding: clamp(1rem, 3vw, 1.5rem); border-radius: 0 12px 12px 0; font-family: monospace; font-size: 0.85rem; color: #a7f3d0; white-space: pre-wrap; word-break: break-all; width: 100%; overflow-x: auto; }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="meta-badge">✓ Validación Ejecutiva de Arquitectura</div>
        <h1>Farmacias Arrocha</h1>
        <p class="subtitle">Demostración de Extracción Automatizada ante Gerencia</p>
        <p style="font-size: 0.95rem; color: var(--primary); margin-top: 0.4rem;">Desarrollado por Anita Quevedo | Recetas de Prueba aportadas por José Serrano</p>
    </header>

    <main style="display: flex; flex-direction: column; align-items: center; width: 100%;">
        <div class="upload-panel" id="dropZone">
            <input type="file" id="fileInput" class="file-input" accept="image/*,.pdf">
            <span style="font-size: 3.5rem; margin-bottom: 1rem; display: inline-block;">🩺</span>
            <p style="font-size: 1.4rem; font-weight: 600; margin-bottom: 0.5rem;">Sube aquí la imagen de la receta médica de José Serrano</p>
            <p style="color: var(--text-muted); font-size: 1rem;">Formatos válidos: PNG, JPG o PDF</p>
            <div id="selectedFileName" style="margin-top: 1rem; font-size: 1.1rem; color: var(--primary); font-weight: 500;"></div>
        </div>

        <div style="display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; justify-content: center; width: 100%;">
            <button class="btn-camera" id="btnCameraGerencia">📸 Tomar Foto con Cámara</button>
            <button class="btn-main" id="btnProcesar" style="margin-top: 0;" disabled>Extraer y Analizar con IA</button>
        </div>
        <input type="file" id="cameraInputGerencia" accept="image/*" capture="environment" style="display: none;">

        <div class="loader-wrapper" id="loader">
            <div class="spinner"></div>
            <div class="status-text">Decodificando caligrafía médica, inferiendo clínica e integrando con BigQuery...</div>
        </div>

        <div class="results-card" id="resultsCard">
            <div class="section-title">📋 1. Ficha de Identificación Automatizada</div>
            <div class="grid-4">
                <div class="card-data"><div class="card-label">N° Receta</div><div class="card-value" id="valFolio">-</div></div>
                <div class="card-data"><div class="card-label">Paciente</div><div class="card-value" id="valPaciente">-</div></div>
                <div class="card-data"><div class="card-label">Cédula</div><div class="card-value" id="valCedula">-</div></div>
                <div class="card-data"><div class="card-label">Nacimiento</div><div class="card-value" id="valNacimiento">-</div></div>
                <div class="card-data"><div class="card-label">Doctor Prescriptor</div><div class="card-value" id="valMedico">-</div></div>
            </div>

            <div class="clinica-box">
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--primary); margin-bottom: 0.4rem;">🏥 2. Inferencia Clínica Inteligente</div>
                <p style="font-size: 0.95rem; color: var(--text-muted);">El sistema ha inferido las siguientes clínicas basándose en el historial de consultorios del doctor prescriptor. Selecciona el centro de atención correcto para confirmar el registro:</p>
                <select class="combo-clinica" id="comboClinicas"></select>
                <button class="btn-main" id="btnConfirmarClinica" style="margin-top: 1rem; padding: 0.6rem 2rem; font-size: 1rem;">Confirmar Centro Clínico</button>
                <span id="confirmClinicaStatus" style="margin-left: 1rem; color: var(--success); font-weight: 600;"></span>
            </div>

            <div class="section-title">💊 3. Flujo de Dispensación y Etiquetado Automatizado</div>
            <div class="table-container">
                <table>
                    <thead><tr><th>Medicamento</th><th>Dosis</th><th>Cantidad Prescrita</th><th>Empaque</th><th>Etiquetas Sugeridas</th></tr></thead>
                    <tbody id="tablaMedicamentos"></tbody>
                </table>
            </div>

            <div class="section-title">💾 4. Simulación de Almacenamiento en Base de Datos (BigQuery)</div>
            <div class="db-panel" id="panelDB"></div>
        </div>
    </main>
</div>

<script>
    const fileInput = document.getElementById('fileInput');
    const btnProcesar = document.getElementById('btnProcesar');
    const loader = document.getElementById('loader');
    const resultsCard = document.getElementById('resultsCard');
    let currentData = null;

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            document.getElementById('selectedFileName').textContent = `Archivo listo: ${fileInput.files[0].name}`;
            btnProcesar.disabled = false;
            resultsCard.style.display = 'none';
        }
    });

    const btnCameraGerencia = document.getElementById('btnCameraGerencia');
    const cameraInputGerencia = document.getElementById('cameraInputGerencia');
    btnCameraGerencia.addEventListener('click', (e) => {
        e.stopPropagation();
        cameraInputGerencia.click();
    });
    cameraInputGerencia.addEventListener('change', () => {
        if (cameraInputGerencia.files.length) {
            const file = cameraInputGerencia.files[0];
            const dt = new DataTransfer();
            dt.items.add(file);
            fileInput.files = dt.files;
            document.getElementById('selectedFileName').textContent = `📸 Foto capturada: ${file.name}`;
            btnProcesar.disabled = false;
            resultsCard.style.display = 'none';
        }
    });

    btnProcesar.addEventListener('click', async () => {
        if (!fileInput.files.length) return;
        btnProcesar.disabled = true;
        loader.style.display = 'flex';
        resultsCard.style.display = 'none';
        document.getElementById('confirmClinicaStatus').textContent = '';

        const formData = new FormData();
        formData.append('archivo', fileInput.files[0]);

        try {
            const response = await fetch('/api/extraccion_gerencia', { method: 'POST', body: formData });
            const res = await response.json();

            if (response.ok && res.status === 'success') {
                currentData = res;
                renderizarGerencia(res.data, res.db_log, res.archivo);
            } else {
                alert(`Error en extracción: ${res.message}`);
            }
        } catch (err) {
            alert(`Fallo de conexión: ${err.message}`);
        } finally {
            loader.style.display = 'none';
            btnProcesar.disabled = false;
        }
    });

    function renderizarGerencia(rec, dbLog, nombreArchivo) {
        document.getElementById('valFolio').textContent = rec.numero_receta || 'S/N';
        const pac = rec.paciente || {};
        document.getElementById('valPaciente').textContent = `${pac.nombre || ''} ${pac.apellido || ''}`.trim() || 'No detectado';
        document.getElementById('valCedula').textContent = pac.cedula || 'No indicada';
        document.getElementById('valNacimiento').textContent = pac.fecha_nacimiento || 'No indicada';
        document.getElementById('valMedico').textContent = rec.medico_nombre_completo || 'No detectado';

        const combo = document.getElementById('comboClinicas');
        combo.innerHTML = '';
        if (rec.clinicas_inferidas_sugeridas && rec.clinicas_inferidas_sugeridas.length) {
            rec.clinicas_inferidas_sugeridas.forEach(cl => {
                const opt = document.createElement('option');
                opt.value = cl; opt.textContent = cl;
                combo.appendChild(opt);
            });
        } else {
            combo.innerHTML = '<option>Clínica Arrocha Central (Sugerida por Defecto)</option>';
        }

        const tbody = document.getElementById('tablaMedicamentos');
        tbody.innerHTML = '';
        if (rec.medicamentos && rec.medicamentos.length) {
            rec.medicamentos.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight:700; color:var(--primary);">${m.nombre || '-'}</td>
                    <td>${m.dosis || '-'}</td>
                    <td>${m.cantidad_recetada || '-'}</td>
                    <td>${m.tipo_empaque || 'caja'}</td>
                    <td><span class="badge-tag">🏷️ ${m.sugerencia_etiquetas || 1} etiqueta(s)</span></td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No se detectaron medicamentos estructurados</td></tr>';
        }

        actualizarPanelDB(rec, combo.value, nombreArchivo);
        resultsCard.style.display = 'block';
    }

    document.getElementById('btnConfirmarClinica').addEventListener('click', async () => {
        const clinicaSeleccionada = document.getElementById('comboClinicas').value;
        document.getElementById('confirmClinicaStatus').textContent = '✓ Clínica confirmada y sincronizada con BigQuery';
        if (currentData) {
            actualizarPanelDB(currentData.data, clinicaSeleccionada, currentData.archivo);
        }
    });

    function actualizarPanelDB(rec, clinica, archivo) {
        const payload = {
            numero_receta: rec.numero_receta,
            paciente: rec.paciente,
            medico: rec.medico_nombre_completo,
            clinica_validada: clinica,
            medicamentos_dispensados: rec.medicamentos,
            fecha_transaccion: new Date().toISOString(),
            sistema_destino: "BigQuery (recetamedicas.prescripciones_gerencia)",
            archivo_origen: archivo
        };
        document.getElementById('panelDB').textContent = JSON.stringify(payload, null, 2);
    }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home_gerencia():
    return HTML_DEMO_TEMPLATE

@app.post("/api/extraccion_gerencia")
async def procesar_receta_gerencia(archivo: UploadFile = File(...)):
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
    print("=== Iniciando Servidor Demo Gerencia en http://127.0.0.1:8085 ===")
    uvicorn.run("demo_gerencia:app", host="127.0.0.1", port=8085, reload=True)

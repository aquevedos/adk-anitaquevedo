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
from fastapi import FastAPI, UploadFile, File, Form

load_dotenv()
from fastapi.responses import HTMLResponse, JSONResponse
from google import genai
from google.genai import types
from google.cloud import bigquery

from tools.extraction_tools import RecetaEstructurada
from limpiar_tabla import limpiar_tabla_prescripciones

app = FastAPI(title="ADK Web - Extracción por Lotes de Recetas Médicas")

logger = logging.getLogger(__name__)

# Interfaz HTML con diseño moderno y procesamiento por lotes (Rich Aesthetics, Glassmorphism, Google Fonts, Dark Mode premium)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADK Portal - Extracción Inteligente por Lotes</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #002a54;
            --surface: rgba(0, 75, 147, 0.3);
            --surface-card: rgba(0, 75, 147, 0.45);
            --border: rgba(255, 255, 255, 0.15);
            --border-hover: rgba(255, 184, 0, 0.6);
            --text-main: #ffffff;
            --text-muted: #cbd5e1;
            --primary: #ffb800;
            --primary-glow: rgba(255, 184, 0, 0.35);
            --accent: #38bdf8;
            --success: #34d399;
            --radius: 16px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem 1rem;
            overflow-x: hidden;
            background-image: 
                radial-gradient(at 10% 10%, rgba(45, 212, 191, 0.1) 0px, transparent 50%),
                radial-gradient(at 90% 90%, rgba(56, 189, 248, 0.1) 0px, transparent 50%);
            background-attachment: fixed;
        }

        .container {
            width: 100%;
            max-width: 1050px;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        header {
            text-align: center;
            margin-bottom: 1rem;
        }

        h1 {
            font-size: 2.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff 0%, #ffb800 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.03em;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 1.1rem;
            font-weight: 300;
        }

        /* Glassmorphism Upload Area */
        .upload-panel {
            background: var(--surface);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 2px dashed var(--border);
            border-radius: var(--radius);
            padding: 3rem 2rem;
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
            width: 100%;
        }

        .upload-panel:hover, .upload-panel.dragover {
            border-color: var(--primary);
            background: rgba(20, 29, 49, 0.85);
            box-shadow: 0 0 25px var(--primary-glow);
            transform: translateY(-2px);
        }

        .upload-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            display: inline-block;
            transition: var(--transition);
        }

        .upload-panel:hover .upload-icon {
            transform: scale(1.1);
        }

        .file-input {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .file-list {
            margin-top: 1rem;
            font-weight: 500;
            color: var(--primary);
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
            font-size: 0.95rem;
        }

        .btn-main {
            background: linear-gradient(135deg, var(--primary) 0%, #ffd700 100%);
            color: #002a54;
            border: none;
            padding: 0.85rem 2.5rem;
            font-size: 1.05rem;
            font-weight: 600;
            border-radius: 100px;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 4px 15px var(--primary-glow);
            margin-top: 1.5rem;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-main:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(45, 212, 191, 0.4);
            filter: brightness(1.05);
        }

        .btn-main:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

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
        }
        .btn-camera:hover { transform: translateY(-2px); filter: brightness(1.1); box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5); }

        .btn-clear {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid #ef4444;
            padding: 0.85rem 2rem;
            font-size: 1.05rem;
            font-weight: 600;
            border-radius: 100px;
            cursor: pointer;
            transition: var(--transition);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn-clear:hover {
            background: #ef4444;
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
            transform: translateY(-2px);
        }

        /* Spinner and Status */
        .loader-wrapper {
            display: none;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
            margin: 2.5rem 0;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 3px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            box-shadow: 0 0 15px var(--primary-glow);
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .status-text {
            color: var(--accent);
            font-weight: 500;
            font-size: 1.1rem;
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Results Layout */
        .results-container {
            display: flex;
            flex-direction: column;
            gap: 2rem;
            width: 100%;
        }

        .results-header {
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--primary);
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.8rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .recipe-card {
            background: rgba(20, 28, 48, 0.6);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            animation: fadeIn 0.5s ease-out forwards;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }

        .recipe-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--accent);
            border-bottom: 1px solid rgba(255,255,255,0.04);
            padding-bottom: 0.75rem;
        }

        .grid-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .info-card {
            background: var(--surface-card);
            border: 1px solid rgba(255,255,255,0.03);
            border-radius: 10px;
            padding: 1rem;
        }

        .info-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.3rem;
            font-weight: 500;
        }

        .info-value {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-main);
        }

        /* Table Styling */
        .table-container {
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 12px;
            overflow-x: auto;
            background: rgba(13, 18, 30, 0.5);
            width: 100%;
        }

        .table-title {
            background: rgba(255,255,255,0.02);
            padding: 0.75rem 1.25rem;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            border-bottom: 1px solid rgba(255,255,255,0.04);
        }

        .badge-bq {
            background: rgba(52, 211, 153, 0.15);
            color: var(--success);
            border: 1px solid rgba(52, 211, 153, 0.3);
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-err {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            padding: 0.75rem 1.25rem;
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            background: rgba(0,0,0,0.15);
        }

        td {
            padding: 0.85rem 1.25rem;
            border-bottom: 1px solid rgba(255,255,255,0.02);
            color: var(--text-main);
            font-size: 0.9rem;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .bq-log {
            font-size: 0.85rem;
            color: var(--success);
            background: rgba(52, 211, 153, 0.05);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border-left: 3px solid var(--success);
        }

        .bq-log-err {
            font-size: 0.85rem;
            color: #f87171;
            background: rgba(239, 68, 68, 0.05);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border-left: 3px solid #ef4444;
        }
    </style>
</head>
<body>

<div class="container">
    <header>
        <h1>Farmacias Arrocha</h1>
        <p class="subtitle" style="color: var(--primary); font-weight: 500;">Portal ADK - Extracción Inteligente de Recetas Médicas</p>
    </header>

    <main style="display: flex; flex-direction: column; align-items: center; width: 100%;">
        <!-- Área de Carga Múltiple -->
        <div class="upload-panel" id="dropZone">
            <input type="file" id="fileInput" class="file-input" accept=".pdf" multiple>
            <span class="upload-icon">📄</span>
            <p style="font-size: 1.2rem; font-weight: 500; margin-bottom: 0.5rem;">Arrastra uno o varios PDFs de recetas médicas aquí</p>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Puedes seleccionar múltiples archivos a la vez</p>
            <div class="file-list" id="fileListDisplay"></div>
        </div>
        
        <div style="display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; justify-content: center; width: 100%;">
            <button class="btn-camera" id="btnCamera" style="margin-top: 0;">📸 Tomar Foto con Cámara</button>
            <button class="btn-main" id="uploadBtn" style="margin-top: 0;" disabled>Procesar Lote con ADK</button>
            <button class="btn-clear" id="clearTableBtn" style="margin-top: 0;">🗑️ Vaciar Tabla BigQuery</button>
        </div>
        <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display: none;">

        <!-- Animación de Carga -->
        <div class="loader-wrapper" id="loader">
            <div class="spinner"></div>
            <div class="status-text" id="statusText">Procesando lote de recetas con Gemini e insertando en BigQuery...</div>
        </div>

        <!-- Visualización Dinámica de Resultados -->
        <div class="results-container" id="resultsContainer" style="display: none;">
            <div class="results-header">
                <span id="resultsTitle">Resultados del Procesamiento</span>
                <span style="font-size: 0.9rem; color: var(--text-muted);" id="resultsSummary"></span>
            </div>
            <div id="recipesCardsArea" style="display: flex; flex-direction: column; gap: 1.5rem;"></div>
        </div>
    </main>
</div>

<script>
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileListDisplay = document.getElementById('fileListDisplay');
    const uploadBtn = document.getElementById('uploadBtn');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('resultsContainer');
    const recipesCardsArea = document.getElementById('recipesCardsArea');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsSummary = document.getElementById('resultsSummary');

    // Evitar comportamiento por defecto en toda la ventana
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFiles, false);

    const btnCamera = document.getElementById('btnCamera');
    const cameraInput = document.getElementById('cameraInput');
    btnCamera.addEventListener('click', (e) => {
        e.stopPropagation();
        cameraInput.click();
    });
    cameraInput.addEventListener('change', () => {
        if (cameraInput.files.length) {
            selectedFiles.push(cameraInput.files[0]);
            actualizarVistaArchivos();
        }
    });

    let selectedFiles = [];

    function handleDrop(e) {
        const dt = e.dataTransfer;
        if (dt.files.length) {
            const newFiles = Array.from(dt.files);
            selectedFiles = [...selectedFiles, ...newFiles];
            actualizarVistaArchivos();
        }
    }

    function handleFiles() {
        const newFiles = Array.from(fileInput.files);
        selectedFiles = [...selectedFiles, ...newFiles];
        actualizarVistaArchivos();
    }

    function actualizarVistaArchivos() {
        fileListDisplay.innerHTML = '';
        
        if (selectedFiles.length) {
            const countText = document.createElement('div');
            countText.style.color = 'var(--text-main)';
            countText.style.fontWeight = '600';
            countText.style.marginBottom = '0.5rem';
            countText.textContent = `📁 ${selectedFiles.length} archivo(s) listo(s) para extraer:`;
            fileListDisplay.appendChild(countText);

            // Listar hasta 5 nombres y un resumen si hay más
            selectedFiles.slice(0, 5).forEach(file => {
                const item = document.createElement('div');
                item.style.color = 'var(--primary)';
                item.textContent = `• ${file.name}`;
                fileListDisplay.appendChild(item);
            });

            if (selectedFiles.length > 5) {
                const extra = document.createElement('div');
                extra.style.color = 'var(--text-muted)';
                extra.textContent = `...y ${selectedFiles.length - 5} archivo(s) más.`;
                fileListDisplay.appendChild(extra);
            }

            uploadBtn.disabled = false;
            uploadBtn.textContent = `Procesar ${selectedFiles.length} Receta(s) con ADK`;
        } else {
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Procesar Lote con ADK';
        }
    }

    uploadBtn.addEventListener('click', async () => {
        if (!selectedFiles.length) return;

        // Resetear vista
        resultsContainer.style.display = 'none';
        recipesCardsArea.innerHTML = '';
        loader.style.display = 'flex';
        uploadBtn.disabled = true;
        dropZone.style.pointerEvents = 'none';
        dropZone.style.opacity = '0.5';

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('archivos', file);
        });

        try {
            const response = await fetch('/api/procesar_lote', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                renderBatchResults(data);
            } else {
                alert(`Error en el servidor: ${data.message || 'Fallo general'}`);
            }
        } catch (error) {
            alert(`Error de red: ${error.message}`);
        } finally {
            loader.style.display = 'none';
            uploadBtn.disabled = false;
            dropZone.style.pointerEvents = 'auto';
            dropZone.style.opacity = '1';
        }
    });

    const clearTableBtn = document.getElementById('clearTableBtn');
    clearTableBtn.addEventListener('click', async () => {
        if (!confirm('⚠️ ¿Estás absolutamente seguro de vaciar todos los registros de prescripciones de prueba en BigQuery?')) return;
        
        clearTableBtn.disabled = true;
        const originalText = clearTableBtn.innerHTML;
        clearTableBtn.innerHTML = '⏳ Limpiando tabla...';

        try {
            const res = await fetch('/api/limpiar_tabla', { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                alert('✅ ¡La tabla de BigQuery ha sido limpiada exitosamente!');
                resultsContainer.style.display = 'none';
                recipesCardsArea.innerHTML = '';
            } else {
                alert(`❌ Error al limpiar la tabla: ${data.message}`);
            }
        } catch (e) {
            alert(`❌ Error de red: ${e.message}`);
        } finally {
            clearTableBtn.disabled = false;
            clearTableBtn.innerHTML = originalText;
        }
    });

    function renderBatchResults(resList) {
        resultsTitle.textContent = `Lote Procesado (${resList.length} archivo(s))`;
        const exitosos = resList.filter(r => r.status === 'success').length;
        resultsSummary.textContent = `${exitosos} guardado(s) en BigQuery | ${resList.length - exitosos} con error`;
        
        resList.forEach((res, idx) => {
            const card = document.createElement('div');
            card.className = 'recipe-card';

            const isSuccess = res.status === 'success';
            const badge = isSuccess ? 
                '<span class="badge-bq">✓ Guardado en BigQuery</span>' : 
                '<span class="badge-err">✕ Error en Procesamiento</span>';

            let infoHtml = '';
            let tableHtml = '';

            if (isSuccess && res.data) {
                const rec = res.data;
                infoHtml = `
                    <div class="grid-info">
                        <div class="info-card">
                            <div class="info-label">Paciente</div>
                            <div class="info-value">${rec.nombre_paciente || '-'}</div>
                        </div>
                        <div class="info-card">
                            <div class="info-label">Médico</div>
                            <div class="info-value">${rec.nombre_medico || '-'}</div>
                        </div>
                        <div class="info-card">
                            <div class="info-label">Fecha</div>
                            <div class="info-value">${rec.fecha || '-'}</div>
                        </div>
                        <div class="info-card">
                            <div class="info-label">Diagnóstico</div>
                            <div class="info-value">${rec.diagnostico || '-'}</div>
                        </div>
                    </div>
                `;

                let medRows = '';
                if (rec.medicamentos && rec.medicamentos.length) {
                    rec.medicamentos.forEach(m => {
                        medRows += `
                            <tr>
                                <td style="font-weight:500; color:var(--primary);">${m.nombre || '-'}</td>
                                <td>${m.dosis || '-'}</td>
                                <td>${m.frecuencia || '-'}</td>
                                <td>${m.duracion || '-'}</td>
                            </tr>
                        `;
                    });
                } else {
                    medRows = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No se hallaron medicamentos detallados</td></tr>';
                }

                let clinicasSugeridas = rec.clinicas_sugeridas || ['Clínica Arrocha Central'];
                let clinicasOptions = clinicasSugeridas.map(c => `<option value="${c}">${c}</option>`).join('');
                let clinicaBoxHtml = `
                    <div class="clinica-box" style="background: rgba(255,184,0,0.1); border: 1px solid var(--primary); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
                        <div style="font-weight: 700; color: var(--primary); margin-bottom: 0.5rem;">🏥 Inferencia de Clínica (Sugerida por IA)</div>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">Basándose en el historial del doctor prescriptor, elija el consultorio:</p>
                        <select class="combo-clinica" style="width: 100%; padding: 0.6rem 1rem; background: #001b38; color: #fff; border: 1px solid var(--primary); border-radius: 8px; font-size: 0.95rem; margin-bottom: 0.5rem;">
                            ${clinicasOptions}
                        </select>
                        <button style="background: var(--primary); color: #002a54; font-weight: 700; padding: 0.4rem 1.2rem; border: none; border-radius: 100px; cursor: pointer; font-size: 0.85rem; margin-top: 0.5rem;" onclick="confirmarClinicaSeleccion(this, '${res.archivo}')">Confirmar Centro Clínico</button>
                        <span class="status-clinica" style="margin-left: 0.8rem; font-size: 0.85rem; color: var(--success); font-weight: 600;"></span>
                    </div>
                `;

                tableHtml = `
                    ${clinicaBoxHtml}
                    <div class="table-container">
                        <div class="table-title">Listado de Medicamentos Prescritos</div>
                        <table>
                            <thead>
                                <tr>
                                    <th>Medicamento</th>
                                    <th>Dosis</th>
                                    <th>Frecuencia</th>
                                    <th>Duración</th>
                                </tr>
                            </thead>
                            <tbody>${medRows}</tbody>
                        </table>
                    </div>
                `;
            }

            const logClass = isSuccess ? 'bq-log' : 'bq-log-err';

            card.innerHTML = `
                <div class="recipe-card-header">
                    <span>📄 Archivo: ${res.archivo}</span>
                    ${badge}
                </div>
                ${infoHtml}
                ${tableHtml}
                <div class="${logClass}">${res.message}</div>
            `;

            recipesCardsArea.appendChild(card);
        });

        resultsContainer.style.display = 'flex';
    }

    async function confirmarClinicaSeleccion(btn, archivo) {
        const container = btn.parentElement;
        const select = container.querySelector('.combo-clinica');
        const status = container.querySelector('.status-clinica');
        btn.disabled = true;
        btn.textContent = '⏳ Sincronizando con BigQuery...';

        const formData = new FormData();
        formData.append('archivo', archivo);
        formData.append('clinica', select.value);

        try {
            const res = await fetch('/api/confirmar_clinica', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                status.textContent = `✓ Confirmado en BigQuery: ${select.value}`;
                btn.textContent = '✓ Selección Guardada';
                btn.disabled = true;
                btn.style.opacity = '0.6';
                btn.style.cursor = 'default';
                select.disabled = true;
            } else {
                alert(`Error al guardar en BigQuery: ${data.message}`);
                btn.disabled = false;
                btn.textContent = 'Confirmar Centro Clínico';
            }
        } catch (e) {
            alert(`Error de conexión: ${e.message}`);
            btn.disabled = false;
            btn.textContent = 'Confirmar Centro Clínico';
        }
    }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    """Sirve la página de la interfaz web de usuario habilitada para procesamiento por lotes."""
    return HTML_TEMPLATE

@app.post("/api/limpiar_tabla")
async def api_limpiar_tabla_endpoint():
    """Endpoint web para vaciar la tabla de prescripciones en BigQuery bajo demanda."""
    try:
        limpiar_tabla_prescripciones(interactivo=False)
        return {"status": "success", "message": "La tabla ha sido limpiada correctamente."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/confirmar_clinica")
async def api_confirmar_clinica_endpoint(archivo: str = Form(...), clinica: str = Form(...)):
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
async def api_procesar_lote(archivos: List[UploadFile] = File(...)):
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
    print("=== Iniciando Servidor ADK Batch Web UI en http://127.0.0.1:8000 ===")
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=True)

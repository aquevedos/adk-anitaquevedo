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

# Interfaz HTML idéntica a web_app.py adaptada para rutas de Cloud Run Functions
HTML_SERVERLESS_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Farmacias Arrocha - Cloud Run Serverless Portal</title>
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

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }

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

        .container { width: 100%; max-width: 1050px; display: flex; flex-direction: column; gap: 2rem; }

        header { text-align: center; margin-bottom: 1rem; }

        h1 {
            font-size: clamp(1.8rem, 6vw, 2.8rem);
            font-weight: 700;
            background: linear-gradient(135deg, #ffffff 0%, #ffb800 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.03em;
            line-height: 1.1;
        }

        .subtitle { color: var(--text-muted); font-size: clamp(1rem, 3.5vw, 1.1rem); font-weight: 300; }

        /* Glassmorphism Upload Area */
        .upload-panel {
            background: var(--surface);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 2px dashed var(--border);
            border-radius: var(--radius);
            padding: clamp(2rem, 5vw, 3.5rem) clamp(1.5rem, 4vw, 3rem);
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
            position: relative;
            width: 100%;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        .upload-panel:hover, .upload-panel.dragover {
            border-color: var(--primary);
            background: rgba(0, 90, 175, 0.45);
            box-shadow: 0 0 25px var(--primary-glow);
            transform: translateY(-2px);
        }
        .file-input { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        .upload-icon { font-size: clamp(3rem, 6vw, 4rem); display: inline-block; margin-bottom: 1rem; filter: drop-shadow(0 4px 10px rgba(0,0,0,0.3)); }
        .file-list { margin-top: 1.5rem; text-align: left; background: rgba(0,0,0,0.25); padding: 1rem 1.5rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }

        /* Buttons */
        .btn-main {
            background: linear-gradient(135deg, var(--primary) 0%, #ffd700 100%);
            color: #002a54;
            border: none;
            padding: 0.85rem clamp(1.5rem, 4vw, 2.8rem);
            font-size: clamp(0.95rem, 3vw, 1.1rem);
            font-weight: 700;
            border-radius: 100px;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 4px 20px var(--primary-glow);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
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
        }
        .btn-camera:hover { transform: translateY(-2px); filter: brightness(1.1); box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5); }

        .btn-clear {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid #ef4444;
            padding: 0.85rem clamp(1.2rem, 3vw, 2rem);
            font-size: clamp(0.95rem, 3vw, 1.05rem);
            font-weight: 600;
            border-radius: 100px;
            cursor: pointer;
            transition: var(--transition);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn-clear:hover { background: #ef4444; color: #ffffff; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); transform: translateY(-2px); }

        /* Loader */
        .loader-wrapper { display: none; flex-direction: column; align-items: center; gap: 1.2rem; margin: 3rem 0; width: 100%; }
        .spinner { width: 50px; height: 50px; border: 4px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite; box-shadow: 0 0 20px var(--primary-glow); }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status-text { color: var(--primary); font-weight: 600; font-size: clamp(1rem, 3vw, 1.2rem); text-align: center; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

        /* Results Cards */
        .results-container { width: 100%; display: flex; flex-direction: column; gap: 1.5rem; margin-top: 1rem; }
        .results-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem; }
        #resultsTitle { font-size: clamp(1.2rem, 4vw, 1.6rem); font-weight: 700; color: var(--primary); }
        .recipe-card { background: rgba(10, 25, 50, 0.75); border: 1px solid var(--border); border-radius: var(--radius); padding: clamp(1.2rem, 4vw, 2rem); box-shadow: 0 15px 35px rgba(0,0,0,0.3); width: 100%; animation: fadeIn 0.5s forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .recipe-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); font-weight: 600; font-size: clamp(1rem, 3vw, 1.15rem); color: #38bdf8; flex-wrap: wrap; gap: 0.5rem; }
        .grid-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
        .info-card { background: var(--surface-card); border: 1px solid rgba(255,255,255,0.03); border-radius: 10px; padding: 1rem; }
        .info-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; font-weight: 500; }
        .info-value { font-size: 1.1rem; font-weight: 600; color: var(--text-main); word-break: break-word; }

        /* Table */
        .table-container { border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; overflow-x: auto; background: rgba(13, 18, 30, 0.5); width: 100%; margin-top: 1.5rem; }
        .table-title { background: rgba(255,255,255,0.02); padding: 0.75rem 1.25rem; font-size: 0.85rem; font-weight: 600; color: var(--text-muted); border-bottom: 1px solid rgba(255,255,255,0.04); }
        table { width: 100%; border-collapse: collapse; text-align: left; min-width: 500px; }
        th { padding: 0.85rem 1.25rem; background: rgba(0,0,0,0.3); color: var(--primary); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid rgba(255,255,255,0.1); }
        td { padding: 0.85rem 1.25rem; border-bottom: 1px solid rgba(255,255,255,0.04); color: var(--text-main); font-size: 0.9rem; }
        
        .badge-bq { background: rgba(52, 211, 153, 0.15); color: var(--success); border: 1px solid rgba(52, 211, 153, 0.3); padding: 0.25rem 0.75rem; border-radius: 100px; font-size: 0.75rem; font-weight: 600; white-space: nowrap; }
        .badge-err { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 0.25rem 0.75rem; border-radius: 100px; font-size: 0.75rem; font-weight: 600; white-space: nowrap; }
        .bq-log { font-size: 0.85rem; color: var(--success); background: rgba(52, 211, 153, 0.05); padding: 0.75rem 1rem; border-radius: 8px; border-left: 3px solid var(--success); margin-top: 1.5rem; }
        .bq-log-err { font-size: 0.85rem; color: #f87171; background: rgba(239, 68, 68, 0.05); padding: 0.75rem 1rem; border-radius: 8px; border-left: 3px solid #ef4444; margin-top: 1.5rem; }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div style="display:inline-block; background: rgba(255,184,0,0.15); border: 1px solid var(--primary); padding: 0.4rem 1.2rem; border-radius: 100px; font-size: 0.85rem; font-weight: 700; color: var(--primary); margin-bottom: 1rem;">⚡ Portal Serverless Cloud Run (2nd Gen)</div>
        <h1>Farmacias Arrocha</h1>
        <p class="subtitle" style="color: var(--primary); font-weight: 500;">Portal ADK Serverless - Extracción Inteligente de Recetas Médicas</p>
    </header>

    <main style="display: flex; flex-direction: column; align-items: center; width: 100%;">
        <div class="upload-panel" id="dropZone">
            <input type="file" id="fileInput" class="file-input" accept="image/*,.pdf" multiple>
            <span class="upload-icon">📄</span>
            <p style="font-size: 1.2rem; font-weight: 500; margin-bottom: 0.5rem;">Arrastra uno o varios PDFs / Imágenes de recetas aquí</p>
            <p style="color: var(--text-muted); font-size: 0.9rem;">O captura directamente con la cámara en tu celular</p>
            <div class="file-list" id="fileListDisplay"></div>
        </div>
        
        <div style="display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; justify-content: center; width: 100%;">
            <button class="btn-camera" id="btnCamera">📸 Tomar Foto con Cámara</button>
            <button class="btn-main" id="uploadBtn" disabled>Procesar Lote Serverless</button>
            <button class="btn-clear" id="clearTableBtn">🗑️ Vaciar Tabla BigQuery</button>
        </div>
        <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display: none;">

        <div class="loader-wrapper" id="loader">
            <div class="spinner"></div>
            <div class="status-text" id="statusText">Procesando lote de recetas de forma Serverless e insertando en BigQuery...</div>
        </div>

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

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

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
    btnCamera.addEventListener('click', (e) => { e.stopPropagation(); cameraInput.click(); });
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
            uploadBtn.textContent = `Procesar ${selectedFiles.length} Receta(s) en Nube`;
        } else {
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Procesar Lote Serverless';
        }
    }

    uploadBtn.addEventListener('click', async () => {
        if (!selectedFiles.length) return;

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
            const response = await fetch(window.location.pathname, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                renderBatchResults(data);
            } else {
                alert(`Error en la nube: ${data.message || 'Fallo general'}`);
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
        if (!confirm('⚠️ ¿Estás absolutamente seguro de vaciar (eliminar) la tabla de producción prescripciones_cloud_run en BigQuery?')) return;
        
        clearTableBtn.disabled = true;
        const originalText = clearTableBtn.innerHTML;
        clearTableBtn.innerHTML = '⏳ Limpiando tabla...';

        try {
            const formDataLimpiar = new FormData();
            formDataLimpiar.append('action', 'limpiar');
            const res = await fetch(window.location.pathname, { method: 'POST', body: formDataLimpiar });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                alert('✅ ¡La tabla de BigQuery ha sido limpiada exitosamente!');
                resultsContainer.style.display = 'none';
                recipesCardsArea.innerHTML = '';
                selectedFiles = [];
                actualizarVistaArchivos();
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
                            <div class="info-value">${rec.paciente_nombre || '-'} ${rec.paciente_apellido || ''}</div>
                        </div>
                        <div class="info-card">
                            <div class="info-label">Médico</div>
                            <div class="info-value">${rec.medico_nombre || '-'}</div>
                        </div>
                        <div class="info-card">
                            <div class="info-label">Cédula</div>
                            <div class="info-value">${rec.paciente_cedula || '-'}</div>
                        </div>
                        <div class="info-card">
                            <div class="info-label">Folio Receta</div>
                            <div class="info-value">${rec.numero_receta || '-'}</div>
                        </div>
                    </div>
                `;

                let medRows = '';
                if (rec.medicamentos && rec.medicamentos.length) {
                    rec.medicamentos.forEach(m => {
                        medRows += `
                            <tr>
                                <td style="font-weight:700; color:var(--primary);">${m.nombre || '-'}</td>
                                <td>${m.dosis || '-'}</td>
                                <td>${m.cantidad_recetada || m.cantidad || '-'}</td>
                                <td>🏷️ ${m.sugerencia_etiquetas || 1} etiqueta(s)</td>
                            </tr>
                        `;
                    });
                } else {
                    medRows = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No se hallaron medicamentos detallados</td></tr>';
                }

                let clinicasSugeridas = rec.clinicas_inferidas_sugeridas || rec.clinicas_inferidas || ['Clínica Arrocha Central'];
                if (typeof clinicasSugeridas === 'string') clinicasSugeridas = clinicasSugeridas.split(',').map(s => s.trim());
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
                                    <th>Cantidad</th>
                                    <th>Etiquetas Sugeridas</th>
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
        formData.append('action', 'confirmar');
        formData.append('archivo', archivo);
        formData.append('clinica', select.value);

        try {
            const res = await fetch(window.location.pathname, { method: 'POST', body: formData });
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

    if request.method == 'GET':
        headers_html = {'Content-Type': 'text/html; charset=utf-8', 'Access-Control-Allow-Origin': '*'}
        return (HTML_SERVERLESS_TEMPLATE, 200, headers_html)

    if request.method != 'POST':
        return (json.dumps({"status": "error", "message": "Sólo se permite el método POST o GET."}), 405, headers)

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

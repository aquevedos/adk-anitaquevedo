/**
 * MÓDULO: Gobernanza y Gestión de Metadatos (Knowledge Catalog Tagging & SDP Auto-Tagging)
 */

let currentTaggingAssetId = null;
let currentAssetTagsData = null;

function initTagging() {
  loadTaggingSelector();
  loadRegisteredTagTemplates();
}

async function loadTaggingSelector() {
  const selectEl = document.getElementById("tagging-asset-select");
  if (!selectEl) return;

  try {
    const res = await fetch(`${API_BASE}/api/catalog/assets`);
    const data = await res.json();
    if (data.status === "success" && data.data.length > 0) {
      selectEl.innerHTML = data.data.map(a => `
        <option value="${a.id}">[${a.cloud}] ${a.name} (${a.dataset}.${a.table_name})</option>
      `).join("");

      currentTaggingAssetId = data.data[0].id;
      loadAssetTags(currentTaggingAssetId);
    }
  } catch (err) {
    console.error("Error cargando selector de tagging:", err);
  }
}

async function selectTaggingAsset(assetId) {
  currentTaggingAssetId = assetId;
  const selectEl = document.getElementById("tagging-asset-select");
  if (selectEl) selectEl.value = assetId;
  await loadAssetTags(assetId);
}

async function loadAssetTags(assetId) {
  if (!assetId) return;
  currentTaggingAssetId = assetId;

  const container = document.getElementById("tagging-content-container");
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted);"><em>Cargando etiquetas y plantillas de Knowledge Catalog para '${assetId}'...</em></div>`;

  try {
    const res = await fetch(`${API_BASE}/api/tags/asset/${assetId}`);
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      currentAssetTagsData = data.data;
      renderAssetTaggingWorkspace(data.data);
    } else {
      container.innerHTML = `<div style="color: var(--pastel-rose-text); padding: 1.5rem;">Error al obtener etiquetas del activo.</div>`;
    }
  } catch (err) {
    console.error("Error al cargar etiquetas:", err);
    container.innerHTML = `<div style="color: var(--pastel-rose-text); padding: 1.5rem;">Error de conexión al cargar etiquetas.</div>`;
  }
}

function renderAssetTaggingWorkspace(tagsData) {
  const container = document.getElementById("tagging-content-container");
  if (!container) return;

  const tags = tagsData.applied_tags || {};
  const govTag = tags.data_governance_core?.fields || {};
  const sdpTag = tags.sdp_security_classification?.fields || {};
  const dqTag = tags.dataplex_quality_slas?.fields || {};
  const cols = tagsData.columns || [];

  const isLiveMySQL = (tagsData.cloud || "").toUpperCase().includes("MYSQL");
  const cloudBadgeClass = isLiveMySQL ? "badge-amber" : "badge-blue";

  container.innerHTML = `
    <!-- ASSET HEADER BANNER -->
    <div class="pastel-card" style="margin-bottom: 1.25rem; border-left: 4px solid var(--pastel-blue-accent);">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="stat-metric-badge ${cloudBadgeClass}">● ${escapeHtml(tagsData.cloud)}</span>
            <span class="stat-metric-badge badge-purple">${escapeHtml(tagsData.service || 'Knowledge Catalog')}</span>
          </div>
          <h3 style="font-size: 1.25rem; font-weight: 700; color: var(--text-main); margin-top: 0.35rem;">
            🏷️ ${escapeHtml(tagsData.asset_name)}
          </h3>
          <div style="font-size: 0.8rem; color: var(--pastel-blue-text); font-family: monospace;">
            📍 ${escapeHtml(tagsData.location)}
          </div>
        </div>

        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <button class="btn-secondary" onclick="executeAutoTaggingWithSDP('${escapeHtml(tagsData.asset_id)}')">
            ⚡ Auto-Tagging con SDP (Cloud DLP)
          </button>
          <button class="btn-primary" onclick="saveAllGovernanceTags('${escapeHtml(tagsData.asset_id)}')">
            💾 Guardar Etiquetas de Gobierno
          </button>
        </div>
      </div>
    </div>

    <!-- 3 KNOWLEDGE CATALOG TAG TEMPLATE CARDS -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem;">
      
      <!-- 1. CORE GOVERNANCE TAG TEMPLATE -->
      <div class="pastel-card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <span style="font-weight: 700; color: var(--pastel-blue-text); font-size: 0.88rem;">📋 Plantilla de Gobernanza (Core)</span>
            <span class="stat-metric-badge badge-blue">Knowledge Catalog</span>
          </div>
          
          <div style="display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.8rem;">
            <div>
              <label class="form-label">Data Steward Responsable:</label>
              <input type="text" id="tag-input-steward" class="form-input" style="width: 100%;" value="${escapeHtml(govTag.data_steward || tagsData.steward || 'Lucía Morales (Data Steward)')}">
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
              <div>
                <label class="form-label">Dominio de Negocio:</label>
                <select id="tag-input-domain" class="form-input" style="width: 100%;">
                  <option value="clientes" ${govTag.data_domain === 'clientes' ? 'selected' : ''}>Clientes</option>
                  <option value="ventas" ${govTag.data_domain === 'ventas' ? 'selected' : ''}>Ventas</option>
                  <option value="finanzas" ${govTag.data_domain === 'finanzas' ? 'selected' : ''}>Finanzas</option>
                  <option value="operaciones" ${govTag.data_domain === 'operaciones' ? 'selected' : ''}>Operaciones</option>
                </select>
              </div>

              <div>
                <label class="form-label">Confidencialidad:</label>
                <select id="tag-input-confidentiality" class="form-input" style="width: 100%;">
                  <option value="Pública" ${govTag.confidentiality_level === 'Pública' ? 'selected' : ''}>Pública</option>
                  <option value="Uso Interno" ${govTag.confidentiality_level === 'Uso Interno' ? 'selected' : ''}>Uso Interno</option>
                  <option value="Confidencial PII" ${govTag.confidentiality_level === 'Confidencial PII' ? 'selected' : ''}>Confidencial PII</option>
                  <option value="Altamente Restringida" ${govTag.confidentiality_level === 'Altamente Restringida' ? 'selected' : ''}>Altamente Restringida</option>
                </select>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
              <div>
                <label class="form-label">Retención (Meses):</label>
                <input type="number" id="tag-input-retention" class="form-input" style="width: 100%;" value="${govTag.retention_policy_months || 24}">
              </div>
              <div>
                <label class="form-label">Aprobado para IA / RAG:</label>
                <select id="tag-input-ai-cert" class="form-input" style="width: 100%;">
                  <option value="true" ${govTag.ai_certified ? 'selected' : ''}>✅ Certificado IA</option>
                  <option value="false" ${!govTag.ai_certified ? 'selected' : ''}>❌ No Aprobado</option>
                </select>
              </div>
            </div>

            <div>
              <label class="form-label">Fuente Dorada de Origen:</label>
              <input type="text" id="tag-input-golden-src" class="form-input" style="width: 100%;" value="${escapeHtml(govTag.golden_source || tagsData.location)}">
            </div>
          </div>
        </div>
      </div>

      <!-- 2. SDP & SECURITY CLASSIFICATION TAG TEMPLATE -->
      <div class="pastel-card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <span style="font-weight: 700; color: var(--pastel-rose-text); font-size: 0.88rem;">🛡️ Plantilla de Seguridad & SDP</span>
            <span class="stat-metric-badge badge-rose">Cloud DLP</span>
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.8rem;">
            <div>
              <label class="form-label">InfoTypes Detectados (SDP):</label>
              <input type="text" id="tag-input-infotypes" class="form-input" style="width: 100%;" value="${escapeHtml(sdpTag.infotypes_detected || 'Ninguno')}">
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
              <div>
                <label class="form-label">Nivel de Riesgo DLP:</label>
                <select id="tag-input-dlp-risk" class="form-input" style="width: 100%;">
                  <option value="Bajo / Sin PII" ${sdpTag.dlp_risk_level === 'Bajo / Sin PII' ? 'selected' : ''}>Bajo / Sin PII</option>
                  <option value="Medio" ${sdpTag.dlp_risk_level === 'Medio' ? 'selected' : ''}>Medio</option>
                  <option value="Alto" ${sdpTag.dlp_risk_level === 'Alto' ? 'selected' : ''}>Alto</option>
                  <option value="Crítico" ${sdpTag.dlp_risk_level === 'Crítico' ? 'selected' : ''}>Crítico</option>
                </select>
              </div>

              <div>
                <label class="form-label">Dynamic Masking:</label>
                <select id="tag-input-masking" class="form-input" style="width: 100%;">
                  <option value="true" ${sdpTag.dynamic_masking_enabled ? 'selected' : ''}>🔒 Activo (DDM)</option>
                  <option value="false" ${!sdpTag.dynamic_masking_enabled ? 'selected' : ''}>👁️ Desactivado</option>
                </select>
              </div>
            </div>

            <div>
              <label class="form-label">Taxonomía de Policy Tags:</label>
              <input type="text" id="tag-input-taxonomy" class="form-input" style="width: 100%;" value="${escapeHtml(sdpTag.policy_tag_taxonomy || 'Taxonomy_PII_Confidential')}">
            </div>

            <div style="background: var(--bg-app); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem;">
              🕒 <strong>Último Escaneo SDP:</strong> ${escapeHtml(sdpTag.last_scan_date || 'Reciente')}
            </div>
          </div>
        </div>
      </div>

      <!-- 3. DATAPLEX QUALITY SLA TAG TEMPLATE -->
      <div class="pastel-card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <span style="font-weight: 700; color: var(--pastel-emerald-text); font-size: 0.88rem;">🩺 Plantilla de Calidad & SLAs</span>
            <span class="stat-metric-badge badge-emerald">Dataplex</span>
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.8rem;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
              <div>
                <label class="form-label">Quality Score (%):</label>
                <input type="number" id="tag-input-quality-score" class="form-input" style="width: 100%; font-weight: 700; color: var(--pastel-emerald-text);" value="${dqTag.quality_score || 98.8}">
              </div>
              <div>
                <label class="form-label">SLA Frescura (Horas):</label>
                <input type="number" id="tag-input-freshness" class="form-input" style="width: 100%;" value="${dqTag.freshness_hours || 1.0}">
              </div>
            </div>

            <div>
              <label class="form-label">Estado de Cumplimiento de Reglas:</label>
              <input type="text" id="tag-input-rules-status" class="form-input" style="width: 100%;" value="${escapeHtml(dqTag.rules_status || '5 de 5 reglas aprobadas (100%)')}">
            </div>

            <div style="background: var(--pastel-emerald-bg); border: 1px solid var(--pastel-emerald-border); padding: 0.6rem; border-radius: var(--radius-sm); margin-top: 0.5rem;">
              <strong style="color: var(--pastel-emerald-text); font-size: 0.78rem;">✅ Verificación Dataplex Automatizada</strong>
              <p style="font-size: 0.74rem; color: var(--text-main); margin-top: 0.15rem;">Las métricas se sincronizan con las reglas de completitud, unicidad y frescura.</p>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- COLUMN-LEVEL TAGGING & METADATA MANAGEMENT -->
    <div class="pastel-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <div>
          <h4 style="font-size: 1rem; font-weight: 700; color: var(--text-main);">
            🏷️ Gestión de Metadatos y Etiquetas a Nivel de Columna
          </h4>
          <p style="font-size: 0.78rem; color: var(--text-muted);">
            Define etiquetas de negocio, infotypes de Cloud DLP y asignación de Policy Tags por cada campo.
          </p>
        </div>
        <span class="stat-metric-badge badge-blue">${cols.length} columnas gobernadas</span>
      </div>

      <div style="overflow-x: auto;">
        <table class="table-clean">
          <thead>
            <tr>
              <th>Columna</th>
              <th>Tipo de Dato</th>
              <th>Etiqueta de Negocio</th>
              <th>InfoType (DLP)</th>
              <th>Policy Tag Asociada</th>
              <th>Enmascaramiento</th>
            </tr>
          </thead>
          <tbody>
            ${cols.map((col, idx) => {
              const isPii = col.is_pii || false;
              const dlpType = col.dlp_info_type || "";
              const policyTag = col.policy_tag || (isPii ? "Taxonomy_PII_Confidential" : "");
              const bTag = col.business_tag || (isPii ? "Dato Sensible / PII" : (col.is_primary_key ? "Identificador Único" : "Atributo de Negocio"));

              return `
                <tr>
                  <td>
                    <strong>${escapeHtml(col.name)}</strong>
                    ${col.is_primary_key ? '<span style="color: var(--pastel-amber-text); font-size: 0.7rem; font-weight: 700;"> [PK]</span>' : ''}
                  </td>
                  <td><code>${escapeHtml(col.type)}</code></td>
                  <td>
                    <input type="text" class="form-input col-tag-input" data-col="${escapeHtml(col.name)}" data-field="business_tag" style="font-size: 0.78rem; padding: 0.25rem 0.5rem; width: 100%;" value="${escapeHtml(bTag)}">
                  </td>
                  <td>
                    <select class="form-input col-tag-input" data-col="${escapeHtml(col.name)}" data-field="dlp_info_type" style="font-size: 0.78rem; padding: 0.25rem 0.5rem; width: 100%;">
                      <option value="">-- Sin InfoType --</option>
                      <option value="PERSON_NAME" ${dlpType === 'PERSON_NAME' ? 'selected' : ''}>PERSON_NAME</option>
                      <option value="EMAIL_ADDRESS" ${dlpType === 'EMAIL_ADDRESS' ? 'selected' : ''}>EMAIL_ADDRESS</option>
                      <option value="PHONE_NUMBER" ${dlpType === 'PHONE_NUMBER' ? 'selected' : ''}>PHONE_NUMBER</option>
                      <option value="LOCATION_GEO" ${dlpType === 'LOCATION_GEO' ? 'selected' : ''}>LOCATION_GEO</option>
                      <option value="CREDIT_CARD_NUMBER" ${dlpType === 'CREDIT_CARD_NUMBER' ? 'selected' : ''}>CREDIT_CARD_NUMBER</option>
                      <option value="FINANCIAL_NUMERIC" ${dlpType === 'FINANCIAL_NUMERIC' ? 'selected' : ''}>FINANCIAL_NUMERIC</option>
                    </select>
                  </td>
                  <td>
                    <input type="text" class="form-input col-tag-input" data-col="${escapeHtml(col.name)}" data-field="policy_tag" style="font-size: 0.78rem; padding: 0.25rem 0.5rem; width: 100%;" value="${escapeHtml(policyTag)}" placeholder="ej. Taxonomy_PII_Confidential">
                  </td>
                  <td style="text-align: center;">
                    <input type="checkbox" class="col-tag-checkbox" data-col="${escapeHtml(col.name)}" data-field="masked" ${col.masked ? 'checked' : ''} style="cursor: pointer;">
                  </td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

async function saveAllGovernanceTags(assetId) {
  if (!assetId) return;

  showToast("Guardando etiquetas en Google Cloud Knowledge Catalog...", "info");

  // 1. Recoger datos de plantillas
  const steward = document.getElementById("tag-input-steward")?.value.trim();
  const domain = document.getElementById("tag-input-domain")?.value;
  const confidentiality = document.getElementById("tag-input-confidentiality")?.value;
  const retention = parseInt(document.getElementById("tag-input-retention")?.value || "24");
  const goldenSrc = document.getElementById("tag-input-golden-src")?.value.trim();
  const aiCertified = document.getElementById("tag-input-ai-cert")?.value === "true";

  const infotypes = document.getElementById("tag-input-infotypes")?.value.trim();
  const dlpRisk = document.getElementById("tag-input-dlp-risk")?.value;
  const maskingEnabled = document.getElementById("tag-input-masking")?.value === "true";
  const taxonomy = document.getElementById("tag-input-taxonomy")?.value.trim();

  const qualityScore = parseFloat(document.getElementById("tag-input-quality-score")?.value || "98.8");
  const freshness = parseFloat(document.getElementById("tag-input-freshness")?.value || "1.0");
  const rulesStatus = document.getElementById("tag-input-rules-status")?.value.trim();

  // 2. Recoger datos de columnas
  const colRows = document.querySelectorAll(".col-tag-input");
  const colMap = {};

  colRows.forEach(input => {
    const colName = input.getAttribute("data-col");
    const field = input.getAttribute("data-field");
    colMap[colName] = colMap[colName] || { name: colName };
    colMap[colName][field] = input.value;
  });

  const checkboxes = document.querySelectorAll(".col-tag-checkbox");
  checkboxes.forEach(cb => {
    const colName = cb.getAttribute("data-col");
    colMap[colName] = colMap[colName] || { name: colName };
    colMap[colName]["masked"] = cb.checked;
    colMap[colName]["is_pii"] = !!colMap[colName]["dlp_info_type"] || cb.checked;
  });

  const columnUpdates = Object.values(colMap);

  try {
    // Actualizar Plantilla de Gobernanza
    const resGov = await fetch(`${API_BASE}/api/tags/asset/${assetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: "data_governance_core",
        fields: {
          data_steward: steward,
          data_domain: domain,
          confidentiality_level: confidentiality,
          retention_policy_months: retention,
          golden_source: goldenSrc,
          ai_certified: aiCertified
        },
        column_tags: columnUpdates
      })
    });

    // Actualizar Plantilla de Seguridad SDP
    await fetch(`${API_BASE}/api/tags/asset/${assetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: "sdp_security_classification",
        fields: {
          infotypes_detected: infotypes,
          dlp_risk_level: dlpRisk,
          dynamic_masking_enabled: maskingEnabled,
          policy_tag_taxonomy: taxonomy
        }
      })
    });

    // Actualizar Plantilla de Calidad SLAs
    await fetch(`${API_BASE}/api/tags/asset/${assetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: "dataplex_quality_slas",
        fields: {
          quality_score: qualityScore,
          freshness_hours: freshness,
          rules_status: rulesStatus
        }
      })
    });

    showToast("¡Etiquetas y Metadatos guardados con éxito en Knowledge Catalog!", "success");
    await loadAssetTags(assetId);
    if (typeof loadCatalogAssets === "function") loadCatalogAssets();
  } catch (err) {
    console.error("Error guardando etiquetas:", err);
    showToast("Error al guardar etiquetas.", "error");
  }
}

async function executeAutoTaggingWithSDP(assetId) {
  if (!assetId) return;

  showToast("Ejecutando escáner SDP y Auto-Tagging de Knowledge Catalog...", "info");

  try {
    const res = await fetch(`${API_BASE}/api/tags/auto_tag_sdp/${assetId}`, { method: "POST" });
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      showToast("¡Auto-Tagging con SDP completado! Taxonomías y Policy Tags asignadas.", "success");
      await loadAssetTags(assetId);
      if (typeof loadCatalogAssets === "function") loadCatalogAssets();
    } else {
      showToast("Error al ejecutar Auto-Tagging.", "error");
    }
  } catch (err) {
    console.error("Error en auto-tagging:", err);
    showToast("Error de conexión durante el Auto-Tagging.", "error");
  }
}

async function loadRegisteredTagTemplates() {
  const container = document.getElementById("tag-templates-catalog-list");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/tags/templates`);
    const data = await res.json();
    if (data.status === "success") {
      container.innerHTML = data.data.map(tpl => `
        <div style="background: var(--bg-app); border: 1px solid var(--border-light); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem; font-size: 0.78rem;">
          <div style="display: flex; justify-content: space-between;">
            <strong style="color: var(--pastel-blue-text);">${escapeHtml(tpl.display_name)}</strong>
            <code style="font-size: 0.7rem; color: var(--text-muted);">${escapeHtml(tpl.template_id)}</code>
          </div>
          <p style="color: var(--text-main); font-size: 0.74rem; margin: 0.25rem 0;">${escapeHtml(tpl.description)}</p>
          <div style="color: var(--text-muted); font-size: 0.72rem;">
            <strong>Campos:</strong> ${tpl.fields.map(f => `${f.display_name} (<code>${f.type}</code>)`).join(" • ")}
          </div>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Error loading tag templates list:", err);
  }
}

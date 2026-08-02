/**
 * Connectors & Automated External Database Discovery Controller
 * Supports MySQL Online (FreeMySQLDatabase), Azure SQL Server, Postgres, BigQuery, AWS
 */

function initConnectors() {
  loadConnectorsStatus();
}

async function loadConnectorsStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/connectors/status`);
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      renderConnectorsGrid(data.data);
    }
  } catch (err) {
    console.error("Error loading connectors:", err);
  }
}

function renderConnectorsGrid(connectors) {
  const container = document.getElementById("connectors-grid");
  if (!container) return;

  container.innerHTML = connectors.map(c => `
    <div class="pastel-card" style="border-top: 3px solid ${c.status === 'CONNECTED' ? 'var(--pastel-emerald-accent)' : 'var(--pastel-blue-accent)'};">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 1.4rem;">${c.cloud === 'GCP' ? '🌐' : (c.cloud === 'AWS' ? '☁️' : '🔷')}</span>
        <span class="stat-metric-badge ${c.status === 'CONNECTED' ? 'badge-emerald' : 'badge-amber'}">
          ● ${escapeHtml(c.status)}
        </span>
      </div>

      <div>
        <strong style="color: var(--text-main); font-size: 0.95rem;">${escapeHtml(c.name)}</strong>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem;">${escapeHtml(c.description)}</div>
      </div>

      <div style="background: var(--bg-app); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm); font-size: 0.75rem; font-family: monospace;">
        <div><strong>Recurso:</strong> ${escapeHtml(c.target_resource || c.project_id || 'Multi-Cloud Endpoint')}</div>
        <div><strong>Protocolo:</strong> Zero-Copy Federated API</div>
      </div>

      <div style="display: flex; gap: 0.5rem; margin-top: 0.25rem;">
        ${c.cloud === 'GCP' ? `
          <button class="btn-primary" style="font-size: 0.75rem; width: 100%;" onclick="triggerSyncRealGCP()">
            🔄 Sincronizar BigQuery en Vivo
          </button>
        ` : `
          <button class="btn-secondary" style="font-size: 0.75rem; width: 100%;" onclick="openExternalDBModal('${c.cloud}')">
            ⚙️ Configurar Conexión
          </button>
        `}
      </div>
    </div>
  `).join("");
}

async function triggerSyncRealGCP() {
  showToast("Sincronizando esquemas de BigQuery en 'agentspace-demos-466121'...", "info");
  try {
    const res = await fetch(`${API_BASE}/api/connectors/sync_real_gcp`, { method: "POST" });
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      showToast(data.message || "BigQuery sincronizado exitosamente.", "success");
      if (typeof loadCatalogAssets === "function") loadCatalogAssets();
    }
  } catch (err) {
    showToast("Error al sincronizar con BigQuery.", "error");
  }
}

// Preset filler for FreeMySQLDatabase, Aiven Cloud or Azure SQL
function fillMySQLPreset(presetType) {
  if (presetType === "freesql" || presetType === "aiven" || presetType === "mysql") {
    document.getElementById("ext-host").value = "mysql-1c645071-google-beed.j.aivencloud.com";
    document.getElementById("ext-port").value = "10283";
    document.getElementById("ext-db").value = "bdcomercial";
    document.getElementById("ext-user").value = "avnadmin";
    document.getElementById("ext-pass").value = "";
    document.getElementById("ext-tables").value = "clientes, ventas, productos, detalles_ventas, resumen_comercial_consolidado, vendedores";
    showToast("Preset cargado: MySQL Aiven Cloud (bdcomercial)", "info");
  } else if (presetType === "azuresql") {
    document.getElementById("ext-host").value = "enterprise-sql.database.windows.net";
    document.getElementById("ext-port").value = "1433";
    document.getElementById("ext-db").value = "crm_curated_db";
    document.getElementById("ext-user").value = "cloud_governance_admin";
    document.getElementById("ext-tables").value = "prospects_lake_v2, customer_contracts, payments_log";
    showToast("Preset cargado: Azure SQL Server Enterprise", "info");
  }
}

async function testExternalConnection() {
  const host = document.getElementById("ext-host")?.value.trim();
  const port = parseInt(document.getElementById("ext-port")?.value || "10283");
  const database = document.getElementById("ext-db")?.value.trim();
  const user = document.getElementById("ext-user")?.value.trim();
  const password = document.getElementById("ext-pass")?.value || "";

  if (!host || !database || !user) {
    showToast("Por favor completa el host, base de datos y usuario.", "error");
    return;
  }

  showToast(`Probando conexión con ${host}:${port}...`, "info");
  try {
    const res = await fetch(`${API_BASE}/api/connectors/external/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        engine: "mysql",
        host: host,
        port: port,
        database: database,
        user: user,
        password: password
      })
    });
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      const connData = data.data;
      if (connData.connected) {
        showToast(connData.message || "¡Conexión exitosa!", "success");
      } else {
        showToast(connData.message || "Error al conectar.", "error");
      }
    }
  } catch (err) {
    showToast("Error al conectar con la base de datos externa.", "error");
  }
}

async function triggerExternalDiscovery() {
  const host = document.getElementById("ext-host")?.value.trim();
  const port = parseInt(document.getElementById("ext-port")?.value || "10283");
  const database = document.getElementById("ext-db")?.value.trim();
  const user = document.getElementById("ext-user")?.value.trim();
  const password = document.getElementById("ext-pass")?.value || "";
  const tablesText = document.getElementById("ext-tables")?.value.trim() || "";
  const csvFile = document.getElementById("ext-csv-file")?.files[0];

  if (!host || !database) {
    showToast("Completa los datos de conexión.", "error");
    return;
  }

  let csvContent = null;
  if (csvFile) {
    csvContent = await csvFile.text();
  }

  const selectedTables = tablesText ? tablesText.split(",").map(t => t.trim()) : null;

  showToast("Iniciando Descubrimiento Automatizado, Linaje y Data Profiling...", "info");

  try {
    const res = await fetch(`${API_BASE}/api/connectors/external/discover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        engine: "mysql",
        host: host,
        port: port,
        database: database,
        user: user,
        password: password,
        selected_tables: selectedTables,
        csv_content: csvContent
      })
    });

    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      const disc = data.data;
      renderDiscoveryResults(disc);
      if (typeof loadCatalogAssets === "function") loadCatalogAssets();
      if (typeof loadLineageSelector === "function") loadLineageSelector();
      if (typeof loadQualitySelector === "function") loadQualitySelector();
      if (typeof loadDLPSelector === "function") loadDLPSelector();
      if (typeof loadTaggingSelector === "function") loadTaggingSelector();
    }
  } catch (err) {
    console.error("Discovery error:", err);
    showToast("Error durante el descubrimiento.", "error");
  }
}

function renderDiscoveryResults(disc) {
  const container = document.getElementById("discovery-results-container");
  if (!container) return;

  const isLive = disc.is_live_connection;
  const liveBadge = isLive 
    ? `<span class="stat-metric-badge badge-emerald">● Conexión en Vivo MySQL (Aiven Cloud)</span>`
    : `<span class="stat-metric-badge badge-blue">● Conexión Federada</span>`;

  const activityHtml = (disc.activity_log || []).map(act => `
    <div style="padding: 0.45rem 0.65rem; border-left: 3px solid ${act.status === 'SUCCESS' ? 'var(--pastel-emerald-accent)' : 'var(--pastel-blue-accent)'}; background: var(--bg-app); border-radius: 4px; margin-bottom: 0.4rem; font-size: 0.78rem;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-weight: 700; color: var(--text-main);">${escapeHtml(act.action)}</span>
        <span style="font-size: 0.7rem; color: var(--text-muted);">${escapeHtml(act.timestamp)}</span>
      </div>
      <div style="color: var(--text-muted); margin-top: 0.15rem; font-size: 0.75rem;">${escapeHtml(act.details)}</div>
    </div>
  `).join("");

  container.innerHTML = `
    <div style="background: var(--pastel-blue-bg); border: 1px solid var(--pastel-blue-border); padding: 1.25rem; border-radius: var(--radius-md); margin-top: 1.25rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
        <h4 style="color: var(--pastel-blue-text); font-weight: 700;">✅ Resultado del Descubrimiento & Data Profiling Real</h4>
        <div style="display: flex; gap: 0.4rem;">
          ${liveBadge}
          <span class="stat-metric-badge badge-purple">Knowledge Catalog Sincronizado</span>
        </div>
      </div>

      <div style="margin-top: 0.75rem; font-size: 0.82rem; color: var(--text-main);">
        <ul style="padding-left: 1.2rem; line-height: 1.6;">
          ${(disc.insights || []).map(i => `<li>${escapeHtml(i)}</li>`).join("")}
        </ul>
      </div>

      <div style="margin-top: 1rem; overflow-x: auto;">
        <table class="table-clean">
          <thead>
            <tr>
              <th>Tabla Indexada</th>
              <th>Filas Reales</th>
              <th>Columnas</th>
              <th>DLP / PII Status</th>
              <th>Quality Score</th>
            </tr>
          </thead>
          <tbody>
            ${(disc.discovered_assets || []).map(a => `
              <tr>
                <td><strong>${escapeHtml(a.name)}</strong></td>
                <td><span style="font-weight: 700; color: var(--pastel-blue-text);">${Number(a.row_count || 0).toLocaleString()}</span> filas</td>
                <td>${a.columns_count} columnas</td>
                <td><span class="stat-metric-badge ${a.dlp_status?.risk_level === 'Medio' ? 'badge-blue' : 'badge-purple'}">● ${a.dlp_status?.policy_tags_applied ? 'Dynamic Masking Activo' : 'Inspeccionado'}</span></td>
                <td><span class="stat-metric-badge badge-emerald">${a.dataplex_quality?.overall_score || 98.8}%</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>

      <!-- KNOWLEDGE CATALOG ACTIVITY AUDIT TRAIL -->
      <div style="margin-top: 1.25rem; border-top: 1px solid var(--border-light); padding-top: 1rem;">
        <div style="font-size: 0.82rem; font-weight: 700; color: var(--pastel-blue-text); margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem;">
          <span>📜 Registro de Actividades & Auditoría de Google Cloud Knowledge Catalog (${(disc.activity_log || []).length} eventos)</span>
        </div>
        <div style="max-height: 220px; overflow-y: auto;">
          ${activityHtml}
        </div>
      </div>
    </div>
  `;
}

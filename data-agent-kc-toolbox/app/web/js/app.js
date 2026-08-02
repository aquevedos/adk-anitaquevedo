/**
 * CMI Data Governance Platform — Frontend Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  loadGovernanceStatus();
  loadCatalogEntries();
  loadConfig();
  initChat();
});

// Navigation controller
function initNavigation() {
  const navBtns = document.querySelectorAll(".nav-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      navBtns.forEach((b) => b.classList.remove("active"));
      tabContents.forEach((t) => t.classList.remove("active"));

      btn.classList.add("active");
      const activeContent = document.getElementById(`tab-${targetTab}`);
      if (activeContent) {
        activeContent.classList.add("active");
      }
    });
  });
}

// Fetch governance metrics & health score
async function loadGovernanceStatus() {
  try {
    const res = await fetch("/api/governance/status");
    const json = await res.json();
    if (json.status === "success") {
      document.getElementById("healthScore").innerText = `${json.health_score}%`;
      document.getElementById("buCount").innerText = json.business_units_count;
      document.getElementById("rulesCount").innerText = json.quality_rules_count;
      document.getElementById("glossaryCount").innerText = json.glossary_terms_count;

      const alertsTbody = document.getElementById("alertsTableBody");
      if (alertsTbody && json.recent_alerts) {
        alertsTbody.innerHTML = json.recent_alerts
          .map(
            (alt) => `
          <tr>
            <td><span class="badge badge-${alt.severidad}">${alt.tipo}</span></td>
            <td><strong>${alt.dominio}</strong></td>
            <td>${alt.mensaje}</td>
            <td><span style="color: var(--text-muted); font-size: 11px;">${alt.timestamp}</span></td>
          </tr>
        `
          )
          .join("");
      }
    }
  } catch (err) {
    console.error("Error loading governance status:", err);
  }
}

// Fetch and display Dataplex catalog entries
async function loadCatalogEntries() {
  try {
    const res = await fetch("/api/catalog/entries");
    const json = await res.json();
    if (json.status === "success") {
      const tbody = document.getElementById("catalogTableBody");
      if (tbody && json.data) {
        tbody.innerHTML = json.data
          .map(
            (entry) => `
          <tr>
            <td><code>${entry.name}</code></td>
            <td><span class="badge badge-primary">${entry.category}</span></td>
            <td>${entry.description}</td>
            <td><span class="badge badge-warning">${entry.security_level || 'USO_INTERNO'}</span></td>
            <td><strong>${entry.unit || 'CMI Corporativo'}</strong></td>
          </tr>
        `
          )
          .join("");
      }
    }
  } catch (err) {
    console.error("Error loading catalog entries:", err);
  }
}

// Load and populate Admin Configuration
let currentConfig = {};
async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const json = await res.json();
    if (json.status === "success") {
      currentConfig = json.data;

      // Populate Form Fields
      document.getElementById("cfgProject").value = currentConfig.infraestructura?.gcp_project_id || "";
      document.getElementById("cfgDataset").value = currentConfig.infraestructura?.bigquery_dataset_default || "";
      document.getElementById("cfgBucket").value = currentConfig.infraestructura?.gcs_bucket_politicas || "";
      document.getElementById("cfgEntryGroup").value = currentConfig.infraestructura?.dataplex_entry_group || "";

      document.getElementById("cfgMaxNulls").value = currentConfig.reglas_calidad?.tolerancia_nulos_maxima_pct || 5;
      document.getElementById("cfgMaxReturns").value = currentConfig.reglas_calidad?.umbral_alerta_devoluciones_pct || 8;
      document.getElementById("cfgMaxFreshness").value = currentConfig.reglas_calidad?.frescura_datos_max_horas || 24;

      renderGlossaryAdmin(currentConfig.glosario_terminos || []);
    }
  } catch (err) {
    console.error("Error loading config:", err);
  }
}

function renderGlossaryAdmin(glossary) {
  const container = document.getElementById("glossaryAdminList");
  if (!container) return;
  container.innerHTML = glossary
    .map(
      (item, idx) => `
      <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--border-color); padding: 14px; border-radius: var(--radius-sm); margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="color: var(--primary); font-size: 14px;">${item.termino}</strong>
          <span class="badge badge-primary">${item.unidad_negocio}</span>
        </div>
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 4px;">${item.definicion}</p>
        <div style="font-size: 12px; font-family: monospace; color: #a7f3d0;">Fórmula: ${item.formula_sql}</div>
      </div>
    `
    )
    .join("");
}

// Save Admin Configuration
async function saveConfig() {
  if (!currentConfig.infraestructura) currentConfig.infraestructura = {};
  if (!currentConfig.reglas_calidad) currentConfig.reglas_calidad = {};

  currentConfig.infraestructura.gcp_project_id = document.getElementById("cfgProject").value;
  currentConfig.infraestructura.bigquery_dataset_default = document.getElementById("cfgDataset").value;
  currentConfig.infraestructura.gcs_bucket_politicas = document.getElementById("cfgBucket").value;
  currentConfig.infraestructura.dataplex_entry_group = document.getElementById("cfgEntryGroup").value;

  currentConfig.reglas_calidad.tolerancia_nulos_maxima_pct = parseFloat(document.getElementById("cfgMaxNulls").value);
  currentConfig.reglas_calidad.umbral_alerta_devoluciones_pct = parseFloat(document.getElementById("cfgMaxReturns").value);
  currentConfig.reglas_calidad.frescura_datos_max_horas = parseInt(document.getElementById("cfgMaxFreshness").value);

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: currentConfig }),
    });
    const json = await res.json();
    if (json.status === "success") {
      alert("✅ Configuración de Gobierno de Datos CMI guardada y aplicada exitosamente.");
      loadGovernanceStatus();
    } else {
      alert("❌ Error al guardar la configuración.");
    }
  } catch (err) {
    alert("❌ Error de comunicación con el servidor.");
  }
}

// Chat controller
function initChat() {
  const chatInput = document.getElementById("chatInput");
  const btnSend = document.getElementById("btnSend");
  const quickBtns = document.querySelectorAll(".quick-btn");

  btnSend.addEventListener("click", sendMessage);
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  quickBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      chatInput.value = prompt;
      sendMessage();
    });
  });
}

async function sendMessage() {
  const chatInput = document.getElementById("chatInput");
  const messagesContainer = document.getElementById("chatMessages");
  const buSelect = document.getElementById("globalBuSelect");

  const text = chatInput.value.trim();
  if (!text) return;

  const bu = buSelect ? buSelect.value : "cmi_alimentos";

  // Append user message
  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user";
  userBubble.innerHTML = `<div style="font-weight: 600; font-size: 11px; margin-bottom: 4px; opacity: 0.8;">TÚ [${bu.toUpperCase()}]</div>${escapeHtml(text)}`;
  messagesContainer.appendChild(userBubble);
  chatInput.value = "";
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  // Append thinking bubble
  const thinkingBubble = document.createElement("div");
  thinkingBubble.className = "chat-bubble agent";
  thinkingBubble.innerHTML = `
    <div style="display: flex; align-items: center; gap: 10px; color: var(--primary);">
      <div class="status-dot"></div>
      <span>El Agente Especialista CMI está buscando en Dataplex Knowledge Catalog y verificando reglas de gobierno...</span>
    </div>
  `;
  messagesContainer.appendChild(thinkingBubble);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, business_unit: bu }),
    });
    const data = await res.json();

    let stagesHtml = "";
    if (data.stages && data.stages.length > 0) {
      stagesHtml = `
        <div class="agent-stages">
          <h4>Orquestación de Gobierno de Datos</h4>
          ${data.stages.map((s) => `<div class="stage-item done"><strong>Etapa ${s.stage}:</strong> ${s.title}</div>`).join("")}
        </div>
      `;
    }

    thinkingBubble.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: var(--primary); margin-bottom: 12px;">
        <span>🛡️ Agente Especialista en Gobierno de Datos CMI</span>
      </div>
      ${stagesHtml}
      <div class="agent-markdown">${formatMarkdown(data.response || "No se obtuvo respuesta.")}</div>
    `;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  } catch (err) {
    thinkingBubble.innerHTML = `<div style="color: var(--danger);">❌ Error de conexión al consultar el agente.</div>`;
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}

function formatMarkdown(text) {
  if (!text) return "";

  // Split lines
  const lines = text.split("\n");
  let html = "";
  let inTable = false;
  let tableHeaderParsed = false;
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();

    // Check for Table Row
    if (line.startsWith("|") && line.endsWith("|")) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      // Check if it's separator row like |---|---|
      if (/^\|[-|\s]+\|$/.test(line)) {
        tableHeaderParsed = true;
        continue;
      }

      if (!inTable) {
        inTable = true;
        tableHeaderParsed = false;
        html += '<table class="custom-table" style="margin: 14px 0; width: 100%; border-collapse: collapse;">';
      }

      const cells = line.split("|").slice(1, -1).map(c => c.trim());
      if (!tableHeaderParsed) {
        html += "<thead><tr>" + cells.map(c => `<th style="padding: 10px 12px; background: rgba(14, 165, 233, 0.15); color: #fff; text-align: left; border: 1px solid var(--border-color);">${formatInline(c)}</th>`).join("") + "</tr></thead><tbody>";
      } else {
        html += "<tr>" + cells.map(c => `<td style="padding: 8px 12px; border: 1px solid var(--border-color);">${formatInline(c)}</td>`).join("") + "</tr>";
      }
      continue;
    } else {
      if (inTable) {
        html += "</tbody></table>";
        inTable = false;
      }
    }

    // Check for Lists (- or *)
    if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) {
        inList = true;
        html += '<ul style="margin: 8px 0; padding-left: 20px;">';
      }
      html += `<li style="margin-bottom: 4px; color: var(--text-secondary);">${formatInline(line.substring(2))}</li>`;
      continue;
    } else {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
    }

    // Horizontal Rule
    if (line === "---" || line === "***" || line === "___") {
      html += '<hr style="border: 0; height: 1px; background: var(--border-color); margin: 16px 0;">';
      continue;
    }

    // Headings
    if (line.startsWith("### ")) {
      html += `<h3 style="color: #ffffff; margin: 16px 0 8px 0; font-family: 'Outfit', sans-serif; font-size: 16px; font-weight: 700;">${formatInline(line.substring(4))}</h3>`;
      continue;
    }
    if (line.startsWith("#### ")) {
      html += `<h4 style="color: var(--primary); margin: 12px 0 6px 0; font-size: 14px; font-weight: 600;">${formatInline(line.substring(5))}</h4>`;
      continue;
    }

    // Regular paragraphs
    if (line.length > 0) {
      html += `<p style="margin-bottom: 8px; line-height: 1.6; color: var(--text-primary); font-size: 14px;">${formatInline(line)}</p>`;
    }
  }

  if (inTable) html += "</tbody></table>";
  if (inList) html += "</ul>";

  return html;
}

function formatInline(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.35); padding: 2px 6px; border-radius: 4px; color: #a7f3d0; font-family: monospace;">$1</code>');
}

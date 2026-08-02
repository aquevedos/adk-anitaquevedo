/**
 * Data Stewards & AI/RAG Dataset Readiness UI Controller
 */

function initStewards() {
  loadDomains();
  loadAIReadiness();
}

async function loadDomains() {
  const container = document.getElementById("domains-grid");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/stewards/domains`);
    const data = await res.json();
    if (data.status === "success") {
      renderDomains(data.data);
    }
  } catch (err) {
    console.error("Error loading domains:", err);
  }
}

function renderDomains(domains) {
  const container = document.getElementById("domains-grid");
  if (!container) return;

  container.innerHTML = domains.map(d => `
    <div class="asset-card">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <span class="tag-badge">Dominio de Negocio</span>
          <h3 class="asset-name" style="margin-top: 0.35rem;">${escapeHtml(d.nombre)}</h3>
        </div>
        <span style="font-size: 0.75rem; color: ${d.criticidad === 'Crítica' ? 'var(--accent-rose)' : 'var(--accent-amber)'}; font-weight: 700;">${escapeHtml(d.criticidad)}</span>
      </div>

      <div style="font-size: 0.85rem; color: var(--text-secondary);">
        👤 <strong>Data Steward:</strong> ${escapeHtml(d.steward)}<br/>
        ✉️ <code>${escapeHtml(d.email)}</code>
      </div>

      <div class="metrics-row">
        <div>
          <span style="color: #9ca3af; font-size: 0.72rem;">TABLAS ACTIVAS</span>
          <div style="font-weight: 700; color: #fff;">${d.active_assets_count || 0}</div>
        </div>
        <div>
          <span style="color: #9ca3af; font-size: 0.72rem;">CALIDAD MEDIA</span>
          <div style="font-weight: 700; color: var(--accent-emerald);">${d.avg_quality_score || 95}%</div>
        </div>
        <div>
          <span style="color: #9ca3af; font-size: 0.72rem;">CERTIFICADAS IA</span>
          <div style="font-weight: 700; color: #93c5fd;">${d.ai_certified_assets || 0}</div>
        </div>
      </div>
    </div>
  `).join("");
}

async function loadAIReadiness() {
  const container = document.getElementById("ai-readiness-table-body");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/stewards/ai_readiness`);
    const data = await res.json();
    if (data.status === "success") {
      renderAIReadinessTable(data.data);
    }
  } catch (err) {
    console.error("Error loading AI readiness:", err);
  }
}

function renderAIReadinessTable(items) {
  const container = document.getElementById("ai-readiness-table-body");
  if (!container) return;

  container.innerHTML = items.map(item => {
    const isCert = item.certified_for_rag;
    return `
      <tr>
        <td><strong>${escapeHtml(item.name)}</strong></td>
        <td><span class="cloud-badge ${item.cloud.toLowerCase()}">${escapeHtml(item.cloud)}</span></td>
        <td><code>${escapeHtml(item.domain)}</code></td>
        <td><strong style="color: ${item.quality_score >= 90 ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">${item.quality_score}%</strong></td>
        <td>${item.dynamic_masking ? `🔒 Masked (DLP)` : `👁️ Unmasked`}</td>
        <td>
          <span style="font-weight: 700; color: ${isCert ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">
            ${isCert ? `✅ Certificado para RAG` : `⚠️ No Aprobado`}
          </span>
          <div style="font-size: 0.75rem; color: #9ca3af;">${escapeHtml(item.compliance_status)}</div>
        </td>
        <td>
          <button class="${isCert ? 'btn-secondary' : 'btn-primary'}" style="padding: 0.35rem 0.75rem; font-size: 0.78rem;" onclick="toggleAICertification('${item.asset_id}', ${!isCert})">
            ${isCert ? 'Revocar' : 'Certificar IA'}
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

async function toggleAICertification(assetId, newState) {
  try {
    const res = await fetch(`${API_BASE}/api/stewards/certify_ai/${assetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ certified: newState, notes: newState ? "Certificado por Data Steward para Modelos RAG" : "Revocado por revisión de cumplimiento" })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast(data.data.message, "success");
      loadAIReadiness();
      loadDomains();
      loadCatalogAssets();
    }
  } catch (err) {
    console.error("Error certifying AI dataset:", err);
    showToast("Error al actualizar certificación", "error");
  }
}

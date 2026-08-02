/**
 * Knowledge Catalog & Context Graph UI Controller
 */

function initCatalog() {
  loadCatalogAssets();

  const searchInput = document.getElementById("catalog-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", debounce(() => {
      const q = searchInput.value.trim();
      if (q.length > 0) {
        searchAssets(q);
      } else {
        loadCatalogAssets();
      }
    }, 300));
  }

  // Cloud filters
  const filterBtns = document.querySelectorAll(".cloud-filter-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const cloud = btn.getAttribute("data-cloud");
      loadCatalogAssets(cloud);
    });
  });
}

async function loadCatalogAssets(cloud = "all") {
  try {
    const url = cloud && cloud !== "all" ? `${API_BASE}/api/catalog/assets?cloud=${encodeURIComponent(cloud)}` : `${API_BASE}/api/catalog/assets`;
    const res = await fetch(url);
    const data = await res.json();
    if (data.status === "success") {
      AppState.assets = data.data;
      renderAssetCards(data.data);
    }
  } catch (err) {
    console.error("Error loading catalog assets:", err);
  }
}

async function searchAssets(query) {
  try {
    const res = await fetch(`${API_BASE}/api/catalog/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (data.status === "success") {
      renderAssetCards(data.data);
    }
  } catch (err) {
    console.error("Error searching assets:", err);
  }
}

function renderAssetCards(assets) {
  const grid = document.getElementById("assets-grid");
  if (!grid) return;

  if (assets.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: #9ca3af; padding: 2rem;">No se encontraron activos para los filtros seleccionados.</div>`;
    return;
  }

  grid.innerHTML = assets.map(asset => {
    const cloudClass = (asset.cloud || "").toLowerCase().replace(/\s+/g, '-');
    const qualityScore = asset.dataplex_quality?.overall_score || 95;
    const qualityBadgeColor = qualityScore >= 90 ? "var(--accent-emerald)" : "var(--accent-amber)";
    const dlpRisk = asset.dlp_status?.risk_level || "Bajo";

    return `
      <div class="asset-card">
        <div class="asset-header">
          <div>
            <span class="cloud-badge ${cloudClass}">${asset.cloud} • ${asset.service}</span>
            <h3 class="asset-name" style="margin-top: 0.35rem;">${escapeHtml(asset.name)}</h3>
            <span class="asset-table-sub">${escapeHtml(asset.project_or_db)}.${escapeHtml(asset.dataset)}.${escapeHtml(asset.table_name)}</span>
          </div>
        </div>

        <p class="asset-desc">${escapeHtml(asset.description)}</p>

        <div class="metrics-row">
          <div>
            <span style="color: #9ca3af; font-size: 0.72rem;">CALIDAD DATAPLEX</span>
            <div style="font-weight: 700; color: ${qualityBadgeColor};">${qualityScore}%</div>
          </div>
          <div>
            <span style="color: #9ca3af; font-size: 0.72rem;">RIESGO DLP</span>
            <div style="font-weight: 700; color: ${dlpRisk.includes('Alto') || dlpRisk.includes('Crítico') ? 'var(--accent-rose)' : '#93c5fd'};">${dlpRisk}</div>
          </div>
          <div>
            <span style="color: #9ca3af; font-size: 0.72rem;">COLUMNAS</span>
            <div style="font-weight: 700; color: #fff;">${asset.columns?.length || 0}</div>
          </div>
        </div>

        <div class="asset-actions" style="flex-wrap: wrap;">
          <button class="btn-secondary" onclick="openAssetDetailModal('${asset.id}')">📋 Esquema</button>
          <button class="btn-secondary" onclick="viewLineageForAsset('${asset.id}')">🔗 Linaje</button>
          <button class="btn-secondary" onclick="navigateToAssetTagging('${asset.id}')">🏷️ Tags</button>
          <button class="btn-primary" onclick="openMetadataEditModal('${asset.id}')">✏️ Editar</button>
        </div>
      </div>
    `;
  }).join("");
}

function navigateToAssetTagging(assetId) {
  const taggingBtn = document.querySelector('[data-pane="pane-tagging"]');
  if (taggingBtn) {
    taggingBtn.click();
  } else {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content-pane").forEach(p => p.classList.remove("active"));
    const pane = document.getElementById("pane-tagging");
    if (pane) pane.classList.add("active");
  }
  if (typeof selectTaggingAsset === "function") {
    selectTaggingAsset(assetId);
  }
}

async function openAssetDetailModal(assetId) {
  try {
    const res = await fetch(`${API_BASE}/api/catalog/assets/${assetId}`);
    const data = await res.json();
    if (data.status !== "success") return;

    const asset = data.data;
    AppState.selectedAsset = asset;

    const modal = document.getElementById("asset-detail-modal");
    const titleEl = document.getElementById("modal-asset-title");
    const bodyEl = document.getElementById("modal-asset-body");

    if (titleEl) titleEl.innerText = `${asset.name} (${asset.cloud} - ${asset.service})`;

    const columnsHtml = (asset.columns || []).map(col => `
      <tr>
        <td><strong>${escapeHtml(col.name)}</strong></td>
        <td><code>${escapeHtml(col.type)}</code></td>
        <td>${escapeHtml(col.description || "-")}</td>
        <td>${col.is_pii ? `<span class="pii-badge">${escapeHtml(col.dlp_info_type || 'PII')}</span>` : `<span style="color: #9ca3af;">No</span>`}</td>
        <td>${col.policy_tag ? `<span class="tag-badge">${escapeHtml(col.policy_tag)}</span>` : `<span style="color: #6b7280;">Ninguno</span>`}</td>
        <td>${col.masked ? `🔒 Enmascarado` : `👁️ Visible`}</td>
      </tr>
    `).join("");

    bodyEl.innerHTML = `
      <div>
        <p style="color: #d1d5db; margin-bottom: 0.5rem;"><strong>Descripción:</strong> ${escapeHtml(asset.description)}</p>
        <p style="color: #9ca3af; font-size: 0.85rem;"><strong>Data Steward:</strong> ${escapeHtml(asset.steward || "No asignado")}</p>
        <p style="color: #9ca3af; font-size: 0.85rem;"><strong>Ubicación Física:</strong> <code>${escapeHtml(asset.project_or_db)}.${escapeHtml(asset.dataset)}.${escapeHtml(asset.table_name)}</code></p>
      </div>

      <h4 style="margin-top: 0.75rem; color: #93c5fd; font-size: 0.95rem;">Esquema y Clasificación de Columnas</h4>
      <div style="overflow-x: auto;">
        <table class="governance-table">
          <thead>
            <tr>
              <th>Columna</th>
              <th>Tipo</th>
              <th>Descripción</th>
              <th>DLP PII</th>
              <th>Policy Tag</th>
              <th>Enmascaramiento</th>
            </tr>
          </thead>
          <tbody>
            ${columnsHtml}
          </tbody>
        </table>
      </div>

      <div style="margin-top: 1rem;">
        <h4 style="color: #93c5fd; font-size: 0.95rem; margin-bottom: 0.4rem;">Golden Query Pre-Aprobada</h4>
        <pre><code>${escapeHtml(asset.golden_query || "SELECT * FROM dataset.table LIMIT 10;")}</code></pre>
      </div>
    `;

    modal.classList.add("active");
  } catch (err) {
    console.error("Error opening asset modal:", err);
  }
}

function openMetadataEditModal(assetId) {
  const asset = AppState.assets.find(a => a.id === assetId);
  if (!asset) return;

  const modal = document.getElementById("asset-edit-modal");
  document.getElementById("edit-asset-id").value = asset.id;
  document.getElementById("edit-asset-name").innerText = asset.name;
  document.getElementById("edit-asset-description").value = asset.description;
  document.getElementById("edit-asset-steward").value = asset.steward || "";
  document.getElementById("edit-asset-golden-query").value = asset.golden_query || "";

  modal.classList.add("active");
}

async function saveMetadataEdits() {
  const assetId = document.getElementById("edit-asset-id").value;
  const description = document.getElementById("edit-asset-description").value.trim();
  const steward = document.getElementById("edit-asset-steward").value.trim();
  const golden_query = document.getElementById("edit-asset-golden-query").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/catalog/assets/${assetId}/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description, steward, golden_query })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast("Metadatos actualizados en Knowledge Catalog", "success");
      closeAllModals();
      loadCatalogAssets();
    }
  } catch (err) {
    console.error("Error updating metadata:", err);
    showToast("Error al guardar cambios de metadatos", "error");
  }
}

function closeAllModals() {
  document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
}

function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/**
 * End-to-End Data Lineage & Impact Analysis UI Controller
 */

let currentLineageData = null;

function initLineage() {
  loadLineageSelector();
}

async function loadLineageSelector() {
  const selectEl = document.getElementById("lineage-asset-select");
  if (!selectEl) return;

  try {
    const res = await fetch(`${API_BASE}/api/catalog/assets`);
    const data = await res.json();
    if (data.status === "success") {
      selectEl.innerHTML = data.data.map(a => `
        <option value="${a.id}">[${a.cloud}] ${a.name} (${a.table_name})</option>
      `).join("");

      if (data.data.length > 0) {
        viewLineageForAsset(data.data[0].id);
      }
    }
  } catch (err) {
    console.error("Error loading lineage selector:", err);
  }
}

async function viewLineageForAsset(assetId) {
  if (!assetId) {
    const selectEl = document.getElementById("lineage-asset-select");
    if (selectEl) assetId = selectEl.value;
  }
  if (!assetId) return;

  // Switch to lineage tab if not already on it
  const lineageTabBtn = document.querySelector('[data-target="lineage-tab"]');
  if (lineageTabBtn && !lineageTabBtn.classList.contains("active")) {
    lineageTabBtn.click();
  }

  const selectEl = document.getElementById("lineage-asset-select");
  if (selectEl) selectEl.value = assetId;

  try {
    const res = await fetch(`${API_BASE}/api/lineage/${assetId}`);
    const data = await res.json();
    if (data.status === "success") {
      currentLineageData = data.data;
      renderLineageDiagram(data.data);
    }
  } catch (err) {
    console.error("Error fetching lineage:", err);
  }
}

function renderCurrentLineage() {
  if (currentLineageData) {
    renderLineageDiagram(currentLineageData);
  }
}

function renderLineageDiagram(lineage) {
  const container = document.getElementById("lineage-svg-container");
  if (!container) return;

  const width = container.clientWidth || 900;
  const height = 480;

  const nodes = lineage.nodes || [];
  const upstreamNodes = nodes.filter(n => n.type === "upstream");
  const centralNode = nodes.find(n => n.type === "central");
  const downstreamNodes = nodes.filter(n => n.type === "downstream");

  // Calculate coordinates
  const colX = {
    upstream: 160,
    central: width / 2,
    downstream: width - 180
  };

  const nodeElements = [];
  const edgeElements = [];

  // Central Node Coords
  const centralY = height / 2;
  const centralNodePos = { x: colX.central, y: centralY, data: centralNode };

  // Upstream positions
  const upSpacing = height / (upstreamNodes.length + 1);
  const upPositions = upstreamNodes.map((node, i) => ({
    x: colX.upstream,
    y: (i + 1) * upSpacing,
    data: node
  }));

  // Downstream positions
  const downSpacing = height / (downstreamNodes.length + 1);
  const downPositions = downstreamNodes.map((node, i) => ({
    x: colX.downstream,
    y: (i + 1) * downSpacing,
    data: node
  }));

  // Build Edge Paths (Bezier Curves)
  upPositions.forEach(up => {
    const pathD = `M ${up.x + 90} ${up.y} C ${(up.x + centralNodePos.x)/2} ${up.y}, ${(up.x + centralNodePos.x)/2} ${centralNodePos.y}, ${centralNodePos.x - 110} ${centralNodePos.y}`;
    edgeElements.push(`
      <path d="${pathD}" fill="none" stroke="rgba(59, 130, 246, 0.4)" stroke-width="2.5" stroke-dasharray="4 2"/>
      <circle cx="${(up.x + centralNodePos.x)/2}" cy="${(up.y + centralNodePos.y)/2}" r="3" fill="#3b82f6" />
    `);
  });

  downPositions.forEach(down => {
    const pathD = `M ${centralNodePos.x + 110} ${centralNodePos.y} C ${(centralNodePos.x + down.x)/2} ${centralNodePos.y}, ${(centralNodePos.x + down.x)/2} ${down.y}, ${down.x - 90} ${down.y}`;
    edgeElements.push(`
      <path d="${pathD}" fill="none" stroke="rgba(139, 92, 246, 0.5)" stroke-width="2.5" />
      <circle cx="${(centralNodePos.x + down.x)/2}" cy="${(centralNodePos.y + down.y)/2}" r="3" fill="#8b5cf6" />
    `);
  });

  // Render SVG
  container.innerHTML = `
    <svg class="lineage-svg" viewBox="0 0 ${width} ${height}">
      <defs>
        <filter id="nodeGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="rgba(0,0,0,0.5)" />
        </filter>
      </defs>

      <!-- Grid Background -->
      <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
        <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(255, 255, 255, 0.03)" stroke-width="1"/>
      </pattern>
      <rect width="100%" height="100%" fill="url(#grid)" />

      <!-- Edges -->
      <g class="lineage-edges">
        ${edgeElements.join("")}
      </g>

      <!-- Upstream Nodes -->
      <g class="lineage-nodes-upstream">
        ${upPositions.map(p => `
          <g transform="translate(${p.x - 90}, ${p.y - 30})" filter="url(#nodeGlow)">
            <rect width="180" height="60" rx="8" fill="#1e293b" stroke="rgba(255,255,255,0.15)" stroke-width="1.5" />
            <text x="12" y="24" fill="#93c5fd" font-size="11" font-weight="700">UPSTREAM ORIGIN</text>
            <text x="12" y="42" fill="#fff" font-size="11" font-weight="600">${escapeXml(truncateStr(p.data.label, 22))}</text>
          </g>
        `).join("")}
      </g>

      <!-- Central Node -->
      <g class="lineage-node-central" transform="translate(${centralNodePos.x - 110}, ${centralNodePos.y - 45})" filter="url(#nodeGlow)">
        <rect width="220" height="90" rx="12" fill="#0f172a" stroke="#3b82f6" stroke-width="2" />
        <rect x="0" y="0" width="220" height="26" rx="12" fill="rgba(59, 130, 246, 0.2)" />
        <text x="14" y="18" fill="#93c5fd" font-size="11" font-weight="700">📍 CURRENT ASSET [GCP/AWS/AZURE]</text>
        <text x="14" y="48" fill="#ffffff" font-size="13" font-weight="700">${escapeXml(truncateStr(centralNodePos.data?.label || "", 20))}</text>
        <text x="14" y="68" fill="#9ca3af" font-size="11">Score: ${centralNodePos.data?.quality_score || 95}% | DLP: ${centralNodePos.data?.risk_level || 'Bajo'}</text>
      </g>

      <!-- Downstream Nodes -->
      <g class="lineage-nodes-downstream">
        ${downPositions.map(p => `
          <g transform="translate(${p.x - 90}, ${p.y - 30})" filter="url(#nodeGlow)">
            <rect width="180" height="60" rx="8" fill="#1e293b" stroke="rgba(139, 92, 246, 0.4)" stroke-width="1.5" />
            <text x="12" y="24" fill="#c4b5fd" font-size="11" font-weight="700">DOWNSTREAM CONSUMER</text>
            <text x="12" y="42" fill="#fff" font-size="11" font-weight="600">${escapeXml(truncateStr(p.data.label, 22))}</text>
          </g>
        `).join("")}
      </g>
    </svg>
  `;

  // Render impact panel
  const impactSummaryEl = document.getElementById("lineage-impact-summary");
  if (impactSummaryEl) {
    impactSummaryEl.innerHTML = `
      <div style="background: rgba(0,0,0,0.25); padding: 1rem; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
        <h4 style="color: #93c5fd; font-size: 0.95rem; margin-bottom: 0.4rem;">Análisis de Linaje y Dependencias</h4>
        <p style="font-size: 0.85rem; color: #d1d5db;">El activo <strong>${escapeHtml(lineage.asset_name)}</strong> se alimenta de <strong>${lineage.upstream_count}</strong> fuentes primarias y transfiere valor hacia <strong>${lineage.downstream_count}</strong> consumidores directos (incluyendo modelos de IA en Vertex AI y tableros BI).</p>
      </div>
    `;
  }
}

async function triggerImpactSimulation() {
  const selectEl = document.getElementById("lineage-asset-select");
  const assetId = selectEl ? selectEl.value : null;
  if (!assetId) return;

  try {
    const res = await fetch(`${API_BASE}/api/lineage/impact_analysis/${assetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modified_columns: ["customer_id", "email_address", "billing_tax_id"] })
    });
    const data = await res.json();
    if (data.status === "success") {
      const imp = data.data;
      showToast(`Impacto simulado: ${imp.total_downstream_impacted} sistemas dependientes afectados.`, "info");
    }
  } catch (err) {
    console.error("Error analyzing impact:", err);
  }
}

function truncateStr(str, max) {
  if (!str) return "";
  return str.length > max ? str.substring(0, max) + "..." : str;
}

function escapeXml(unsafe) {
  return unsafe.replace(/[<>&'"]/g, c => {
    switch (c) {
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '&': return '&amp;';
      case '\'': return '&apos;';
      case '"': return '&quot;';
    }
  });
}

/**
 * Looker Semantic Layer & Metric Governance Controller
 */

function initLooker() {
  loadLookerMetrics();
}

async function loadLookerMetrics() {
  const container = document.getElementById("looker-metrics-grid");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/looker/semantic_metrics`);
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      renderLookerMetrics(data.data);
    }
  } catch (err) {
    console.error("Error loading looker metrics:", err);
  }
}

function renderLookerMetrics(metrics) {
  const container = document.getElementById("looker-metrics-grid");
  if (!container) return;

  container.innerHTML = metrics.map(m => `
    <div class="pastel-card" style="border-top: 3px solid var(--pastel-blue-accent);">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span class="stat-metric-badge badge-blue">${escapeHtml(m.domain)}</span>
        <span class="stat-metric-badge badge-emerald">● ${escapeHtml(m.governance_status)}</span>
      </div>

      <div>
        <strong style="color: var(--text-main); font-size: 1rem;">${escapeHtml(m.name)}</strong>
        <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">${escapeHtml(m.definition)}</div>
      </div>

      <div style="background: #0f172a; padding: 0.7rem; border-radius: var(--radius-sm); font-family: monospace; font-size: 0.75rem; color: #7dd3fc; overflow-x: auto;">
        <div># LookML Dimension / Measure</div>
        <div>view: ${escapeHtml(m.lookml_view)} {</div>
        <div>  measure: ${escapeHtml(m.id)} {</div>
        <div>    sql: ${escapeHtml(m.lookml_sql)};;</div>
        <div>  }</div>
        <div>}</div>
      </div>

      <div style="font-size: 0.75rem; color: var(--text-main); background: var(--bg-app); padding: 0.5rem 0.75rem; border-radius: var(--radius-sm);">
        <div><strong>Tabla Origen:</strong> <code style="color: var(--pastel-blue-text);">${escapeHtml(m.source_table)}</code></div>
        <div><strong>Steward Responsable:</strong> ${escapeHtml(m.owner_steward)}</div>
        <div><strong>Protección PII:</strong> ${escapeHtml(m.pii_classification)}</div>
      </div>

      <div style="font-size: 0.72rem; color: var(--text-muted);">
        📊 <strong>Consumidores:</strong> ${(m.dashboard_consumers || []).join(" • ")}
      </div>
    </div>
  `).join("");
}

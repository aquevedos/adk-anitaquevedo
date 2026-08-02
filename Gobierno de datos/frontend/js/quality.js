/**
 * Dataplex Data Quality & Advanced Business Rules (Drill-Down & Dynamic Thresholds)
 */

function initQuality() {
  loadQualitySelector();
  loadGlobalHealthBreakdown();
  loadRealDataplexConsoleScans();
  loadBusinessQualityRules();
}

async function loadQualitySelector() {
  const selectEl = document.getElementById("quality-asset-select");
  if (!selectEl) return;

  try {
    const res = await fetch(`${API_BASE}/api/catalog/assets`);
    const data = await res.json();
    if (data.status === "success") {
      selectEl.innerHTML = data.data.map(a => `
        <option value="${a.id}">[${a.cloud}] ${a.name} (Score: ${a.dataplex_quality?.overall_score || 90}%)</option>
      `).join("");

      if (data.data.length > 0) {
        runQualityScanForAsset(data.data[0].id);
      }
    }
  } catch (err) {
    console.error("Error loading quality assets:", err);
  }
}

async function loadGlobalHealthBreakdown() {
  const alertsCont = document.getElementById("quality-alerts-container");
  if (!alertsCont) return;

  try {
    const res = await fetch(`${API_BASE}/api/quality/health`);
    const data = await res.json();
    if (data.status === "success") {
      const alerts = data.data.alerts || [];
      if (alerts.length === 0) {
        alertsCont.innerHTML = `<div style="color: var(--pastel-emerald-text); font-size: 0.82rem;">✅ Todos los activos multi-cloud cumplen con el umbral mínimo de calidad (>90%).</div>`;
      } else {
        alertsCont.innerHTML = alerts.map(al => `
          <div style="background: var(--pastel-rose-bg); border: 1px solid var(--pastel-rose-border); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between;">
              <strong style="color: var(--pastel-rose-text); font-size: 0.82rem;">${escapeHtml(al.name)} (${escapeHtml(al.cloud)})</strong>
              <span style="font-weight: 700; color: var(--pastel-rose-text);">${al.score}%</span>
            </div>
            <p style="color: var(--text-main); font-size: 0.75rem; margin-top: 0.2rem;">${escapeHtml(al.issue)}</p>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    console.error("Error loading health breakdown:", err);
  }
}

async function runQualityScanForAsset(assetId) {
  const container = document.getElementById("quality-results-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/quality/scan/${assetId}`);
    const data = await res.json();
    if (data.status === "success") {
      const q = data.data.quality || {};
      const score = q.overall_score || 95;
      const rules = q.rule_results || [];

      container.innerHTML = `
        <div class="pastel-card" style="margin-bottom: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h3 style="font-size: 1.1rem; font-weight: 700; color: var(--text-main);">${escapeHtml(data.data.name)}</h3>
              <p style="font-size: 0.78rem; color: var(--pastel-blue-text); font-family: monospace;">${escapeHtml(data.data.resource)}</p>
            </div>
            <div style="text-align: right;">
              <div style="font-size: 1.8rem; font-weight: 800; color: ${score >= 90 ? 'var(--pastel-emerald-text)' : 'var(--pastel-rose-text)'};">${score}%</div>
              <span class="stat-metric-badge ${score >= 90 ? 'badge-emerald' : 'badge-rose'}">
                ${score >= 90 ? '● Dataplex Aprobado' : '● Requiere Remediación'}
              </span>
            </div>
          </div>

          <div style="margin-top: 1rem; overflow-x: auto;">
            <table class="table-clean">
              <thead>
                <tr>
                  <th>Regla de Calidad Dataplex</th>
                  <th>Estado</th>
                  <th>Detalle de Inspección</th>
                </tr>
              </thead>
              <tbody>
                ${rules.map(r => `
                  <tr>
                    <td><strong>${escapeHtml(r.rule)}</strong></td>
                    <td>
                      <span class="stat-metric-badge ${r.status === 'PASSED' ? 'badge-emerald' : 'badge-rose'}">
                        ${r.status === 'PASSED' ? 'PASÓ' : 'FALLÓ'}
                      </span>
                    </td>
                    <td style="color: var(--text-main); font-size: 0.8rem;">${escapeHtml(r.details)}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }
  } catch (err) {
    console.error("Error running quality scan:", err);
  }
}

// ---------------------------------------------------------------------------
// REGLAS DE NEGOCIO AVANZADAS (ANOMALÍAS EN VENTAS, CONCILIACIÓN, DRILL-DOWN)
// ---------------------------------------------------------------------------
async function loadBusinessQualityRules() {
  try {
    const res = await fetch(`${API_BASE}/api/quality/business_rules`);
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      renderBusinessRulesList(data.data);
      if (data.last_evaluation) {
        renderBusinessRulesEvaluation(data.last_evaluation);
      }
    }
  } catch (err) {
    console.error("Error loading business rules:", err);
  }
}

function renderBusinessRulesList(rules) {
  const container = document.getElementById("business-rules-list-container");
  if (!container) return;

  container.innerHTML = rules.map(r => {
    let thresholdInput = "";
    if (r.metric_type === "PERCENT_DEVIATION") {
      thresholdInput = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <input type="number" step="1" min="1" max="100" id="threshold-${r.rule_id}" class="form-input" style="width: 80px; padding: 0.3rem 0.5rem; font-size: 0.8rem;" value="${r.current_threshold_percent}">
          <span style="font-size: 0.75rem; color: var(--text-muted);">% máx variación</span>
          <button class="btn-secondary" style="font-size: 0.7rem; padding: 0.3rem 0.6rem;" onclick="updateThreshold('${r.rule_id}')">Guardar</button>
        </div>
      `;
    } else if (r.metric_type === "TOLERANCE_AMOUNT_USD") {
      thresholdInput = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <input type="number" step="0.01" min="0" id="threshold-${r.rule_id}" class="form-input" style="width: 80px; padding: 0.3rem 0.5rem; font-size: 0.8rem;" value="${r.current_threshold_amount}">
          <span style="font-size: 0.75rem; color: var(--text-muted);">$ USD tolerancia</span>
          <button class="btn-secondary" style="font-size: 0.7rem; padding: 0.3rem 0.6rem;" onclick="updateThreshold('${r.rule_id}')">Guardar</button>
        </div>
      `;
    } else {
      thresholdInput = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <input type="number" step="0.5" min="0.5" id="threshold-${r.rule_id}" class="form-input" style="width: 80px; padding: 0.3rem 0.5rem; font-size: 0.8rem;" value="${r.current_threshold_hours}">
          <span style="font-size: 0.75rem; color: var(--text-muted);">horas SLA</span>
          <button class="btn-secondary" style="font-size: 0.7rem; padding: 0.3rem 0.6rem;" onclick="updateThreshold('${r.rule_id}')">Guardar</button>
        </div>
      `;
    }

    return `
      <tr>
        <td>
          <strong style="color: var(--text-main); font-size: 0.85rem;">${escapeHtml(r.name)}</strong>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(r.description)}</div>
        </td>
        <td><span class="stat-metric-badge badge-purple">${escapeHtml(r.category)}</span></td>
        <td>${thresholdInput}</td>
        <td><span class="stat-metric-badge badge-emerald">● ${escapeHtml(r.status)}</span></td>
      </tr>
    `;
  }).join("");
}

async function updateThreshold(ruleId) {
  const input = document.getElementById(`threshold-${ruleId}`);
  if (!input) return;
  const val = parseFloat(input.value);

  showToast("Actualizando umbral dinámico...", "info");
  try {
    const res = await fetch(`${API_BASE}/api/quality/business_rules/update_threshold`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rule_id: ruleId, new_threshold: val })
    });
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      showToast(data.message || "Umbral actualizado.", "success");
    }
  } catch (err) {
    showToast("Error al actualizar umbral.", "error");
  }
}

async function triggerEvaluateBusinessRules() {
  showToast("Evaluando reglas de negocio y detectando variaciones en ventas...", "info");
  try {
    const res = await fetch(`${API_BASE}/api/quality/business_rules/evaluate`, { method: "POST" });
    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      showToast(`Evaluación completada: ${data.data.failed_rules_count} anomalías detectadas.`, "success");
      renderBusinessRulesEvaluation(data.data);
    }
  } catch (err) {
    showToast("Error al evaluar reglas de negocio.", "error");
  }
}

function renderBusinessRulesEvaluation(evalData) {
  const container = document.getElementById("business-rules-results-container");
  if (!container) return;

  const failures = evalData.drill_down_failures || [];

  container.innerHTML = `
    <div style="margin-top: 1rem;">
      <div class="card-grid" style="margin-bottom: 1rem;">
        <div class="pastel-card" style="border-top: 3px solid var(--pastel-rose-accent);">
          <span class="stat-metric-badge badge-rose">ESTADO DE REGLAS DE NEGOCIO</span>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--text-main);">${evalData.overall_status}</div>
          <p style="font-size: 0.78rem; color: var(--text-muted);">${evalData.failed_rules_count} reglas requieren atención • ${evalData.passed_rules_count} conformes</p>
        </div>

        <div class="pastel-card" style="border-top: 3px solid var(--pastel-blue-accent);">
          <span class="stat-metric-badge badge-blue">ÚLTIMA AUDITORÍA</span>
          <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-main);">${evalData.evaluated_at}</div>
          <p style="font-size: 0.78rem; color: var(--text-muted);">${evalData.total_rules_evaluated} reglas evaluadas contra baseline histórico.</p>
        </div>
      </div>

      <!-- Drill-Down Section -->
      ${failures.length > 0 ? `
        <div class="pastel-card" style="border-left: 4px solid var(--pastel-rose-accent);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--pastel-rose-text);">🔍 Drill-Down de Anomalías Detectadas & Análisis de Causa Raíz</h4>
            <span class="stat-metric-badge badge-rose">Investigación en Profundidad</span>
          </div>

          ${failures.map(f => `
            <div style="background: var(--bg-app); border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 0.85rem; margin-bottom: 0.75rem;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong style="color: var(--text-main); font-size: 0.88rem;">${escapeHtml(f.rule_name)}</strong>
                <span class="stat-metric-badge badge-rose">Entidad: ${escapeHtml(f.failed_entity)}</span>
              </div>
              
              <div style="margin-top: 0.5rem; overflow-x: auto;">
                <table class="table-clean" style="font-size: 0.78rem;">
                  <thead>
                    <tr>
                      ${Object.keys(f.sample_records[0] || {}).map(k => `<th>${escapeHtml(k)}</th>`).join("")}
                    </tr>
                  </thead>
                  <tbody>
                    ${f.sample_records.map(rec => `
                      <tr>
                        ${Object.values(rec).map(v => `<td>${escapeHtml(String(v))}</td>`).join("")}
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>

              <div style="margin-top: 0.5rem; font-size: 0.78rem; color: var(--pastel-blue-text);">
                💡 <strong>Sugerencia de Remediación:</strong> ${escapeHtml(f.suggested_remediation)}
              </div>
            </div>
          `).join("")}
        </div>
      ` : `
        <div style="background: var(--pastel-emerald-bg); border: 1px solid var(--pastel-emerald-border); padding: 1rem; border-radius: var(--radius-sm); color: var(--pastel-emerald-text); text-align: center;">
          🎉 Cero anomalías en ventas o conciliación financiera. Todos los umbrales de negocio están conformes.
        </div>
      `}
    </div>
  `;
}

async function loadRealDataplexConsoleScans() {
  const tableBody = document.getElementById("real-dataplex-scans-table");
  if (!tableBody) return;

  try {
    const res = await fetch(`${API_BASE}/api/quality/real_dataplex_scans`);
    const data = await res.json();
    if (data.status === "success" && data.data) {
      tableBody.innerHTML = data.data.map(s => `
        <tr>
          <td><strong style="color: var(--text-main);">${escapeHtml(s.display_name)}</strong></td>
          <td><span class="stat-metric-badge badge-purple">${escapeHtml(s.type)}</span></td>
          <td><code style="font-size: 0.75rem; color: var(--pastel-blue-text);">${escapeHtml(s.resource)}</code></td>
          <td><span class="stat-metric-badge badge-emerald">● ${escapeHtml(s.state)}</span></td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Error loading real dataplex scans:", err);
  }
}

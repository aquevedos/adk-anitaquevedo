/**
 * Governance Profiles & Firestore Integration Controller
 */

let allProfiles = [];
let currentActiveProfileId = "guardian_dato";

function initProfiles() {
  loadProfiles();
}

async function loadProfiles() {
  try {
    const res = await fetch(`${API_BASE}/api/profiles`);
    const data = await res.json();
    if (data.status === "success") {
      allProfiles = data.data || [];
      currentActiveProfileId = data.active_profile_id || "guardian_dato";
      renderProfileSwitcherPills();
      renderProfilesCards();
      updateChatHeaderProfile();
    }
  } catch (err) {
    console.error("Error loading profiles:", err);
  }
}

function renderProfileSwitcherPills() {
  const container = document.getElementById("profiles-pill-bar");
  if (!container) return;

  container.innerHTML = allProfiles.map(p => {
    const isActive = p.id === currentActiveProfileId;
    return `
      <button class="profile-pill ${isActive ? 'active' : ''}" onclick="selectProfile('${escapeHtml(p.id)}')">
        <span style="font-size: 1.1rem;">${escapeHtml(p.avatar)}</span>
        <div style="text-align: left;">
          <div style="font-weight: 700; font-size: 0.85rem;">${escapeHtml(p.name)}</div>
          <div style="font-size: 0.7rem; opacity: 0.8;">${escapeHtml(p.role)}</div>
        </div>
      </button>
    `;
  }).join("");
}

async function selectProfile(profileId) {
  try {
    const res = await fetch(`${API_BASE}/api/profiles/switch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: profileId })
    });
    const data = await res.json();
    if (data.status === "success") {
      currentActiveProfileId = profileId;
      renderProfileSwitcherPills();
      renderProfilesCards();
      updateChatHeaderProfile();
      showToast(`Perfil cambiado a: ${data.data.active_profile.name} (Sincronizado en Firestore)`, "success");
      
      // Update quick prompts in chat
      if (typeof updateQuickPromptsForProfile === "function") {
        updateQuickPromptsForProfile(data.data.active_profile);
      }
    }
  } catch (err) {
    console.error("Error switching profile:", err);
    showToast("Error al cambiar de perfil", "error");
  }
}

function updateChatHeaderProfile() {
  const current = allProfiles.find(p => p.id === currentActiveProfileId);
  if (!current) return;

  const headerAvatar = document.getElementById("chat-profile-avatar");
  const headerName = document.getElementById("chat-profile-name");
  const headerRole = document.getElementById("chat-profile-role");
  const headerMission = document.getElementById("chat-profile-mission");

  if (headerAvatar) headerAvatar.innerText = current.avatar;
  if (headerName) headerName.innerText = current.name;
  if (headerRole) headerRole.innerText = current.role;
  if (headerMission) headerMission.innerText = `🎯 ${current.mission}`;
}

function renderProfilesCards() {
  const grid = document.getElementById("profiles-grid");
  if (!grid) return;

  grid.innerHTML = allProfiles.map(p => {
    const isActive = p.id === currentActiveProfileId;

    const raciRows = Object.entries(p.raci_roles || {}).map(([task, role]) => `
      <div style="display: flex; justify-content: space-between; font-size: 0.8rem; padding: 0.3rem 0; border-bottom: 1px dashed rgba(255,255,255,0.08);">
        <span style="color: #d1d5db;">${escapeHtml(task)}:</span>
        <span style="font-weight: 700; color: #93c5fd;">${escapeHtml(role)}</span>
      </div>
    `).join("");

    return `
      <div class="asset-card" style="border: 2px solid ${isActive ? 'var(--accent-blue)' : 'var(--border-color)'};">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div style="display: flex; gap: 0.75rem; align-items: center;">
            <div style="font-size: 2rem; background: rgba(255,255,255,0.05); padding: 0.5rem; border-radius: var(--radius-md);">${escapeHtml(p.avatar)}</div>
            <div>
              <h3 class="asset-name" style="font-size: 1.15rem;">${escapeHtml(p.name)}</h3>
              <div style="font-size: 0.8rem; color: #93c5fd; font-weight: 600;">${escapeHtml(p.role)}</div>
            </div>
          </div>
          ${isActive ? '<span class="tag-badge" style="background: rgba(59,130,246,0.3); border: 1px solid #3b82f6; color: #fff;">✅ ACTIVO</span>' : ''}
        </div>

        <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4;">
          <strong>Misión:</strong> ${escapeHtml(p.mission)}
        </div>

        <div style="font-size: 0.82rem; color: #9ca3af;">
          <strong>Habilidades del Agente:</strong>
          <ul style="margin: 0.35rem 0 0 1.2rem; padding: 0; display: flex; flex-direction: column; gap: 0.2rem;">
            ${p.skills.map(s => `<li style="color: #e5e7eb;">${escapeHtml(s)}</li>`).join("")}
          </ul>
        </div>

        <div style="background: rgba(0,0,0,0.3); padding: 0.75rem; border-radius: var(--radius-md);">
          <strong style="font-size: 0.75rem; color: #9ca3af; text-transform: uppercase;">Matriz RACI Asignada</strong>
          <div style="margin-top: 0.35rem;">
            ${raciRows}
          </div>
        </div>

        <div style="font-size: 0.8rem; color: #cbd5e1; background: rgba(59,130,246,0.08); padding: 0.6rem 0.8rem; border-radius: var(--radius-md);">
          💡 <strong>Utilidad para Clientes:</strong> ${escapeHtml(p.utility)}
        </div>

        <button class="${isActive ? 'btn-secondary' : 'btn-primary'}" style="margin-top: auto;" onclick="selectProfile('${escapeHtml(p.id)}')">
          ${isActive ? '✅ Perfil en Uso' : '👉 Asumir este Rol'}
        </button>
      </div>
    `;
  }).join("");
}

async function runMaturityAssessment() {
  const q1 = parseInt(document.getElementById("mat-q1")?.value || "3");
  const q2 = parseInt(document.getElementById("mat-q2")?.value || "3");
  const q3 = parseInt(document.getElementById("mat-q3")?.value || "2");
  const q4 = parseInt(document.getElementById("mat-q4")?.value || "3");

  try {
    const res = await fetch(`${API_BASE}/api/profiles/maturity_diagnosis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: { q1, q2, q3, q4 } })
    });
    const data = await res.json();
    if (data.status === "success") {
      const resContainer = document.getElementById("maturity-results-container");
      if (resContainer) {
        const d = data.data;
        resContainer.innerHTML = `
          <div style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.3); border-radius: var(--radius-lg); padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-size: 0.75rem; color: #9ca3af;">DIAGNÓSTICO DE MADUREZ (DMM)</span>
                <h3 style="font-size: 1.3rem; color: #93c5fd; margin-top: 0.2rem;">${escapeHtml(d.maturity_level)}</h3>
              </div>
              <div style="font-size: 2rem; font-weight: 800; color: #fff;">${d.score} / ${d.max_score}</div>
            </div>

            <p style="color: #e5e7eb; font-size: 0.9rem; line-height: 1.5;">${escapeHtml(d.recommendation)}</p>

            <h4 style="color: #fff; font-size: 0.95rem; margin-top: 0.5rem;">Roadmap Ágil Paso a Paso:</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem;">
              ${d.roadmap_sprints.map(s => `
                <div style="background: rgba(0,0,0,0.3); padding: 0.75rem 1rem; border-radius: var(--radius-md); border-left: 3px solid var(--accent-purple);">
                  <strong style="color: #c084fc; font-size: 0.85rem;">${escapeHtml(s.sprint)}</strong>
                  <p style="color: #cbd5e1; font-size: 0.8rem; margin-top: 0.25rem;">${escapeHtml(s.foco)}</p>
                </div>
              `).join("")}
            </div>
          </div>
        `;
      }
      showToast("Diagnóstico de Madurez generado con éxito", "success");
    }
  } catch (err) {
    console.error("Error in maturity diagnosis:", err);
  }
}

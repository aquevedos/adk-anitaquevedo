/**
 * Authentication and Strict Role-Based Workspace Controller
 */

let currentUser = null;

function initAuth() {
  const savedUser = localStorage.getItem("governance_user");
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      applyAuthenticatedUser(currentUser);
    } catch (e) {
      showLoginModal();
    }
  } else {
    showLoginModal();
  }

  setupLoginForm();
}

function showLoginModal() {
  const overlay = document.getElementById("login-overlay");
  if (overlay) overlay.style.display = "flex";
}

function hideLoginModal() {
  const overlay = document.getElementById("login-overlay");
  if (overlay) overlay.style.display = "none";
}

function setupLoginForm() {
  const form = document.getElementById("login-form");
  if (form) {
    form.onsubmit = async (e) => {
      e.preventDefault();
      const email = document.getElementById("login-email")?.value;
      const password = document.getElementById("login-password")?.value;
      await performLogin(email, password);
    };
  }
}

function quickSelectLoginRole(email, password, roleKey) {
  const emailInput = document.getElementById("login-email");
  const passInput = document.getElementById("login-password");
  if (emailInput) emailInput.value = email;
  if (passInput) passInput.value = password;

  document.querySelectorAll(".role-option-btn").forEach(b => b.classList.remove("selected"));
  const activeBtn = document.querySelector(`.role-option-btn[data-email="${email}"]`);
  if (activeBtn) activeBtn.classList.add("selected");

  performLogin(email, password);
}

async function performLogin(email, password) {
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password: password.trim() })
    });

    const data = await res.json();
    if (res.status === 200 && data.status === "success") {
      currentUser = data.user;
      localStorage.setItem("governance_user", JSON.stringify(currentUser));
      applyAuthenticatedUser(currentUser);
      hideLoginModal();
      showToast(`Sesión iniciada como: ${currentUser.user_name || currentUser.name}`, "success");
    } else {
      showToast(data.detail || "Credenciales incorrectas.", "error");
    }
  } catch (err) {
    console.error("Login error:", err);
    showToast("Error de conexión con el servidor.", "error");
  }
}

function applyAuthenticatedUser(user) {
  if (!user) return;

  // 1. Header Identity
  const headerAvatar = document.getElementById("header-user-avatar");
  const headerName = document.getElementById("header-user-name");
  const headerRole = document.getElementById("header-user-role");
  const headerCard = document.getElementById("header-user-card");

  if (headerAvatar) headerAvatar.innerText = user.avatar || "👤";
  if (headerName) headerName.innerText = user.user_name || user.name;
  if (headerRole) {
    headerRole.innerText = user.role;
    headerRole.style.background = user.theme_pastel?.badge_bg || "var(--pastel-blue-bg)";
    headerRole.style.color = user.theme_pastel?.text || "var(--pastel-blue-text)";
  }
  if (headerCard) headerCard.style.display = "flex";

  // 2. Role Workspace Banner
  const bannerAvatar = document.getElementById("role-banner-avatar");
  const bannerTitle = document.getElementById("role-banner-title");
  const bannerMission = document.getElementById("role-banner-mission");
  if (bannerAvatar) bannerAvatar.innerText = user.avatar || "👤";
  if (bannerTitle) bannerTitle.innerText = `${user.name} — ${user.user_name || ''}`;
  if (bannerMission) bannerMission.innerText = `🎯 ${user.mission}`;

  // 3. Dynamic Filter of Navigation Tabs (Strictly by Role)
  renderRoleSpecificTabs(user.id);

  // 4. Update Chat Workspace
  if (typeof updateChatForRole === "function") {
    updateChatForRole(user);
  }
}

function renderRoleSpecificTabs(roleId) {
  const tabsContainer = document.getElementById("nav-tabs-bar");
  if (!tabsContainer) return;

  let tabDefinitions = [];

  if (roleId === "estratega_ejecutivo") {
    tabDefinitions = [
      { id: "tab-cdo-chat", name: "💬 Asistente Estratégico (CDO)", paneId: "pane-chat" },
      { id: "tab-cdo-roi", name: "💼 Tablero de Valor & ROI", paneId: "pane-cdo-roi" },
      { id: "tab-cdo-sdp", name: "🛡️ SDP: Sensibilidad & Riesgo PII", paneId: "pane-dlp" },
      { id: "tab-tagging", name: "🏷️ Metadatos & Tagging", paneId: "pane-tagging" },
      { id: "tab-looker", name: "📊 Looker & Capa Semántica", paneId: "pane-looker" },
      { id: "tab-policies", name: "📜 Compliance Scorecard (KC MCP)", paneId: "pane-policies" },
      { id: "tab-cdo-catalog", name: "🔍 Catálogo de Negocio", paneId: "pane-catalog" }
    ];
  } else if (roleId === "gestor_programa") {
    tabDefinitions = [
      { id: "tab-gov-chat", name: "💬 Asistente de Gobernanza Ágil", paneId: "pane-chat" },
      { id: "tab-gov-maturity", name: "📋 Diagnóstico de Madurez & Sprints", paneId: "pane-maturity" },
      { id: "tab-gov-sdp", name: "🛡️ SDP: Discovery Profiles & Content Policies", paneId: "pane-dlp" },
      { id: "tab-tagging", name: "🏷️ Metadatos & Tagging", paneId: "pane-tagging" },
      { id: "tab-gov-raci", name: "👥 Matriz RACI & Comités", paneId: "pane-raci" },
      { id: "tab-looker", name: "📊 Métricas Semánticas Looker", paneId: "pane-looker" },
      { id: "tab-policies", name: "📜 Policy as Code (KC MCP)", paneId: "pane-policies" }
    ];
  } else if (roleId === "guardian_dato") {
    tabDefinitions = [
      { id: "tab-steward-chat", name: "💬 Asistente de Calidad & DLP", paneId: "pane-chat" },
      { id: "tab-steward-sdp", name: "🛡️ Sensitive Data Protection (Discovery, Inspección & Riesgo)", paneId: "pane-dlp" },
      { id: "tab-tagging", name: "🏷️ Metadatos & Tagging (Plantillas KC)", paneId: "pane-tagging" },
      { id: "tab-steward-quality", name: "🩺 Calidad Dataplex & Reglas de Negocio", paneId: "pane-quality" },
      { id: "tab-policies", name: "📜 Policy as Code (KC MCP)", paneId: "pane-policies" },
      { id: "tab-steward-glossary", name: "📖 Glosario & Certificación RAG", paneId: "pane-stewards" }
    ];
  } else { // arquitecto_ingeniero
    tabDefinitions = [
      { id: "tab-arch-chat", name: "💬 Asistente Técnico & SQL", paneId: "pane-chat" },
      { id: "tab-arch-sdp", name: "🛡️ SDP: Pipelines, Triggers & BigQuery Risk", paneId: "pane-dlp" },
      { id: "tab-arch-connectors", name: "🔌 Conectores & Discovery Externo (MySQL/Azure)", paneId: "pane-connectors" },
      { id: "tab-tagging", name: "🏷️ Metadatos & Tagging", paneId: "pane-tagging" },
      { id: "tab-arch-lineage", name: "🔗 Linaje End-to-End & Impacto", paneId: "pane-lineage" },
      { id: "tab-looker", name: "📊 Modelos LookML Semánticos", paneId: "pane-looker" },
      { id: "tab-arch-catalog", name: "⚡ Esquemas Técnicos & Queries", paneId: "pane-catalog" }
    ];
  }

  tabsContainer.innerHTML = tabDefinitions.map((t, idx) => `
    <button class="tab-btn ${idx === 0 ? 'active' : ''}" data-pane="${t.paneId}" onclick="switchWorkspaceTab('${t.paneId}', this)">
      ${t.name}
    </button>
  `).join("");

  // Activate first tab pane
  if (tabDefinitions.length > 0) {
    switchWorkspaceTab(tabDefinitions[0].paneId, tabsContainer.children[0]);
  }
}

function switchWorkspaceTab(paneId, btnEl) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");

  document.querySelectorAll(".tab-content-pane").forEach(p => p.classList.remove("active"));
  const target = document.getElementById(paneId);
  if (target) {
    target.classList.add("active");
  }

  // Trigger sub-renders if needed
  if (paneId === "pane-dlp" && typeof initSDP === "function") {
    initSDP();
  }
  if (paneId === "pane-lineage" && typeof renderCurrentLineage === "function") {
    renderCurrentLineage();
  }
  if (paneId === "pane-quality" && typeof loadRealDataplexConsoleScans === "function") {
    loadRealDataplexConsoleScans();
  }
}

function logoutUser() {
  localStorage.removeItem("governance_user");
  currentUser = null;
  const headerCard = document.getElementById("header-user-card");
  if (headerCard) headerCard.style.display = "none";
  showLoginModal();
  showToast("Has cerrado sesión.", "info");
}

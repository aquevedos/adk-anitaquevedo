/**
 * Master Application State & Global UI Controller
 */

const API_BASE = "";

const AppState = {
  activeTab: "chat-tab",
  assets: [],
  glossary: [],
  selectedAsset: null,
  healthData: null
};

// Global HTML Escaper
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Global Tab Navigator
function navigateToTab(tabId) {
  const tabBtn = document.querySelector(`.nav-tab-btn[data-target="${tabId}"]`);
  if (tabBtn) {
    tabBtn.click();
  } else {
    document.querySelectorAll(".nav-tab-btn").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    const pane = document.getElementById(tabId);
    if (pane) pane.classList.add("active");
  }
}

// Global Modal Closer
function closeAllModals() {
  document.querySelectorAll(".modal-backdrop").forEach(m => m.style.display = "none");
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  loadGlobalHealth();
  initToast();

  // Load authentication and initial sub-modules safely
  try { if (typeof initAuth === "function") initAuth(); } catch(e) { console.error("Error initAuth:", e); }
  try { if (typeof initProfiles === "function") initProfiles(); } catch(e) { console.error("Error initProfiles:", e); }
  try { if (typeof initChat === "function") initChat(); } catch(e) { console.error("Error initChat:", e); }
  try { if (typeof initCatalog === "function") initCatalog(); } catch(e) { console.error("Error initCatalog:", e); }
  try { if (typeof initDLP === "function") initDLP(); } catch(e) { console.error("Error initDLP:", e); }
  try { if (typeof initQuality === "function") initQuality(); } catch(e) { console.error("Error initQuality:", e); }
  try { if (typeof initLineage === "function") initLineage(); } catch(e) { console.error("Error initLineage:", e); }
  try { if (typeof initStewards === "function") initStewards(); } catch(e) { console.error("Error initStewards:", e); }
  try { if (typeof initConnectors === "function") initConnectors(); } catch(e) { console.error("Error initConnectors:", e); }
  try { if (typeof initPolicies === "function") initPolicies(); } catch(e) { console.error("Error initPolicies:", e); }
  try { if (typeof initLooker === "function") initLooker(); } catch(e) { console.error("Error initLooker:", e); }
  try { if (typeof initTagging === "function") initTagging(); } catch(e) { console.error("Error initTagging:", e); }
});

function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const targetId = tab.getAttribute("data-target");
      document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("active");
      });
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add("active");
        AppState.activeTab = targetId;

        // Trigger sub-module updates
        if (targetId === "lineage-tab" && typeof renderCurrentLineage === "function") {
          renderCurrentLineage();
        }
        if (targetId === "profiles-tab" && typeof loadProfiles === "function") {
          loadProfiles();
        }
      }
    });
  });
}

async function loadGlobalHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/quality/health`);
    const data = await res.json();
    if (data.status === "success") {
      AppState.healthData = data.data;
      updateRibbonStats(data.data);
    }
  } catch (err) {
    console.error("Error loading health metrics:", err);
  }
}

function updateRibbonStats(health) {
  const healthEl = document.getElementById("stat-avg-quality");
  if (healthEl) healthEl.innerText = `${health.average_score}%`;

  const totalEl = document.getElementById("stat-total-assets");
  if (totalEl) totalEl.innerText = health.total_assets;

  const passedEl = document.getElementById("stat-passed-rules");
  if (passedEl) passedEl.innerText = health.status_breakdown?.passed || "0";
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container") || document.body;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerText = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function initToast() {
  if (!document.getElementById("toast-container")) {
    const cont = document.createElement("div");
    cont.id = "toast-container";
    cont.className = "toast-container";
    document.body.appendChild(cont);
  }
}

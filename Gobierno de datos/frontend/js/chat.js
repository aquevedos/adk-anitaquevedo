/**
 * Data Governance Agent Chat Controller
 */

function initChat() {
  const sendBtn = document.getElementById("chat-send-btn");
  const chatInput = document.getElementById("chat-input");

  if (sendBtn && chatInput) {
    sendBtn.onclick = () => handleSendMessage();
    chatInput.onkeydown = (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    };
  }

  attachPromptChipsEvents();
}

function attachPromptChipsEvents() {
  const chips = document.querySelectorAll(".chip-btn");
  const chatInput = document.getElementById("chat-input");

  chips.forEach(chip => {
    chip.onclick = () => {
      const text = chip.getAttribute("data-prompt") || chip.innerText.trim();
      if (chatInput && text) {
        chatInput.value = text;
        handleSendMessage();
      }
    };
  });
}

function updateChatForRole(user) {
  const container = document.getElementById("quick-prompts-container");
  if (container && user && user.quick_prompts) {
    container.innerHTML = user.quick_prompts.map(p => `
      <button class="chip-btn" data-prompt="${escapeHtml(p)}">
        ${escapeHtml(p)}
      </button>
    `).join("");
    attachPromptChipsEvents();
  }

  // Welcome message
  const messagesCont = document.getElementById("chat-history-container");
  if (messagesCont) {
    const avatar = user.avatar || "🛡️";
    const name = user.name || "Agente de Gobierno";
    const role = user.role || "Especialista";
    const mission = user.mission || "Gobernar activos de datos.";

    messagesCont.innerHTML = `
      <div class="msg-row agent">
        <div class="role-avatar" style="font-size: 1.4rem; background: var(--pastel-blue-bg); width: 40px; height: 40px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${escapeHtml(avatar)}</div>
        <div class="msg-bubble-card">
          <div style="font-size: 0.75rem; color: var(--pastel-blue-text); font-weight: 700; margin-bottom: 0.25rem;">
            ${escapeHtml(name)} • ${escapeHtml(role)}
          </div>
          <p><strong>¡Hola!</strong> He configurado tu espacio de trabajo como <strong>${escapeHtml(name)}</strong>.</p>
          <p style="margin-top: 0.35rem; color: var(--text-main);">🎯 <strong>Misión:</strong> ${escapeHtml(mission)}</p>
          <div style="margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.3rem;">
            ${(user.skills || []).map(s => `<span class="stat-metric-badge badge-blue">${escapeHtml(s)}</span>`).join("")}
          </div>
        </div>
      </div>
    `;
    messagesCont.scrollTop = messagesCont.scrollHeight;
  }
}

async function handleSendMessage() {
  const chatInput = document.getElementById("chat-input");
  if (!chatInput) return;
  const message = chatInput.value.trim();
  if (!message) return;

  const container = document.getElementById("chat-history-container");
  chatInput.value = "";

  // User message
  const userHtml = `
    <div class="msg-row user">
      <div class="role-avatar" style="font-size: 1.3rem; background: var(--pastel-blue-bg); width: 36px; height: 36px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">👤</div>
      <div class="msg-bubble-card">
        <p>${escapeHtml(message)}</p>
      </div>
    </div>
  `;
  container.insertAdjacentHTML("beforeend", userHtml);
  container.scrollTop = container.scrollHeight;

  const user = typeof currentUser !== "undefined" && currentUser ? currentUser : { id: "guardian_dato", avatar: "🛡️", name: "Guardián del Dato" };

  // Typing
  const typingId = `typing-${Date.now()}`;
  const typingHtml = `
    <div class="msg-row agent" id="${typingId}">
      <div class="role-avatar" style="font-size: 1.3rem; background: var(--pastel-purple-bg); width: 36px; height: 36px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${escapeHtml(user.avatar || '🤖')}</div>
      <div class="msg-bubble-card">
        <span style="color: var(--text-muted);"><em>[${escapeHtml(user.name)}] Consultando Knowledge Catalog, Dataplex y reglas...</em></span>
      </div>
    </div>
  `;
  container.insertAdjacentHTML("beforeend", typingHtml);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        profile_id: user.id
      })
    });
    const data = await res.json();
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    if (data.status === "success") {
      renderAgentResponse(data.data, user);
    } else {
      renderErrorMessage("Error al procesar la solicitud con el Agente.");
    }
  } catch (err) {
    console.error("Chat error:", err);
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();
    renderErrorMessage("Error de conexión con el backend.");
  }
}

function renderAgentResponse(responseData, user) {
  const container = document.getElementById("chat-history-container");
  const rawText = responseData.message || "";
  const profile = responseData.active_profile || user;
  const formattedHtml = parseMarkdownToPastelHtml(rawText);

  const responseHtml = `
    <div class="msg-row agent">
      <div class="role-avatar" style="font-size: 1.3rem; background: var(--pastel-blue-bg); width: 36px; height: 36px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${escapeHtml(profile.avatar || '🤖')}</div>
      <div class="msg-bubble-card">
        <div style="font-size: 0.75rem; color: var(--pastel-blue-text); font-weight: 700; margin-bottom: 0.25rem;">
          ${escapeHtml(profile.name)} • ${escapeHtml(profile.role || '')}
        </div>
        ${formattedHtml}
      </div>
    </div>
  `;

  container.insertAdjacentHTML("beforeend", responseHtml);
  container.scrollTop = container.scrollHeight;
}

function renderErrorMessage(msg) {
  const container = document.getElementById("chat-history-container");
  const errHtml = `
    <div class="msg-row agent">
      <div class="role-avatar" style="font-size: 1.3rem;">⚠️</div>
      <div class="msg-bubble-card" style="border-left: 3px solid var(--pastel-rose-accent);">
        <p style="color: var(--pastel-rose-text);"><strong>Error:</strong> ${escapeHtml(msg)}</p>
      </div>
    </div>
  `;
  container.insertAdjacentHTML("beforeend", errHtml);
  container.scrollTop = container.scrollHeight;
}

function parseMarkdownToPastelHtml(md) {
  if (!md) return "";

  let html = md
    .replace(/^### (.*$)/gim, '<h4 style="color: var(--pastel-blue-text); margin-top: 0.75rem; margin-bottom: 0.25rem; font-size: 0.92rem;">$1</h4>')
    .replace(/^## (.*$)/gim, '<h3 style="color: var(--text-main); margin-top: 0.85rem; margin-bottom: 0.35rem; font-size: 1rem;">$1</h3>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`([^`]+)`/gim, '<code style="background: var(--bg-app); border: 1px solid var(--border-light); padding: 0.1rem 0.3rem; border-radius: 4px; color: var(--pastel-blue-text); font-size: 0.85em;">$1</code>')
    .replace(/^\s*-\s+(.*$)/gim, '<li style="margin-left: 1.2rem; color: var(--text-main); margin-bottom: 0.2rem;">$1</li>');

  html = html.replace(/```sql([\s\S]*?)```/gim, (match, code) => {
    return `<div class="sql-code-box"><code>${escapeHtml(code.trim())}</code></div>`;
  });

  html = html.replace(/```([\s\S]*?)```/gim, (match, code) => {
    return `<pre style="background: #0f172a; padding: 0.75rem; border-radius: 6px; overflow-x: auto; color: #a5f3fc; font-size: 0.8rem;"><code>${escapeHtml(code.trim())}</code></pre>`;
  });

  html = html.replace(/\n\n+/g, '<br/><br/>');

  return html;
}

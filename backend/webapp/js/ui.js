// Shared layout shell + small render helpers.
import { getSession, clearSession } from "./store.js";
import { apiGet, apiPost } from "./api.js";

export function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// Format an ISO datetime ("2026-06-20T17:00:00" or "...Z") for display.
export function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString([], { weekday: "short", day: "numeric", month: "short",
                                hour: "2-digit", minute: "2-digit" });
}

const NAV = {
  patient: [["#/patient", "Diagnose"], ["#/patient/appointments", "Appointments"], ["#/patient/history", "History"]],
  doctor: [["#/doctor", "Console"]],
  admin: [["#/admin", "Dashboard"]],
};

export function layout(active, content) {
  const s = getSession();
  const links = (NAV[s.role] || [])
    .map(([h, l]) => `<a href="${h}" class="nav-link ${active === h ? "active" : ""}">${l}</a>`)
    .join("");
  return `
    <header class="topbar">
      <div class="brand" style="display:flex;align-items:center;gap:9px">
        <img src="/app/logo.svg" alt="" style="width:28px;height:28px;border-radius:8px">
        <span style="background:linear-gradient(90deg,#9db8ff,#d6c2ff);-webkit-background-clip:text;background-clip:text;color:transparent"><span>Derm</span>AI</span>
      </div>
      <nav class="nav">${links}</nav>
      <div class="user">
        <div class="notif">
          <button id="notifBtn" class="btn ghost sm" title="Notifications" aria-label="Notifications">🔔<span id="notifCount" class="notif-count" style="display:none"></span></button>
          <div id="notifPanel" class="notif-panel" style="display:none" role="region" aria-label="Notifications list"></div>
        </div>
        <span class="role-chip ${s.role}">${s.role}</span>
        <span class="uid">${esc(s.name || s.username || s.uid)}</span>
        <button id="logoutBtn" class="btn ghost sm" aria-label="Log out">Logout</button>
      </div>
    </header>
    <main class="content">${content}</main>`;
}

// Call after layout() is in the DOM to wire the logout button + notifications.
export function bindLayout() {
  const b = document.getElementById("logoutBtn");
  if (b) b.onclick = () => { clearSession(); location.hash = "#/login"; };
  setupNotifications();
}

function setupNotifications() {
  const btn = document.getElementById("notifBtn");
  if (!btn) return;
  const panel = document.getElementById("notifPanel");
  const countEl = document.getElementById("notifCount");

  async function refreshCount() {
    try {
      const { unread } = await apiGet("/notifications/unread_count");
      if (unread > 0) { countEl.textContent = unread > 9 ? "9+" : unread; countEl.style.display = "inline-block"; }
      else countEl.style.display = "none";
    } catch { /* not logged in / offline — ignore */ }
  }

  btn.onclick = async (e) => {
    e.stopPropagation();
    if (panel.style.display === "block") { panel.style.display = "none"; return; }
    panel.style.display = "block";
    panel.innerHTML = `<div class="empty">Loading…</div>`;
    try {
      const items = await apiGet("/notifications");
      panel.innerHTML = items.length
        ? items.map(n => `<div class="notif-item ${n.read ? "" : "unread"}">
            <div>${esc(n.text)}</div><div class="meta">${fmtDateTime(n.created_at)}</div></div>`).join("")
        : `<div class="empty">No notifications yet.</div>`;
      await apiPost("/notifications/read", {});
      refreshCount();
    } catch { panel.innerHTML = `<div class="empty">Couldn't load notifications.</div>`; }
  };

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".notif")) panel.style.display = "none";
  });

  refreshCount();
  clearInterval(window.__notifTimer);
  window.__notifTimer = setInterval(refreshCount, 20000);
}

export function modeBadge(mode) {
  return `<span class="badge b-${mode}">${mode}</span>`;
}

// Lightweight, non-blocking toast (replaces alert()). type: "info" | "ok" | "err".
export function toast(message, type = "info") {
  let host = document.getElementById("toastHost");
  if (!host) {
    host = document.createElement("div");
    host.id = "toastHost";
    host.className = "toast-host";
    document.body.appendChild(host);
  }
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => { el.classList.add("leaving"); setTimeout(() => el.remove(), 250); }, 3200);
}

// Dermatological history fields (Rook's / Fitzpatrick framework) — shared by the
// patient form and the doctor's view/edit modal.
export const MEDICAL_FIELDS = [
  { k: "full_name", label: "Full name", type: "text" },
  { k: "age", label: "Age", type: "number" },
  { k: "sex", label: "Sex", type: "select", options: ["Male", "Female", "Other"] },
  { k: "occupation", label: "Occupation", type: "text" },
  { k: "fitzpatrick_type", label: "Skin tone — how does your skin react to the sun?", type: "select", options: [
      "I — very fair, always burns, never tans",
      "II — fair, usually burns, tans a little",
      "III — medium, sometimes burns, tans gradually",
      "IV — olive, rarely burns, tans easily",
      "V — brown, very rarely burns",
      "VI — dark / black, never burns",
  ] },
  { k: "previous_skin_conditions", label: "Any past skin problems?", type: "text" },
  { k: "atopy_history", label: "Do you (or family) have eczema, asthma or hay fever?", type: "text" },
  { k: "family_history", label: "Family history (skin disease)", type: "text" },
  { k: "skin_cancer_history", label: "Skin cancer history (personal/family)", type: "text" },
  { k: "sun_exposure", label: "Sun exposure", type: "select", options: ["High", "Moderate", "Low"] },
  { k: "sunscreen_use", label: "Sunscreen use", type: "select", options: ["Regular", "Sometimes", "Never"] },
  { k: "chronic_conditions", label: "Chronic conditions (diabetes, thyroid, autoimmune)", type: "text" },
  { k: "current_medications", label: "Current medications", type: "text" },
  { k: "allergies", label: "Allergies (drug / contact)", type: "text" },
  { k: "smoking", label: "Smoking", type: "select", options: ["never", "former", "current"] },
  { k: "alcohol", label: "Alcohol", type: "select", options: ["none", "occasional", "regular"] },
  { k: "notes", label: "Other notes", type: "text" },
];

export function medicalFormHTML(history, prefix = "mh_") {
  const h = history || {};
  return MEDICAL_FIELDS.map(f => {
    const v = h[f.k] != null ? h[f.k] : "";
    if (f.type === "select") {
      const opts = `<option value="">—</option>` +
        f.options.map(o => `<option ${String(v) === String(o) ? "selected" : ""}>${o}</option>`).join("");
      return `<label>${f.label}</label><select id="${prefix}${f.k}">${opts}</select>`;
    }
    return `<label>${f.label}</label><input id="${prefix}${f.k}" type="${f.type === "number" ? "number" : "text"}" value="${esc(v)}">`;
  }).join("");
}

export function collectMedical(root, prefix = "mh_") {
  const out = {};
  MEDICAL_FIELDS.forEach(f => {
    const el = root.querySelector("#" + prefix + f.k);
    const val = el ? el.value : "";
    out[f.k] = f.k === "age" ? (val ? Number(val) : null) : (val || null);
  });
  return out;
}

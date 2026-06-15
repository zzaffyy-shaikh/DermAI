// Patient dashboard: Diagnose flow (upload -> brief -> chat -> consult) + History.
import { layout, bindLayout, esc, modeBadge, medicalFormHTML, collectMedical, fmtDateTime } from "../ui.js";
import { apiGet, apiPost, apiPut, apiUpload, errText } from "../api.js";
import { getSession } from "../store.js";

let sessionId = null;

const REGIONS = ["face", "scalp", "neck", "chest", "back", "arm", "forearm",
  "hand", "abdomen", "leg", "foot"];

export function mount(root, hash) {
  if (hash === "#/patient/appointments") return renderAppointments(root);
  if (hash === "#/patient/history") return renderHistory(root);
  return renderDiagnose(root);
}

/* ---------------- Diagnose ---------------- */
function renderDiagnose(root) {
  sessionId = null;
  root.innerHTML = layout("#/patient", `
    <div class="page-title">Skin Screening</div>

    <div class="card" id="mhCard">
      <h2>0 · Medical history</h2>
      <div class="muted" style="margin-bottom:8px">Complete once — required before diagnosis, used in every screening and shared with the doctor.</div>
      <div id="mhBody"><div class="empty">Loading…</div></div>
      <div style="margin-top:12px"><button class="btn" id="btnSaveMH">Save medical history</button> <span class="muted" id="mhStatus"></span></div>
    </div>

    <div class="card">
      <h2>1 · Upload &amp; Diagnose</h2>
      <div class="row">
        <div>
          <label>Skin image</label>
          <input type="file" id="image" accept="image/*">
        </div>
        <div style="flex:0 0 200px">
          <label>Affected body region</label>
          <select id="region">
            <option value="">— not provided —</option>
            ${REGIONS.map(r => `<option>${r}</option>`).join("")}
          </select>
        </div>
        <div style="flex:0 0 150px"><button class="btn" id="btnDiagnose">Diagnose</button></div>
      </div>
      <img id="preview" class="preview">
      <div class="err" id="diagErr"></div>
    </div>

    <div class="card" id="briefCard" style="display:none">
      <h2>2 · Result <span id="modeBadge"></span> <span id="urgentBadge"></span></h2>
      <div class="grid" id="briefGrid"></div>
      <div id="briefInsights" class="muted" style="margin-top:10px"></div>
    </div>

    <div class="card" id="chatCard" style="display:none">
      <h2>3 · Follow-up questions</h2>
      <div class="chat" id="chat"></div>
      <div class="row" style="margin-top:12px">
        <div style="flex:1"><input id="answer" placeholder="Type your answer..."></div>
        <div style="flex:0 0 110px"><button class="btn" id="btnSend">Send</button></div>
      </div>
      <div id="doneBox"></div>
    </div>

    <div class="card" id="consultCard" style="display:none">
      <h2>4 · Book a dermatologist 🎥</h2>
      <div class="muted" style="margin-bottom:8px">Choose a dermatologist and one of their available times. Consultations are over <b>video</b>; the doctor receives your report and medical history.</div>
      <div class="row">
        <div style="flex:1"><label>Note for the doctor (optional)</label><input id="consultNote" placeholder="anything you'd like to mention"></div>
        <div style="flex:0 0 160px"><label>&nbsp;</label><button class="btn ghost" id="btnRefreshDocs">↻ Refresh</button></div>
      </div>
      <div class="list" id="docList" style="margin-top:12px"><div class="empty">Loading dermatologists…</div></div>
      <div class="muted" id="consultOut" style="margin-top:10px"></div>
      <div style="margin-top:12px"><a id="reportLink" class="btn purple sm" target="_blank" rel="noopener" style="text-decoration:none;display:none">📄 View diagnosis report (PDF)</a></div>
    </div>
  `);
  bindLayout();

  const $ = s => root.querySelector(s);

  // load + save medical history (full dermatological history)
  (async () => {
    try {
      const r = await apiGet("/profile/medical-history");
      $("#mhBody").innerHTML = medicalFormHTML(r.history);
    } catch (e) {
      $("#mhBody").innerHTML = `<div class="err">${esc(errText(e))}</div>`;
    }
  })();
  $("#btnSaveMH").onclick = async () => {
    try {
      await apiPut("/profile/medical-history", collectMedical(root));
      $("#mhStatus").textContent = "✓ Saved";
    } catch (e) { $("#mhStatus").textContent = "Error: " + errText(e); }
  };

  $("#image").onchange = e => {
    const f = e.target.files[0], img = $("#preview");
    if (f) { img.src = URL.createObjectURL(f); img.style.display = "block"; }
  };

  $("#btnDiagnose").onclick = async () => {
    $("#diagErr").textContent = "";
    const file = $("#image").files[0];
    if (!file) { $("#diagErr").textContent = "Please choose an image first."; return; }
    const btn = $("#btnDiagnose"); btn.disabled = true; btn.textContent = "Analysing...";
    try {
      const fd = new FormData();
      fd.append("image", file);
      if ($("#region").value) fd.append("body_region", $("#region").value);
      const data = await apiUpload("/diagnose", fd);
      sessionId = data.session_id;
      renderBrief(root, data.brief);
      startChat(root, data.message, data.awaiting_answer);
    } catch (err) {
      const msg = errText(err);
      $("#diagErr").textContent = "Error: " + msg;
      if (/medical history/i.test(msg)) $("#mhCard").scrollIntoView({ behavior: "smooth" });
    } finally { btn.disabled = false; btn.textContent = "Diagnose"; }
  };

  $("#btnSend").onclick = () => sendAnswer(root);
  $("#answer").addEventListener("keydown", e => { if (e.key === "Enter") sendAnswer(root); });
  $("#btnRefreshDocs").onclick = () => loadDoctors(root);
}

function renderBrief(root, b) {
  const $ = s => root.querySelector(s);
  $("#briefCard").style.display = "block";
  $("#modeBadge").outerHTML = `<span id="modeBadge">${modeBadge(b.mode)}</span>`;
  $("#urgentBadge").innerHTML = b.urgent ? '<span class="badge b-urgent">URGENT</span>' : "";
  const rows = [
    ["Disease", esc(b.disease)],
    ["Confidence", (b.confidence * 100).toFixed(1) + "%"],
    ["Entropy", b.entropy],
    ["2nd guess", b.second_guess ? esc(b.second_guess.disease) : "—"],
    ["Region", esc(b.body_region) || "—"],
    ["Severity", esc(b.severity) || "—"],
    ["Image", esc(b.image_quality)],
  ];
  $("#briefGrid").innerHTML = rows.map(([k, v]) =>
    `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
  $("#briefInsights").innerHTML = b.insights ? "🔍 " + esc(b.insights.summary) : "";
}

/* ---------------- Chat ---------------- */
function addMsg(root, who, text) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  d.innerHTML = `<div class="bubble">${esc(text)}</div>`;
  const chat = root.querySelector("#chat");
  chat.appendChild(d); chat.scrollTop = chat.scrollHeight;
}

function setChatEnabled(root, on) {
  root.querySelector("#answer").disabled = !on;
  root.querySelector("#btnSend").disabled = !on;
  if (on) root.querySelector("#answer").focus();
}

function startChat(root, message, awaiting) {
  root.querySelector("#chatCard").style.display = "block";
  root.querySelector("#chat").innerHTML = "";
  root.querySelector("#doneBox").innerHTML = "";
  root.querySelector("#consultCard").style.display = "none";
  addMsg(root, "assistant", message);
  setChatEnabled(root, awaiting);
  if (!awaiting) finishChat(root);
}

function finishChat(root) {
  root.querySelector("#doneBox").innerHTML = '<div class="done">✓ Screening complete</div>';
  root.querySelector("#consultCard").style.display = "block";
  setChatEnabled(root, false);
  const rl = root.querySelector("#reportLink");
  if (rl) {
    rl.href = `/report/${sessionId}?token=${getSession().token}`;
    rl.style.display = "inline-block";
  }
  loadDoctors(root);
}

async function sendAnswer(root) {
  const inp = root.querySelector("#answer");
  const text = inp.value.trim();
  if (!text || !sessionId) return;
  addMsg(root, "user", text); inp.value = ""; setChatEnabled(root, false);
  try {
    const turn = await apiPost("/chat/answer", { session_id: sessionId, answer: text });
    addMsg(root, "assistant", turn.message);
    if (turn.done) finishChat(root); else setChatEnabled(root, true);
  } catch (err) {
    addMsg(root, "assistant", "⚠️ " + errText(err));
    setChatEnabled(root, true);
  }
}

async function loadDoctors(root) {
  const el = root.querySelector("#docList");
  if (!el) return;
  el.innerHTML = `<div class="empty">Loading dermatologists…</div>`;
  try {
    const docs = await apiGet("/consult/doctors");
    el.innerHTML = docs.length ? docs.map(d => `
      <div class="item" style="flex-direction:column;align-items:stretch">
        <div><b>${esc(d.name)}</b> <span class="muted">${esc(d.specialization || "Dermatology")}${d.qualification ? " · " + esc(d.qualification) : ""}</span></div>
        <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:8px">
          ${d.slots.length
            ? d.slots.map(s => `<button class="btn teal sm" data-doc="${esc(d.uid)}" data-slot="${esc(s.id)}">${esc(fmtDateTime(s.start))}</button>`).join("")
            : `<span class="muted">No open times right now — check back later.</span>`}
        </div>
      </div>`).join("") : '<div class="empty">No dermatologists are available right now.</div>';
    el.querySelectorAll("[data-slot]").forEach(b =>
      b.onclick = () => book(root, b.dataset.doc, b.dataset.slot));
  } catch (err) {
    el.innerHTML = `<div class="err">${esc(errText(err))}</div>`;
  }
}

async function book(root, doctorId, slotId) {
  const out = root.querySelector("#consultOut");
  try {
    const c = await apiPost("/consult/request", {
      session_id: sessionId, doctor_id: doctorId, slot_id: slotId,
      mode: "video", note: root.querySelector("#consultNote").value || null,
    });
    out.innerHTML = `✅ Appointment requested with <b>${esc(c.doctor_name)}</b> for
      <b>${esc(fmtDateTime(c.appointment_time))}</b>. You'll be notified when the doctor confirms.
      <a href="#/patient/appointments">View my appointments →</a>`;
    loadDoctors(root);   // refresh so the booked slot disappears
  } catch (err) {
    out.innerHTML = `<span class="err">Error: ${esc(errText(err))}</span>`;
  }
}

/* ---------------- Appointments ---------------- */
const STATUS_LABEL = {
  pending: "Awaiting confirmation", confirmed: "Confirmed",
  declined: "Declined", closed: "Completed",
};

async function renderAppointments(root) {
  root.innerHTML = layout("#/patient/appointments", `
    <div class="page-title">My Appointments</div>
    <div class="card"><div class="list" id="appts"><div class="empty">Loading…</div></div></div>`);
  bindLayout();
  const el = root.querySelector("#appts");
  try {
    const items = await apiGet("/consult/my");
    el.innerHTML = items.length ? items.map(c => {
      const join = c.status === "confirmed" && c.room
        ? `<a class="btn ok sm" href="https://meet.jit.si/${esc(c.room)}" target="_blank" rel="noopener" style="text-decoration:none">🎥 Join call</a>` : "";
      return `
      <div class="item" style="flex-direction:column;align-items:stretch">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap">
          <div>
            <b>${esc(c.doctor_name || "Dermatologist")}</b>
            <span class="badge ${c.status === "confirmed" ? "b-verified" : c.status === "declined" ? "b-urgent" : "b-normal"}">${esc(STATUS_LABEL[c.status] || c.status)}</span>
            <div class="meta">${esc(fmtDateTime(c.appointment_time))}${c.brief ? " · " + esc(c.brief.disease) : ""}</div>
            ${c.note ? `<div class="meta">your note: ${esc(c.note)}</div>` : ""}
            ${c.solution ? `<div class="meta">💬 Doctor's advice: ${esc(c.solution)}</div>` : ""}
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <a class="btn purple sm" href="/report/${esc(c.session_id)}?token=${esc(getSession().token)}" target="_blank" rel="noopener" style="text-decoration:none">📄 Report</a>
            ${join}
          </div>
        </div>
      </div>`;
    }).join("") : '<div class="empty">No appointments yet. Run a screening, then book a dermatologist.</div>';
  } catch (err) {
    el.innerHTML = `<div class="err">${esc(errText(err))}</div>`;
  }
}

/* ---------------- History ---------------- */
async function renderHistory(root) {
  root.innerHTML = layout("#/patient/history", `
    <div class="page-title">My Screenings</div>
    <div class="card"><div class="list" id="hist"><div class="empty">Loading…</div></div></div>`);
  bindLayout();
  try {
    const items = await apiGet("/history");
    const el = root.querySelector("#hist");
    el.innerHTML = items.length ? items.map(s => `
      <div class="item">
        <div>
          <b>${esc(s.disease)}</b> ${modeBadge(s.mode)} ${s.urgent ? '<span class="badge b-urgent">URGENT</span>' : ""}
          <div class="meta">confidence ${(s.confidence * 100).toFixed(1)}% · ${s.done ? "completed" : "in progress"}</div>
          <div class="meta">session ${esc(s.session_id)}</div>
        </div>
      </div>`).join("") : '<div class="empty">No screenings yet. Run one from the Diagnose tab.</div>';
  } catch (err) {
    root.querySelector("#hist").innerHTML = `<div class="err">${esc(errText(err))}</div>`;
  }
}

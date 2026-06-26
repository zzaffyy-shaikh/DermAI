// Patient dashboard: Diagnose flow (upload -> brief -> chat -> consult) + History.
import { layout, bindLayout, esc, modeBadge, medicalFormHTML, collectMedical, fmtDateTime, toast } from "../ui.js";
import { apiGet, apiPost, apiPut, apiUpload, errText } from "../api.js";
import { getSession } from "../store.js";

let sessionId = null;
let lastBrief = null;      // brief currently shown, so it can be refreshed after refinement
let lastOptions = null;    // structured options for the current question (for retry)

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

    <div class="card onboard" id="onboard" style="display:none">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <b>👋 How DermAI works</b>
        <button class="btn ghost sm" id="onboardDismiss" aria-label="Dismiss guide">Got it</button>
      </div>
      <ol style="margin:10px 0 0 18px;line-height:1.7;color:var(--muted);font-size:13px">
        <li>Fill in your medical history once (below).</li>
        <li>Upload a clear, well-lit photo of the affected skin.</li>
        <li>Answer a few quick follow-up questions.</li>
        <li>Get a preliminary result and a downloadable PDF report.</li>
        <li>Book a video consultation with a verified dermatologist.</li>
      </ol>
    </div>

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
      <div class="photo-tips">📸 <b>For the most reliable result:</b> use good lighting, hold the camera steady and in focus, fill the frame with the affected area, and avoid heavy shadows or filters.</div>
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
      <div id="answerOptions" style="display:none;gap:8px;flex-wrap:wrap;margin-top:12px"></div>
      <div class="row" id="answerRow" style="margin-top:12px">
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
      lastBrief = data.brief;
      renderBrief(root, data.brief);
      startChat(root, data.message, data.awaiting_answer, data.options);
    } catch (err) {
      const msg = errText(err);
      $("#diagErr").textContent = "Error: " + msg;
      if (/medical history/i.test(msg)) $("#mhCard").scrollIntoView({ behavior: "smooth" });
    } finally { btn.disabled = false; btn.textContent = "Diagnose"; }
  };

  $("#btnSend").onclick = () => sendAnswer(root);
  $("#answer").addEventListener("keydown", e => { if (e.key === "Enter") sendAnswer(root); });
  $("#btnRefreshDocs").onclick = () => loadDoctors(root);

  // first-run onboarding guide (shown once)
  if (!localStorage.getItem("dermai.onboarded")) $("#onboard").style.display = "block";
  $("#onboardDismiss").onclick = () => {
    localStorage.setItem("dermai.onboarded", "1");
    $("#onboard").style.display = "none";
  };
}

// Turn a raw confidence into a plain word a non-specialist understands.
function confidenceBand(c) {
  if (c >= 0.75) return "High";
  if (c >= 0.5) return "Moderate";
  return "Low";
}

// A reassuring, plain-language headline based on the screening mode.
function plainResult(b) {
  if (b.mode === "healthy")
    return "Good news — no clear signs of a skin condition were found in this photo. "
      + "Please still answer the follow-up questions so nothing that a picture can't show is missed.";
  if (b.mode === "ood")
    return "This photo wasn't clear enough to confidently identify a specific condition. "
      + "It's best to see a dermatologist for an in-person check.";
  const urgent = b.urgent
    ? " A few features here deserve a prompt in-person check by a dermatologist."
    : "";
  return `This most closely resembles <b>${esc(b.disease)}</b>.${urgent}`;
}

function renderBrief(root, b, refined = false) {
  const $ = s => root.querySelector(s);
  $("#briefCard").style.display = "block";
  $("#modeBadge").outerHTML = `<span id="modeBadge">${modeBadge(b.mode)}</span>`;
  $("#urgentBadge").innerHTML = b.urgent ? '<span class="badge b-urgent">needs a doctor</span>' : "";

  const band = confidenceBand(b.confidence);
  const refinedNote = refined
    ? `<div style="grid-column:1/-1;font-size:12.5px;color:var(--doctor);font-weight:650">✓ Updated using your answers</div>`
    : "";
  const banner = refinedNote + `<div class="result-headline" style="grid-column:1/-1">${plainResult(b)}</div>`;
  const rows = b.mode === "healthy" ? [
    ["Result", "No condition detected"],
    ["Confidence", `${band}`],
    ["Photo quality", esc(b.image_quality)],
  ] : [
    ["Most likely", esc(b.disease)],
    ["Likelihood", `${band} (${(b.confidence * 100).toFixed(0)}%)`],
    ["Other possibility", b.second_guess ? esc(b.second_guess.disease) : "—"],
    ["Affected area", esc(b.body_region) || "—"],
    ["Severity", esc(b.severity) || "—"],
    ["Photo quality", esc(b.image_quality)],
  ];
  $("#briefGrid").innerHTML = banner + rows.map(([k, v]) =>
    `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");

  const blurryWarn = b.image_quality === "blurry"
    ? `<div class="warn-box">⚠️ This photo looks <b>blurry</b>, so the result may be less reliable. `
      + `For a clearer reading, retake it in good light, hold steady, and fill the frame with the affected area.</div>`
    : "";
  const insight = b.insights ? `<div>🔍 ${esc(b.insights.summary)}</div>` : "";
  $("#briefInsights").innerHTML = blurryWarn + insight
    + `<div class="disclaimer">⚕️ This is a preliminary AI screening, <b>not a medical diagnosis</b>. `
    + `Always confirm with a qualified dermatologist.</div>`;
}

/* ---------------- Chat ---------------- */
function addMsg(root, who, text) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  d.innerHTML = `<div class="bubble">${esc(text)}</div>`;
  const chat = root.querySelector("#chat");
  chat.appendChild(d); chat.scrollTop = chat.scrollHeight;
}

// Show either tappable answer options (structured differential questions) or the
// free-text box (conversational safety-net questions).
function showAnswerControls(root, awaiting, options) {
  lastOptions = options || null;
  const optsEl = root.querySelector("#answerOptions");
  const rowEl = root.querySelector("#answerRow");
  if (!awaiting) { optsEl.style.display = "none"; rowEl.style.display = "none"; return; }
  if (options && options.length) {
    rowEl.style.display = "none";
    optsEl.style.display = "flex";
    optsEl.innerHTML = options.map(o => `<button class="btn teal sm" data-opt="${esc(o)}">${esc(o)}</button>`).join("");
    optsEl.querySelectorAll("[data-opt]").forEach(b => b.onclick = () => sendAnswer(root, b.dataset.opt));
  } else {
    optsEl.style.display = "none";
    rowEl.style.display = "flex";
    root.querySelector("#answer").disabled = false;
    root.querySelector("#btnSend").disabled = false;
    root.querySelector("#answer").focus();
  }
}

function lockAnswerControls(root) {
  root.querySelector("#answerOptions").style.display = "none";
  root.querySelector("#answer").disabled = true;
  root.querySelector("#btnSend").disabled = true;
}

function startChat(root, message, awaiting, options) {
  root.querySelector("#chatCard").style.display = "block";
  root.querySelector("#chat").innerHTML = "";
  root.querySelector("#doneBox").innerHTML = "";
  root.querySelector("#consultCard").style.display = "none";
  addMsg(root, "assistant", message);
  showAnswerControls(root, awaiting, options);
  if (!awaiting) finishChat(root);
}

function finishChat(root) {
  root.querySelector("#doneBox").innerHTML = '<div class="done">✓ Screening complete</div>';
  root.querySelector("#consultCard").style.display = "block";
  root.querySelector("#answerOptions").style.display = "none";
  root.querySelector("#answerRow").style.display = "none";
  const rl = root.querySelector("#reportLink");
  if (rl) {
    rl.href = `/report/${sessionId}?token=${getSession().token}`;
    rl.style.display = "inline-block";
  }
  loadDoctors(root);
  refreshRefinedResult(root);
}

// After the questions, pull the finalised result and update the result card so the
// confidence/diagnosis reflect the answers (not just the photo).
async function refreshRefinedResult(root) {
  if (!lastBrief) return;
  try {
    const r = await apiGet(`/chat/${sessionId}/result`);
    if (r && r.disease) {
      lastBrief = { ...lastBrief, disease: r.disease, confidence: r.confidence, urgent: r.urgent };
      renderBrief(root, lastBrief, true);
    }
  } catch { /* result not ready / not refined — leave the image result as-is */ }
}

async function sendAnswer(root, forced) {
  const inp = root.querySelector("#answer");
  const text = forced != null ? forced : inp.value.trim();
  if (!text || !sessionId) return;
  addMsg(root, "user", text);
  if (forced == null) inp.value = "";
  lockAnswerControls(root);
  try {
    const turn = await apiPost("/chat/answer", { session_id: sessionId, answer: text });
    addMsg(root, "assistant", turn.message);
    if (turn.done) finishChat(root);
    else showAnswerControls(root, true, turn.options);
  } catch (err) {
    addMsg(root, "assistant", "⚠️ " + errText(err));
    showAnswerControls(root, true, lastOptions);
  }
}

// Reusable booking UI — works from the diagnose flow AND from past screenings.
async function loadDoctors(root, sid = sessionId, listSel = "#docList", outSel = "#consultOut") {
  const el = root.querySelector(listSel);
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
      b.onclick = () => book(root, b.dataset.doc, b.dataset.slot, sid, listSel, outSel));
  } catch (err) {
    el.innerHTML = `<div class="err">${esc(errText(err))}</div>`;
  }
}

async function book(root, doctorId, slotId, sid = sessionId, listSel = "#docList", outSel = "#consultOut") {
  const out = root.querySelector(outSel);
  const noteEl = root.querySelector("#consultNote");
  try {
    const c = await apiPost("/consult/request", {
      session_id: sid, doctor_id: doctorId, slot_id: slotId,
      mode: "video", note: (noteEl && noteEl.value) || null,
    });
    out.innerHTML = `✅ Appointment requested with <b>${esc(c.doctor_name)}</b> for
      <b>${esc(fmtDateTime(c.appointment_time))}</b>. You'll be notified when the doctor confirms.
      <a href="#/patient/appointments">View my appointments →</a>`;
    loadDoctors(root, sid, listSel, outSel);   // refresh so the booked slot disappears
  } catch (err) {
    out.innerHTML = `<span class="err">Error: ${esc(errText(err))}</span>`;
  }
}

/* ---------------- Appointments ---------------- */
const STATUS_LABEL = {
  pending: "Awaiting confirmation", confirmed: "Confirmed",
  declined: "Declined", cancelled: "Cancelled", closed: "Completed",
};

async function cancelAppt(root, id) {
  if (!confirm("Cancel this appointment? The time slot will be released.")) return;
  try {
    await apiPost(`/consult/${id}/cancel`, {});
    toast("Appointment cancelled", "ok");
    renderAppointments(root);
  } catch (e) { toast(errText(e), "err"); }
}

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
            <span class="badge ${c.status === "confirmed" ? "b-verified" : (c.status === "declined" || c.status === "cancelled") ? "b-urgent" : "b-normal"}">${esc(STATUS_LABEL[c.status] || c.status)}</span>
            <div class="meta">${esc(fmtDateTime(c.appointment_time))}${c.brief ? " · " + esc(c.brief.disease) : ""}</div>
            ${c.note ? `<div class="meta">your note: ${esc(c.note)}</div>` : ""}
            ${c.solution ? `<div class="meta">💬 Doctor's advice: ${esc(c.solution)}</div>` : ""}
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <a class="btn purple sm" href="/report/${esc(c.session_id)}?token=${esc(getSession().token)}" target="_blank" rel="noopener" style="text-decoration:none">📄 Report</a>
            ${join}
            ${(c.status === "pending" || c.status === "confirmed") ? `<button class="btn err sm" data-cancel="${esc(c.id)}">Cancel</button>` : ""}
          </div>
        </div>
      </div>`;
    }).join("") : '<div class="empty">No appointments yet. Run a screening, then book a dermatologist.</div>';
    el.querySelectorAll("[data-cancel]").forEach(b => b.onclick = () => cancelAppt(root, b.dataset.cancel));
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
      <div class="item" style="flex-direction:column;align-items:stretch">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap">
          <div>
            <b>${esc(s.disease)}</b> ${modeBadge(s.mode)} ${s.urgent ? '<span class="badge b-urgent">URGENT</span>' : ""}
            <div class="meta">confidence ${(s.confidence * 100).toFixed(1)}% · ${s.done ? "completed" : "in progress"}</div>
            <div class="meta">session ${esc(s.session_id)}</div>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <a class="btn purple sm" href="/report/${esc(s.session_id)}?token=${esc(getSession().token)}" target="_blank" rel="noopener" style="text-decoration:none">📄 Report</a>
            <button class="btn teal sm" data-book="${esc(s.session_id)}">🎥 Book a dermatologist</button>
          </div>
        </div>
        <div id="bklist_${esc(s.session_id)}" style="display:none;margin-top:10px"></div>
        <div class="muted" id="bkout_${esc(s.session_id)}" style="margin-top:6px"></div>
      </div>`).join("") : '<div class="empty">No screenings yet. Run one from the Diagnose tab.</div>';
    el.querySelectorAll("[data-book]").forEach(b => b.onclick = () => {
      const sid = b.dataset.book;
      const panel = root.querySelector(`#bklist_${sid}`);
      if (panel.style.display === "block") { panel.style.display = "none"; return; }
      panel.style.display = "block";
      loadDoctors(root, sid, `#bklist_${sid}`, `#bkout_${sid}`);
    });
  } catch (err) {
    root.querySelector("#hist").innerHTML = `<div class="err">${esc(errText(err))}</div>`;
  }
}

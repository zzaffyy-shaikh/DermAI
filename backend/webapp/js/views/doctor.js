// Doctor console: availability, incoming requests (with full context), and
// appointments with solution notes. Online consults are dermatologist-only.
import { layout, bindLayout, esc, modeBadge, medicalFormHTML, collectMedical, fmtDateTime } from "../ui.js";
import { apiGet, apiPost, apiPut, apiDelete, errText } from "../api.js";
import { getSession } from "../store.js";

export function mount(root) {
  root.innerHTML = layout("#/doctor", `
    <div class="page-title">Doctor Console</div>

    <div class="grid" style="margin-bottom:18px">
      <div class="stat"><div class="k">Requests</div><div class="v" id="stReq">–</div></div>
      <div class="stat"><div class="k">Upcoming</div><div class="v" id="stUp">–</div></div>
      <div class="stat"><div class="k">Resolved</div><div class="v" id="stDone">–</div></div>
    </div>

    <div class="card" id="availErr" style="display:none"></div>

    <div class="card">
      <h2>📅 My availability <button class="btn ghost sm" id="btnAvail" style="margin-left:auto">↻</button></h2>
      <div class="muted" style="margin-bottom:8px">Publish time slots patients can book.</div>
      <div class="row">
        <div><label>Add a slot</label><input type="datetime-local" id="slotInput"></div>
        <div style="flex:0 0 130px"><label>&nbsp;</label><button class="btn teal" id="btnAddSlot">Add slot</button></div>
      </div>
      <div class="list" id="slots" style="margin-top:12px"><div class="empty">Loading…</div></div>
    </div>

    <div class="card">
      <h2>🔔 Incoming requests <button class="btn ghost sm" id="btnReq" style="margin-left:auto">↻</button></h2>
      <div class="list" id="requests"><div class="empty">Loading…</div></div>
    </div>

    <div class="card">
      <h2>🩺 My appointments <button class="btn ghost sm" id="btnMine" style="margin-left:auto">↻</button></h2>
      <div class="list" id="mine"><div class="empty">Loading…</div></div>
    </div>

    <div id="mhModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.5);z-index:50;align-items:center;justify-content:center;padding:20px">
      <div class="card" style="max-width:560px;width:100%;max-height:85vh;overflow:auto">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <h2 style="margin:0">Patient Medical History</h2>
          <button class="btn ghost sm" id="mhClose">Close</button>
        </div>
        <div id="mhBody" style="margin-top:10px"></div>
      </div>
    </div>`);
  bindLayout();

  root.querySelector("#btnAvail").onclick = () => loadAvailability(root);
  root.querySelector("#btnReq").onclick = () => loadRequests(root);
  root.querySelector("#btnMine").onclick = () => loadMine(root);
  root.querySelector("#btnAddSlot").onclick = () => addSlot(root);
  root.querySelector("#mhClose").onclick = () => { root.querySelector("#mhModal").style.display = "none"; };

  loadAvailability(root); loadRequests(root); loadMine(root);
}

/* ---------------- availability ---------------- */
async function loadAvailability(root) {
  const el = root.querySelector("#slots");
  try {
    const slots = await apiGet("/consult/availability");
    el.innerHTML = slots.length ? slots.map(s => `
      <div class="item">
        <div><b>${esc(fmtDateTime(s.start))}</b>
          <span class="badge ${s.status === "open" ? "b-normal" : "b-pending"}">${esc(s.status)}</span></div>
        ${s.status === "open" ? `<button class="btn err sm" data-rmslot="${esc(s.id)}">Remove</button>` : ""}
      </div>`).join("") : '<div class="empty">No slots yet — add one above.</div>';
    el.querySelectorAll("[data-rmslot]").forEach(b => b.onclick = () => removeSlot(root, b.dataset.rmslot));
    root.querySelector("#availErr").style.display = "none";
  } catch (e) {
    // a non-dermatologist (or unverified) doctor lands here
    const box = root.querySelector("#availErr");
    box.style.display = "block";
    box.innerHTML = `<div class="muted">${esc(errText(e))}</div>`;
    el.innerHTML = '<div class="empty">Availability unavailable.</div>';
  }
}

async function addSlot(root) {
  const inp = root.querySelector("#slotInput");
  if (!inp.value) return;
  try {
    await apiPost("/consult/availability", { slots: [inp.value + ":00"] });
    inp.value = "";
    loadAvailability(root);
  } catch (e) { alert(errText(e)); }
}

async function removeSlot(root, id) {
  try { await apiDelete(`/consult/availability/${id}`); loadAvailability(root); }
  catch (e) { alert(errText(e)); }
}

/* ---------------- case rendering ---------------- */
function caseHeader(c) {
  const b = c.brief || {};
  const urgent = b.urgent ? '<span class="badge b-urgent">URGENT</span>' : "";
  const conf = b.confidence != null ? ` · ${(b.confidence * 100).toFixed(0)}%` : "";
  return `<b>${esc(b.disease || "Unknown")}</b> ${b.mode ? modeBadge(b.mode) : ""} ${urgent}
    <div class="meta">${esc(c.patient_name || c.patient_id)} · 🕒 ${esc(fmtDateTime(c.appointment_time))}${conf}</div>
    ${c.note ? `<div class="meta">note: ${esc(c.note)}</div>` : ""}`;
}

function contextButtons(c) {
  const token = getSession().token;
  return `
    <a class="btn purple sm" href="/report/${esc(c.session_id)}?token=${esc(token)}" target="_blank" rel="noopener" style="text-decoration:none">📄 Report</a>
    <button class="btn sm" style="background:var(--warn)" data-history="${esc(c.patient_id)}">🩺 History</button>`;
}

function casePhoto(c) {
  const token = getSession().token;
  const src = `/image/${esc(c.session_id)}?token=${esc(token)}`;
  return `<a href="${src}" target="_blank" rel="noopener" title="Open full size">
    <img src="${src}" alt="affected area"
      style="width:84px;height:84px;object-fit:cover;border-radius:10px;border:1px solid var(--line)"
      onerror="this.style.display='none'"></a>`;
}

async function loadRequests(root) {
  const el = root.querySelector("#requests");
  try {
    const cases = await apiGet("/consult/requests");
    root.querySelector("#stReq").textContent = cases.length;
    el.innerHTML = cases.length ? cases.map(c => `
      <div class="item" style="flex-direction:column;align-items:stretch">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap">
          <div style="display:flex;gap:12px">${casePhoto(c)}<div>${caseHeader(c)}</div></div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            ${contextButtons(c)}
            <button class="btn ok sm" data-confirm="${esc(c.id)}">✓ Confirm</button>
            <button class="btn err sm" data-decline="${esc(c.id)}">Decline</button>
          </div>
        </div>
      </div>`).join("") : '<div class="empty">No pending requests.</div>';
    bindHistory(root, el);
    el.querySelectorAll("[data-confirm]").forEach(b => b.onclick = () => act(root, b.dataset.confirm, "confirm"));
    el.querySelectorAll("[data-decline]").forEach(b => b.onclick = () => act(root, b.dataset.decline, "decline"));
  } catch (e) { el.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

async function loadMine(root) {
  const el = root.querySelector("#mine");
  try {
    const cases = (await apiGet("/consult/mine")).filter(c => c.status !== "pending" && c.status !== "declined");
    root.querySelector("#stUp").textContent = cases.filter(c => c.status === "confirmed").length;
    root.querySelector("#stDone").textContent = cases.filter(c => c.status === "closed").length;
    el.innerHTML = cases.length ? cases.map(c => `
      <div class="item" style="flex-direction:column;align-items:stretch">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap">
          <div style="display:flex;gap:12px">${casePhoto(c)}<div>${caseHeader(c)}</div></div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <span class="badge ${c.status === "closed" ? "b-verified" : "b-normal"}">${esc(c.status)}</span>
            ${contextButtons(c)}
            ${c.room ? `<a class="btn ok sm" href="https://meet.jit.si/${esc(c.room)}" target="_blank" rel="noopener" style="text-decoration:none">🎥 Join</a>` : ""}
            <button class="btn ghost sm" data-close="${esc(c.id)}">Close</button>
          </div>
        </div>
        <label>Solution / advice</label>
        <textarea id="sol_${esc(c.id)}" rows="2" placeholder="Your assessment & advice for the patient">${esc(c.solution || "")}</textarea>
        <div style="margin-top:8px"><button class="btn sm" data-solve="${esc(c.id)}">Save solution</button></div>
      </div>`).join("") : '<div class="empty">No confirmed appointments yet.</div>';
    bindHistory(root, el);
    el.querySelectorAll("[data-close]").forEach(b => b.onclick = () => act(root, b.dataset.close, "close"));
    el.querySelectorAll("[data-solve]").forEach(b => b.onclick = () => saveSolution(root, b.dataset.solve));
  } catch (e) { el.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

function bindHistory(root, el) {
  el.querySelectorAll("[data-history]").forEach(b => b.onclick = () => openHistory(root, b.dataset.history));
}

async function act(root, id, action) {
  try { await apiPost(`/consult/${id}/${action}`, {}); loadRequests(root); loadMine(root); }
  catch (e) { alert(errText(e)); }
}

async function saveSolution(root, id) {
  const ta = root.querySelector("#sol_" + id);
  try { await apiPost(`/consult/${id}/solution`, { solution: ta.value }); loadMine(root); }
  catch (e) { alert(errText(e)); }
}

async function openHistory(root, uid) {
  const modal = root.querySelector("#mhModal");
  const body = root.querySelector("#mhBody");
  body.innerHTML = "Loading…";
  modal.style.display = "flex";
  try {
    const r = await apiGet(`/profile/medical-history/${uid}`);
    body.innerHTML = medicalFormHTML(r.history, "dmh_")
      + `<div style="margin-top:12px"><button class="btn" id="dmhSave">Save</button> <span class="muted" id="dmhStatus"></span></div>`;
    root.querySelector("#dmhSave").onclick = async () => {
      try {
        await apiPut(`/profile/medical-history/${uid}`, collectMedical(root, "dmh_"));
        root.querySelector("#dmhStatus").textContent = "✓ Saved";
      } catch (e) { root.querySelector("#dmhStatus").textContent = "Error: " + errText(e); }
    };
  } catch (e) { body.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

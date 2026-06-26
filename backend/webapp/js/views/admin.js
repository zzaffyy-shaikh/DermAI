// Management dashboard: system stats + verification queue for doctors & management,
// plus a searchable patient registry.
import { layout, bindLayout, esc, fmtDateTime, toast } from "../ui.js";
import { apiGet, apiPost, apiDelete, errText } from "../api.js";
import { getSession } from "../store.js";

const BASE = window.location.origin;

export function mount(root) {
  root.innerHTML = layout("#/admin", `
    <div class="page-title">Management</div>

    <div class="card">
      <h2>📊 System statistics <button class="btn ghost sm" id="btnStats" style="margin-left:auto">↻</button></h2>
      <div class="grid" id="stats"><div class="empty">Loading…</div></div>
    </div>

    <div class="card">
      <h2>🕓 Pending verification <button class="btn ghost sm" id="btnPending" style="margin-left:auto">↻</button></h2>
      <div class="muted" style="margin-bottom:8px">Review credentials, then approve or reject.</div>
      <div id="pending"><div class="empty">Loading…</div></div>
    </div>

    <div class="card">
      <h2>🧑‍🦰 Patients <button class="btn ghost sm" id="btnPatients" style="margin-left:auto">↻</button></h2>
      <div class="muted" style="margin-bottom:8px">Search by patient ID, username, name or email to see their problem and what happened.</div>
      <div class="row">
        <div style="flex:1"><input id="patSearch" placeholder="Search patients…"></div>
        <div style="flex:0 0 120px"><button class="btn" id="btnPatSearch">Search</button></div>
      </div>
      <div class="list" id="patients" style="margin-top:12px"><div class="empty">Loading…</div></div>
    </div>

    <div class="card">
      <h2>👨‍⚕️ All doctors <button class="btn ghost sm" id="btnDoctors" style="margin-left:auto">↻</button></h2>
      <div class="list" id="doctors"></div>
    </div>

    <div id="patModal" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.5);z-index:50;align-items:center;justify-content:center;padding:20px">
      <div class="card" style="max-width:640px;width:100%;max-height:85vh;overflow:auto">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <h2 style="margin:0">Patient record</h2>
          <button class="btn ghost sm" id="patClose">Close</button>
        </div>
        <div id="patBody" style="margin-top:10px"></div>
      </div>
    </div>`);
  bindLayout();

  root.querySelector("#btnStats").onclick = () => loadStats(root);
  root.querySelector("#btnPending").onclick = () => loadPending(root);
  root.querySelector("#btnDoctors").onclick = () => loadDoctors(root);
  root.querySelector("#btnPatients").onclick = () => loadPatients(root);
  root.querySelector("#btnPatSearch").onclick = () => loadPatients(root, root.querySelector("#patSearch").value);
  root.querySelector("#patSearch").addEventListener("keydown", e => {
    if (e.key === "Enter") loadPatients(root, e.target.value);
  });
  root.querySelector("#patClose").onclick = () => { root.querySelector("#patModal").style.display = "none"; };
  loadStats(root); loadPending(root); loadDoctors(root); loadPatients(root);
}

async function loadPatients(root, q) {
  const el = root.querySelector("#patients");
  el.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    const items = await apiGet("/admin/patients" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    el.innerHTML = items.length ? items.map(p => `
      <div class="item">
        <div>
          <b>${esc(p.name || p.username)}</b> <span class="muted">@${esc(p.username)}</span>
          <div class="meta">ID ${esc(p.uid)}</div>
          <div class="meta">${p.age != null ? esc(p.age) + "y · " : ""}${esc(p.gender || "—")} · ${p.screenings} screening(s) · ${p.consultations} consult(s)</div>
        </div>
        <button class="btn sm" data-pat="${esc(p.uid)}">View record</button>
      </div>`).join("") : '<div class="empty">No matching patients.</div>';
    el.querySelectorAll("[data-pat]").forEach(b => b.onclick = () => openPatient(root, b.dataset.pat));
  } catch (e) { el.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

async function openPatient(root, uid) {
  const modal = root.querySelector("#patModal");
  const body = root.querySelector("#patBody");
  body.innerHTML = "Loading…";
  modal.style.display = "flex";
  try {
    const p = await apiGet(`/admin/patients/${uid}`);
    const mh = p.medical_history || {};
    const mhRows = Object.entries(mh).filter(([, v]) => v != null && v !== "")
      .map(([k, v]) => `<div class="meta">${esc(k.replace(/_/g, " "))}: ${esc(v)}</div>`).join("") || '<div class="meta">No medical history on file.</div>';
    const screenings = p.screenings.length ? p.screenings.map(s => `
      <div class="item" style="flex-direction:column;align-items:stretch">
        <div><b>${esc(s.disease || "—")}</b> <span class="badge b-${esc(s.mode || "normal")}">${esc(s.mode || "—")}</span>
          ${s.urgent ? '<span class="badge b-urgent">URGENT</span>' : ""}
          <span class="muted">${s.confidence != null ? (s.confidence * 100).toFixed(0) + "%" : ""}</span></div>
        ${s.outcome ? `<div class="meta">outcome: ${esc(s.outcome)}</div>` : `<div class="meta">${s.done ? "completed" : "in progress"}</div>`}
        ${s.recommendation ? `<div class="meta">recommendation: ${esc(s.recommendation)}</div>` : ""}
      </div>`).join("") : '<div class="empty">No screenings.</div>';
    const consults = p.consultations.length ? p.consultations.map(c => `
      <div class="item" style="flex-direction:column;align-items:stretch">
        <div><b>${esc(c.doctor_name || "—")}</b> <span class="badge ${c.status === "confirmed" ? "b-verified" : c.status === "declined" ? "b-urgent" : "b-normal"}">${esc(c.status)}</span>
          <span class="muted">${esc(fmtDateTime(c.appointment_time))}</span></div>
        ${c.disease ? `<div class="meta">problem: ${esc(c.disease)}</div>` : ""}
        ${c.solution ? `<div class="meta">💬 advice: ${esc(c.solution)}</div>` : ""}
      </div>`).join("") : '<div class="empty">No consultations.</div>';
    body.innerHTML = `
      <div><b>${esc(p.name || p.username)}</b> <span class="muted">@${esc(p.username)} · ${esc(p.email || "no email")}</span></div>
      <div class="meta">ID ${esc(p.uid)} · ${p.age != null ? esc(p.age) + "y · " : ""}${esc(p.gender || "—")}</div>
      <h3 style="margin:14px 0 6px">Medical history</h3>${mhRows}
      <h3 style="margin:14px 0 6px">Screenings &amp; outcomes</h3><div class="list">${screenings}</div>
      <h3 style="margin:14px 0 6px">Consultations</h3><div class="list">${consults}</div>`;
  } catch (e) { body.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

async function loadStats(root) {
  const el = root.querySelector("#stats");
  try {
    const s = await apiGet("/admin/stats");
    el.innerHTML = Object.entries(s).map(([k, v]) =>
      `<div class="stat"><div class="k">${k.replace(/_/g, " ")}</div><div class="v">${v}</div></div>`).join("");
  } catch (e) { el.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

async function loadPending(root) {
  const el = root.querySelector("#pending");
  try {
    const p = await apiGet("/admin/pending");
    const docs = p.doctors.map(d => `
      <div class="item">
        <div>
          <b>${esc(d.name || d.username)}</b> <span class="muted">@${esc(d.username)} · doctor</span>
          <div class="meta">${esc(d.specialization || "—")} · ${esc(d.qualification || "—")}</div>
          <div class="meta">Grad: ${esc(d.graduation || "—")} · House job: ${esc(d.house_job || "—")}</div>
          <div class="meta">PMDC: ${esc(d.pmdc_number || "—")}</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          ${d.has_license
            ? `<button class="btn ghost sm" data-license="${esc(d.uid)}">📄 License</button>`
            : `<span class="badge b-pending">no license</span>`}
          <button class="btn ok sm" data-approve="${esc(d.uid)}">Approve</button>
          <button class="btn err sm" data-reject="${esc(d.uid)}">Reject</button>
        </div>
      </div>`).join("");
    const mgmt = p.management.map(a => `
      <div class="item">
        <div><b>${esc(a.name || a.username)}</b> <span class="muted">@${esc(a.username)} · management</span></div>
        <div style="display:flex;gap:8px">
          <button class="btn ok sm" data-approve="${esc(a.uid)}">Approve</button>
          <button class="btn err sm" data-reject="${esc(a.uid)}">Reject</button>
        </div>
      </div>`).join("");
    const body = docs + mgmt;
    el.innerHTML = body || '<div class="empty">Nothing pending.</div>';

    el.querySelectorAll("[data-approve]").forEach(b => b.onclick = () => verify(root, b.dataset.approve, true));
    el.querySelectorAll("[data-reject]").forEach(b => b.onclick = () => reject(root, b.dataset.reject));
    el.querySelectorAll("[data-license]").forEach(b => b.onclick = () => viewLicense(b.dataset.license));
  } catch (e) { el.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

async function loadDoctors(root) {
  const el = root.querySelector("#doctors");
  try {
    const docs = await apiGet("/admin/doctors");
    el.innerHTML = docs.length ? docs.map(d => `
      <div class="item">
        <div>
          <b>${esc(d.name || d.username)}</b> <span class="muted">@${esc(d.username)}</span>
          <div class="meta">${esc(d.specialization || "—")} · ${esc(d.qualification || "—")} · PMDC: ${esc(d.pmdc_number || "—")}</div>
          <div class="meta">Grad: ${esc(d.graduation || "—")} · House job: ${esc(d.house_job || "—")}</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          ${d.has_license ? `<button class="btn ghost sm" data-license="${esc(d.uid)}">📄 License</button>` : `<span class="badge b-pending">no license</span>`}
          <span class="badge ${d.verified ? "b-verified" : "b-pending"}">${d.verified ? "verified" : "pending"}</span>
          ${d.verified
            ? `<button class="btn err sm" data-revoke="${esc(d.uid)}">Revoke</button>`
            : `<button class="btn ok sm" data-approve="${esc(d.uid)}">Approve</button>`}
        </div>
      </div>`).join("") : '<div class="empty">No doctors yet.</div>';
    el.querySelectorAll("[data-approve]").forEach(b => b.onclick = () => verify(root, b.dataset.approve, true));
    el.querySelectorAll("[data-revoke]").forEach(b => b.onclick = () => verify(root, b.dataset.revoke, false));
    el.querySelectorAll("[data-license]").forEach(b => b.onclick = () => viewLicense(b.dataset.license));
  } catch (e) { el.innerHTML = `<div class="err">${esc(errText(e))}</div>`; }
}

async function verify(root, uid, approved) {
  try {
    await apiPost("/admin/verify", { uid, approved });
    loadPending(root); loadDoctors(root); loadStats(root);
  } catch (e) { toast(errText(e), "err"); }
}

async function reject(root, uid) {
  if (!confirm("Reject and permanently delete this account? This cannot be undone.")) return;
  try {
    await apiDelete(`/admin/users/${uid}`);
    loadPending(root); loadDoctors(root); loadStats(root);
  } catch (e) { toast(errText(e), "err"); }
}

async function viewLicense(uid) {
  try {
    const s = getSession();
    const r = await fetch(`${BASE}/admin/doctors/${uid}/license`, { headers: { Authorization: "Bearer " + s.token } });
    if (!r.ok) { toast("No license available", "err"); return; }
    const blob = await r.blob();
    window.open(URL.createObjectURL(blob), "_blank");
  } catch (e) { toast(errText(e), "err"); }
}

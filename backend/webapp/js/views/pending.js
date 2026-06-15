// Shown to doctors / management whose accounts await admin verification.
import { getSession, clearSession, patchSession } from "../store.js";
import { apiGet, errText } from "../api.js";

const BASE = window.location.origin;

export function mount(root) {
  const s = getSession();
  const isDoctor = s.role === "doctor";
  root.innerHTML = `
    <div class="login-wrap">
      <div class="login-card">
        <div class="brand"><span>Derm</span>AI</div>
        <div class="sub">Account pending verification</div>
        <div class="hint">
          Your <b>${s.role === "admin" ? "management" : "doctor"}</b> account is awaiting approval by
          a verified administrator. You'll get access once it's reviewed.
        </div>
        ${isDoctor ? `
          <label>Upload your medical license / PMDC registration</label>
          <input type="file" id="lic" accept="image/*,application/pdf">
          <button class="btn block" id="uploadBtn" style="margin-top:10px">Upload license</button>
          <div class="muted" id="licStatus" style="margin-top:8px"></div>
        ` : ""}
        <div style="margin-top:18px"></div>
        <button class="btn block" id="refreshBtn">I've been approved — check status</button>
        <button class="btn ghost block" id="logoutBtn" style="margin-top:10px">Logout</button>
        <div class="err" id="err"></div>
      </div>
    </div>`;

  if (isDoctor) {
    root.querySelector("#uploadBtn").onclick = async () => {
      const f = root.querySelector("#lic").files[0];
      const st = root.querySelector("#licStatus");
      if (!f) { st.textContent = "Choose a file first."; return; }
      try {
        const fd = new FormData();
        fd.append("file", f);
        const r = await fetch(BASE + "/auth/license", {
          method: "POST",
          headers: { Authorization: "Bearer " + s.token },
          body: fd,
        });
        if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
        st.textContent = "✓ License uploaded — management can now review it.";
      } catch (e) { st.textContent = "Error: " + errText(e); }
    };
  }

  root.querySelector("#refreshBtn").onclick = async () => {
    try {
      const me = await apiGet("/auth/me");
      if (me.verified) {
        patchSession({ verified: true });
        location.hash = s.role === "doctor" ? "#/doctor" : "#/admin";
      } else {
        root.querySelector("#err").textContent = "Still pending — please check back later.";
      }
    } catch (e) { root.querySelector("#err").textContent = errText(e); }
  };

  root.querySelector("#logoutBtn").onclick = () => { clearSession(); location.hash = "#/login"; };
}

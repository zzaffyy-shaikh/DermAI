// Login + account creation. Patients and doctors can self-register; admin is seeded.
import { setSession } from "../store.js";
import { apiGet, apiPost, errText } from "../api.js";

const dashboard = r => r === "patient" ? "#/patient" : r === "doctor" ? "#/doctor" : "#/admin";

export function mount(root) {
  let tab = "signin";   // signin | signup
  let role = "patient"; // for signup

  render();

  function render() {
    root.innerHTML = `
      <div class="login-wrap">
        <form class="login-card" id="form">
          <div class="brand"><span>Derm</span>AI</div>
          <div class="sub">AI-powered skin disease screening</div>

          <div class="seg" id="modeSeg">
            <button type="button" class="seg-btn ${tab === "signin" ? "active" : ""}" data-tab="signin">Sign in</button>
            <button type="button" class="seg-btn ${tab === "signup" ? "active" : ""}" data-tab="signup">Create account</button>
          </div>

          ${tab === "signup" ? roleSelector() : ""}

          <label>Username</label>
          <input id="username" placeholder="e.g. ali" autocomplete="username" required>
          <label>Password</label>
          <input id="password" type="password" placeholder="••••••••" autocomplete="${tab === "signup" ? "new-password" : "current-password"}" required>

          ${tab === "signup" ? signupFields() : ""}

          <div style="margin-top:18px"></div>
          <button class="btn block" type="submit">${tab === "signin" ? "Sign in" : "Create account"}</button>
          <div id="googleWrap" style="display:none"><div class="divider">or</div><div id="googleBox"></div></div>
          <div class="err" id="err"></div>
          ${tab === "signin" ? '<div class="hint" style="margin-top:14px">No account? Choose <b>Create account</b>. Admin uses the seeded credentials.</div>' : ""}
        </form>
      </div>`;

    bind();
  }

  function roleSelector() {
    return `
      <div class="seg" style="margin-top:6px">
        <button type="button" class="seg-btn ${role === "patient" ? "active" : ""}" data-role="patient">🧑 Patient</button>
        <button type="button" class="seg-btn ${role === "doctor" ? "active" : ""}" data-role="doctor">👨‍⚕️ Doctor</button>
        <button type="button" class="seg-btn ${role === "admin" ? "active" : ""}" data-role="admin">🛡️ Mgmt</button>
      </div>`;
  }

  function signupFields() {
    const common = `
      <label>Full name</label><input id="name" placeholder="Full name">
      <label>Email</label><input id="email" type="email" placeholder="you@example.com">`;
    if (role === "doctor") {
      return common + `
        <label>Specialization</label><input id="specialization" placeholder="e.g. Dermatology">
        <label>Qualification</label><input id="qualification" placeholder="e.g. MBBS, FCPS">
        <label>Graduated from (institute / year)</label><input id="graduation" placeholder="e.g. Dow Medical College, 2021">
        <label>House job / internship</label><input id="house_job" placeholder="e.g. 1 yr at Civil Hospital">
        <label>PMDC registration no.</label><input id="pmdc_number" placeholder="e.g. 12345-P">
        <div class="hint" style="margin-top:12px">After signing up you'll <b>upload your license</b> and wait for <b>management verification</b>.</div>`;
    }
    if (role === "admin") {
      return common + `<div class="hint" style="margin-top:12px">Management accounts must be <b>approved by an existing administrator</b> before access.</div>`;
    }
    return common + `
      <div class="row">
        <div><label>Age</label><input id="age" type="number" min="0" placeholder="e.g. 24"></div>
        <div><label>Gender</label>
          <select id="gender"><option value="">—</option><option>Male</option><option>Female</option><option>Other</option></select>
        </div>
      </div>`;
  }

  function bind() {
    root.querySelectorAll("[data-tab]").forEach(b =>
      b.onclick = () => { tab = b.dataset.tab; render(); });
    root.querySelectorAll("[data-role]").forEach(b =>
      b.onclick = () => { role = b.dataset.role; render(); });

    root.querySelector("#form").onsubmit = async e => {
      e.preventDefault();
      const err = root.querySelector("#err");
      err.textContent = "";
      const username = root.querySelector("#username").value.trim();
      const password = root.querySelector("#password").value;
      if (!username || !password) { err.textContent = "Username and password are required."; return; }

      try {
        let auth;
        if (tab === "signin") {
          auth = await apiPost("/auth/login", { username, password });
        } else {
          const body = {
            username, password, role,
            name: val("name"), email: val("email"),
          };
          if (role === "patient") {
            body.age = val("age") ? Number(val("age")) : null;
            body.gender = val("gender") || null;
          } else if (role === "doctor") {
            body.specialization = val("specialization") || null;
            body.qualification = val("qualification") || null;
            body.graduation = val("graduation") || null;
            body.house_job = val("house_job") || null;
            body.pmdc_number = val("pmdc_number") || null;
          }
          auth = await apiPost("/auth/register", body);
        }
        setSession(auth);
        location.hash = dashboard(auth.user.role);
      } catch (ex) {
        err.textContent = errText(ex);
      }
    };

    setupGoogle();
  }

  async function setupGoogle() {
    const wrap = root.querySelector("#googleWrap");
    const box = root.querySelector("#googleBox");
    if (!wrap || !box) return;
    let cfg;
    try { cfg = await apiGet("/auth/google-config"); } catch { return; }
    if (!cfg.client_id) return;                 // not configured -> stay hidden
    try {
      await loadGsi();
      window.google.accounts.id.initialize({ client_id: cfg.client_id, callback: onGoogle });
      box.innerHTML = "";
      window.google.accounts.id.renderButton(box, {
        theme: "outline", size: "large", width: 330,
        text: tab === "signup" ? "signup_with" : "signin_with",
      });
      wrap.style.display = "block";
    } catch (_) { /* leave hidden */ }
  }

  async function onGoogle(resp) {
    const err = root.querySelector("#err");
    try {
      const auth = await apiPost("/auth/google", { credential: resp.credential });
      setSession(auth);
      location.hash = dashboard(auth.user.role);
    } catch (ex) {
      if (err) err.textContent = errText(ex);
    }
  }

  function loadGsi() {
    return new Promise((resolve, reject) => {
      if (window.google?.accounts?.id) return resolve();
      let s = document.getElementById("gsi-script");
      if (!s) {
        s = document.createElement("script");
        s.id = "gsi-script"; s.src = "https://accounts.google.com/gsi/client";
        s.async = true; s.defer = true;
        document.head.appendChild(s);
      }
      const t = setInterval(() => {
        if (window.google?.accounts?.id) { clearInterval(t); resolve(); }
      }, 100);
      setTimeout(() => { clearInterval(t); reject(new Error("GSI load timeout")); }, 6000);
    });
  }

  function val(id) { const el = root.querySelector("#" + id); return el ? el.value.trim() : ""; }
}

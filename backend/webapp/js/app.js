// Hash router + role guard. Bootstraps the whole web app.
import { getSession } from "./store.js";
import * as login from "./views/login.js";
import * as patient from "./views/patient.js";
import * as doctor from "./views/doctor.js";
import * as admin from "./views/admin.js";
import * as pending from "./views/pending.js";

const root = document.getElementById("app");

function dashboardFor(role) {
  return role === "patient" ? "#/patient" : role === "doctor" ? "#/doctor" : "#/admin";
}

function route() {
  const hash = location.hash || "#/login";
  const s = getSession();

  // not logged in -> force login
  if (!s) {
    if (hash !== "#/login") { location.hash = "#/login"; return; }
    return login.mount(root);
  }

  // doctors & management must be verified before they can use their panel
  if ((s.role === "doctor" || s.role === "admin") && s.verified === false) {
    return pending.mount(root);
  }

  // logged in but on login page -> send to dashboard
  if (hash === "#/login") { location.hash = dashboardFor(s.role); return; }

  // role-guarded sections
  if (hash.startsWith("#/patient")) {
    if (s.role !== "patient") { location.hash = dashboardFor(s.role); return; }
    return patient.mount(root, hash);
  }
  if (hash.startsWith("#/doctor")) {
    if (s.role !== "doctor") { location.hash = dashboardFor(s.role); return; }
    return doctor.mount(root);
  }
  if (hash.startsWith("#/admin")) {
    if (s.role !== "admin") { location.hash = dashboardFor(s.role); return; }
    return admin.mount(root);
  }
  location.hash = dashboardFor(s.role);
}

window.addEventListener("hashchange", route);
window.addEventListener("load", route);

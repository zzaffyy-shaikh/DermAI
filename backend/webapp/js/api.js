// Thin fetch wrapper. Attaches the bearer token from the stored session.
import { getSession } from "./store.js";

const BASE = window.location.origin;

function authHeaders(json) {
  const s = getSession();
  const h = {};
  if (s && s.token) h["Authorization"] = "Bearer " + s.token;
  if (json) h["Content-Type"] = "application/json";
  return h;
}

async function handle(res) {
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) {
    throw (data && data.detail !== undefined) ? data.detail : (data || res.statusText);
  }
  return data;
}

export async function apiGet(path) {
  return handle(await fetch(BASE + path, { headers: authHeaders() }));
}

export async function apiPost(path, body) {
  return handle(await fetch(BASE + path, {
    method: "POST", headers: authHeaders(true), body: JSON.stringify(body || {}),
  }));
}

export async function apiPut(path, body) {
  return handle(await fetch(BASE + path, {
    method: "PUT", headers: authHeaders(true), body: JSON.stringify(body || {}),
  }));
}

export async function apiDelete(path) {
  return handle(await fetch(BASE + path, { method: "DELETE", headers: authHeaders() }));
}

export async function apiUpload(path, formData) {
  return handle(await fetch(BASE + path, {
    method: "POST", headers: authHeaders(false), body: formData,
  }));
}

export function errText(e) {
  // Network failure (server down / offline) throws a TypeError from fetch().
  if (e instanceof TypeError && /fetch|network/i.test(e.message))
    return "Can't reach the server. Please check your connection and try again.";
  if (typeof e === "string") return e;
  // FastAPI/Pydantic validation errors come back as an array of {loc, msg}.
  if (Array.isArray(e)) return e.map((x) => {
    const loc = Array.isArray(x.loc) ? x.loc.filter((p) => p !== "body") : [];
    const field = loc.length ? String(loc[loc.length - 1]).replace(/_/g, " ") : "";
    const msg = (x.msg || "is invalid").replace(/^Value error,?\s*/i, "");
    return field ? `${field.charAt(0).toUpperCase() + field.slice(1)}: ${msg}` : msg;
  }).join("; ");
  if (e && e.message) return e.message;
  try { return JSON.stringify(e); } catch { return String(e); }
}

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
  return typeof e === "string" ? e : JSON.stringify(e);
}

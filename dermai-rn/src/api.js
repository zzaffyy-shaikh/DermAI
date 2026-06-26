import { BASE_URL } from "./config";

let _token = null;
export function setToken(t) { _token = t; }
export function getToken() { return _token; }

function headers(json) {
  const h = {};
  if (_token) h["Authorization"] = "Bearer " + _token;
  if (json) h["Content-Type"] = "application/json";
  return h;
}

// Turn FastAPI/Pydantic error payloads into a readable message instead of raw JSON.
function formatDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((e) => {
      const loc = Array.isArray(e.loc) ? e.loc.filter((p) => p !== "body") : [];
      const field = loc.length ? String(loc[loc.length - 1]).replace(/_/g, " ") : "";
      const msg = (e.msg || "is invalid").replace(/^Value error,?\s*/i, "");
      return field ? `${field.charAt(0).toUpperCase() + field.slice(1)}: ${msg}` : msg;
    }).join("\n");
  }
  return detail ? String(detail) : "Something went wrong.";
}

async function handle(res) {
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) {
    const detail = data && data.detail !== undefined ? data.detail : data;
    throw new Error(formatDetail(detail));
  }
  return data;
}

export async function apiGet(path) {
  return handle(await fetch(BASE_URL + path, { headers: headers() }));
}

export async function apiPost(path, body) {
  return handle(await fetch(BASE_URL + path, {
    method: "POST", headers: headers(true), body: JSON.stringify(body || {}),
  }));
}

export async function apiPut(path, body) {
  return handle(await fetch(BASE_URL + path, {
    method: "PUT", headers: headers(true), body: JSON.stringify(body || {}),
  }));
}

export async function apiDelete(path) {
  return handle(await fetch(BASE_URL + path, { method: "DELETE", headers: headers() }));
}

// React Native multipart upload: file is { uri, name, type }.
export async function apiUpload(path, imageUri, fields) {
  const name = imageUri.split("/").pop() || "upload.jpg";
  let ext = (name.split(".").pop() || "jpg").toLowerCase();
  if (ext === "jpg") ext = "jpeg";
  const form = new FormData();
  form.append("image", { uri: imageUri, name, type: `image/${ext}` });
  Object.entries(fields || {}).forEach(([k, v]) => form.append(k, v));
  return handle(await fetch(BASE_URL + path, {
    method: "POST", headers: headers(false), body: form,
  }));
}

import { BASE_URL } from "./config";

let _token = null;
export function setToken(t) { _token = t; }

function headers(json) {
  const h = {};
  if (_token) h["Authorization"] = "Bearer " + _token;
  if (json) h["Content-Type"] = "application/json";
  return h;
}

async function handle(res) {
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) {
    const detail = data && data.detail !== undefined ? data.detail : data;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
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

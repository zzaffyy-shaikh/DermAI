// Session persistence. Holds the auth token + the public user object.
const KEY = "dermai.session";

export function getSession() {
  try { return JSON.parse(localStorage.getItem(KEY)); }
  catch { return null; }
}

// auth = { token, user: { uid, username, role, name, verified, ... } }
export function setSession(auth) {
  localStorage.setItem(KEY, JSON.stringify({
    token: auth.token,
    uid: auth.user.uid,
    role: auth.user.role,
    username: auth.user.username,
    name: auth.user.name,
    verified: auth.user.verified !== false,
  }));
}

export function patchSession(patch) {
  const s = getSession();
  if (s) localStorage.setItem(KEY, JSON.stringify({ ...s, ...patch }));
}

export function clearSession() {
  localStorage.removeItem(KEY);
}

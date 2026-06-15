import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "dermai.session";

// session = { token, uid, role, username, name }
export async function loadSession() {
  const raw = await AsyncStorage.getItem(KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export async function saveSession(s) {
  await AsyncStorage.setItem(KEY, JSON.stringify(s));
}

export async function clearSession() {
  await AsyncStorage.removeItem(KEY);
}

// Normalise an /auth response into our session shape.
export function sessionFromAuth(data) {
  return {
    token: data.token,
    uid: data.user.uid,
    role: data.user.role,
    username: data.user.username,
    name: data.user.name,
  };
}

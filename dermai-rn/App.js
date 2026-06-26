// Load gesture-handler only where its native module exists (custom dev build).
// In Expo Go that native module isn't bundled, and a hard `import` crashes the app
// with "RNGestureHandlerModule could not be found", so we require it defensively.
try { require("react-native-gesture-handler"); } catch (e) { /* Expo Go — not available */ }
import React, { useEffect, useState } from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import { KeyboardProvider } from "./src/kb";

import { loadSession, saveSession, clearSession } from "./src/session";
import { setToken, apiPost } from "./src/api";
import { registerForPush } from "./src/push";
import { colors } from "./src/theme";
import LoginScreen from "./src/screens/LoginScreen";
import PatientHome from "./src/screens/PatientHome";
import DoctorHome from "./src/screens/DoctorHome";
import AdminHome from "./src/screens/AdminHome";
import PendingScreen from "./src/screens/PendingScreen";

function Root() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const s = await loadSession();
      if (s) { setToken(s.token); registerPush(); }
      setSession(s);
      setLoading(false);
    })();
  }, []);

  // Register this device for phone push notifications (best-effort).
  const registerPush = async () => {
    const token = await registerForPush();
    if (token) { try { await apiPost("/notifications/register-token", { token }); } catch (_) {} }
  };

  const onLogin = async (s) => {
    setToken(s.token);
    await saveSession(s);
    setSession(s);
    registerPush();
  };

  const onLogout = async () => {
    try { await apiPost("/auth/logout", {}); } catch (_) {}
    await clearSession();
    setToken(null);
    setSession(null);
  };

  const onVerified = async () => {
    const s = { ...session, verified: true };
    await saveSession(s);
    setSession(s);
  };

  if (loading) {
    return (
      <View style={styles.center}><ActivityIndicator size="large" color={colors.patient} /></View>
    );
  }
  if (!session) return <LoginScreen onLogin={onLogin} />;
  if ((session.role === "doctor" || session.role === "admin") && session.verified === false) {
    return <PendingScreen session={session} onLogout={onLogout} onVerified={onVerified} />;
  }
  if (session.role === "doctor") return <DoctorHome session={session} onLogout={onLogout} />;
  if (session.role === "admin") return <AdminHome session={session} onLogout={onLogout} />;
  return <PatientHome session={session} onLogout={onLogout} />;
}

export default function App() {
  return (
    <KeyboardProvider>
      <Root />
    </KeyboardProvider>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: colors.bg },
});

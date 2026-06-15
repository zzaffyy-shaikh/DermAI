import React, { useState } from "react";
import {
  View, Text, TouchableOpacity, ActivityIndicator, StyleSheet, ScrollView,
} from "react-native";
import * as ImagePicker from "expo-image-picker";

import { apiGet } from "../api";
import { BASE_URL } from "../config";
import { colors } from "../theme";

export default function PendingScreen({ session, onLogout, onVerified }) {
  const isDoctor = session.role === "doctor";
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const uploadLicense = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { setStatus("Permission denied"); return; }
    const res = await ImagePicker.launchImageLibraryAsync({ quality: 0.7 });
    if (res.canceled) return;
    setBusy(true); setStatus(null);
    try {
      const uri = res.assets[0].uri;
      const name = uri.split("/").pop() || "license.jpg";
      let ext = (name.split(".").pop() || "jpg").toLowerCase();
      if (ext === "jpg") ext = "jpeg";
      const fd = new FormData();
      fd.append("file", { uri, name, type: `image/${ext}` });
      const r = await fetch(`${BASE_URL}/auth/license`, {
        method: "POST",
        headers: { Authorization: "Bearer " + session.token },
        body: fd,
      });
      if (!r.ok) throw new Error("upload failed");
      setStatus("✓ License uploaded — management can review it.");
    } catch (e) {
      setStatus("Error: " + (e.message || e));
    } finally { setBusy(false); }
  };

  const checkStatus = async () => {
    setBusy(true); setStatus(null);
    try {
      const me = await apiGet("/auth/me");
      if (me.verified) onVerified();
      else setStatus("Still pending — please check back later.");
    } catch (e) {
      setStatus("Error: " + (e.message || e));
    } finally { setBusy(false); }
  };

  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <View style={styles.card}>
        <Text style={styles.brand}>DermAI</Text>
        <Text style={styles.title}>Account pending verification</Text>
        <Text style={styles.sub}>
          Your {isDoctor ? "doctor" : "management"} account is awaiting approval by a verified
          administrator. You'll get access once it's reviewed.
        </Text>

        {isDoctor && (
          <TouchableOpacity style={styles.outline} onPress={uploadLicense} disabled={busy}>
            <Text style={styles.outlineText}>📄 Upload license / PMDC registration</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity style={styles.btn} onPress={checkStatus} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>I've been approved — check status</Text>}
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.ghost]} onPress={onLogout}>
          <Text style={[styles.btnText, { color: colors.ink }]}>Logout</Text>
        </TouchableOpacity>

        {status && <Text style={styles.status}>{status}</Text>}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { flexGrow: 1, justifyContent: "center", padding: 20, backgroundColor: colors.bg },
  card: { backgroundColor: colors.card, borderRadius: 20, padding: 24, borderWidth: 1, borderColor: colors.line },
  brand: { fontSize: 26, fontWeight: "800", color: colors.patient, textAlign: "center" },
  title: { fontSize: 16, fontWeight: "700", textAlign: "center", marginTop: 12 },
  sub: { color: colors.muted, textAlign: "center", marginTop: 8, marginBottom: 8 },
  outline: { borderWidth: 1, borderColor: colors.line, borderRadius: 12, paddingVertical: 13, alignItems: "center", marginTop: 14 },
  outlineText: { fontWeight: "700", color: colors.ink },
  btn: { backgroundColor: colors.patient, borderRadius: 12, paddingVertical: 14, alignItems: "center", marginTop: 12 },
  ghost: { backgroundColor: "#fff", borderWidth: 1, borderColor: colors.line },
  btnText: { color: "#fff", fontWeight: "700" },
  status: { textAlign: "center", marginTop: 12, color: colors.muted },
});

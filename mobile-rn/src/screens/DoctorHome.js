import React, { useEffect, useState } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, ActivityIndicator, StyleSheet, RefreshControl, Alert,
} from "react-native";

import { apiGet, apiPost } from "../api";
import { colors } from "../theme";

export default function DoctorHome({ session, onLogout }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setCases(await apiGet("/consult/queue")); }
    catch (e) { setError(e.message || String(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const act = async (id, action) => {
    try { await apiPost(`/consult/${id}/${action}`, {}); load(); }
    catch (e) { Alert.alert("Error", e.message || String(e)); }
  };

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { backgroundColor: colors.doctor }]}>
        <Text style={styles.headerTitle}>Consultation Queue</Text>
        <View style={{ flexDirection: "row" }}>
          <TouchableOpacity onPress={load}><Text style={styles.headerBtn}>Refresh</Text></TouchableOpacity>
          <TouchableOpacity onPress={onLogout}><Text style={styles.headerBtn}>Logout</Text></TouchableOpacity>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}>
        {error && <Text style={styles.error}>{error}</Text>}
        {!loading && cases.length === 0 && <Text style={{ color: colors.muted }}>Queue is empty. Pull to refresh.</Text>}
        {cases.map((c) => {
          const b = c.brief || {};
          const conf = b.confidence != null ? ` · ${(b.confidence * 100).toFixed(0)}%` : "";
          return (
            <View key={c.id} style={styles.card}>
              <View style={{ flexDirection: "row", alignItems: "center" }}>
                <Text style={styles.disease}>{b.disease || "Unknown"}</Text>
                {b.urgent && (
                  <View style={styles.urgent}><Text style={styles.urgentText}>URGENT</Text></View>
                )}
              </View>
              <Text style={styles.meta}>patient {c.patient_id} · {c.mode} consult{conf}</Text>
              {c.note ? <Text style={{ marginTop: 4 }}>note: {c.note}</Text> : null}
              <View style={styles.actions}>
                <TouchableOpacity style={[styles.btn, { backgroundColor: colors.doctor }]} onPress={() => act(c.id, "accept")}>
                  <Text style={styles.btnText}>Accept</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={() => act(c.id, "close")}>
                  <Text style={[styles.btnText, { color: colors.ink }]}>Close</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: 48, paddingBottom: 14, paddingHorizontal: 18 },
  headerTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },
  headerBtn: { color: "#fff", fontWeight: "600", marginLeft: 16 },
  card: { backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.line, marginBottom: 14 },
  disease: { fontSize: 16, fontWeight: "700" },
  meta: { color: colors.muted, marginTop: 4, fontSize: 13 },
  urgent: { backgroundColor: colors.err, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2, marginLeft: 8 },
  urgentText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  actions: { flexDirection: "row", justifyContent: "flex-end", marginTop: 12 },
  btn: { borderRadius: 10, paddingVertical: 10, paddingHorizontal: 18, marginLeft: 8 },
  btnOutline: { borderWidth: 1, borderColor: colors.line },
  btnText: { color: "#fff", fontWeight: "700" },
  error: { color: colors.err, marginBottom: 10 },
});

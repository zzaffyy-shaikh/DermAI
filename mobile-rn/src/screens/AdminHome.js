import React, { useEffect, useState } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, ActivityIndicator, StyleSheet, RefreshControl, Alert,
} from "react-native";

import { apiGet, apiPost } from "../api";
import { colors } from "../theme";

export default function AdminHome({ session, onLogout }) {
  const [stats, setStats] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const s = await apiGet("/admin/stats");
      const d = await apiGet("/admin/doctors");
      setStats(s); setDoctors(d);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const verify = async (uid, approved) => {
    try { await apiPost("/admin/doctors/verify", { uid, approved }); load(); }
    catch (e) { Alert.alert("Error", e.message || String(e)); }
  };

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { backgroundColor: colors.admin }]}>
        <Text style={styles.headerTitle}>Administration</Text>
        <View style={{ flexDirection: "row" }}>
          <TouchableOpacity onPress={load}><Text style={styles.headerBtn}>Refresh</Text></TouchableOpacity>
          <TouchableOpacity onPress={onLogout}><Text style={styles.headerBtn}>Logout</Text></TouchableOpacity>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}>
        {error && <Text style={styles.error}>{error}</Text>}

        {stats && (
          <View style={styles.card}>
            <View style={styles.statsWrap}>
              {Object.entries(stats).map(([k, v]) => (
                <View key={k} style={styles.stat}>
                  <Text style={styles.statK}>{k.replace(/_/g, " ")}</Text>
                  <Text style={styles.statV}>{String(v)}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        <Text style={styles.section}>Doctors</Text>
        {!loading && doctors.length === 0 && <Text style={{ color: colors.muted }}>No doctor accounts yet.</Text>}
        {doctors.map((d) => (
          <View key={d.uid} style={styles.card}>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
              <View style={{ flex: 1 }}>
                <Text style={{ fontWeight: "700" }}>{d.name || d.username}</Text>
                <Text style={{ color: colors.muted, fontSize: 12 }}>@{d.username} · {d.specialization || "—"}</Text>
              </View>
              <View style={{ flexDirection: "row", alignItems: "center" }}>
                <View style={[styles.badge, { backgroundColor: d.verified ? colors.ok : colors.warn }]}>
                  <Text style={styles.badgeText}>{d.verified ? "verified" : "pending"}</Text>
                </View>
                {d.verified ? (
                  <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={() => verify(d.uid, false)}>
                    <Text style={[styles.btnText, { color: colors.ink }]}>Revoke</Text>
                  </TouchableOpacity>
                ) : (
                  <TouchableOpacity style={[styles.btn, { backgroundColor: colors.ok }]} onPress={() => verify(d.uid, true)}>
                    <Text style={styles.btnText}>Approve</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          </View>
        ))}
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
  statsWrap: { flexDirection: "row", flexWrap: "wrap" },
  stat: { width: "47%", backgroundColor: "#F8FAFC", borderRadius: 12, borderWidth: 1, borderColor: colors.line, padding: 12, margin: "1.5%" },
  statK: { fontSize: 11, color: colors.muted },
  statV: { fontSize: 19, fontWeight: "700", marginTop: 2 },
  section: { fontSize: 16, fontWeight: "700", marginVertical: 8 },
  badge: { paddingHorizontal: 9, paddingVertical: 3, borderRadius: 999, marginRight: 8 },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  btn: { borderRadius: 10, paddingVertical: 8, paddingHorizontal: 14 },
  btnOutline: { borderWidth: 1, borderColor: colors.line },
  btnText: { color: "#fff", fontWeight: "700" },
  error: { color: colors.err, marginBottom: 10 },
});

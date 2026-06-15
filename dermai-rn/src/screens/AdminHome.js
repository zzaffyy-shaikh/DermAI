import React, { useEffect, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, StyleSheet, RefreshControl, Alert, Modal,
} from "react-native";

import { apiGet, apiPost } from "../api";
import { colors, fmtDateTime } from "../theme";

export default function AdminHome({ session, onLogout }) {
  const [stats, setStats] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const s = await apiGet("/admin/stats");
      const d = await apiGet("/admin/doctors");
      const p = await apiGet("/admin/patients");
      setStats(s); setDoctors(d); setPatients(p);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const searchPatients = async () => {
    try { setPatients(await apiGet("/admin/patients" + (query ? `?q=${encodeURIComponent(query)}` : ""))); }
    catch (e) { Alert.alert("Error", e.message || String(e)); }
  };
  const openPatient = async (uid) => {
    try { setDetail(await apiGet(`/admin/patients/${uid}`)); }
    catch (e) { Alert.alert("Error", e.message || String(e)); }
  };

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

        <Text style={styles.section}>Patients</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <TextInput style={[styles.input, { flex: 1 }]} value={query} onChangeText={setQuery}
              placeholder="Search by ID, username, name…" onSubmitEditing={searchPatients} />
            <TouchableOpacity style={[styles.btn, { backgroundColor: colors.admin, marginLeft: 8 }]} onPress={searchPatients}>
              <Text style={styles.btnText}>Search</Text>
            </TouchableOpacity>
          </View>
          {patients.length === 0 && <Text style={{ color: colors.muted, marginTop: 10 }}>No matching patients.</Text>}
          {patients.map((p) => (
            <TouchableOpacity key={p.uid} style={styles.patRow} onPress={() => openPatient(p.uid)}>
              <View style={{ flex: 1 }}>
                <Text style={{ fontWeight: "700" }}>{p.name || p.username}</Text>
                <Text style={{ color: colors.muted, fontSize: 12 }}>@{p.username} · {p.screenings} screening(s) · {p.consultations} consult(s)</Text>
              </View>
              <Text style={{ color: colors.admin, fontWeight: "600" }}>View</Text>
            </TouchableOpacity>
          ))}
        </View>

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

      <Modal visible={!!detail} animationType="slide" onRequestClose={() => setDetail(null)}>
        <View style={{ flex: 1, backgroundColor: colors.bg }}>
          <View style={[styles.header, { backgroundColor: colors.admin }]}>
            <Text style={styles.headerTitle}>Patient record</Text>
            <TouchableOpacity onPress={() => setDetail(null)}><Text style={styles.headerBtn}>Close</Text></TouchableOpacity>
          </View>
          {detail && (
            <ScrollView contentContainerStyle={{ padding: 16 }}>
              <View style={styles.card}>
                <Text style={{ fontWeight: "700", fontSize: 16 }}>{detail.name || detail.username}</Text>
                <Text style={{ color: colors.muted }}>@{detail.username} · {detail.email || "no email"}</Text>
                <Text style={{ color: colors.muted, marginTop: 2 }}>ID {detail.uid}</Text>
                <Text style={{ color: colors.muted }}>{detail.age != null ? `${detail.age}y · ` : ""}{detail.gender || "—"}</Text>
              </View>

              <Text style={styles.section}>Medical history</Text>
              <View style={styles.card}>
                {Object.entries(detail.medical_history || {}).filter(([, v]) => v != null && v !== "").length === 0
                  ? <Text style={{ color: colors.muted }}>No medical history on file.</Text>
                  : Object.entries(detail.medical_history).filter(([, v]) => v != null && v !== "").map(([k, v]) => (
                      <Text key={k} style={{ color: colors.muted, fontSize: 13 }}>{k.replace(/_/g, " ")}: {String(v)}</Text>
                    ))}
              </View>

              <Text style={styles.section}>Screenings &amp; outcomes</Text>
              {detail.screenings.length === 0 && <Text style={{ color: colors.muted }}>No screenings.</Text>}
              {detail.screenings.map((s, i) => (
                <View key={i} style={styles.card}>
                  <Text style={{ fontWeight: "700" }}>{s.disease || "—"} <Text style={{ color: colors.muted, fontWeight: "400" }}>{s.mode || ""}{s.urgent ? " · URGENT" : ""}</Text></Text>
                  {s.outcome ? <Text style={{ color: colors.muted, marginTop: 4 }}>outcome: {s.outcome}</Text>
                    : <Text style={{ color: colors.muted, marginTop: 4 }}>{s.done ? "completed" : "in progress"}</Text>}
                  {s.recommendation ? <Text style={{ color: colors.muted, marginTop: 2 }}>recommendation: {s.recommendation}</Text> : null}
                </View>
              ))}

              <Text style={styles.section}>Consultations</Text>
              {detail.consultations.length === 0 && <Text style={{ color: colors.muted }}>No consultations.</Text>}
              {detail.consultations.map((c) => (
                <View key={c.id} style={styles.card}>
                  <Text style={{ fontWeight: "700" }}>{c.doctor_name || "—"} <Text style={{ color: colors.muted, fontWeight: "400" }}>· {c.status}</Text></Text>
                  <Text style={{ color: colors.muted, marginTop: 2 }}>{fmtDateTime(c.appointment_time)}</Text>
                  {c.disease ? <Text style={{ color: colors.muted, marginTop: 2 }}>problem: {c.disease}</Text> : null}
                  {c.solution ? <Text style={{ marginTop: 4 }}>💬 {c.solution}</Text> : null}
                </View>
              ))}
            </ScrollView>
          )}
        </View>
      </Modal>
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
  row: { flexDirection: "row", alignItems: "center" },
  input: { borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "#fff" },
  patRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.line, marginTop: 4 },
});

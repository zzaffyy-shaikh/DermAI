import React, { useEffect, useState, useMemo } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator,
  StyleSheet, RefreshControl, Alert, Modal, Linking, Image,
} from "react-native";

import { apiGet, apiPost, apiPut, apiDelete, getToken } from "../api";
import { BASE_URL } from "../config";
import { colors, fmtDateTime } from "../theme";
import CallScreen from "./CallScreen";
import MedicalHistoryScreen from "./MedicalHistoryScreen";
import NotifBell from "./NotifBell";

const TIMES = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"];
const pad = (n) => String(n).padStart(2, "0");
const dateStr = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const dayLabel = (d) => d.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" });

export default function DoctorHome({ session, onLogout }) {
  const [slots, setSlots] = useState([]);
  const [requests, setRequests] = useState([]);
  const [mine, setMine] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notDerm, setNotDerm] = useState(null);
  const [callRoom, setCallRoom] = useState(null);
  const [historyUid, setHistoryUid] = useState(null);
  const [solutions, setSolutions] = useState({});

  // new-slot picker (tap a day + a time)
  const days = useMemo(() => Array.from({ length: 14 }, (_, i) => {
    const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() + i); return d;
  }), []);
  const [selDay, setSelDay] = useState(null);   // Date
  const [selTime, setSelTime] = useState(null); // "HH:MM"

  const load = async () => {
    setLoading(true); setNotDerm(null);
    try {
      const [s, r, m] = await Promise.all([
        apiGet("/consult/availability"),
        apiGet("/consult/requests"),
        apiGet("/consult/mine"),
      ]);
      setSlots(s);
      setRequests(r);
      setMine(m.filter((c) => c.status !== "pending" && c.status !== "declined"));
    } catch (e) {
      setNotDerm(e.message || String(e));
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const addSlot = async () => {
    if (!selDay) { Alert.alert("Add slot", "Tap a day first."); return; }
    const m = (selTime || "").trim().match(/^(\d{1,2}):(\d{2})$/);
    if (!m || +m[1] > 23 || +m[2] > 59) {
      Alert.alert("Add slot", "Enter a valid time like 09:30, 13:45 or 18:05.");
      return;
    }
    const time = `${String(+m[1]).padStart(2, "0")}:${m[2]}`;
    try {
      await apiPost("/consult/availability", { slots: [`${dateStr(selDay)}T${time}:00`] });
      setSelTime(null); load();
    } catch (e) { Alert.alert("Error", e.message || String(e)); }
  };
  const removeSlot = async (id) => {
    try { await apiDelete(`/consult/availability/${id}`); load(); }
    catch (e) { Alert.alert("Error", e.message || String(e)); }
  };
  const act = async (id, action) => {
    try { await apiPost(`/consult/${id}/${action}`, {}); load(); }
    catch (e) { Alert.alert("Error", e.message || String(e)); }
  };
  const saveSolution = async (id) => {
    try { await apiPost(`/consult/${id}/solution`, { solution: solutions[id] || "" }); Alert.alert("Saved", "Solution saved."); load(); }
    catch (e) { Alert.alert("Error", e.message || String(e)); }
  };

  const CaseMeta = ({ c }) => {
    const b = c.brief || {};
    const conf = b.confidence != null ? ` · ${(b.confidence * 100).toFixed(0)}%` : "";
    return (
      <View style={{ flexDirection: "row" }}>
        <Image
          source={{ uri: `${BASE_URL}/image/${c.session_id}?token=${getToken()}` }}
          style={styles.thumb}
        />
        <View style={{ flex: 1 }}>
          <View style={{ flexDirection: "row", alignItems: "center" }}>
            <Text style={styles.disease}>{b.disease || "Unknown"}</Text>
            {b.urgent && <View style={styles.urgent}><Text style={styles.urgentText}>URGENT</Text></View>}
          </View>
          <Text style={styles.meta}>{c.patient_name || c.patient_id} · 🕒 {fmtDateTime(c.appointment_time)}{conf}</Text>
          {c.note ? <Text style={{ marginTop: 4 }}>note: {c.note}</Text> : null}
        </View>
      </View>
    );
  };

  const ContextBtns = ({ c }) => (
    <>
      <TouchableOpacity style={[styles.btn, { backgroundColor: colors.admin }]}
        onPress={() => Linking.openURL(`${BASE_URL}/report/${c.session_id}?token=${getToken()}`)}>
        <Text style={styles.btnText}>📄 Report</Text>
      </TouchableOpacity>
      <TouchableOpacity style={[styles.btn, { backgroundColor: colors.warn }]} onPress={() => setHistoryUid(c.patient_id)}>
        <Text style={styles.btnText}>🩺 History</Text>
      </TouchableOpacity>
    </>
  );

  return (
    <View style={styles.screen}>
      <View style={[styles.header, { backgroundColor: colors.doctor }]}>
        <Text style={styles.headerTitle}>Doctor Console</Text>
        <View style={{ flexDirection: "row", alignItems: "center" }}>
          <NotifBell />
          <TouchableOpacity onPress={load}><Text style={styles.headerBtn}>Refresh</Text></TouchableOpacity>
          <TouchableOpacity onPress={onLogout}><Text style={styles.headerBtn}>Logout</Text></TouchableOpacity>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}>

        {notDerm && (
          <View style={[styles.card, { borderColor: colors.warn }]}>
            <Text style={{ color: colors.muted }}>{notDerm}</Text>
          </View>
        )}

        {/* availability */}
        <Text style={styles.section}>📅 My availability</Text>
        <View style={styles.card}>
          <Text style={styles.pickLabel}>Day</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {days.map((d) => {
              const active = selDay && dateStr(selDay) === dateStr(d);
              return (
                <TouchableOpacity key={dateStr(d)} style={[styles.chip, active && styles.chipActive]}
                  onPress={() => setSelDay(d)}>
                  <Text style={[styles.chipText, active && { color: "#fff" }]}>{dayLabel(d)}</Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
          <Text style={styles.pickLabel}>Time — type any (24-hour, e.g. 13:45) or tap a quick time</Text>
          <TextInput style={styles.input} value={selTime || ""} onChangeText={setSelTime}
            placeholder="HH:MM  (e.g. 13:45)" maxLength={5} />
          <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 8 }}>
            {TIMES.map((t) => {
              const active = selTime === t;
              return (
                <TouchableOpacity key={t} style={[styles.chip, active && styles.chipActive]}
                  onPress={() => setSelTime(t)}>
                  <Text style={[styles.chipText, active && { color: "#fff" }]}>{t}</Text>
                </TouchableOpacity>
              );
            })}
          </View>
          <TouchableOpacity style={[styles.btn, { backgroundColor: colors.doctor, alignSelf: "flex-start", marginTop: 12 }]} onPress={addSlot}>
            <Text style={styles.btnText}>+ Add {selDay && selTime ? `${dayLabel(selDay)} ${selTime}` : "slot"}</Text>
          </TouchableOpacity>
          {slots.length === 0 && <Text style={{ color: colors.muted, marginTop: 10 }}>No slots yet.</Text>}
          {slots.map((s) => (
            <View key={s.id} style={styles.slotRow}>
              <Text>{fmtDateTime(s.start)} <Text style={{ color: colors.muted }}>· {s.status}</Text></Text>
              {s.status === "open" && (
                <TouchableOpacity onPress={() => removeSlot(s.id)}><Text style={{ color: colors.err }}>Remove</Text></TouchableOpacity>
              )}
            </View>
          ))}
        </View>

        {/* incoming requests */}
        <Text style={styles.section}>🔔 Incoming requests</Text>
        {requests.length === 0 && <Text style={{ color: colors.muted, marginBottom: 12 }}>No pending requests.</Text>}
        {requests.map((c) => (
          <View key={c.id} style={styles.card}>
            <CaseMeta c={c} />
            <View style={styles.actions}>
              <ContextBtns c={c} />
              <TouchableOpacity style={[styles.btn, { backgroundColor: colors.ok }]} onPress={() => act(c.id, "confirm")}>
                <Text style={styles.btnText}>✓ Confirm</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, { backgroundColor: colors.err }]} onPress={() => act(c.id, "decline")}>
                <Text style={styles.btnText}>Decline</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))}

        {/* my appointments */}
        <Text style={styles.section}>🩺 My appointments</Text>
        {mine.length === 0 && <Text style={{ color: colors.muted }}>No confirmed appointments yet.</Text>}
        {mine.map((c) => (
          <View key={c.id} style={styles.card}>
            <CaseMeta c={c} />
            <View style={styles.actions}>
              {c.room && (
                <TouchableOpacity style={[styles.btn, { backgroundColor: colors.ok }]} onPress={() => setCallRoom(c.room)}>
                  <Text style={styles.btnText}>🎥 Join</Text>
                </TouchableOpacity>
              )}
              <ContextBtns c={c} />
              <TouchableOpacity style={[styles.btn, styles.btnOutline]} onPress={() => act(c.id, "close")}>
                <Text style={[styles.btnText, { color: colors.ink }]}>Close</Text>
              </TouchableOpacity>
            </View>
            <TextInput style={[styles.input, { marginTop: 10 }]} multiline
              defaultValue={c.solution || ""}
              onChangeText={(t) => setSolutions((s) => ({ ...s, [c.id]: t }))}
              placeholder="Solution / advice for the patient" />
            <TouchableOpacity style={[styles.btn, { backgroundColor: colors.doctor, alignSelf: "flex-start", marginTop: 8 }]}
              onPress={() => saveSolution(c.id)}>
              <Text style={styles.btnText}>Save solution</Text>
            </TouchableOpacity>
          </View>
        ))}
      </ScrollView>

      <Modal visible={!!callRoom} animationType="slide" onRequestClose={() => setCallRoom(null)}>
        {callRoom && <CallScreen room={callRoom} name={session?.name || session?.username} onClose={() => setCallRoom(null)} />}
      </Modal>

      <Modal visible={!!historyUid} animationType="slide" onRequestClose={() => setHistoryUid(null)}>
        <View style={{ flex: 1, backgroundColor: colors.bg }}>
          <View style={[styles.header, { backgroundColor: colors.doctor }]}>
            <Text style={styles.headerTitle}>Patient Medical History</Text>
            <TouchableOpacity onPress={() => setHistoryUid(null)}><Text style={styles.headerBtn}>Close</Text></TouchableOpacity>
          </View>
          {historyUid && <MedicalHistoryScreen uid={historyUid} />}
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
  section: { fontSize: 15, fontWeight: "700", marginBottom: 8, marginTop: 4, color: colors.ink },
  card: { backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.line, marginBottom: 14 },
  thumb: { width: 70, height: 70, borderRadius: 10, marginRight: 12, backgroundColor: "#e6ebf3" },
  disease: { fontSize: 16, fontWeight: "700" },
  meta: { color: colors.muted, marginTop: 4, fontSize: 13 },
  urgent: { backgroundColor: colors.err, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2, marginLeft: 8 },
  urgentText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  actions: { flexDirection: "row", flexWrap: "wrap", justifyContent: "flex-end", marginTop: 12 },
  btn: { borderRadius: 10, paddingVertical: 10, paddingHorizontal: 16, marginLeft: 8, marginTop: 8 },
  btnOutline: { borderWidth: 1, borderColor: colors.line },
  btnText: { color: "#fff", fontWeight: "700" },
  row: { flexDirection: "row", alignItems: "center" },
  input: { borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "#fff" },
  slotRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.line, marginTop: 8 },
  pickLabel: { fontSize: 12, fontWeight: "700", color: colors.muted, marginTop: 10, marginBottom: 6 },
  chip: { borderWidth: 1, borderColor: colors.line, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8, marginRight: 8, marginBottom: 8 },
  chipActive: { backgroundColor: colors.doctor, borderColor: colors.doctor },
  chipText: { color: colors.ink, fontSize: 13 },
  error: { color: colors.err, marginBottom: 10 },
});

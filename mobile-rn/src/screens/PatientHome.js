import React, { useState, useEffect } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, Image,
  ActivityIndicator, StyleSheet, RefreshControl,
} from "react-native";
import * as ImagePicker from "expo-image-picker";

import { apiGet, apiPost, apiUpload } from "../api";
import { colors, modeColor } from "../theme";

const REGIONS = ["face", "scalp", "neck", "chest", "back", "arm", "forearm", "hand", "abdomen", "leg", "foot"];

export default function PatientHome({ session, onLogout }) {
  const [tab, setTab] = useState("diagnose");
  return (
    <View style={styles.screen}>
      <Header title="DermAI" color={colors.patient} onLogout={onLogout} />
      <View style={{ flex: 1 }}>
        {tab === "diagnose" ? <DiagnoseTab /> : <HistoryTab />}
      </View>
      <View style={styles.tabbar}>
        <TabButton label="Diagnose" active={tab === "diagnose"} onPress={() => setTab("diagnose")} />
        <TabButton label="History" active={tab === "history"} onPress={() => setTab("history")} />
      </View>
    </View>
  );
}

function Header({ title, color, onLogout }) {
  return (
    <View style={[styles.header, { backgroundColor: color }]}>
      <Text style={styles.headerTitle}>{title}</Text>
      <TouchableOpacity onPress={onLogout}><Text style={styles.logout}>Logout</Text></TouchableOpacity>
    </View>
  );
}

function TabButton({ label, active, onPress }) {
  return (
    <TouchableOpacity style={styles.tabBtn} onPress={onPress}>
      <Text style={[styles.tabText, active && { color: colors.patient, fontWeight: "700" }]}>{label}</Text>
    </TouchableOpacity>
  );
}

/* ---------------- Diagnose ---------------- */
function DiagnoseTab() {
  const [imageUri, setImageUri] = useState(null);
  const [region, setRegion] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const [brief, setBrief] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [awaiting, setAwaiting] = useState(false);
  const [done, setDone] = useState(false);
  const [answer, setAnswer] = useState("");
  const [note, setNote] = useState("");
  const [consultMsg, setConsultMsg] = useState(null);

  const pick = async (fromCamera) => {
    const perm = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { setError("Permission denied"); return; }
    // (images are the default media type, so we don't pass mediaTypes — avoids
    //  API differences between expo-image-picker versions)
    const res = fromCamera
      ? await ImagePicker.launchCameraAsync({ quality: 0.7 })
      : await ImagePicker.launchImageLibraryAsync({ quality: 0.7 });
    if (!res.canceled) setImageUri(res.assets[0].uri);
  };

  const diagnose = async () => {
    if (!imageUri) { setError("Please choose an image first."); return; }
    setBusy(true); setError(null); setBrief(null); setMessages([]); setDone(false); setConsultMsg(null);
    try {
      const fields = {};
      if (region) fields.body_region = region;
      const data = await apiUpload("/diagnose", imageUri, fields);
      setSessionId(data.session_id);
      setBrief(data.brief);
      setMessages([{ role: "assistant", text: data.message }]);
      setAwaiting(data.awaiting_answer === true);
      setDone(data.awaiting_answer !== true);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const send = async () => {
    const text = answer.trim();
    if (!text || !sessionId) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setAnswer(""); setAwaiting(false);
    try {
      const turn = await apiPost("/chat/answer", { session_id: sessionId, answer: text });
      setMessages((m) => [...m, { role: "assistant", text: turn.message }]);
      setDone(turn.done === true);
      setAwaiting(turn.done !== true);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "⚠️ " + (e.message || e) }]);
      setAwaiting(true);
    }
  };

  const requestConsult = async () => {
    try {
      const c = await apiPost("/consult/request", {
        session_id: sessionId, mode: "video", note: note.trim() || null,
      });
      setConsultMsg(`✅ Video consultation requested (case ${c.id}).`);
    } catch (e) {
      setConsultMsg("Error: " + (e.message || e));
    }
  };

  return (
    <ScrollView contentContainerStyle={{ padding: 16 }}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Skin screening</Text>
        {imageUri && <Image source={{ uri: imageUri }} style={styles.preview} />}
        <View style={styles.row}>
          <TouchableOpacity style={styles.outlineBtn} onPress={() => pick(true)}>
            <Text style={styles.outlineText}>📷 Camera</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.outlineBtn} onPress={() => pick(false)}>
            <Text style={styles.outlineText}>🖼️ Gallery</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.label}>Affected body region (optional)</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginVertical: 6 }}>
          {REGIONS.map((r) => (
            <TouchableOpacity key={r}
              style={[styles.chip, region === r && styles.chipActive]}
              onPress={() => setRegion(region === r ? null : r)}>
              <Text style={[styles.chipText, region === r && { color: "#fff" }]}>{r}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <TouchableOpacity style={styles.primaryBtn} onPress={diagnose} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryText}>Diagnose</Text>}
        </TouchableOpacity>
        {error && <Text style={styles.error}>{error}</Text>}
      </View>

      {brief && <BriefCard brief={brief} />}

      {messages.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Follow-up questions</Text>
          {messages.map((m, i) => (
            <View key={i} style={[styles.bubbleRow, { justifyContent: m.role === "user" ? "flex-end" : "flex-start" }]}>
              <View style={[styles.bubble, m.role === "user" ? styles.bubbleUser : styles.bubbleBot]}>
                <Text style={{ color: m.role === "user" ? "#fff" : colors.ink }}>{m.text}</Text>
              </View>
            </View>
          ))}
          {done ? (
            <Text style={styles.doneText}>✓ Screening complete</Text>
          ) : (
            <View style={styles.row}>
              <TextInput style={[styles.input, { flex: 1 }]} value={answer} onChangeText={setAnswer}
                placeholder="Type your answer..." editable={awaiting} onSubmitEditing={send} />
              <TouchableOpacity style={[styles.primaryBtn, { paddingHorizontal: 18, marginLeft: 8 }]}
                onPress={send} disabled={!awaiting}>
                <Text style={styles.primaryText}>Send</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}

      {done && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Consult a doctor 🎥</Text>
          <Text style={{ color: colors.muted, marginBottom: 8 }}>Consultations are conducted over video.</Text>
          <TextInput style={styles.input} value={note} onChangeText={setNote} placeholder="Note (optional)" />
          <TouchableOpacity style={[styles.primaryBtn, { backgroundColor: colors.doctor, marginTop: 10 }]}
            onPress={requestConsult}>
            <Text style={styles.primaryText}>Request video consultation</Text>
          </TouchableOpacity>
          {consultMsg && <Text style={{ marginTop: 10 }}>{consultMsg}</Text>}
        </View>
      )}
    </ScrollView>
  );
}

function BriefCard({ brief }) {
  const conf = (brief.confidence * 100).toFixed(1);
  return (
    <View style={styles.card}>
      <View style={[styles.row, { alignItems: "center" }]}>
        <Text style={styles.cardTitle}>Result</Text>
        <Badge text={brief.mode} color={modeColor(brief.mode)} />
        {brief.urgent && <Badge text="URGENT" color={colors.err} />}
      </View>
      <KV k="Disease" v={String(brief.disease)} />
      <KV k="Confidence" v={`${conf}%`} />
      <KV k="Region" v={brief.body_region || "—"} />
      <KV k="Severity" v={brief.severity || "—"} />
      <KV k="Image quality" v={brief.image_quality} />
    </View>
  );
}

/* ---------------- History ---------------- */
function HistoryTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setItems(await apiGet("/history")); }
    catch (e) { setError(e.message || String(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  return (
    <ScrollView contentContainerStyle={{ padding: 16 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}>
      {error && <Text style={styles.error}>{error}</Text>}
      {!loading && items.length === 0 && <Text style={{ color: colors.muted }}>No screenings yet.</Text>}
      {items.map((s) => (
        <View key={s.session_id} style={styles.card}>
          <View style={[styles.row, { alignItems: "center" }]}>
            <Text style={{ fontWeight: "700", fontSize: 15 }}>{s.disease}</Text>
            <Badge text={s.mode} color={modeColor(s.mode)} />
            {s.urgent && <Badge text="URGENT" color={colors.err} />}
          </View>
          <Text style={{ color: colors.muted, marginTop: 4 }}>
            confidence {(s.confidence * 100).toFixed(1)}% · {s.done ? "completed" : "in progress"}
          </Text>
        </View>
      ))}
    </ScrollView>
  );
}

function Badge({ text, color }) {
  return (
    <View style={[styles.badge, { backgroundColor: color }]}>
      <Text style={styles.badgeText}>{text}</Text>
    </View>
  );
}
function KV({ k, v }) {
  return (
    <View style={{ flexDirection: "row", paddingVertical: 3 }}>
      <Text style={{ width: 120, color: colors.muted }}>{k}</Text>
      <Text style={{ flex: 1, fontWeight: "600" }}>{v}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: 48, paddingBottom: 14, paddingHorizontal: 18 },
  headerTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },
  logout: { color: "#fff", fontWeight: "600" },
  tabbar: { flexDirection: "row", borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: "#fff" },
  tabBtn: { flex: 1, paddingVertical: 14, alignItems: "center" },
  tabText: { color: colors.muted },
  card: { backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.line, marginBottom: 16 },
  cardTitle: { fontSize: 16, fontWeight: "700", marginRight: 8 },
  preview: { width: "100%", height: 180, borderRadius: 12, marginVertical: 10 },
  row: { flexDirection: "row", alignItems: "center" },
  outlineBtn: { flex: 1, borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingVertical: 11, alignItems: "center", marginHorizontal: 4 },
  outlineText: { fontWeight: "600", color: colors.ink },
  label: { fontSize: 12, fontWeight: "600", color: colors.muted, marginTop: 10 },
  chip: { borderWidth: 1, borderColor: colors.line, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 7, marginRight: 8 },
  chipActive: { backgroundColor: colors.patient, borderColor: colors.patient },
  chipText: { color: colors.ink },
  primaryBtn: { backgroundColor: colors.patient, borderRadius: 10, paddingVertical: 13, alignItems: "center", marginTop: 12 },
  primaryText: { color: "#fff", fontWeight: "700" },
  input: { borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "#fff" },
  error: { color: colors.err, marginTop: 10 },
  badge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 999, marginLeft: 6 },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  bubbleRow: { flexDirection: "row", marginVertical: 4 },
  bubble: { paddingHorizontal: 12, paddingVertical: 9, borderRadius: 14, maxWidth: "80%" },
  bubbleUser: { backgroundColor: colors.patient },
  bubbleBot: { backgroundColor: "#F1F5F9" },
  doneText: { color: colors.ok, fontWeight: "700", textAlign: "center", marginTop: 10 },
});

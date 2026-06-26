import React, { useState, useEffect, useRef } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, Image,
  ActivityIndicator, StyleSheet, RefreshControl, KeyboardAvoidingView, Platform, Modal, Keyboard, Linking, Alert,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { apiGet, apiPost, apiUpload, getToken } from "../api";
import { BASE_URL } from "../config";
import { colors, modeColor, fmtDateTime } from "../theme";
import { KeyboardAwareScrollView } from "../kb";
import CallScreen from "./CallScreen";
import MedicalHistoryScreen from "./MedicalHistoryScreen";
import NotifBell from "./NotifBell";

const REGIONS = ["face", "scalp", "neck", "chest", "back", "arm", "forearm", "hand", "abdomen", "leg", "foot"];

export default function PatientHome({ session, onLogout }) {
  const [tab, setTab] = useState("diagnose");
  return (
    <View style={styles.screen}>
      <Header title="DermAI" color={colors.patient} onLogout={onLogout} />
      <View style={{ flex: 1 }}>
        {tab === "diagnose" && <DiagnoseTab name={session.name || session.username} onNeedHistory={() => setTab("medical")} onBooked={() => setTab("appointments")} />}
        {tab === "medical" && <MedicalHistoryScreen />}
        {tab === "appointments" && <AppointmentsTab name={session.name || session.username} />}
        {tab === "history" && <HistoryTab />}
      </View>
      <View style={styles.tabbar}>
        <TabButton label="Diagnose" active={tab === "diagnose"} onPress={() => setTab("diagnose")} />
        <TabButton label="Medical" active={tab === "medical"} onPress={() => setTab("medical")} />
        <TabButton label="Appointments" active={tab === "appointments"} onPress={() => setTab("appointments")} />
        <TabButton label="Screenings" active={tab === "history"} onPress={() => setTab("history")} />
      </View>
    </View>
  );
}

function Header({ title, color, onLogout }) {
  return (
    <View style={[styles.header, { backgroundColor: color }]}>
      <Text style={styles.headerTitle}>{title}</Text>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <NotifBell />
        <TouchableOpacity onPress={onLogout}><Text style={styles.logout}>Logout</Text></TouchableOpacity>
      </View>
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
function DiagnoseTab({ name, onNeedHistory, onBooked }) {
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
  const [options, setOptions] = useState(null);
  const [showOnboard, setShowOnboard] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    AsyncStorage.getItem("dermai.onboarded").then((v) => { if (!v) setShowOnboard(true); }).catch(() => {});
  }, []);
  const dismissOnboard = () => {
    setShowOnboard(false);
    AsyncStorage.setItem("dermai.onboarded", "1").catch(() => {});
  };

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
    setBusy(true); setError(null); setBrief(null); setMessages([]); setDone(false);
    try {
      const fields = {};
      if (region) fields.body_region = region;
      const data = await apiUpload("/diagnose", imageUri, fields);
      setSessionId(data.session_id);
      setBrief(data.brief);
      setMessages([{ role: "assistant", text: data.message }]);
      setAwaiting(data.awaiting_answer === true);
      setDone(data.awaiting_answer !== true);
      setOptions(data.options || null);
    } catch (e) {
      const msg = e.message || String(e);
      if (/medical history/i.test(msg) && onNeedHistory) {
        setError("Please complete your Medical History first (opening it now).");
        onNeedHistory();
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  const send = async (forced) => {
    const text = forced != null ? forced : answer.trim();
    if (!text || !sessionId) return;
    setMessages((m) => [...m, { role: "user", text }]);
    if (forced == null) setAnswer("");
    setAwaiting(false);
    try {
      const turn = await apiPost("/chat/answer", { session_id: sessionId, answer: text });
      setMessages((m) => [...m, { role: "assistant", text: turn.message }]);
      if (turn.done === true) {
        setDone(true); setAwaiting(false); setOptions(null);
        try {
          const r = await apiGet(`/chat/${sessionId}/result`);   // refined diagnosis
          if (r && r.disease) setBrief((b) => ({ ...b, disease: r.disease, confidence: r.confidence, urgent: r.urgent, refined: true }));
        } catch { /* not refined */ }
      } else {
        setDone(false); setAwaiting(true); setOptions(turn.options || null);
      }
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 150);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "⚠️ " + (e.message || e) }]);
      setAwaiting(true);
    }
  };

  return (
    <View style={{ flex: 1 }}>
    <KeyboardAwareScrollView ref={scrollRef} contentContainerStyle={{ padding: 16, paddingBottom: 24 }} keyboardShouldPersistTaps="handled" bottomOffset={24}>
      {showOnboard && (
        <View style={styles.card}>
          <View style={[styles.row, { justifyContent: "space-between" }]}>
            <Text style={styles.cardTitle}>👋 How DermAI works</Text>
            <TouchableOpacity onPress={dismissOnboard}><Text style={{ color: colors.patient, fontWeight: "700" }}>Got it</Text></TouchableOpacity>
          </View>
          <Text style={{ color: colors.muted, marginTop: 8, lineHeight: 21 }}>
            1. Fill your medical history once.{"\n"}
            2. Upload a clear, well-lit photo of the affected skin.{"\n"}
            3. Answer a few quick follow-up questions.{"\n"}
            4. Get a preliminary result and a PDF report.{"\n"}
            5. Book a video consultation with a dermatologist.
          </Text>
        </View>
      )}
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

        <Text style={styles.photoTips}>📸 Best results: good lighting, hold steady & in focus, fill the frame with the affected area, and avoid shadows.</Text>

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
          ) : options && options.length ? (
            <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 6 }}>
              {options.map((o) => (
                <TouchableOpacity key={o} style={styles.optBtn} onPress={() => send(o)} disabled={!awaiting}>
                  <Text style={styles.optText}>{o}</Text>
                </TouchableOpacity>
              ))}
            </View>
          ) : (
            <View style={styles.row}>
              <TextInput style={[styles.input, { flex: 1 }]} value={answer} onChangeText={setAnswer}
                placeholder="Type your answer..." editable={awaiting} onSubmitEditing={() => send()}
                onFocus={() => setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 250)} />
              <TouchableOpacity style={[styles.primaryBtn, { paddingHorizontal: 18, marginLeft: 8 }]}
                onPress={() => send()} disabled={!awaiting}>
                <Text style={styles.primaryText}>Send</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}

      {done && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Diagnosis report</Text>
          <TouchableOpacity style={[styles.primaryBtn, { backgroundColor: colors.admin, marginTop: 10 }]}
            onPress={() => Linking.openURL(`${BASE_URL}/report/${sessionId}?token=${getToken()}`)}>
            <Text style={styles.primaryText}>📄 View diagnosis report (PDF)</Text>
          </TouchableOpacity>
        </View>
      )}

      {done && <BookConsult sessionId={sessionId} onBooked={onBooked} />}
    </KeyboardAwareScrollView>
    </View>
  );
}

/* ---------------- Book a dermatologist ---------------- */
function BookConsult({ sessionId, onBooked }) {
  const [docs, setDocs] = useState(null);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState(null);

  const load = async () => {
    try { setDocs(await apiGet("/consult/doctors")); }
    catch (e) { setMsg("Error: " + (e.message || e)); }
  };
  useEffect(() => { load(); }, []);

  const book = async (doctorId, slotId) => {
    setMsg(null);
    try {
      const c = await apiPost("/consult/request", {
        session_id: sessionId, doctor_id: doctorId, slot_id: slotId,
        mode: "video", note: note.trim() || null,
      });
      setMsg(`✅ Requested ${c.doctor_name} for ${fmtDateTime(c.appointment_time)}. You'll be notified when it's confirmed.`);
      load();
      onBooked && onBooked();
    } catch (e) { setMsg("Error: " + (e.message || e)); }
  };

  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>Book a dermatologist 🎥</Text>
      <Text style={{ color: colors.muted, marginVertical: 8 }}>
        Pick a dermatologist and an available time. The doctor receives your report and medical history.
      </Text>
      <TextInput style={styles.input} value={note} onChangeText={setNote} placeholder="Note for the doctor (optional)" />
      {docs === null && <ActivityIndicator color={colors.patient} style={{ marginTop: 12 }} />}
      {docs && docs.length === 0 && <Text style={{ color: colors.muted, marginTop: 12 }}>No dermatologists available right now.</Text>}
      {docs && docs.map((d) => (
        <View key={d.uid} style={{ marginTop: 12, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 10 }}>
          <Text style={{ fontWeight: "700" }}>{d.name} <Text style={{ color: colors.muted, fontWeight: "400" }}>· {d.specialization || "Dermatology"}</Text></Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 6 }}>
            {d.slots.length === 0 && <Text style={{ color: colors.muted }}>No open times.</Text>}
            {d.slots.map((s) => (
              <TouchableOpacity key={s.id} style={styles.slotBtn} onPress={() => book(d.uid, s.id)}>
                <Text style={{ color: "#fff", fontWeight: "600", fontSize: 12 }}>{fmtDateTime(s.start)}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      ))}
      {msg && <Text style={{ marginTop: 12 }}>{msg}</Text>}
    </View>
  );
}

/* ---------------- Appointments ---------------- */
const STATUS_LABEL = { pending: "Awaiting confirmation", confirmed: "Confirmed", declined: "Declined", cancelled: "Cancelled", closed: "Completed" };

function AppointmentsTab({ name }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [callRoom, setCallRoom] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setItems(await apiGet("/consult/my")); }
    catch (e) { setError(e.message || String(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const cancel = (id) => {
    Alert.alert("Cancel appointment", "The time slot will be released.", [
      { text: "Keep" },
      { text: "Cancel it", style: "destructive", onPress: async () => {
        try { await apiPost(`/consult/${id}/cancel`, {}); load(); }
        catch (e) { Alert.alert("Error", e.message || String(e)); }
      } },
    ]);
  };

  return (
    <View style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={{ padding: 16 }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}>
        {error && <Text style={styles.error}>{error}</Text>}
        {!loading && items.length === 0 && <Text style={{ color: colors.muted }}>No appointments yet. Book a dermatologist after a screening.</Text>}
        {items.map((c) => (
          <View key={c.id} style={styles.card}>
            <View style={[styles.row, { alignItems: "center" }]}>
              <Text style={{ fontWeight: "700", fontSize: 15, flex: 1 }}>{c.doctor_name || "Dermatologist"}</Text>
              <Badge text={STATUS_LABEL[c.status] || c.status}
                color={c.status === "confirmed" ? colors.ok : (c.status === "declined" || c.status === "cancelled") ? colors.err : colors.warn} />
            </View>
            <Text style={{ color: colors.muted, marginTop: 4 }}>🕒 {fmtDateTime(c.appointment_time)}{c.brief ? ` · ${c.brief.disease}` : ""}</Text>
            {c.solution ? <Text style={{ marginTop: 6 }}>💬 {c.solution}</Text> : null}
            <View style={{ flexDirection: "row", justifyContent: "flex-end", marginTop: 10 }}>
              <TouchableOpacity style={[styles.smBtn, { backgroundColor: colors.admin }]}
                onPress={() => Linking.openURL(`${BASE_URL}/report/${c.session_id}?token=${getToken()}`)}>
                <Text style={styles.smBtnText}>📄 Report</Text>
              </TouchableOpacity>
              {c.status === "confirmed" && c.room && (
                <TouchableOpacity style={[styles.smBtn, { backgroundColor: colors.ok }]} onPress={() => setCallRoom(c.room)}>
                  <Text style={styles.smBtnText}>🎥 Join</Text>
                </TouchableOpacity>
              )}
              {(c.status === "pending" || c.status === "confirmed") && (
                <TouchableOpacity style={[styles.smBtn, { backgroundColor: colors.err }]} onPress={() => cancel(c.id)}>
                  <Text style={styles.smBtnText}>Cancel</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        ))}
      </ScrollView>
      <Modal visible={!!callRoom} animationType="slide" onRequestClose={() => setCallRoom(null)}>
        {callRoom && <CallScreen room={callRoom} name={name} onClose={() => setCallRoom(null)} />}
      </Modal>
    </View>
  );
}

function confidenceBand(c) { return c >= 0.75 ? "High" : c >= 0.5 ? "Moderate" : "Low"; }

function plainResult(b) {
  if (b.mode === "healthy")
    return "Good news — no clear signs of a skin condition were found in this photo. "
      + "Please still answer the follow-up questions so nothing a picture can't show is missed.";
  if (b.mode === "ood")
    return "This photo wasn't clear enough to confidently identify a specific condition. "
      + "It's best to see a dermatologist for an in-person check.";
  return `This most closely resembles ${b.disease}.`
    + (b.urgent ? " A few features here deserve a prompt in-person check by a dermatologist." : "");
}

function BriefCard({ brief }) {
  const band = confidenceBand(brief.confidence);
  const healthy = brief.mode === "healthy";
  return (
    <View style={styles.card}>
      <View style={[styles.row, { alignItems: "center" }]}>
        <Text style={styles.cardTitle}>Result</Text>
        <Badge text={healthy ? "no condition" : brief.urgent ? "needs a doctor" : brief.mode}
          color={brief.urgent ? colors.err : modeColor(brief.mode)} />
      </View>
      {brief.refined ? <Text style={{ color: colors.doctor, fontWeight: "700", fontSize: 12.5, marginTop: 6 }}>✓ Updated using your answers</Text> : null}
      <Text style={styles.headline}>{plainResult(brief)}</Text>
      {healthy ? (
        <>
          <KV k="Result" v="No condition detected" />
          <KV k="Confidence" v={band} />
        </>
      ) : (
        <>
          <KV k="Most likely" v={String(brief.disease)} />
          <KV k="Likelihood" v={`${band} (${(brief.confidence * 100).toFixed(0)}%)`} />
          <KV k="Other possibility" v={brief.second_guess ? String(brief.second_guess.disease) : "—"} />
          <KV k="Affected area" v={brief.body_region || "—"} />
          <KV k="Severity" v={brief.severity || "—"} />
        </>
      )}
      <KV k="Photo quality" v={brief.image_quality} />
      {brief.image_quality === "blurry" ? (
        <Text style={styles.warnBox}>⚠️ This photo looks blurry, so the result may be less reliable. Retake it in good light, hold steady, and fill the frame with the affected area.</Text>
      ) : null}
      {brief.insights ? (
        <Text style={{ marginTop: 8, color: colors.muted }}>🔍 {brief.insights.summary}</Text>
      ) : null}
      <Text style={styles.disclaimer}>⚕️ Preliminary AI screening, not a medical diagnosis. Always confirm with a dermatologist.</Text>
    </View>
  );
}

/* ---------------- History ---------------- */
function HistoryTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [bookSid, setBookSid] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setItems(await apiGet("/history")); }
    catch (e) { setError(e.message || String(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  return (
    <View style={{ flex: 1 }}>
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
            <View style={{ flexDirection: "row", justifyContent: "flex-end", marginTop: 10 }}>
              <TouchableOpacity style={[styles.smBtn, { backgroundColor: colors.admin }]}
                onPress={() => Linking.openURL(`${BASE_URL}/report/${s.session_id}?token=${getToken()}`)}>
                <Text style={styles.smBtnText}>📄 Report</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.smBtn, { backgroundColor: colors.doctor }]}
                onPress={() => setBookSid(s.session_id)}>
                <Text style={styles.smBtnText}>🎥 Book</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </ScrollView>

      <Modal visible={!!bookSid} animationType="slide" onRequestClose={() => setBookSid(null)}>
        <View style={{ flex: 1, backgroundColor: colors.bg }}>
          <View style={[styles.header, { backgroundColor: colors.patient }]}>
            <Text style={styles.headerTitle}>Book a dermatologist</Text>
            <TouchableOpacity onPress={() => setBookSid(null)}><Text style={styles.logout}>Close</Text></TouchableOpacity>
          </View>
          <ScrollView contentContainerStyle={{ padding: 16 }}>
            {bookSid && <BookConsult sessionId={bookSid} onBooked={() => setBookSid(null)} />}
          </ScrollView>
        </View>
      </Modal>
    </View>
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
  photoTips: { marginTop: 10, fontSize: 12, color: colors.muted, backgroundColor: "#eff6ff", borderWidth: 1, borderColor: "#bfdbfe", borderRadius: 10, padding: 10, lineHeight: 17 },
  warnBox: { marginTop: 10, fontSize: 12.5, color: "#92400e", backgroundColor: "#fffbeb", borderWidth: 1, borderColor: "#fde68a", borderRadius: 10, padding: 10, lineHeight: 17 },
  optBtn: { backgroundColor: colors.doctor, borderRadius: 10, paddingVertical: 11, paddingHorizontal: 18, marginRight: 8, marginBottom: 8 },
  optText: { color: "#fff", fontWeight: "700" },
  headline: { backgroundColor: "#eef2ff", borderRadius: 10, padding: 11, color: colors.ink, lineHeight: 20, marginTop: 6, marginBottom: 4 },
  disclaimer: { marginTop: 10, fontSize: 12, color: colors.muted, backgroundColor: "#fff7ed", borderWidth: 1, borderColor: "#fed7aa", borderRadius: 10, padding: 9, lineHeight: 17 },
  slotBtn: { backgroundColor: colors.doctor, borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12, marginRight: 8, marginBottom: 8 },
  smBtn: { borderRadius: 10, paddingVertical: 9, paddingHorizontal: 14, marginLeft: 8 },
  smBtnText: { color: "#fff", fontWeight: "700", fontSize: 13 },
});

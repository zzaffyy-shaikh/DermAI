import React, { useEffect, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ActivityIndicator, StyleSheet,
} from "react-native";
import { KeyboardAwareScrollView } from "../kb";

import { apiGet, apiPut } from "../api";
import { colors } from "../theme";

// Dermatological history (Rook's / Fitzpatrick examination framework)
const FIELDS = [
  { k: "full_name", label: "Full name", type: "text" },
  { k: "age", label: "Age", type: "number" },
  { k: "sex", label: "Sex", type: "chips", options: ["Male", "Female", "Other"] },
  { k: "occupation", label: "Occupation", type: "text" },
  { k: "fitzpatrick_type", label: "Skin tone — how does your skin react to the sun?", type: "rows", options: [
      "I — very fair, always burns, never tans",
      "II — fair, usually burns, tans a little",
      "III — medium, sometimes burns, tans gradually",
      "IV — olive, rarely burns, tans easily",
      "V — brown, very rarely burns",
      "VI — dark / black, never burns",
  ] },
  { k: "previous_skin_conditions", label: "Any past skin problems?", type: "text", multiline: true },
  { k: "atopy_history", label: "Do you (or family) have eczema, asthma or hay fever?", type: "text", multiline: true },
  { k: "family_history", label: "Family history (skin disease)", type: "text", multiline: true },
  { k: "skin_cancer_history", label: "Skin cancer history (personal/family)", type: "text", multiline: true },
  { k: "sun_exposure", label: "Sun exposure", type: "chips", options: ["High", "Moderate", "Low"] },
  { k: "sunscreen_use", label: "Sunscreen use", type: "chips", options: ["Regular", "Sometimes", "Never"] },
  { k: "chronic_conditions", label: "Chronic conditions (diabetes, thyroid, autoimmune)", type: "text", multiline: true },
  { k: "current_medications", label: "Current medications", type: "text", multiline: true },
  { k: "allergies", label: "Allergies (drug / contact)", type: "text", multiline: true },
  { k: "smoking", label: "Smoking", type: "chips", options: ["never", "former", "current"] },
  { k: "alcohol", label: "Alcohol", type: "chips", options: ["none", "occasional", "regular"] },
  { k: "notes", label: "Other notes", type: "text", multiline: true },
];

const EMPTY = Object.fromEntries(FIELDS.map((f) => [f.k, ""]));

export default function MedicalHistoryScreen({ uid } = {}) {
  const path = uid ? `/profile/medical-history/${uid}` : "/profile/medical-history";
  const isDoctorView = !!uid;
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await apiGet(path);
        const incoming = Object.fromEntries(
          Object.entries(r.history || {}).map(([k, v]) => [k, v == null ? "" : String(v)]));
        setForm((f) => ({ ...f, ...incoming }));
        setCompleted(r.completed);
      } catch (e) {
        setStatus("Couldn't load: " + (e.message || e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true); setStatus(null);
    try {
      const payload = {};
      FIELDS.forEach((f) => {
        payload[f.k] = f.k === "age"
          ? (form.age ? Number(form.age) : null)
          : (form[f.k] || null);
      });
      await apiPut(path, payload);
      setCompleted(true);
      setStatus("✓ Saved");
    } catch (e) {
      setStatus("Error: " + (e.message || e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <View style={styles.center}><ActivityIndicator color={colors.patient} /></View>;

  return (
    <KeyboardAwareScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }} keyboardShouldPersistTaps="handled" bottomOffset={24}>
      <View style={styles.card}>
        <Text style={styles.title}>Medical History</Text>
        <Text style={styles.sub}>
          {isDoctorView
            ? "Patient's medical history — review and update."
            : "Complete once. Used in every screening and shared with the doctor."}
          {completed ? " (saved)" : isDoctorView ? "" : " Required before your first diagnosis."}
        </Text>

        {FIELDS.map((f) => (
          <View key={f.k}>
            <Text style={styles.label}>{f.label}</Text>
            {f.type === "rows" ? (
              <View>
                {f.options.map((o) => (
                  <TouchableOpacity key={o}
                    style={[styles.optRow, String(form[f.k]) === String(o) && styles.optRowActive]}
                    onPress={() => set(f.k, o)}>
                    <Text style={[styles.optRowText, String(form[f.k]) === String(o) && { color: "#fff" }]}>{o}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            ) : f.type === "chips" ? (
              <View style={styles.chips}>
                {f.options.map((o) => (
                  <TouchableOpacity key={o}
                    style={[styles.chip, String(form[f.k]) === String(o) && styles.chipActive]}
                    onPress={() => set(f.k, o)}>
                    <Text style={[styles.chipText, String(form[f.k]) === String(o) && { color: "#fff" }]}>{o}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            ) : (
              <TextInput
                style={[styles.input, f.multiline && { height: 64, textAlignVertical: "top" }]}
                value={form[f.k]}
                onChangeText={(t) => set(f.k, t)}
                multiline={!!f.multiline}
                keyboardType={f.type === "number" ? "number-pad" : "default"}
              />
            )}
          </View>
        ))}

        <TouchableOpacity style={styles.btn} onPress={save} disabled={saving}>
          {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Save medical history</Text>}
        </TouchableOpacity>
        {status && <Text style={styles.status}>{status}</Text>}
      </View>
    </KeyboardAwareScrollView>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  card: { backgroundColor: colors.card, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: colors.line },
  title: { fontSize: 18, fontWeight: "700" },
  sub: { color: colors.muted, fontSize: 12.5, marginTop: 4, marginBottom: 8 },
  label: { fontSize: 12, fontWeight: "600", color: colors.muted, marginTop: 12, marginBottom: 4 },
  input: { borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "#fff" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { borderWidth: 1, borderColor: colors.line, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8, marginBottom: 4 },
  chipActive: { backgroundColor: colors.patient, borderColor: colors.patient },
  chipText: { color: colors.ink },
  optRow: { borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11, marginBottom: 6, backgroundColor: "#fff" },
  optRowActive: { backgroundColor: colors.patient, borderColor: colors.patient },
  optRowText: { color: colors.ink, fontSize: 13 },
  btn: { backgroundColor: colors.patient, borderRadius: 10, paddingVertical: 13, alignItems: "center", marginTop: 18 },
  btnText: { color: "#fff", fontWeight: "700" },
  status: { textAlign: "center", marginTop: 10, color: colors.ok, fontWeight: "600" },
});

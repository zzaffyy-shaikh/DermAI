import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, StyleSheet,
} from "react-native";

import { apiPost } from "../api";
import { sessionFromAuth } from "../session";
import { colors } from "../theme";

export default function LoginScreen({ onLogin }) {
  const [signup, setSignup] = useState(false);
  const [role, setRole] = useState("patient");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [specialization, setSpecialization] = useState("");

  const submit = async () => {
    setBusy(true); setError(null);
    try {
      let data;
      if (signup) {
        const body = {
          username: username.trim(), password, role,
          name: name.trim() || null, email: email.trim() || null,
        };
        if (role === "patient") {
          body.age = age.trim() ? Number(age.trim()) : null;
          body.gender = gender || null;
        } else {
          body.specialization = specialization.trim() || null;
        }
        data = await apiPost("/auth/register", body);
      } else {
        data = await apiPost("/auth/login", { username: username.trim(), password });
      }
      await onLogin(sessionFromAuth(data));
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const Seg = ({ value, current, onPress, label }) => (
    <TouchableOpacity
      style={[styles.seg, current === value && styles.segActive]}
      onPress={() => onPress(value)}
    >
      <Text style={[styles.segText, current === value && styles.segTextActive]}>{label}</Text>
    </TouchableOpacity>
  );

  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <View style={styles.card}>
        <Text style={styles.brand}>DermAI</Text>
        <Text style={styles.sub}>AI-powered skin disease screening</Text>

        <View style={styles.segRow}>
          <Seg value={false} current={signup} onPress={setSignup} label="Sign in" />
          <Seg value={true} current={signup} onPress={setSignup} label="Create account" />
        </View>

        {signup && (
          <View style={styles.segRow}>
            <Seg value="patient" current={role} onPress={setRole} label="🧑 Patient" />
            <Seg value="doctor" current={role} onPress={setRole} label="👨‍⚕️ Doctor" />
          </View>
        )}

        <Text style={styles.label}>Username</Text>
        <TextInput style={styles.input} autoCapitalize="none" value={username} onChangeText={setUsername} />
        <Text style={styles.label}>Password</Text>
        <TextInput style={styles.input} secureTextEntry value={password} onChangeText={setPassword} />

        {signup && (
          <>
            <Text style={styles.label}>Full name</Text>
            <TextInput style={styles.input} value={name} onChangeText={setName} />
            <Text style={styles.label}>Email</Text>
            <TextInput style={styles.input} autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} />
            {role === "patient" ? (
              <>
                <Text style={styles.label}>Age</Text>
                <TextInput style={styles.input} keyboardType="number-pad" value={age} onChangeText={setAge} />
                <Text style={styles.label}>Gender</Text>
                <View style={styles.segRow}>
                  {["Male", "Female", "Other"].map((g) => (
                    <Seg key={g} value={g} current={gender} onPress={setGender} label={g} />
                  ))}
                </View>
              </>
            ) : (
              <>
                <Text style={styles.label}>Specialization</Text>
                <TextInput style={styles.input} value={specialization} onChangeText={setSpecialization} />
                <Text style={styles.note}>Doctor accounts require admin verification.</Text>
              </>
            )}
          </>
        )}

        {error && <Text style={styles.error}>{error}</Text>}

        <TouchableOpacity style={styles.button} onPress={submit} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" />
                : <Text style={styles.buttonText}>{signup ? "Create account" : "Sign in"}</Text>}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { flexGrow: 1, justifyContent: "center", padding: 20, backgroundColor: colors.bg },
  card: { backgroundColor: colors.card, borderRadius: 20, padding: 22, borderWidth: 1, borderColor: colors.line },
  brand: { fontSize: 28, fontWeight: "800", color: colors.patient, textAlign: "center" },
  sub: { color: colors.muted, textAlign: "center", marginTop: 2, marginBottom: 16 },
  segRow: { flexDirection: "row", backgroundColor: "#F1F5F9", borderRadius: 12, padding: 4, marginBottom: 10 },
  seg: { flex: 1, paddingVertical: 9, borderRadius: 9, alignItems: "center" },
  segActive: { backgroundColor: "#fff" },
  segText: { color: colors.muted, fontWeight: "600", fontSize: 12 },
  segTextActive: { color: colors.ink },
  label: { fontSize: 12, fontWeight: "600", color: colors.muted, marginTop: 10, marginBottom: 4 },
  input: { borderWidth: 1, borderColor: colors.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "#fff" },
  note: { fontSize: 12, color: colors.muted, marginTop: 8 },
  error: { color: colors.err, marginTop: 12 },
  button: { backgroundColor: colors.patient, borderRadius: 12, paddingVertical: 14, alignItems: "center", marginTop: 18 },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});

import React, { useEffect } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, PermissionsAndroid, Platform, Linking,
} from "react-native";
import { WebView } from "react-native-webview";

import { VIDEO_BASE } from "../config";
import { colors } from "../theme";

// In-app video consultation: embeds the Jitsi room in a WebView so the call
// renders inside DermAI (no browser/app switch).
export default function CallScreen({ room, name, onClose }) {
  // Ask for OS camera/mic permission up front (required for a dev build; Expo Go
  // can't grant WebView media access, so camera only works in a custom dev build).
  useEffect(() => {
    if (Platform.OS === "android") {
      PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.CAMERA,
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
      ]).catch(() => {});
    }
  }, []);

  const cfg = [
    "config.prejoinPageEnabled=false",
    "config.disableDeepLinking=true",
    "config.startWithAudioMuted=false",
    "config.startWithVideoMuted=false",
    "userInfo.displayName=" + encodeURIComponent(name || "DermAI user"),
  ].join("&");
  const uri = `${VIDEO_BASE}/${room}#${cfg}`;

  return (
    <View style={styles.container}>
      <View style={styles.bar}>
        <Text style={styles.title}>Video consultation</Text>
        <View style={{ flexDirection: "row", alignItems: "center" }}>
          <TouchableOpacity onPress={() => Linking.openURL(uri)} style={styles.browser}>
            <Text style={styles.leaveText}>🎥 Browser</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.leave} onPress={onClose}>
            <Text style={styles.leaveText}>Leave</Text>
          </TouchableOpacity>
        </View>
      </View>
      <Text style={styles.hint}>Camera not turning on? Tap “Browser” to open the call where the phone can grant camera/mic.</Text>
      <WebView
        source={{ uri }}
        style={{ flex: 1 }}
        originWhitelist={["*"]}
        javaScriptEnabled
        domStorageEnabled
        allowsInlineMediaPlayback
        mediaPlaybackRequiresUserAction={false}
        // iOS: auto-grant camera/mic to the web content
        mediaCapturePermissionGrantType="grant"
        // Android: grant the WebView's getUserMedia request (app must hold the OS perms)
        onPermissionRequest={(event) => {
          const e = event?.nativeEvent;
          if (e && typeof e.grant === "function") e.grant(e.resources);
        }}
        startInLoadingState
        renderLoading={() => (
          <View style={styles.loading}>
            <ActivityIndicator size="large" color={colors.patient} />
            <Text style={{ marginTop: 12, color: "#cbd5e1", fontSize: 15 }}>Connecting you to the consultation…</Text>
            <Text style={{ marginTop: 6, color: "#64748b", fontSize: 12.5 }}>This can take a few seconds. Allow camera & microphone when asked.</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  bar: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingTop: 44, paddingBottom: 12, paddingHorizontal: 16, backgroundColor: "#0f172a",
  },
  title: { color: "#fff", fontSize: 16, fontWeight: "700" },
  leave: { backgroundColor: colors.err, borderRadius: 8, paddingVertical: 8, paddingHorizontal: 16 },
  leaveText: { color: "#fff", fontWeight: "700" },
  loading: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, alignItems: "center", justifyContent: "center", backgroundColor: "#000" },
  browser: { backgroundColor: colors.ok, borderRadius: 8, paddingVertical: 8, paddingHorizontal: 12, marginRight: 10 },
  hint: { color: "#cbd5e1", fontSize: 11.5, paddingHorizontal: 16, paddingVertical: 8, backgroundColor: "#0f172a" },
});

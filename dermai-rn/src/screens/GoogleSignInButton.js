// Isolated Google sign-in. This file pulls in expo-web-browser / expo-auth-session,
// whose native modules only exist in a dev/production build — NOT in Expo Go. It is
// therefore required lazily (see LoginScreen) so Expo Go never loads it.
import React, { useEffect } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Google from "expo-auth-session/providers/google";

import { apiPost } from "../api";
import { sessionFromAuth } from "../session";
import { colors } from "../theme";
import { GOOGLE_WEB_CLIENT_ID, GOOGLE_ANDROID_CLIENT_ID } from "../config";

WebBrowser.maybeCompleteAuthSession();

export default function GoogleSignInButton({ onLogin, onError, disabled }) {
  const [request, response, promptAsync] = Google.useIdTokenAuthRequest({
    androidClientId: GOOGLE_ANDROID_CLIENT_ID || undefined,
    webClientId: GOOGLE_WEB_CLIENT_ID || undefined,
  });

  useEffect(() => {
    if (response?.type === "success") {
      const idToken = response.params?.id_token || response.authentication?.idToken;
      if (idToken) {
        (async () => {
          try {
            const data = await apiPost("/auth/google", { credential: idToken });
            await onLogin(sessionFromAuth(data));
          } catch (e) {
            onError && onError(e.message || String(e));
          }
        })();
      }
    }
  }, [response]);

  return (
    <>
      <View style={styles.dividerRow}>
        <View style={styles.divLine} /><Text style={styles.divText}>or</Text><View style={styles.divLine} />
      </View>
      <TouchableOpacity style={styles.gbtn} disabled={!request || disabled} onPress={() => promptAsync()}>
        <Text style={styles.gbtnText}>Continue with Google</Text>
      </TouchableOpacity>
    </>
  );
}

const styles = StyleSheet.create({
  dividerRow: { flexDirection: "row", alignItems: "center", marginVertical: 14 },
  divLine: { flex: 1, height: 1, backgroundColor: colors.line },
  divText: { marginHorizontal: 10, color: colors.muted, fontSize: 12 },
  gbtn: { borderWidth: 1, borderColor: colors.line, borderRadius: 12, paddingVertical: 12, alignItems: "center", backgroundColor: "#fff" },
  gbtnText: { fontWeight: "700", color: colors.ink },
});

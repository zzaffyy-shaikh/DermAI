import React, { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, Modal, ScrollView, StyleSheet } from "react-native";

import { apiGet, apiPost } from "../api";
import { colors, fmtDateTime } from "../theme";

export default function NotifBell() {
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);

  const refresh = async () => {
    try { const r = await apiGet("/notifications/unread_count"); setUnread(r.unread || 0); }
    catch { /* ignore */ }
  };
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 20000);
    return () => clearInterval(t);
  }, []);

  const openPanel = async () => {
    setOpen(true);
    try {
      setItems(await apiGet("/notifications"));
      await apiPost("/notifications/read", {});
      setUnread(0);
    } catch { /* ignore */ }
  };

  return (
    <>
      <TouchableOpacity onPress={openPanel} style={{ marginRight: 16 }}
        accessibilityLabel={`Notifications${unread > 0 ? `, ${unread} unread` : ""}`} accessibilityRole="button">
        <Text style={{ fontSize: 18 }}>🔔</Text>
        {unread > 0 && (
          <View style={styles.badge}><Text style={styles.badgeText}>{unread > 9 ? "9+" : unread}</Text></View>
        )}
      </TouchableOpacity>

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <TouchableOpacity style={styles.backdrop} activeOpacity={1} onPress={() => setOpen(false)}>
          <View style={styles.sheet}>
            <View style={styles.sheetHead}>
              <Text style={{ fontWeight: "700", fontSize: 16 }}>Notifications</Text>
              <TouchableOpacity onPress={() => setOpen(false)}><Text style={{ color: colors.muted }}>Close</Text></TouchableOpacity>
            </View>
            <ScrollView style={{ maxHeight: 360 }}>
              {items.length === 0 && <Text style={{ color: colors.muted, padding: 14 }}>No notifications yet.</Text>}
              {items.map((n) => (
                <View key={n.id} style={[styles.item, !n.read && styles.unread]}>
                  <Text>{n.text}</Text>
                  <Text style={styles.meta}>{fmtDateTime(n.created_at)}</Text>
                </View>
              ))}
            </ScrollView>
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  badge: { position: "absolute", top: -6, right: -8, backgroundColor: colors.err, borderRadius: 9, minWidth: 16, height: 16, paddingHorizontal: 3, alignItems: "center", justifyContent: "center" },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "700" },
  backdrop: { flex: 1, backgroundColor: "rgba(15,23,42,.4)", justifyContent: "flex-start" },
  sheet: { backgroundColor: "#fff", marginTop: 90, marginHorizontal: 12, borderRadius: 14, overflow: "hidden" },
  sheetHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 14, borderBottomWidth: 1, borderBottomColor: colors.line },
  item: { padding: 14, borderBottomWidth: 1, borderBottomColor: colors.line },
  unread: { backgroundColor: "rgba(47,107,255,.07)" },
  meta: { color: colors.muted, fontSize: 11, marginTop: 4 },
});

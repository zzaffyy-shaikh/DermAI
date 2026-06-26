// Phone push notifications via Expo. Loaded defensively: if expo-notifications
// isn't installed (or running where it's unavailable) push is simply disabled
// and the rest of the app keeps working.
import { Platform } from "react-native";

const PROJECT_ID = "392c7aa0-287b-4b83-a9ea-4c608f32e23a"; // app.json extra.eas.projectId

let Notifications = null;
try {
  Notifications = require("expo-notifications");
} catch (e) {
  // package not installed — push disabled
}

if (Notifications) {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowAlert: true, // back-compat for older expo-notifications
    }),
  });
}

// Ask permission, get this device's Expo push token. Returns null if unavailable.
export async function registerForPush() {
  if (!Notifications) return null;
  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "Default",
        importance: Notifications.AndroidImportance.MAX,
      });
    }
    let status = (await Notifications.getPermissionsAsync()).status;
    if (status !== "granted") {
      status = (await Notifications.requestPermissionsAsync()).status;
    }
    if (status !== "granted") return null;
    const res = await Notifications.getExpoPushTokenAsync({ projectId: PROJECT_ID });
    return res.data;
  } catch (e) {
    return null;
  }
}

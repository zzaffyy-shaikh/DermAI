// Keyboard handling that works in BOTH a custom dev build and Expo Go.
// - Dev build: uses react-native-keyboard-controller (input always rises above keyboard).
// - Expo Go: that native module isn't bundled, so we fall back to plain components.
import { ScrollView } from "react-native";

let KeyboardProvider = ({ children }) => children;
let KeyboardAwareScrollView = ScrollView;

try {
  const kc = require("react-native-keyboard-controller");
  if (kc?.KeyboardProvider) KeyboardProvider = kc.KeyboardProvider;
  if (kc?.KeyboardAwareScrollView) KeyboardAwareScrollView = kc.KeyboardAwareScrollView;
} catch (e) {
  // not available (Expo Go) — fallbacks above are used
}

export { KeyboardProvider, KeyboardAwareScrollView };

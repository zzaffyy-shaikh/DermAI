// Backend base URL.
// - Android emulator: 10.0.2.2 maps to the host PC (NOT 127.0.0.1).
// - Expo Go on a real phone (same Wi-Fi): use your PC's LAN IP, e.g.
//     export const BASE_URL = "http://192.168.1.50:8000";
//   and start the backend with: uvicorn app.main:app --host 0.0.0.0 --port 8000
export const BASE_URL = "http://192.168.1.3:8000";

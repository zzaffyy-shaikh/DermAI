// Backend base URL.
// - Android emulator: 10.0.2.2 maps to the host PC (NOT 127.0.0.1).
// - Expo Go on a real phone (same Wi-Fi): use your PC's LAN IP, e.g.
//     export const BASE_URL = "http://192.168.1.50:8000";
//   and start the backend with: uvicorn app.main:app --host 0.0.0.0 --port 8000
export const BASE_URL = "https://zzaffy-dermai.hf.space";

// Base URL for video consultations (Jitsi Meet — free, no account needed).
export const VIDEO_BASE = "https://meet.jit.si";

// Google sign-in client IDs (from Google Cloud Console).
// - WEB id is used as the audience the backend trusts (also used by the web app).
// - ANDROID id is required for the Google button to work in the mobile dev/release build.
// Leave blank to hide the Google button on mobile.
export const GOOGLE_WEB_CLIENT_ID = "529239133336-b59ss1rh743l34jfp8h6a6hgm7sui20v.apps.googleusercontent.com";
export const GOOGLE_ANDROID_CLIENT_ID = "529239133336-c7u686dju2e1ehupjjjciin9ohpccsj5.apps.googleusercontent.com";

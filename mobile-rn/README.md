# DermAI — Mobile App (React Native + Expo)

Cross-platform client for the DermAI backend: role-based login/signup, patient diagnosis
+ follow-up questions, **video** consultation, doctor queue, and admin panel.

```
mobile-rn/
├─ App.js                  # root: restores session, routes by role
└─ src/
   ├─ config.js           # backend base URL (EDIT THIS)
   ├─ theme.js
   ├─ api.js              # fetch + bearer token + multipart upload
   ├─ session.js          # token persistence (AsyncStorage)
   └─ screens/
      ├─ LoginScreen.js   # sign in / create account (patient & doctor)
      ├─ PatientHome.js   # camera/gallery → diagnose → chat → video consult + history
      ├─ DoctorHome.js    # consultation queue (accept / close)
      └─ AdminHome.js     # stats + doctor verification
```

## What to install
1. **Node.js LTS** — https://nodejs.org (gives you `node` + `npx` + `npm`).
2. **Expo Go** app on your phone (Play Store / App Store) — for instant testing.
3. *(optional)* Android Studio — only for an emulator or to build a standalone APK.

## Create the project and add this code
Expo can't run from loose files; scaffold a project, then drop our code in:

```powershell
cd C:\Users\ossam\Documents\fyp
npx create-expo-app@latest dermai-rn --template blank
cd dermai-rn
npx expo install expo-image-picker @react-native-async-storage/async-storage

# copy our source over the generated defaults:
Copy-Item ..\mobile-rn\App.js . -Force
Copy-Item ..\mobile-rn\src . -Recurse -Force
```

## Point the app at your backend — `src/config.js`
- **Phone via Expo Go (recommended):** set your PC's LAN IP, e.g. `http://192.168.1.50:8000`
  (find it with `ipconfig`), and run the backend so the phone can reach it:
  ```
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```
  Allow port 8000 through Windows Firewall, and keep the phone on the same Wi-Fi.
- **Android emulator:** use `http://10.0.2.2:8000`.

## Run
```powershell
npx expo start
```
- Scan the QR code with **Expo Go** (Android) / Camera (iOS), **or** press `a` for an Android emulator.
- HTTP works in Expo Go for development. (For a production APK you'd add the
  `expo-build-properties` plugin with `android.usesCleartextTraffic: true`.)

## Test accounts
- Admin (seeded): `admin` / `admin123`
- Create patient & doctor accounts from the **Create account** tab.
- Doctors start **pending** → approve them from the Admin screen.

## Notes
- Same `/auth` token flow as the web app; token stored via AsyncStorage so you stay logged in.
- Consultation is **video-only** by design.
- The earlier Flutter version under `../mobile/` is superseded by this RN app — you can ignore/delete it.
```

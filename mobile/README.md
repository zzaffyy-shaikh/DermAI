# DermAI — Mobile App (Flutter)

Cross-platform client for the DermAI backend. Same features as the web app:
role-based login/signup, patient diagnosis + follow-up questions, **video** consultation,
doctor queue, and admin panel.

```
mobile/
├─ pubspec.yaml
└─ lib/
   ├─ main.dart            # app entry + role-based routing (RootGate)
   ├─ config.dart          # backend base URL (EDIT THIS)
   ├─ theme.dart
   ├─ services/
   │  ├─ api_client.dart   # http + bearer token
   │  └─ session.dart      # token persistence (shared_preferences)
   └─ screens/
      ├─ login_screen.dart # sign in / create account (patient & doctor)
      ├─ patient_home.dart # Diagnose (camera/gallery → chat → video consult) + History
      ├─ doctor_home.dart  # consultation queue (accept / close)
      └─ admin_home.dart   # stats + doctor verification
```

## 1. Install the toolchain (one-time)
- Flutter SDK: https://docs.flutter.dev/get-started/install/windows
- Android Studio (for the Android SDK + an emulator), then run `flutter doctor` until it's green.

## 2. Create the platform scaffolding
This repo has the `lib/` and `pubspec.yaml`, but not the generated `android/ios` folders.
Create a fresh project and copy our code in (this avoids `flutter create` overwriting files):

```powershell
cd C:\Users\ossam\Documents\fyp
flutter create dermai_app
# copy our app code over the generated defaults:
Copy-Item mobile\pubspec.yaml dermai_app\ -Force
Copy-Item mobile\lib\* dermai_app\lib\ -Recurse -Force
cd dermai_app
flutter pub get
```

## 3. Allow plain-HTTP (the backend is http, not https)
Android blocks cleartext HTTP by default. In
`dermai_app\android\app\src\main\AndroidManifest.xml`, add to the `<application>` tag:

```xml
<application
    android:usesCleartextTraffic="true"
    ... >
```

(For camera capture, also ensure this permission is present in the same manifest:
`<uses-permission android:name="android.permission.CAMERA"/>`.)

## 4. Point the app at your backend — `lib/config.dart`
- **Android emulator:** keep `http://10.0.2.2:8000` (10.0.2.2 = the host PC from inside the emulator).
- **Real phone (same Wi-Fi):** set your PC's LAN IP, e.g. `http://192.168.1.50:8000`
  (find it with `ipconfig`), and start the backend so it listens on all interfaces:
  ```
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```
  (also allow port 8000 through Windows Firewall).

## 5. Run
```powershell
flutter run
```

## Test accounts
- Admin (seeded): `admin` / `admin123`
- Create patient & doctor accounts from the app's **Create account** tab.
- Doctors start **pending** → approve them from the Admin screen.

## Notes
- Auth uses the same `/auth/login` + bearer-token flow as the web app; the token is
  stored with `shared_preferences` so you stay logged in.
- Consultation is **video-only** by design.

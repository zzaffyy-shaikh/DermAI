# DermAI — Development Log & Architecture

A complete record of how DermAI was taken from a basic classifier + proposal to a full
multi-platform, role-based teledermatology application: the requests made, the work done,
the decisions, the bugs found and fixed, and the final architecture.

> **Project:** DermAI — AI-powered skin-disease screening (FYP, Hamdard University, Karachi).
> **Team:** Huzaifa Bin Shakeel, Abdul Wasay, Shahzaib Hussain Pirzada.
> **Stack:** Python/FastAPI + ConvNeXt-Tiny (PyTorch) + Gemini LLM + SQLite, vanilla-JS web app,
> React Native (Expo) mobile app.

---

## 1. System architecture (final)

```
                         ┌──────────────────────────────────────────────┐
   CLIENTS               │  Web app (/app, vanilla ES-module SPA)        │
                         │  Mobile app (React Native + Expo)             │
                         │  Roles: Patient · Doctor · Management(admin)  │
                         └───────────────┬──────────────────────────────┘
                                         │ HTTPS (bearer-token auth)
                         ┌───────────────▼──────────────────────────────┐
   API GATEWAY           │  FastAPI  (REST)  — RBAC + verification gate  │
                         │  /auth /diagnose /chat /consult /profile      │
                         │  /report /admin /history                      │
                         └───────────────┬──────────────────────────────┘
              ┌──────────────────────────┼───────────────────────────┐
              ▼                          ▼                           ▼
   ┌─────────────────────┐  ┌──────────────────────┐  ┌────────────────────────┐
   │ AI pipeline         │  │ LLM cross-questioning │  │ Persistence            │
   │ • ConvNeXt-Tiny     │  │ • prompt builder      │  │ • SQLite (SQLAlchemy)  │
   │   (WHOLE image)     │  │ • Gemini 2.5-flash    │  │   users + auth_tokens  │
   │ • CV insights       │  │   (scripted fallback) │  │ • sessions (in-mem)    │
   │ • decision gate     │  │ • orchestrator        │  │ • consults (in-mem)    │
   │   healthy/OOD/normal│  │   (state machine)     │  │ • reports/ (PDF)       │
   └─────────────────────┘  └──────────────────────┘  └────────────────────────┘
              │                          │
              ▼                          ▼
   ClinicalBrief (JSON: disease, confidence, entropy, body region,
   visual insights, patient demographics + medical history)  ──►  LLM (never sees the image)
                                         │
                                         ▼
                         Final result + PDF report ──► Doctor video consult (Jitsi)
```

**Locked-in design decisions**
- **ConvNeXt classifies the WHOLE image** (it was trained on whole images) — MobileSAM/FastSAM is for overlay/severity only, never the classifier input.
- **Body region comes from the patient's tap**, not a model.
- **The LLM never sees the image** — only a structured `ClinicalBrief`, so it asks clinical (not visual) questions.
- **Consultation is video-only** (Jitsi).
- **Doctors and management start unverified** and are gated until a verified admin approves them.

---

## 2. Components & file map

```
fyp/
├─ codes/                         # model training
│  ├─ train.py                    # original (kept)
│  ├─ convnext_skin_fyp_new.pth   # original (leakage-trained) model
│  ├─ prepare_data.py             # NEW: split-FIRST then augment (leakage-free)
│  ├─ train_v2.py                 # NEW: class-weighted, best-val-F1 checkpoint
│  ├─ evaluate_and_calibrate.py   # NEW: clean test confusion matrix + thresholds
│  └─ convnext_skin_best.pth      # NEW: honest retrained model (~89% test acc)
├─ backend/                       # FastAPI service (API + web app)
│  ├─ app/
│  │  ├─ main.py                  # app, CORS, no-cache, model warm-up, routers
│  │  ├─ config.py                # env settings (DERMAI_*)
│  │  ├─ db.py / models.py        # SQLAlchemy + auto-migration
│  │  ├─ schemas.py
│  │  ├─ ml/  classifier · segmentation · insights · decision_gate · preprocess
│  │  ├─ llm/ prompt_builder · providers (scripted/openai/gemini) · orchestrator · question_bank
│  │  ├─ services/ sessions · consult · report (PDF) · auth
│  │  └─ api/ deps · routes_auth · routes_diagnose · routes_chat · routes_consult
│  │           routes_profile · routes_report · routes_admin · routes_history
│  ├─ webapp/                     # web SPA (login + patient/doctor/admin)
│  ├─ tests/                      # pytest suite (11 tests)
│  ├─ qa_probe.py                 # exploratory SQA probe
│  ├─ requirements.txt · Dockerfile · SECURITY.md · DEPLOYMENT.md · README.md
├─ dermai-rn/                     # LIVE React Native (Expo) app
│  └─ src/ config · theme · api · session · kb · screens(Login/Patient/Doctor/Admin/Pending/Call/MedicalHistory)
├─ mobile/                        # earlier Flutter version (superseded)
└─ Docs/                          # proposal, compliance report, architecture, this log
```

---

## 3. Chronological development log

### Phase 0 — Review of the existing project
- **Request:** "review the docs and the code and the model I have trained."
- **Done:** Read proposal + compliance PDFs, the training/inference scripts, the confusion matrix, and the dataset (8 classes). 
- **Findings:** (1) **Critical data leakage** — augmentation was applied *before* the train/val split, so augmented copies of the same image were in both sets → the ~100% accuracy and confusion matrix were inflated/fake; (2) model is **ConvNeXt-Tiny, 8 classes** (docs said EfficientNet/CoAtNet/MobileNetV2 — mismatch); (3) no "fungal infection" class despite the proposal; (4) PyTorch model vs docs' TensorFlow/TFLite plan; (5) folder typo "Hyper Pigmintation"; (6) a stray license-plate-detector project in `checkpoints/`.

### Phase 1 — Architecture
- **Request:** "make an architecture for the project … webapp + flutter, LLM, MobileSAM."
- **Done:** Authored `Docs/DermAI_Architecture.md` + a graphical `DermAI_Architecture.html` (3 role-based logins). Clarified that the **LLM receives the CNN's structured output (context injection), never the raw image**, so it acts like a doctor who has already examined the patient; defined the **healthy / out-of-distribution / normal** routing; established **body region from a UI tap** (not a flaky body-part model); reviewed multithreading and corrected the diagram's ConvNeXt-on-SAM-crop dependency (kept whole-image classification).

### Phase 2 — Backend service
- **Request:** "start writing optimized code in structured files."
- **Done:** Built a structured FastAPI backend — ConvNeXt classifier (whole image, top-k + entropy), optional MobileSAM, decision gate, LLM prompt builder + providers (scripted offline default) + orchestrator, in-memory session/consult stores, RBAC dependencies, routes. Ran on CUDA; verified `/diagnose` end-to-end.
- **Also:** wrote the leakage-free training trio (`prepare_data.py`, `train_v2.py`, `evaluate_and_calibrate.py`).

### Phase 3 — Frontends
- **Request:** "attach a frontend so I can test it thoroughly" → then a full web app.
- **Done:** A built-in test console at `/ui`, then a full web SPA at `/app` (no build step, ES modules) with **role-based login pages** and patient/doctor/admin dashboards, served by the backend (fixed the Windows `.js` MIME gotcha).

### Phase 4 — Accounts, database, video-only consult
- **Request:** "create an account flow, use a database for credentials/patient/doctor info, remove chat — only video."
- **Done:** SQLite via SQLAlchemy (`users`, `auth_tokens`), PBKDF2-hashed passwords, register/login/logout with bearer tokens, seeded admin. Consultation made **video-only**.

### Phase 5 — Mobile app
- **Request:** "start working on a mobile application" → then "use React Native instead of Flutter."
- **Done:** Installed Node, scaffolded an **Expo** app (`dermai-rn`), built login + patient/doctor/admin screens against the same API. Hit SDK/Expo-Go version issues; created an **EAS development build**.

### Phase 6 — In-app video
- **Request:** "in-app video call, not 3rd party."
- **Done:** Embedded **Jitsi in a WebView** (`CallScreen`) so the call renders inside the app; each consult gets a shared room (`DermAI-<id>`). Camera/mic require the dev build (Expo Go can't grant WebView camera).

### Phase 7 — Quality & intelligence fixes
- **Requests & fixes:**
  - **Questions repeating / asking a male about menstrual cycle** → de-dup in the orchestrator + **profile-aware** question bank (uses sex/age; never asks sex-inappropriate questions); switched LLM to **Gemini 2.5-flash** for real generation (scripted remains the offline fallback).
  - **Keyboard hid the input** → diagnosed as SDK 54 Android edge-to-edge; adopted `react-native-keyboard-controller` (with an Expo-Go fallback shim `kb.js`).
  - **"No insights (colour/edges/etc.)"** → added a CV **visual-analysis** module (dominant colour, redness, texture, affected-area %, borders) fed into the LLM + report.
  - **PDF report** → `services/report.py` (fpdf2): diagnosis + visual analysis + medical history + Q&A + recommendation; viewable by patient and doctor.
  - **Google sign-in** → web + mobile (`/auth/google`, accepts web & android client IDs).

### Phase 8 — Proper medical history
- **Request:** "take a proper medical history before diagnosis and use it in the LLM."
- **Done:** A persistent **dermatological history** modelled on **Rook's** + **Fitzpatrick** (demographics, Fitzpatrick skin phototype, atopy, sun exposure/sunscreen, skin-cancer history, family history, chronic conditions, meds, allergies, smoking). **Required before diagnosis** (HTTP 428 gate); injected into the LLM prompt and the PDF. Later made **layman-friendly** (e.g. "how does your skin react to the sun?" instead of "Fitzpatrick I–VI"; "eczema/asthma/hay fever?" instead of "atopy").

### Phase 9 — Roles, verification & management
- **Requests & fixes:**
  - Doctors must **not** get instant access → doctor signup collects **specialization, qualification, graduation, house job, PMDC number + license upload**; doctors land on a **Pending screen** and are gated until approved.
  - **Management portal** added to signup; **management accounts must be approved by an existing verified admin** (seeded `admin` bootstraps).
  - Admin panel rebuilt: **verification queue** with full credentials + **View license**, Approve/**Reject**.
  - **Doctor console** enriched: stats (in queue / my cases / resolved), queue + "my cases" with **solution notes**.
  - **Bug:** "Reject" did nothing (it re-set verified=false on an already-pending account) → added a real **DELETE** endpoint; Reject now removes the account. Also fixed the unreadable red button (solid red).
  - **Bug:** reload showed the old page → added a **no-cache** middleware for `/app` and `/ui`.

### Phase 10 — Honest model (leakage retrain)
- **Done:** Ran `prepare_data.py` (split-first-then-augment, verified disjoint), trained `train_v2.py` (stopped after the best epoch). Result: **~88% validation, ~89% on the clean test set** — a *real* number replacing the fake ~100%. Generated the honest confusion matrix and calibrated decision-gate thresholds. New model saved as `convnext_skin_best.pth` (original kept).

### Phase 11 — Senior-SQA QA pass
- **Request:** "treat this as a Silicon-Valley industrial project; test it as a senior SQA."
- **Done:** Wrote `qa_probe.py` (security / authorization / validation / abuse) and ran it in prod-auth mode.
  - 🔴 **HIGH (fixed):** any verified doctor could read **any** patient's medical history & report → now scoped to an actual **consult relationship**.
  - 🟠 **MED (fixed):** whitespace-only usernames → trimmed/rejected.
  - 🟢 **LOW (fixed):** negative age → constrained 0–120.
  - **Passed:** cross-patient access blocked, logged-out tokens rejected, role gating, non-image rejection, history gate, admin self-delete prevention.
  - Result: regression `pytest` = 11/11; probe = 0 findings. Documented residual risks (token expiry, rate limiting, audit log) in `SECURITY.md`.

### Phase 12 — Sharing / remote testing
- **Request:** "open via Expo Go" / "let my friend test it."
- **Done:** Fixed an Expo bundling error (`react-native-worklets` needed for Reanimated 4); added the `kb.js` Expo-Go fallback. For remote access, exposed the backend via a **Cloudflare quick tunnel** — friend uses the **web app** in a browser (the web app calls the API same-origin, so no config change), verified live (`/health` ok through the tunnel).

---

## 4. Issues found & fixed (summary)

| # | Issue | Severity | Resolution |
|---|---|---|---|
| 1 | Train/val **data leakage** (augment before split) | Critical | `prepare_data.py` split-first; retrained → honest 89% |
| 2 | Doctor could read ANY patient's records | High (privacy) | Access scoped to a consult relationship |
| 3 | Repeated / sex-inappropriate questions | High (UX) | Orchestrator de-dup + profile-aware bank + Gemini |
| 4 | Keyboard covered the input (Android) | High (UX) | `react-native-keyboard-controller` + Expo-Go shim |
| 5 | Doctors/management got instant access | High | Verification gate + credentials + admin approval |
| 6 | "Reject" was a no-op | Medium | Real DELETE endpoint |
| 7 | Stale page on reload | Medium | No-cache middleware |
| 8 | Whitespace username / negative age | Med/Low | Input validation |
| 9 | Clinical jargon (Fitzpatrick/atopy) | Low (UX) | Plain-language form |
| 10 | Model files / docs mismatch | Low | Documented; report wording to update |

---

## 5. Current status

- **Backend:** complete, 11/11 tests green, QA-clean. Gemini 2.5-flash + Google sign-in supported.
- **Web app:** complete — login (incl. Google), patient flow (history gate → diagnosis → chat → video consult → PDF), doctor console, management verification panel.
- **Mobile app:** feature-complete in code; runs in **Expo Go** (with degraded keyboard / no native Google); full keyboard + mobile Google + camera need the **EAS dev build** (Gradle build to be finalized).
- **Model:** honest retrained `convnext_skin_best.pth` (~89% test) — point `.env` `DERMAI_MODEL_PATH` at it.

### Known follow-ups
- Finalize the **EAS Android dev build** (and APK).
- Production hardening: **token expiry, rate limiting, audit logging** (see `SECURITY.md`).
- **Rotate the Gemini API key** (it was committed to `.env.example`).
- Update the **FYP report** wording: ConvNeXt-Tiny (not EfficientNet/CoAtNet), React Native (not Flutter), 8 classes (no "fungal infection").

---

## 6. How to run

**Backend (+ web app):**
```
conda activate fyp
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000   # web app at http://localhost:8000/
```
**Tests:** `python -m pytest tests -q`  ·  **QA probe:** `python qa_probe.py`
**Mobile (Expo Go):** `cd dermai-rn && npx expo start --go -c`
**Retrain (optional):** `python prepare_data.py && python train_v2.py && python evaluate_and_calibrate.py`
**Share remotely:** `cloudflared tunnel --url http://localhost:8000` → open the printed URL.

**Seeded admin:** `admin` / `admin123` (change in production).

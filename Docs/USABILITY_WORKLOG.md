# DermAI — Usability Improvements Worklog

A running record of the usability work, so anything can be understood, verified, or
rolled back. **Read the "Rollback" section first if something breaks.**

- **Started:** 2026-06-25
- **Scope:** Usability enhancements only. **Excluded:** Urdu/English bilingual UI
  (deferred — high effort/risk) and phone push notifications (needs a mobile dev
  build, not possible in Expo Go).
- **Rule for this effort:** implement ONE feature at a time, then run the full test
  suite before moving on.

---

## Restore points / Rollback

| What | Value |
|---|---|
| Known-good commit (pushed to GitHub) | `2cf3d3f` — "Initial commit — DermAI final year project" |
| Remote | https://github.com/zzaffyy-shaikh/DermAI |
| Branch | `main` |

**Restore commands (run from `C:\Users\ossam\Documents\fyp`):**

```bash
# See everything changed since the known-good commit
git diff --stat HEAD

# Discard ALL uncommitted changes and return to the last commit
git stash            # (recoverable) — OR —
git checkout -- .    # (permanent discard)

# Hard reset back to the pushed restore point (loses uncommitted work)
git reset --hard 2cf3d3f
```

> Uncommitted work present at the start of this effort (NOT in commit `2cf3d3f`):
> `backend/webapp/js/views/patient.js`, `dermai-rn/src/screens/PatientHome.js`
> (the "book from a previous diagnosis" feature) and `dermai-rn/src/config.js`
> (LAN IP). These are intended changes; back them up before any hard reset if you
> want to keep them.

---

## Baseline architecture (for context)

- **Backend** — FastAPI (`backend/app`): ConvNeXt classifier + decision gate,
  Gemini LLM cross-questioning, medical history, appointment-based consults,
  in-app notifications, RBAC + admin. In-memory stores for sessions / consults /
  slots / notifications; users + history in SQLite. Serves the web app at `/app`.
- **Web app** — vanilla-JS SPA (`backend/webapp/js`): `views/patient.js`,
  `views/doctor.js`, `views/admin.js`, shared `ui.js` / `api.js` / `store.js`.
- **Mobile** — React Native + Expo (`dermai-rn/src`): `screens/PatientHome.js`,
  `DoctorHome.js`, `AdminHome.js`, `CallScreen.js`, `NotifBell.js`, `theme.js`.

## How each feature is tested ("test everything")

- **Backend:** `python -m compileall app` + `pytest -q` (full suite) from `backend/`.
- **Web (vanilla ESM):** ESM syntax check via `node --check` on a temp `.mjs` copy.
- **Mobile (JSX):** Babel parse via the project's `babel-preset-expo`
  (`node -e "require('@babel/core').transformFileSync(...)"`).
- **Manual:** explicit click-through steps recorded per feature.

Interpreter: `C:\Users\ossam\anaconda3\envs\fyp\python.exe`.

---

## Feature plan & status

| # | Feature | Surfaces | Status |
|---|---|---|---|
| 1 | Lay-friendly results & confidence framing | web + mobile | ✅ done & tested |
| 2 | Photo-capture guidance + blurry-retake prompt | web + mobile | ✅ done & tested |
| 3 | Loading / empty / error states + feedback | web | ✅ done & tested |
| 4 | Friendlier doctor availability picker | web + mobile | ✅ done & tested |
| 5 | Cancel appointments (+ rebook) | backend + web + mobile | ✅ done & tested |
| 6 | Video-call connecting state | mobile | ✅ done & tested |
| 7 | Accessibility (focus, aria labels) | web + mobile | ✅ done & tested |
| 8 | First-run onboarding tips | web + mobile | ✅ done & tested |

Legend: ⏳ planned · 🔨 in progress · ✅ done & tested

---

## Change log (per feature)

> Each entry records: what changed, files touched, and test results.

### Feature 1 — Lay-friendly results & confidence framing ✅
**Why:** Patients saw raw `Entropy`, a scary precise `Melanoma 89.0%`, and no plain
explanation or disclaimer.
**What changed:**
- Added a plain-language headline per mode (healthy / unclear / likely-condition),
  qualitative confidence band (**Low / Moderate / High**) instead of a bare %, and a
  prominent "preliminary screening, not a diagnosis" disclaimer.
- Removed the internal `Entropy` metric from the patient view; relabelled fields
  (Most likely / Likelihood / Other possibility / Affected area / Photo quality).
- The "URGENT" badge now reads "needs a doctor" (supportive, not alarming).
**Files:**
- `backend/webapp/js/views/patient.js` — `renderBrief` + `confidenceBand`/`plainResult`.
- `backend/webapp/css/styles.css` — `.result-headline`, `.disclaimer`.
- `dermai-rn/src/screens/PatientHome.js` — `BriefCard` + helpers + styles.
**Tested:** web ESM `node --check` OK · mobile JSX babel-parse OK · backend
`compileall` + `pytest` 13/13 passed.
**Manual check:** run a screening → result card shows headline + band + disclaimer,
no "Entropy".

### Feature 2 — Photo-capture guidance + blurry-retake prompt ✅
**Why:** The app computed image quality (`blur_score` → `image_quality`) but never
guided the user to take a good photo or warned when it was blurry.
**What changed:**
- A capture-tips note under the image picker (lighting, focus, fill frame, no shadows).
- When the result comes back as `blurry`, a prominent amber warning suggests retaking,
  on both web and mobile.
**Files:**
- `backend/webapp/js/views/patient.js` — tips in the upload card; blurry warning in `renderBrief`.
- `backend/webapp/css/styles.css` — `.photo-tips`, `.warn-box`.
- `dermai-rn/src/screens/PatientHome.js` — tips in `DiagnoseTab`; warning in `BriefCard`; styles.
**Tested:** web ESM OK · mobile JSX OK · backend `pytest` 13/13.
**Manual check:** upload a blurry photo → amber "looks blurry, retake" warning appears.

### Feature 3 — Friendly errors + toast feedback (web) ✅
**Why:** Web used blocking `alert()` popups, and a server-down error rendered as an
ugly `{}` (JSON.stringify of a TypeError).
**What changed:**
- `errText()` now detects network failures → "Can't reach the server…" and unwraps
  `Error.message` instead of stringifying objects.
- Added a non-blocking `toast()` helper (info/ok/err) and replaced all `alert()` calls
  in the doctor & admin consoles; added success toasts (confirm/decline/close/solution).
**Files:** `backend/webapp/js/api.js`, `ui.js`, `views/doctor.js`, `views/admin.js`,
`backend/webapp/css/styles.css` (`.toast*`).
**Note:** mobile already uses native `Alert`/`ActivityIndicator`, so no change needed there.
**Tested:** ESM `node --check` on api/ui/doctor/admin/patient OK · backend `pytest` 13/13.
**Manual check:** trigger a doctor/admin action with the server stopped → red toast
"Can't reach the server…"; confirm an appointment → green "Appointment confirmed".

### Feature 4 — Friendlier doctor availability picker ✅
**Why:** On mobile the doctor had to type `YYYY-MM-DD` and `HH:MM` by hand.
**What changed:**
- Mobile: tap a **day chip** (next 14 days) + a **time chip** → "Add slot" (no new
  dependency; works in Expo Go).
- Web: kept the native `datetime-local` picker but set `min` to now (no past slots).
**Files:** `dermai-rn/src/screens/DoctorHome.js` (chips + helpers + styles),
`backend/webapp/js/views/doctor.js` (min attr).
**Tested:** web ESM OK · mobile JSX OK.
**Manual check:** doctor → My availability → tap a day + time → Add → slot appears.

### Feature 5 — Cancel appointments ✅
**Why:** Patients could book but never cancel; a freed slot couldn't be reused.
**What changed:**
- Backend: `ConsultStore.cancel(case_id, patient_id)` (only own pending/confirmed) +
  `POST /consult/{id}/cancel` → releases the slot and notifies the doctor.
- Web + mobile: a **Cancel** button on pending/confirmed appointments (with confirm
  prompt); status badge + label show "Cancelled". Rebook via the existing
  book-from-history flow.
**Files:** `backend/app/services/consult.py`, `backend/app/api/routes_consult.py`,
`backend/app/schemas.py`, `backend/tests/test_api.py` (new test),
`backend/webapp/js/views/patient.js`, `dermai-rn/src/screens/PatientHome.js`.
**Tested:** new `test_patient_can_cancel_appointment` (slot freed + ownership enforced)
→ backend `pytest` **14/14**; web ESM OK; mobile JSX OK.

### Feature 6 — Video-call connecting state (mobile) ✅
**What changed:** Clearer connecting copy on the in-app call screen + a reminder to
allow camera/mic. (Web joins the call in a browser tab, so no in-app state needed.)
**Files:** `dermai-rn/src/screens/CallScreen.js`. **Tested:** JSX parse OK.

### Feature 7 — Accessibility ✅
**What changed:**
- Web: global `:focus-visible` outline for keyboard navigation; `aria-label`s on the
  notification bell, its panel, and the logout button.
- Mobile: `accessibilityLabel`/`accessibilityRole` on the notification bell (announces
  unread count).
- (Urgency already conveyed by text — "needs a doctor"/"URGENT" — not color alone.)
**Files:** `backend/webapp/css/styles.css`, `backend/webapp/js/ui.js`,
`dermai-rn/src/screens/NotifBell.js`. **Tested:** ESM + JSX OK.

### Feature 8 — First-run onboarding ✅
**What changed:** A dismissible "How DermAI works" guide (5 steps) on the patient
screen, shown once — persisted via `localStorage` (web) / `AsyncStorage` (mobile).
**Files:** `backend/webapp/js/views/patient.js`, `backend/webapp/css/styles.css`
(`.onboard`), `dermai-rn/src/screens/PatientHome.js`.
**Tested:** ESM + JSX OK; backend `pytest` 14/14.

---

### Fix — truncated final LLM summary (Gemini) ✅
**Symptom:** The final cross-questioning summary cut off mid-sentence
("…it's highly likely") and never named the condition.
**Cause:** `gemini-2.5-flash` performs hidden "thinking" by default; those tokens
consumed the `max_output_tokens=400` budget and truncated the visible answer.
**Fix:** In `GeminiProvider._generate`, set `ThinkingConfig(thinking_budget=0)`
(disable thinking) and raise `max_output_tokens` to 800.
**File:** `backend/app/llm/providers.py`.
**Tested:** live Gemini `fuse()` call now returns a complete 497-char summary that
names the condition (verified end-to-end); backend `pytest` 14/14.

---

### Feature 9 — Answer-aware differential refinement ✅
**Why (user-reported):** (1) The confidence never changed no matter how the patient
answered — the cross-questioning didn't feed back into the diagnosis. (2) The
questions confirmed a single prediction instead of discriminating between look-alike
conditions ("multidisciplinary" differential).
**Approach:** Rule-based (naive-Bayes) refinement — image softmax = prior; curated
discriminating symptoms update the posterior; final diagnosis + confidence come from
the refined posterior. Chosen for explainability + testability (vs. letting the LLM
invent a number).
**What changed:**
- New engine `backend/app/ml/differential.py` — 11 discriminating features with
  per-disease P(yes|disease); `initial_posterior` / `update` / `next_feature` /
  `leading` / `normalise_answer`.
- `Orchestrator` now drives NORMAL mode as structured **Yes / No / Not sure**
  questions, updating the posterior each answer; `_finalize` folds the refined
  disease/confidence back into the brief (so summary, report, and result card update).
  HEALTHY/OOD keep conversational questions.
- `ChatTurn` / `DiagnoseResponse` carry `options`; `Session` stores posterior +
  asked features + pending feature.
- Web + mobile: render tappable answer options for structured questions; after the
  questions, re-fetch `/chat/{id}/result` and update the result card with a
  "✓ Updated using your answers" note.
**Limitation surfaced to the user:** "seborrheic dermatitis" is NOT a trained class
(only "Seborrheic Keratoses"), so that specific case can't be labelled correctly
without retraining; refinement is limited to the 8 trained classes.
**Files:** `backend/app/ml/differential.py` (new), `app/llm/orchestrator.py`,
`app/schemas.py`, `app/services/sessions.py`, `app/api/routes_diagnose.py`,
`backend/tests/test_differential.py` (new), `backend/webapp/js/views/patient.js`,
`dermai-rn/src/screens/PatientHome.js`.
**Tested:** 6 new tests (engine math + ownership of update + orchestrator end-to-end
proving confidence != image value) → backend `pytest` **20/20**; web ESM + mobile JSX OK.

---

## Summary

All 8 planned usability features delivered and tested (Urdu/English bilingual and
phone push intentionally excluded — see Scope). Final test state: **backend
`pytest` 14/14**, all changed web modules pass `node --check`, all changed mobile
screens pass Babel JSX parse. Restore point remains commit `2cf3d3f`.

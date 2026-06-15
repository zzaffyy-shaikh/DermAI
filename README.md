# DermAI — AI-Powered Skin Disease Screening & Teledermatology

DermAI is a final-year project (Hamdard University, Karachi) that screens skin
conditions from a photo using a deep-learning classifier, conducts an LLM-driven
clinical interview, generates a PDF report, and connects patients to **verified
dermatologists** for appointment-based video consultations.

> ⚠️ **Medical disclaimer:** DermAI is a preliminary screening aid for educational
> purposes, **not** a medical diagnosis. Always consult a qualified dermatologist.

## Features

- **Skin classifier** — ConvNeXt-Tiny (PyTorch) over 8 classes (Acne, Atopic
  Dermatitis, Eczema, Healthy, Hyperpigmentation, Melanoma, Psoriasis, Seborrheic
  Keratoses) with a confidence/entropy decision gate (healthy / out-of-distribution
  / normal).
- **Clinical interview** — an LLM (Google Gemini, with offline scripted fallback)
  cross-questions the patient using the vision findings + their medical history;
  it never sees the raw image, only a structured brief.
- **Medical history** — a one-time dermatological history (Rook's / Fitzpatrick
  framework) collected before diagnosis and reused in every screening and report.
- **Teledermatology** — patients book a published time slot with a verified
  dermatologist; in-app notifications drive the appointment lifecycle (request →
  confirm/decline → solution). Video calls run over Jitsi.
- **Role-based portals** — Patient, Doctor (with verification of credentials/PMDC
  + license), and Management (approves doctors/management, searchable patient
  registry). RBAC + verification gating throughout.
- **PDF report** — AI findings, visual analysis, affected-area photo, medical
  history, questionnaire and recommendation.

## Architecture

```
DermAI/
├── backend/        FastAPI API + web app (vanilla-JS SPA) + ML pipeline
│   ├── app/        routes, ML (classifier/segmentation/insights), LLM, services
│   └── webapp/     patient / doctor / admin single-page app
├── dermai-rn/      React Native (Expo) mobile app
├── codes/          model training & evaluation scripts + weights (Git LFS)
└── Docs/           development log & project documentation
```

## Quick start

### Backend + web app
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # (or use a conda env)
pip install -r requirements.txt
copy .env.example .env                               # then set your keys in .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open the web app at <http://127.0.0.1:8000/>. Set `DERMAI_MODEL_PATH` in `.env`
to your trained weights and `DERMAI_LLM_PROVIDER=gemini` with `DERMAI_GEMINI_API_KEY`
to enable the live LLM.

### Mobile app (Expo)
```bash
cd dermai-rn
npm install
npx expo start            # scan the QR with Expo Go (same Wi-Fi)
```
Set `BASE_URL` in `src/config.js` to your PC's LAN IP.

## Trained models

Model weights (`*.pth`) are stored with **Git LFS**. After cloning:
```bash
git lfs install
git lfs pull
```

## Tech stack

FastAPI · PyTorch / torchvision (ConvNeXt) · SQLAlchemy + SQLite · Google Gemini ·
fpdf2 · React Native + Expo · Jitsi Meet.

## Team

Huzaifa Bin Shakeel · Abdul Wasay · Shahzaib Hussain Pirzada — Hamdard University, Karachi.

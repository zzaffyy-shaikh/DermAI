# DermAI Backend

FastAPI service implementing the DermAI pipeline: **ConvNeXt-Tiny** classifier (whole image)
→ **MobileSAM** overlay/severity (optional) → **decision gate** (healthy / OOD / normal)
→ **LLM cross-questioning** → result + **doctor consultation** + **admin** management.

Runs out of the box with **no OpenAI key and no Firebase** (scripted LLM + dev auth).

## Structure

```
backend/
├─ app/
│  ├─ main.py              # FastAPI app, model warm-up, router wiring
│  ├─ config.py            # env-driven settings (prefix DERMAI_)
│  ├─ schemas.py           # Pydantic models (ClinicalBrief, ChatTurn, ...)
│  ├─ ml/
│  │  ├─ preprocess.py     # val transform + blur check
│  │  ├─ classifier.py     # ConvNeXt-Tiny singleton (WHOLE image)
│  │  ├─ segmentation.py   # MobileSAM (overlay/severity only, optional)
│  │  └─ decision_gate.py  # healthy / OOD / normal routing
│  ├─ llm/
│  │  ├─ question_bank.py  # per-disease clinical questions
│  │  ├─ prompt_builder.py # 3-mode system prompts (no visual questions)
│  │  ├─ providers.py      # ScriptedProvider + OpenAIProvider
│  │  └─ orchestrator.py   # cross-questioning state machine
│  ├─ services/
│  │  ├─ sessions.py       # diagnosis session store
│  │  └─ consult.py        # consult queue + doctor/user registry
│  └─ api/
│     ├─ deps.py           # auth (dev headers / Firebase) + RBAC
│     ├─ routes_diagnose.py
│     ├─ routes_chat.py    # REST + WebSocket
│     ├─ routes_consult.py
│     └─ routes_admin.py
├─ classes.json            # class order (MUST match training)
├─ requirements.txt
└─ .env.example
```

## Setup

```powershell
cd C:\Users\ossam\Documents\fyp\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# install torch matching your CUDA first (see requirements.txt), then:
pip install -r requirements.txt
copy .env.example .env        # edit paths/keys as needed
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs

## Auth during development

Send these headers (no real login needed in `dev` mode):
- `X-User-Id: <any id>`
- `X-Role: patient | doctor | admin`

Switch to real auth with `DERMAI_AUTH_MODE=firebase` + a service-account JSON.

## Quick test (PowerShell)

```powershell
# 1) diagnose (as a patient)
curl -X POST http://127.0.0.1:8000/diagnose `
  -H "X-Role: patient" -H "X-User-Id: u1" `
  -F "image=@C:\Users\ossam\Documents\fyp\testing photos\download (1).jpg" `
  -F "body_region=forearm"

# 2) answer a question (use the session_id from step 1)
curl -X POST http://127.0.0.1:8000/chat/answer `
  -H "X-Role: patient" -H "X-User-Id: u1" -H "Content-Type: application/json" `
  -d '{"session_id":"<ID>","answer":"It has been itchy for two weeks"}'

# 3) admin stats
curl http://127.0.0.1:8000/admin/stats -H "X-Role: admin" -H "X-User-Id: admin1"
```

## Endpoints by role

| Method | Path | Role |
|---|---|---|
| POST | `/diagnose` | patient / doctor |
| POST | `/chat/answer` | patient / doctor |
| WS | `/chat/ws/{session_id}` | (session-scoped) |
| GET | `/chat/{session_id}/result` | patient / doctor |
| POST | `/consult/request` | patient |
| GET | `/consult/queue` | doctor |
| POST | `/consult/{id}/accept` · `/close` | doctor |
| GET | `/admin/stats` · `/admin/doctors` | admin |
| POST | `/admin/doctors/verify` | admin |

## ⚠️ Before trusting confidence

The decision gate's `confidence_threshold` and `entropy_threshold` are only meaningful
once the model is retrained **without train/val leakage** (split *before* augmenting).
See `../codes/prepare_data.py` and `../codes/train.py` updates.

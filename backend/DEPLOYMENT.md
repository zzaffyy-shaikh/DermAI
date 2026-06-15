# DermAI — Deployment Guide

The backend serves the **API + web app (`/app`) + test console (`/ui`)** from one process.
Mobile (Expo) connects to the same API over the network.

## Production environment variables (`.env`)
| Var | Production value |
|---|---|
| `DERMAI_AUTH_MODE` | **not** `dev` (e.g. `prod`) — disables the header bypass |
| `DERMAI_SEED_ADMIN_PASSWORD` | a strong password |
| `DERMAI_CORS_ORIGINS` | your real origin(s), e.g. `["https://dermai.example.com"]` |
| `DERMAI_MODEL_PATH` | path to `convnext_skin_best.pth` (the retrained model) |
| `DERMAI_CONFIDENCE_THRESHOLD` / `DERMAI_ENTROPY_THRESHOLD` | calibrated values from `evaluate_and_calibrate.py` |
| `DERMAI_LLM_PROVIDER` | `gemini` |
| `DERMAI_GEMINI_API_KEY` | a **rotated** key (the old one was committed — replace it) |
| `DERMAI_GOOGLE_CLIENT_ID` | your production OAuth client id |
| `DERMAI_DATABASE_URL` | keep SQLite for small scale, or `postgresql://…` for real scale |

## Pre-flight checklist
- [ ] `python -m pytest tests -q` → all green
- [ ] Retrained model in place; `.env` points at it with calibrated thresholds
- [ ] `DERMAI_AUTH_MODE` ≠ `dev`, admin password changed, CORS restricted (see `SECURITY.md`)
- [ ] Gemini key rotated; secrets only in `.env` (gitignored), never in `.env.example`
- [ ] HTTPS in front (nginx / Caddy / platform TLS)

## Run (single host)
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Put **nginx/Caddy** in front for TLS and to proxy to `127.0.0.1:8000`. Use **one worker** — the
ConvNeXt model loads per worker, so multiple workers multiply VRAM/RAM use. Scale by running more
single-worker containers behind the proxy instead.

## Docker
```bash
# from backend/ — provide the model via a volume (kept out of the image)
docker build -t dermai-backend .
docker run -p 8000:8000 \
  -v /abs/path/to/convnext_skin_best.pth:/models/model.pth \
  -e DERMAI_MODEL_PATH=/models/model.pth \
  -e DERMAI_AUTH_MODE=prod \
  -e DERMAI_GEMINI_API_KEY=*** \
  -e DERMAI_GOOGLE_CLIENT_ID=*** \
  -e DERMAI_SEED_ADMIN_PASSWORD=*** \
  dermai-backend
```
The image above is **CPU**. For GPU inference, base it on `nvidia/cuda` + install the CUDA build of
torch, and run with `--gpus all`.

## Mobile (Expo) for release
- Point `dermai-rn/src/config.js` `BASE_URL` at the deployed **https** API.
- Build the release APK: `eas build --profile production --platform android`.
- Add the production API origin to the Google OAuth client when you wire mobile Google sign-in.

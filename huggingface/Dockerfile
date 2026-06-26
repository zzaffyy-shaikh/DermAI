# DermAI — Hugging Face Spaces (Docker SDK) image.
# Free hosting, no card. This builds by cloning the public GitHub repo (which carries
# the trained model via Git LFS), so the Space itself only needs this file + README.md.
# HF serves the app over HTTPS on port 7860.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        git git-lfs libjpeg62-turbo libpng16-16 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

WORKDIR /app
# Public repo includes backend/, webapp/ and the model in codes/ (Git LFS).
RUN git clone --depth 1 https://github.com/zzaffyy-shaikh/DermAI.git . && git lfs pull

WORKDIR /app/backend
RUN pip install --upgrade pip && pip install -r requirements.txt

# Runtime config. Secrets (Gemini key, admin password) come from Space "Secrets".
ENV DERMAI_MODEL_PATH=/app/codes/convnext_skin_best.pth \
    DERMAI_DEVICE=cpu \
    DERMAI_LLM_PROVIDER=gemini \
    DERMAI_GEMINI_MODEL=gemini-2.5-flash \
    DERMAI_AUTH_MODE=prod

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

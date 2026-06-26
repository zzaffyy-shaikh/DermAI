# DermAI backend — production image (API + bundled web app).
# Multi-arch: builds on Oracle Cloud's free ARM (Ampere A1) and on x86. CPU-only
# inference — on ARM the default PyPI torch wheels are already CPU builds.
# Build from the REPO ROOT (so the model in codes/ is in context):
#   docker build -f backend/Dockerfile -t dermai-backend .
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/backend

# small runtime libs some wheels expect
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo libpng16-16 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python deps first so this layer caches across code changes.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application code + bundled web app + the honest trained model (Git LFS).
COPY backend/ /app/backend/
COPY codes/convnext_skin_best.pth /app/codes/convnext_skin_best.pth

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

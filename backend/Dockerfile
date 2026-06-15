# CPU image for the DermAI backend (API + web app).
# For GPU inference, switch the base to an nvidia/cuda image and install the CUDA build of torch.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# system deps for Pillow / OpenCV-free stack
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo libpng16-16 \
 && rm -rf /var/lib/apt/lists/*

# install CPU torch first (smaller), then the rest
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
COPY requirements.txt .
RUN pip install -r requirements.txt

# app code + frontends + classes.json
COPY app ./app
COPY classes.json ./
COPY webapp ./webapp
COPY static ./static

# model is provided at runtime via a volume (see DEPLOYMENT.md) to keep the image small
ENV DERMAI_MODEL_PATH=/models/model.pth \
    DERMAI_AUTH_MODE=prod

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

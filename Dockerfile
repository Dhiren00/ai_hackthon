FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TF_ENABLE_ONEDNN_OPTS=0 TF_CPP_MIN_LOG_LEVEL=3
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg tesseract-ocr fonts-noto-core && rm -rf /var/lib/apt/lists/*
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-full.txt
COPY . .
RUN python scripts/setup_models.py
EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

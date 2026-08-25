FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
        libfreetype6-dev \
        ffmpeg \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/resources /app/logs

# yt-dlp needs the latest release to keep up with site changes (Instagram, etc.),
# so refresh it on every container start (best-effort - don't block boot if PyPI is unreachable).
CMD ["sh", "-c", "pip install --no-cache-dir --upgrade yt-dlp || true; exec python3 -u main.py"]

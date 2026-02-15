FROM python:3.11-slim

# System deps for lxml/pillow/cffi etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libxml2-dev libxslt1-dev libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Cache buster - change this value to force rebuild
ARG CACHE_BUST=2026-02-15-ai-endpoints-fix

# Copy application files explicitly (avoids permission issues)
COPY templates ./templates
COPY static ./static

# Copy Python application files
COPY *.py ./

# Security: don't ship local sqlite/db/git in image
RUN rm -f physio.db physio_backup.db || true \
    && rm -rf .git || true

# Use Gunicorn (Flask app is main:app)
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["gunicorn", "-w", "3", "-k", "gthread", "-b", "0.0.0.0:8080", "--timeout", "120", "main:app"]
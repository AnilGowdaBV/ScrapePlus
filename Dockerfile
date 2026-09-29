FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    BROWSER_HEADLESS=true

WORKDIR /app

# Install system utilities needed by playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages + playwright chromium
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt \
    && python -m playwright install --with-deps chromium

# Copy application code
COPY alembic.ini ./alembic.ini
COPY backend ./backend
COPY scraper ./scraper

# Ensure database storage folder exists
RUN mkdir -p database

EXPOSE 8000

# Upgrade migrations and launch uvicorn on Render's dynamic $PORT
CMD ["sh", "-c", "alembic upgrade head && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

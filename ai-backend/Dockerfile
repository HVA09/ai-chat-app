# ---- مرحلة البناء (تثبيت المكتبات فقط) ----
# Docker Official Images mirrored on ECR Public to avoid Docker Hub pull-rate-limit failures.
FROM ghcr.io/astral-sh/uv:0.12.23-python3.12-trixie-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---- مرحلة التشغيل (صورة نهائية أصغر، بدون أدوات بناء) ----
FROM ghcr.io/astral-sh/uv:0.12.23-python3.12-trixie-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home appuser \
    && mkdir -p /app/uploads && chown appuser:appuser /app/uploads

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser scripts/start.sh ./scripts/start.sh

RUN chmod +x ./scripts/start.sh

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EMBEDDED_CELERY=false

USER appuser

EXPOSE 8000

CMD ["./scripts/start.sh"]

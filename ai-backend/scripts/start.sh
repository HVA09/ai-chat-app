#!/bin/sh
set -eu

alembic upgrade head

if [ -n "${S3_BUCKET:-}" ] && [ -n "${S3_ENDPOINT_URL:-}" ] && [ -n "${S3_REGION:-}" ] && [ -n "${S3_ACCESS_KEY_ID:-}" ] && [ -n "${S3_SECRET_ACCESS_KEY:-}" ]; then
  if python - <<'PY'
from app.services.storage import check_connection
check_connection()
print("Object Storage connectivity: OK")
PY
  then
    :
  else
    echo "Object Storage connectivity: FAILED"
  fi
else
  echo "Object Storage remote storage is not configured"
fi

WORKER_PID=""
BEAT_PID=""
WATCHDOG_PID=""
API_PID=""

cleanup() {
  for pid in "$WATCHDOG_PID" "$WORKER_PID" "$BEAT_PID" "$API_PID"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}

trap cleanup INT TERM EXIT

if [ "${EMBEDDED_CELERY:-false}" = "true" ]; then
  echo "Embedded Celery enabled"
  echo "Celery binary: $(command -v celery)"

  python -m celery -A app.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    --hostname=free-worker@%h &
  WORKER_PID=$!

  python -m celery -A app.tasks.celery_app beat \
    --loglevel=info \
    --schedule=/tmp/celerybeat-schedule &
  BEAT_PID=$!

  sleep 3

  if kill -0 "$WORKER_PID" 2>/dev/null; then
    echo "Embedded Celery worker process started (pid=$WORKER_PID)"
  else
    echo "Embedded Celery worker process exited during startup"
    exit 1
  fi

  if kill -0 "$BEAT_PID" 2>/dev/null; then
    echo "Embedded Celery beat process started (pid=$BEAT_PID)"
  else
    echo "Embedded Celery beat process exited during startup"
    exit 1
  fi

  (
    while true; do
      if ! kill -0 "$WORKER_PID" 2>/dev/null; then
        echo "Embedded Celery worker process exited"
        kill "$API_PID" 2>/dev/null || true
        exit 1
      fi
      if ! kill -0 "$BEAT_PID" 2>/dev/null; then
        echo "Embedded Celery beat process exited"
        kill "$API_PID" 2>/dev/null || true
        exit 1
      fi
      sleep 10
    done
  ) &
  WATCHDOG_PID=$!
else
  echo "Embedded Celery disabled"
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

wait "$API_PID"

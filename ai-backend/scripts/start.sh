#!/bin/sh
set -eu

alembic upgrade head

WORKER_PID=""
BEAT_PID=""
API_PID=""

cleanup() {
  for pid in "$WORKER_PID" "$BEAT_PID" "$API_PID"; do
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

  python -m celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1 &
  WORKER_PID=$!

  python -m celery -A app.tasks.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule &
  BEAT_PID=$!
else
  echo "Embedded Celery disabled"
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

wait "$API_PID"

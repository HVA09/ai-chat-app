#!/bin/sh
set -eu

alembic upgrade head

WORKER_PID=""
BEAT_PID=""
API_PID=""

cleanup() {
  for pid in "$API_PID" "$WORKER_PID" "$BEAT_PID"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}

trap cleanup INT TERM EXIT

if [ "${EMBEDDED_CELERY:-false}" = "true" ]; then
  celery -A app.tasks.celery_app worker --loglevel=info &
  WORKER_PID=$!

  celery -A app.tasks.celery_app beat --loglevel=info &
  BEAT_PID=$!
fi

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

while kill -0 "$API_PID" 2>/dev/null; do
  if [ -n "$WORKER_PID" ] && ! kill -0 "$WORKER_PID" 2>/dev/null; then
    exit 1
  fi
  if [ -n "$BEAT_PID" ] && ! kill -0 "$BEAT_PID" 2>/dev/null; then
    exit 1
  fi
  sleep 2
done

wait "$API_PID"

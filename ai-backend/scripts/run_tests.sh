#!/usr/bin/env bash
# تشغيل اختبارات الباك اند ضد PostgreSQL محلي
set -euo pipefail
cd "$(dirname "$0")/.."

DB_URL="${TEST_DATABASE_URL:-postgresql://postgres:postgres@127.0.0.1:5432/ai_backend_test}"

export DATABASE_URL="${DATABASE_URL:-$DB_URL}"
export TEST_DATABASE_URL="$DB_URL"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-test-secret-key-for-ci-only}"
export AI_API_KEY="${AI_API_KEY:-test-key-not-real}"
export ENVIRONMENT="${ENVIRONMENT:-test}"

echo "→ TEST_DATABASE_URL=$TEST_DATABASE_URL"
python -m pytest -v "$@"

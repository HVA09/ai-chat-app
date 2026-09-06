#!/usr/bin/env bash
# فحص سريع بعد النشر: /health و /billing/plans
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
info() { printf '\033[36m%s\033[0m\n' "$*"; }

fail=0

info "→ Smoke against $BASE_URL"

health_body="$(curl -sS -m 15 -w '\n%{http_code}' "$BASE_URL/health" || true)"
health_code="$(echo "$health_body" | tail -n1)"
health_json="$(echo "$health_body" | sed '$d')"

if [[ "$health_code" != "200" ]]; then
  red "FAIL /health HTTP $health_code"
  fail=1
else
  status="$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  db="$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('database',''))" 2>/dev/null || echo "")"
  if [[ "$status" == "ok" && "$db" == "ok" ]]; then
    green "OK   /health status=$status database=$db"
  else
    red "FAIL /health body=$health_json"
    fail=1
  fi
fi

plans_body="$(curl -sS -m 15 -w '\n%{http_code}' "$BASE_URL/billing/plans" || true)"
plans_code="$(echo "$plans_body" | tail -n1)"
plans_json="$(echo "$plans_body" | sed '$d')"

if [[ "$plans_code" != "200" ]]; then
  red "FAIL /billing/plans HTTP $plans_code"
  fail=1
else
  count="$(echo "$plans_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo 0)"
  if [[ "$count" -ge 1 ]]; then
    green "OK   /billing/plans count=$count"
  else
    red "FAIL /billing/plans empty or invalid"
    fail=1
  fi
fi

rid="$(curl -sS -m 10 -D - -o /dev/null "$BASE_URL/health" 2>/dev/null | tr -d '\r' | awk -F': ' 'tolower($1)=="x-request-id"{print $2}')"
if [[ -n "${rid:-}" ]]; then
  green "OK   X-Request-ID present"
else
  info "…    X-Request-ID not found (optional)"
fi

if [[ "$fail" -ne 0 ]]; then
  red "Smoke FAILED"
  exit 1
fi
green "Smoke PASSED"

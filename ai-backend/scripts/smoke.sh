#!/usr/bin/env bash
# فحص سريع بعد النشر: /health و /billing/plans
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
info() { printf '\033[36m%s\033[0m\n' "$*"; }

fail=0
tmp_health="$(mktemp)"
tmp_plans="$(mktemp)"
trap 'rm -f "$tmp_health" "$tmp_plans"' EXIT

info "→ Smoke against $BASE_URL"

health_meta="$(curl -sS -m 15 -o "$tmp_health" -w '%{http_code} %{time_total}' "$BASE_URL/health" || true)"
health_code="$(echo "$health_meta" | awk '{print $1}')"
health_time="$(echo "$health_meta" | awk '{print $2}')"
health_json="$(cat "$tmp_health")"

if [[ "$health_code" != "200" ]]; then
  red "FAIL /health HTTP $health_code"
  fail=1
else
  status="$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  db="$(echo "$health_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('database',''))" 2>/dev/null || echo "")"
  if [[ "$status" == "ok" && "$db" == "ok" ]]; then
    green "OK   /health status=$status database=$db latency=${health_time:-unknown}s"
  else
    red "FAIL /health body=$health_json"
    fail=1
  fi
fi

plans_meta="$(curl -sS -m 15 -o "$tmp_plans" -w '%{http_code} %{time_total}' "$BASE_URL/billing/plans" || true)"
plans_code="$(echo "$plans_meta" | awk '{print $1}')"
plans_time="$(echo "$plans_meta" | awk '{print $2}')"
plans_json="$(cat "$tmp_plans")"

if [[ "$plans_code" != "200" ]]; then
  red "FAIL /billing/plans HTTP $plans_code"
  fail=1
else
  count="$(echo "$plans_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo 0)"
  if [[ "$count" -ge 1 ]]; then
    green "OK   /billing/plans count=$count latency=${plans_time:-unknown}s"
  else
    red "FAIL /billing/plans empty or invalid"
    fail=1
  fi
fi

rid="$(curl -sS -m 10 -H 'X-Request-ID: smoke-check' -D - -o /dev/null "$BASE_URL/health" 2>/dev/null | tr -d '\r' | awk -F': ' 'tolower($1)=="x-request-id"{print $2}')"
if [[ "$rid" == "smoke-check" ]]; then
  green "OK   X-Request-ID propagation"
else
  red "FAIL X-Request-ID propagation"
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  red "Smoke FAILED"
  exit 1
fi
green "Smoke PASSED"

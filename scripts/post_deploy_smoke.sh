#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:?Missing BASE (Function base URL, e.g., https://your-func.azurewebsites.net)}"
CODE="${CODE:-}"

probe_url="$BASE/api/ai_probe"
if [ -n "$CODE" ]; then
  probe_url="$probe_url?code=$CODE"
fi

echo "== AI Probe URL:"
echo "$probe_url"
echo

# Don't use -f so we can capture non-2xx responses
http_body="$(mktemp)"
http_status=$(curl -sS -o "$http_body" -w "%{http_code}" "$probe_url" || true)

echo "== HTTP status: $http_status"
echo "== Response body:"
cat "$http_body" || true
echo

if [ "$http_status" != "200" ]; then
  echo "Probe failed (HTTP $http_status)"
  exit 1
fi

echo "OK"

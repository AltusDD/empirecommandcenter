#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:?Missing BASE (Function base URL, e.g., https://your-func.azurewebsites.net)}"
CODE="${CODE:-}"

probe_url="$BASE/api/ai_probe"
if [ -n "$CODE" ]; then
  probe_url="$probe_url?code=$CODE"
fi

echo "== AI Probe: $probe_url"
out="$(curl -fsSL "$probe_url")" || { echo "Probe failed"; exit 1; }
echo "$out" | jq . || echo "$out"
echo "OK"

#!/usr/bin/env bash
# SessionStart auto-check for the travel-hacking-toolkit.
#
# Runs once when you launch `claude --plugin-dir .`. Two jobs:
#   1. points-valuations.json — auto-refresh from sources IF it's past its TTL
#      (not every launch: that would add latency and risk rate-limiting).
#   2. sweet-spots.json — check whether upstream (borski/main) is newer and
#      NOTIFY only (it's editorial data; you review before replacing it).
#
# This script must NEVER block or fail the session: it always exits 0, bounds
# its network calls, and degrades to a one-line note if anything is unreachable.
# Note: macOS has no `timeout` binary, so we rely on curl --max-time and the
# scraper's own per-request urllib timeouts rather than wrapping with timeout.

REPO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)}"
cd "$REPO" 2>/dev/null || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

# --- 1. points-valuations: refresh if stale ---
PV="data/points-valuations.json"
if [ -f "$PV" ]; then
  STATUS="$(python3 - "$PV" <<'PY'
import json, sys, datetime
try:
    m = json.load(open(sys.argv[1])).get("_meta", {})
    age = (datetime.date.today() - datetime.date.fromisoformat(m["last_updated"])).days
    print("STALE" if age > int(m.get("staleness_days", 45)) else "FRESH")
except Exception:
    print("SKIP")
PY
)"
  if [ "$STATUS" = "STALE" ]; then
    echo "[travel-hacker] points-valuations is stale — refreshing from sources..."
    if python3 scripts/refresh-points-valuations.py >/dev/null 2>&1; then
      echo "[travel-hacker] points-valuations refreshed."
    else
      echo "[travel-hacker] points-valuations refresh couldn't reach sources; using existing data."
    fi
  fi
fi

# --- 2. sweet-spots: notify if upstream is newer (never auto-overwrite) ---
SS="data/sweet-spots.json"
RAW="https://raw.githubusercontent.com/borski/travel-hacking-toolkit/main/data/sweet-spots.json"
if [ -f "$SS" ] && command -v curl >/dev/null 2>&1; then
  LOCAL_LU="$(python3 -c "import json;print(json.load(open('$SS')).get('_meta',{}).get('last_updated',''))" 2>/dev/null)"
  UP_LU="$(curl -fsS --max-time 8 "$RAW" 2>/dev/null | python3 -c "import json,sys;print(json.load(sys.stdin).get('_meta',{}).get('last_updated',''))" 2>/dev/null)"
  if [ -n "$UP_LU" ] && [ -n "$LOCAL_LU" ] && [ "$UP_LU" \> "$LOCAL_LU" ]; then
    echo "[travel-hacker] Sweet spots updated upstream: local $LOCAL_LU -> upstream $UP_LU."
    echo "                Review & pull just that file:"
    echo "                  git fetch origin && git checkout origin/main -- data/sweet-spots.json"
  fi
fi

exit 0

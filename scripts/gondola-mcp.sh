#!/usr/bin/env bash
# Gondola hotel search via direct MCP-over-HTTP.
#
# WHY THIS EXISTS: the native Gondola MCP client (and the mcp-health-check hook)
# negotiate content-type incorrectly and get HTTP 406 ("Not Acceptable") from
# mcp.gondola.ai. Sending the correct `Accept: application/json, text/event-stream`
# header and doing the MCP handshake by hand returns 200 with real data. This
# script is that workaround, so the toolkit can still pull cash + points hotel
# rates when the MCP path is stuck.
#
# Gondola is STATELESS: initialize returns no Mcp-Session-Id, and tools/call works
# without one. We still capture a session id if the server ever sends one.
#
# Only Gondola's PUBLIC (unauthenticated) hotel tools work here:
#   search_hotels, compare_rates, get_hotel_details
# Account/payment tools (get_payment_methods, ...) require OAuth and return 401;
# this script does not use them.
#
# Usage:
#   scripts/gondola-mcp.sh <tool_name> '<json_args>'
# Examples:
#   scripts/gondola-mcp.sh search_hotels \
#     '{"location":"Palma de Mallorca, Spain","checkin":"2026-07-16","checkout":"2026-07-19","num_adults":2}'
#   scripts/gondola-mcp.sh compare_rates \
#     '{"hotel_ids":[41283859,39649094],"checkin":"2026-07-16","checkout":"2026-07-19","num_adults":2}'
#   scripts/gondola-mcp.sh get_hotel_details '{"hotel_id":41283859}'

set -u

URL="https://mcp.gondola.ai/mcp"
ACCEPT="application/json, text/event-stream"

TOOL="${1:?tool name required (e.g. search_hotels)}"
# NB: avoid ${2:-{}} — the brace in the default prematurely closes the expansion.
ARGS="${2:-}"
[ -z "$ARGS" ] && ARGS='{}'

command -v curl >/dev/null 2>&1 || { echo "gondola-mcp: curl is required" >&2; exit 2; }
command -v jq   >/dev/null 2>&1 || { echo "gondola-mcp: jq is required"   >&2; exit 2; }

# --- 1. initialize (capture a session id only if the server sends one) ---
HDRS="$(mktemp)"
trap 'rm -f "$HDRS"' EXIT
if ! curl -fsS -D "$HDRS" -o /dev/null -X POST "$URL" \
      -H "Content-Type: application/json" -H "Accept: $ACCEPT" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"toolkit-fallback","version":"1.0"}}}'; then
  echo "gondola-mcp: initialize request failed (endpoint may be down)" >&2
  exit 1
fi

SID="$(grep -i '^mcp-session-id:' "$HDRS" 2>/dev/null | tr -d '\r' | awk '{print $2}')"
SID_HDR=()
[ -n "${SID:-}" ] && SID_HDR=(-H "Mcp-Session-Id: $SID")

# --- 2. initialized notification (best-effort) ---
curl -fsS -o /dev/null -X POST "$URL" \
  -H "Content-Type: application/json" -H "Accept: $ACCEPT" ${SID_HDR[@]+"${SID_HDR[@]}"} \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null 2>&1 || true

# --- 3. tools/call ---
if ! BODY="$(curl -fsS -X POST "$URL" \
      -H "Content-Type: application/json" -H "Accept: $ACCEPT" ${SID_HDR[@]+"${SID_HDR[@]}"} \
      -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"$TOOL\",\"arguments\":$ARGS}}")"; then
  echo "gondola-mcp: tools/call request failed" >&2
  exit 1
fi

# Pull JSON-RPC objects out of the SSE stream; keep the one carrying result/error.
RESULT="$(printf '%s\n' "$BODY" | grep '^data:' | sed 's/^data: *//' \
  | jq -c 'select(.result or .error)' 2>/dev/null | tail -1)"

# Server may answer with plain JSON instead of SSE (Accept lists both) — parse as-is.
if [ -z "${RESULT:-}" ]; then
  RESULT="$(printf '%s' "$BODY" | jq -c 'select(.result or .error)' 2>/dev/null | tail -1)"
fi

if [ -z "${RESULT:-}" ]; then
  echo "gondola-mcp: no result in response. Raw (first 300 chars):" >&2
  printf '%s' "$BODY" | head -c 300 >&2; echo >&2
  exit 1
fi

printf '%s\n' "$RESULT" | jq -r '
  if .error then "gondola-mcp error: " + (.error.message // (.error | tostring))
  else (.result.content[]? | select(.type == "text") | .text)
  end'

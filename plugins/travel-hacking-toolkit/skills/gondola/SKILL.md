---
name: gondola
description: Gondola hotel search returning cash AND loyalty points rates side-by-side across Marriott, Hilton, Hyatt, IHG, Accor, Wyndham and more, with cents-per-point (cpp) valuation. Use for hotel points-vs-cash comparison and award hotel pricing. Works around a 406 content-negotiation bug in the native Gondola MCP server by calling the endpoint directly via scripts/gondola-mcp.sh.
category: hotels
summary: Cash + points hotel rates via Gondola (direct-HTTP fallback for the 406 bug).
license: MIT
---

# Gondola Skill (direct-HTTP fallback)

Gondola is the one source that returns **cash and loyalty-points hotel rates together**
with a cents-per-point valuation — ideal for deciding whether to pay cash or redeem
points for a hotel. It complements the cash-only hotel sources (Trivago, SerpAPI,
LiteAPI) and the chain-award angle.

## Why this skill calls a script instead of the MCP server

A `gondola` MCP server may be registered (user scope), but it currently returns
**HTTP 406 ("Not Acceptable")**: the MCP client and the `mcp-health-check` hook don't
send the `Accept: application/json, text/event-stream` header Gondola requires, so the
call is blocked before it runs. Calling the endpoint directly with the correct header
and a manual MCP handshake returns 200 with real data.

**Therefore: do NOT call the `gondola` MCP tools directly. Use the script below.**
If the native MCP server is ever fixed, the script keeps working regardless.

## Usage

```bash
# Search hotels (cash + points + cpp) for a city and dates
scripts/gondola-mcp.sh search_hotels \
  '{"location":"Palma de Mallorca, Spain","checkin":"2026-07-16","checkout":"2026-07-19","num_adults":2}'

# Compare specific hotels side-by-side (hotel_ids come from search_hotels results)
scripts/gondola-mcp.sh compare_rates \
  '{"hotel_ids":[41283859,39649094],"checkin":"2026-07-16","checkout":"2026-07-19","num_adults":2}'

# Detailed info for one hotel
scripts/gondola-mcp.sh get_hotel_details '{"hotel_id":41283859}'
```

Run it from the repo root (the path is relative to the repo). It prints Gondola's
formatted results to stdout. On failure (endpoint down, bad args) it prints an error
to stderr and exits non-zero — fall through to other hotel sources.

## Tools

| Tool | Arguments | Returns |
|------|-----------|---------|
| `search_hotels` | `location` (required), `checkin`, `checkout`, `num_adults` (default 2), optional `chain_name`, `loyalty_programs`, `loyalty_points` | Hotels with cash rate, points rate, cpp, and deal scores |
| `compare_rates` | `hotel_ids` (array, from search), `checkin`, `checkout`, `num_adults` | Side-by-side cash vs points with best-value flags |
| `get_hotel_details` | `hotel_id` | Rooms, rates, booking options for one hotel |

## Notes

- **Cash vs points:** Gondola reports cpp directly. Apply the usual floors — Hyatt
  ~1.5cpp is good; Hilton ~0.4cpp floor is almost always worse than cash. Cross-check
  against the `points-valuations` skill before recommending a redemption.
- **Reachability:** the points programs Gondola shows (e.g. World of Hyatt) may need a
  transfer from a card currency (Chase UR → Hyatt 1:1). Verify the path in
  `data/transfer-partners.json` before recommending a transfer.
- **Scope:** only Gondola's public hotel tools are used. Account/payment/loyalty tools
  require OAuth and are intentionally not called.
- This is a workaround for an upstream content-negotiation bug, not an official Gondola
  integration.

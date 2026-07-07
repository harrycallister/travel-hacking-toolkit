---
name: best-card-for-spend
description: Earn-side optimizer. Given a purchase, merchant, or spending category, ranks the user's cards by REAL value returned (points earned × cents-per-point), not raw multiplier, and STACKS shopping portals (Rakuten etc.) and hotel/airline/card-linked promos on top. Answers "which card should I swipe?" and "how do I maximize points/cashback on this?" Triggers on "which card", "best card for", "maximize points/cashback on", "earn rate", "card to swipe", "rakuten", "shopping portal", "cashback portal", "hotel promo", "airline promo", "Amex/Chase offers", "stack".
category: loyalty
summary: Wallet-based card ranking for cash spend. Value-first (cents back per dollar) using points-valuations floors. Merchant→category classification, caps, and how to refresh earn rates via awardtravelfinder MCP.
---

# Best Card for Spend (Earn-Side Optimizer)

The rest of this toolkit optimizes the **burn** side (redeeming points). This skill is the **earn** side: when the user is about to pay cash, which card throws off the most *value* — not the biggest multiplier.

**The core insight:** raw multipliers lie. 6x Marriott (0.6cpp floor) = 3.6¢/$. 2x Capital One (1.6cpp) = 3.2¢/$. 4x Amex MR dining (1.7cpp) = 6.8¢/$. Always rank by `multiplier × cpp`, never by multiplier alone. This matches the user's value-first philosophy in `CLAUDE.local.md`.

## Data files

- **`data/my-cards.local.json`** — the user's wallet (gitignored). Each card has a `points_program` key (matching `points-valuations.json`), `earn` rates per category, optional `caps`, and freshness stamps (`last_verified`, `verified`, `verified_source`).
- **`data/points-valuations.json`** — cents-per-point floors/ceilings. The script reads `floor` by default (conservative, per the `points-valuations` skill's decision rules).
- **`data/earn-stack.local.json`** — booster registry (gitignored): shopping portals (Rakuten etc.), promo sources (Marriott/Delta/card-linked offers), and where to look each up live. See "Stacking boosters" below.

## How to use it

The deterministic math lives in `scripts/best-card.py`. Run it; don't recompute by hand.

```bash
python3 scripts/best-card.py dining --amount 250      # category + spend amount
python3 scripts/best-card.py --merchant "Whole Foods" # classify merchant → category
python3 scripts/best-card.py groceries                # just the ranking
python3 scripts/best-card.py travel --mode ceiling    # optimistic valuations
python3 scripts/best-card.py --table                  # full card × category matrix
python3 scripts/best-card.py --list-categories
```

Categories: `dining, groceries, gas, transit, travel, flights, hotels, vacation_rentals, streaming, online_retail, drugstores, entertainment, other`. `other` is the everyday/base rate.

## Workflow when the user asks "which card for X?"

**Verify the relevant card's rates LIVE every time — do not trust the snapshot.** Card categories change without warning (the CSP added 3x gas + 3x Airbnb/Vrbo on 2026-06-15, one day after this wallet was first built). The wallet is a cache, not a source of truth.

1. **Classify the purchase.** If they name a merchant, map it to a category (the script has hints, but use judgment — "Costco" is groceries but Amex acceptance and warehouse-club exclusions matter). If ambiguous, pick the most likely and say so.
2. **VERIFY current rates for the contending card(s) in that category.** This is mandatory, not optional. Scope it to the category asked (cheap — usually one card, one check). Source priority:
   - `awardtravelfinder` MCP: `cards_list_cards` / `get_card` for the card's current multipliers.
   - **Web** (`WebSearch`/`WebFetch`) — the authoritative source for *brand-new* changes the MCP DB hasn't ingested yet. Search e.g. `"<card name> earning categories 2026 <category>"`. Trust the issuer's own page and FrequentMiler/TPG over aggregators.
   - If the live rate differs from the wallet, **update `data/my-cards.local.json`** (the `earn` value, `caps`, `last_verified` = today, `verified` = true, `verified_source`) and re-run the script.
3. **Run the script** for that category (`--amount` shows points + dollar value). It prints a "Re-verify before trusting" list of any card not yet confirmed — those are your verification to-do for this query if they're in contention.
4. **Present the ranked table** (markdown) + a one-line recommendation with the cpp math, and state the as-of date ("rates current as of <date>").
5. **Flag caps.** Surface the winner's category cap (e.g. Amex Gold groceries 4x to $25k/yr) — the user may have blown it, dropping to 1x.
6. **Note portal-only rates.** 5x Chase Travel / 5x Capital One Travel are portal bookings, not swipes — mention as a separate path, don't fold into the swipe ranking.

Don't re-verify all five cards on every query — only the ones that could plausibly win the asked category. A `gas` question doesn't need the Marriott card re-checked.

## The freshness mechanism

Each card in the wallet carries:
- `last_verified` — ISO date its rates were last confirmed.
- `verified` — `true` only if confirmed against a live source this session; `false` cards print a ⚠ and appear in the script's "Re-verify" list.
- `verified_source` — where the rate came from.

`_meta.reverify_after_days` (default 7) is the staleness threshold: a `verified` card older than that also gets flagged. Run `python3 scripts/best-card.py <category> --json` to read the ranking + reverify list machine-readably during the verify step.

## Adding or changing a card

Use the **awardtravelfinder MCP** (`cards_list_cards` by `provider`/`region`, then `get_card`) plus a web check, then edit `data/my-cards.local.json`: set `earn`, `caps`, `last_verified`, `verified`, `verified_source`. Use `cards_find_cards_for_category` to spot a missing-category gap (the user currently has no strong gas card beyond CSP's new 3x). Never commit this file — it's gitignored via `*.local.json`.

## Stacking boosters: shopping portals + promos

The card swipe is only the base layer. For **online** purchases a shopping portal stacks on top; for **hotel/airline** spend a promo can too; **card-linked offers** (Amex/Chase/Cap One Offers) add a one-time credit. Registry: `data/earn-stack.local.json` (portals, promo sources, optional `active_promos`).

`python3 scripts/best-card.py --portals` and `--promos` list the user's boosters and where to check them live.

**Same dynamic-data rule as card rates, but stronger:** portal rates are per-merchant and change daily; promos are time-boxed and need registration. NEVER use a stored number — look it up live at decision time.

### Online purchase workflow
1. Find the best card for the category (normal flow above).
2. **Look up the live portal rate for THIS merchant.** Check `cashbackmonitor.com` or `evreward.com` (they compare every portal at once), or the portal directly. Pick the highest-*value* portal — a lower % paid into MR (×1.7) can beat a higher % cash. The registry says what each portal pays.
3. **Stack it:** `python3 scripts/best-card.py <category> --amount N --portal-pct <live%> --portal-currency <key|cash> --portal-name <portal>`. Output shows card + portal + combined cents/$.
4. Present the total. Note that the portal usually dominates (8% into MR ≈ 13.6¢/$ vs a 1–4x card), so the "which card" answer matters less online than which portal.

### Travel purchase workflow (hotel/airline)
1. Best card for `hotels`/`flights`/`vacation_rentals`.
2. **Check live promos** for that chain/airline via the `--promos` sources (e.g. Marriott quarterly promo, Delta targeted offer). Register BEFORE booking/staying or it won't count. Add genuinely-active ones to `active_promos` with an expiry.
3. Factor the promo bonus into the recommendation (promos are often flat bonuses — "2,000 pts after 2 nights" — so express as added value on the specific spend, not a clean cents/$).
4. **Portals DO stack on hotel/airline direct bookings — check, don't skip.** A shopping portal (Rakuten etc.) that clicks through to the brand's OWN site (Marriott.com, Delta.com, the "Book Direct" page) is still a direct booking: full loyalty points + elite-night/MQM credit are earned AND the portal cashback stacks on top. Only portals that re-book through an OTA (Expedia, Hotels.com, Booking.com) strip loyalty earning — avoid those for award/status purposes. So for a direct hotel/flight booking, always check cashbackmonitor.com/evreward.com for a portal paying on the brand's site and stack it; the earlier "skip portals on travel" instinct is wrong when the portal links to book-direct.

### Card-linked offers (Amex/Chase/Cap One Offers)
Always a free check before any sizeable purchase: log in, add the offer to the card, then buy with that card. These stack on everything else and are pure upside. The `--promos` list links each issuer's offers page.

## Edge cases the script handles

- A category a card doesn't bonus falls back to its `other` (base) rate, labeled `(base)`.
- A `points_program` with no valuation entry shows `?` and sorts last (rather than silently scoring 0).
- `--mode ceiling` uses optimistic valuations; default `floor` is conservative for real decisions.

## What this does NOT do

- It doesn't track welcome-bonus spend or annual-fee breakeven (use `cards_rank_welcome_bonuses` / `cards_analyze_spending` in the MCP for that).
- It doesn't know live cap consumption — caps are shown as notes, not enforced.
- It ranks *earning*. For whether to then *burn* those points, hand off to `points-valuations`, `transfer-partners`, and `award-sweet-spots`.

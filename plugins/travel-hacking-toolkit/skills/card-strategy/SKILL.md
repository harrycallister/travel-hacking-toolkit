---
name: card-strategy
description: Credit card acquisition and portfolio strategy. Whether to get a new card, which card to apply for, welcome bonus ROI math, issuer application gating rules (Chase 5/24, Amex once-per-lifetime and pop-up jail, Citi 48-month, Capital One inquiry sensitivity), annual fee breakeven, keep/downgrade/cancel decisions, retention offers, and two-player household sequencing. Triggers on "should I get a card", "new card", "apply for", "welcome bonus", "sign-up bonus", "SUB", "annual fee worth it", "5/24", "downgrade", "product change", "cancel my card", "retention offer", "keep or cancel".
category: loyalty
summary: Card acquisition thinking partner. Welcome-bonus ROI math, issuer gating rules (5/24, once-per-lifetime, 48-month), fee breakeven on honestly-used credits, keep/downgrade/cancel tree, 2-player sequencing.
---

# Card Strategy (Acquisition & Portfolio)

`best-card-for-spend` answers "which card do I swipe?" This skill answers the
slower questions: **which card should I get next, is this annual fee still earning
its keep, and how do two players sequence applications?** Welcome bonuses are the
single largest source of points for most people — a typical 60-100K bonus dwarfs a
year of category earning — so acquisition strategy usually matters more than swipe
optimization.

## The Acquisition Decision Sequence

Run in order; each step can kill or reshape the application.

1. **Start from the redemption, not the card.** What trip is this funding, in
   which program, at what cpp? A bonus in a currency the user can't spend well is
   a small bonus. Check earmarks first (the user's memory/notes may already
   reserve currencies for planned trips — don't recommend a card whose bonus
   duplicates a currency they're already rich in, unless that's the point).
2. **Check issuer gating BEFORE falling in love with a bonus** (table below).
   An application that will be denied, or that torches a future better bonus,
   is worse than no application.
3. **Verify the CURRENT bonus live.** Bonuses are elevated and cut constantly.
   Sources: awardtravelfinder MCP `cards_rank_welcome_bonuses` + `cards_list_changes`,
   then FrequentMiler / the issuer's own application page for anything the DB
   might lag on. Also check for elevated/targeted offers (referral links,
   CardMatch, in-branch, "apply via incognito") — the public offer is the floor,
   not the ceiling. State the as-of date.
4. **Run the ROI math** (below). If min-spend doesn't fit organic spending in the
   window, stop — manufactured urgency to hit a spend target destroys the value.
5. **Sequence for the household (2-player mode).** Player 1 refers Player 2
   (referral bonus + second welcome bonus on the same product), or the players
   alternate issuers to stay under gating limits. One player can hold the premium
   card while the other holds the no-fee sibling.
6. **Plan the exit before applying.** Know today what year 2 looks like: keep
   (credits clear the fee), downgrade path (which no-fee sibling preserves the
   credit line and history), or cancel (only after 12 months; earlier risks
   clawback and issuer relationships).

## Issuer Gating Rules

These change; treat this table as the checklist of WHAT to verify, and confirm
current rules live (FrequentMiler/Doctor of Credit) before advising. As of 2026-07:

| Issuer | Rule to check | Practical effect |
|--------|---------------|------------------|
| Chase | 5/24: ~5+ personal cards opened across ALL issuers in 24 months → auto-deny | Get Chase cards FIRST in any application sequence. Most business cards don't add to the count but are blocked by it. |
| Amex | Once-per-lifetime bonus per product; "family rules" (e.g., holding/having had a Platinum can block Gold-family bonuses — direction matters); pop-up jail warns pre-submission | Never apply if the pop-up says no bonus — withdraw. Order within a family: lower tier before higher when bonuses matter. |
| Citi | 48-month clock between bonuses on some products/families | Check the specific card's terms language. |
| Capital One | Pulls all 3 bureaus; unusually velocity/profile-sensitive; ~1 card per 6 months | Denials common even with high scores; don't burn an inquiry casually. |
| All | 2+ applications same day, business card EIN/sole-prop questions, credit line reallocation options | Verify per issuer at decision time. |

## Welcome Bonus ROI

```
ROI = bonus_points × floor_cpp            (points-valuations floor, not TPG headline)
    + first_year_category_earn_delta      (vs. the card the spend would otherwise hit)
    + credits_honestly_used               (only ones you'd buy anyway — see below)
    − annual_fee
    − min_spend_opportunity_cost          (what that spend earned on your best existing card)
```

- **Credits count only at honest value.** A $300 travel credit you'd naturally
  spend = $300. A $20/month streaming credit for a service you don't want = $0.
  Do NOT let issuer marketing math ("$1,500 in value!") into the comparison.
- **The bonus is one-time; the fee is annual.** Evaluate year 1 (with bonus) and
  steady-state year 2 (without) separately. A card can be a clear yes for year 1
  and a clear downgrade at month 13 — say both.
- **Compare against the best alternative application,** not against nothing.
  The real question is which bonus this application slot buys.

## Keep / Downgrade / Cancel (at each renewal)

1. Fee posted? You have ~30 days to decide with a full refund window (verify per issuer).
2. **Ask for a retention offer first** — a phone call/chat costs nothing and
   frequently pays 20-40% of the fee in points or credits. Take it if it flips the math.
3. Steady-state math (ROI formula minus bonus) positive → keep.
4. Negative but the credit line/age matters, or it's a transfer-currency keystone
   (e.g., the only card keeping MR points alive) → **downgrade, don't cancel.**
   Cancelling the last card in a currency FORFEITS the points — check this every time.
5. Cancel only when downgraded value is also zero and the points are safe.

## What This Skill Does NOT Cover

- Which existing card to swipe → `best-card-for-spend`.
- Whether a specific redemption is good → `points-valuations`, `award-sweet-spots`.
- Live card data: use awardtravelfinder MCP `cards_list_cards`, `get_card`,
  `cards_compare_cards`, `cards_find_cards_for_category`, `cards_analyze_spending`.
- The user's holdings and earmarks: `data/my-cards.local.json` + `CLAUDE.local.md`
  + session memory. Always reconcile advice against what they already hold.

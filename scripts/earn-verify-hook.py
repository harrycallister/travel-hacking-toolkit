#!/usr/bin/env python3
"""earn-verify-hook.py — UserPromptSubmit hook for the best-card-for-spend skill.

Fires on every user prompt. If the prompt looks like an earn-side / spend / booking
question, it injects a MANDATORY verification checklist into the agent's context
BEFORE the agent answers — so the "verify live every time" rule is enforced
automatically, not left to the skill loading or the agent remembering.

It does NOT do the live lookups itself (a shell hook can't hit the web/MCP). It
makes the requirement unmissable and lists exactly which cards are stale/unverified.

Hook I/O: reads the UserPromptSubmit JSON on stdin ({"prompt": "...", ...}).
On a match, prints the mandate to stdout (added to context). On no match or any
error, exits 0 silently so normal prompts are never disrupted.
"""
import datetime
import json
import os
import re
import sys

# Intent keywords. Kept tight so only genuinely relevant prompts trigger the mandate.
TRIGGER = re.compile(
    r"\b("
    r"which card|best card|what card|card to (use|swipe)|should i (use|pay|swipe)|"
    r"swipe|earn(ing)?|points on|cash ?back|maximi[sz]e|"
    r"rakuten|shopping portal|portal|"
    r"promo|amex offer|chase offer|capital one offer|card[- ]linked|"
    r"book(ing)?\s+(a\s+)?(hotel|flight|stay|room)|pay (with|for)|redeem"
    r")\b",
    re.IGNORECASE,
)

PROJECT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLET = os.path.join(PROJECT, "data", "my-cards.local.json")


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def stale_cards(wallet):
    """Names of cards that are unverified or aged past reverify_after_days."""
    if not wallet:
        return []
    threshold = wallet.get("_meta", {}).get("reverify_after_days", 7)
    today = datetime.date.today()
    out = []
    for card in wallet.get("cards", []):
        name = card.get("name", "?")
        if not card.get("verified", False):
            out.append(f"{name} (never independently verified)")
            continue
        lv = card.get("last_verified")
        try:
            age = (today - datetime.date.fromisoformat(lv)).days
            if age > threshold:
                out.append(f"{name} (verified {age}d ago, stale)")
        except Exception:
            out.append(f"{name} (no valid verify date)")
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # not parseable; never disrupt the prompt
    prompt = data.get("prompt", "") if isinstance(data, dict) else ""
    if not prompt or not TRIGGER.search(prompt):
        return  # not an earn/spend/booking prompt → stay silent

    stale = stale_cards(load(WALLET))
    lines = [
        "[best-card-for-spend ENFORCEMENT] This prompt involves card earnings, a "
        "shopping portal, a promo, or a booking. Before giving any recommendation you "
        "MUST complete all three live checks — do not trust stored numbers:",
        "  1. CARD RATES — verify the contending card's CURRENT multipliers for the "
        "asked category (awardtravelfinder MCP / issuer page / FrequentMiler). Update "
        "data/my-cards.local.json if they changed.",
        "  2. SHOPPING PORTALS — for any online purchase, look up the live per-merchant "
        "rate at cashbackmonitor.com / evreward.com and stack the best-VALUE one "
        "(a lower % into MR can beat higher % cash).",
        "  3. PROMOS — for hotel/airline spend, check the chain/airline promo page and "
        "the card-linked offers (Amex/Chase/Cap One); register BEFORE booking.",
        "State the as-of date in your answer. The script's math is only as fresh as "
        "these checks.",
    ]
    if stale:
        lines.append("Cards needing verification RIGHT NOW: " + "; ".join(stale) + ".")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

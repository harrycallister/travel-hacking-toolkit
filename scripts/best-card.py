#!/usr/bin/env python3
"""best-card.py — Earn-side optimizer for the travel-hacking-toolkit.

Given a spending category (or a merchant), rank the cards in your wallet by the
REAL value they return — points earned per dollar times what those points are
worth (cents-per-point) — not by raw multiplier. A 4x card in a 0.6cpp currency
loses to a 2x card in a 1.7cpp currency, and this surfaces that.

Data sources (read-only):
  data/my-cards.local.json     your wallet (gitignored)
  data/points-valuations.json  cpp floors/ceilings per program

Usage:
  python3 scripts/best-card.py dining
  python3 scripts/best-card.py groceries --amount 250
  python3 scripts/best-card.py --merchant "Whole Foods" --amount 180
  python3 scripts/best-card.py travel --mode ceiling
  python3 scripts/best-card.py --table          # full earn matrix
  python3 scripts/best-card.py --list-categories
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WALLET_PATH = os.path.join(ROOT, "data", "my-cards.local.json")
VALUATIONS_PATH = os.path.join(ROOT, "data", "points-valuations.json")
STACK_PATH = os.path.join(ROOT, "data", "earn-stack.local.json")

CATEGORIES = [
    "dining", "groceries", "gas", "transit", "travel", "flights",
    "hotels", "vacation_rentals", "streaming", "online_retail",
    "drugstores", "entertainment", "other",
]

# Lightweight merchant -> category hints. Substring match, case-insensitive.
# This is a convenience only; the skill does smarter merchant classification.
MERCHANT_HINTS = {
    "dining": ["restaurant", "cafe", "coffee", "starbucks", "doordash",
               "uber eats", "grubhub", "mcdonald", "chipotle", "bar ", "grill"],
    "groceries": ["whole foods", "trader joe", "safeway", "kroger", "publix",
                  "albertsons", "wegmans", "supermarket", "grocery", "aldi"],
    "gas": ["shell", "chevron", "exxon", "bp ", "mobil", "texaco", "gas station",
            "76 ", "arco", "costco gas"],
    "transit": ["uber", "lyft", "metro", "subway transit", "transit", "parking",
                "toll", "amtrak", "caltrain"],
    "flights": ["airline", "airlines", "delta", "united", "american air",
                "southwest", "jetblue", "alaska air", "flight"],
    "hotels": ["marriott", "hilton", "hyatt", "ihg", "holiday inn", "westin",
               "sheraton", "ritz", "hotel", "motel", "inn "],
    "vacation_rentals": ["airbnb", "vrbo", "vacation home", "vacation rental"],
    "streaming": ["netflix", "spotify", "hulu", "disney+", "hbo", "max ",
                  "youtube premium", "apple music", "peacock", "paramount+"],
    "online_retail": ["amazon", "ebay", "etsy", "walmart.com", "target.com"],
    "drugstores": ["cvs", "walgreens", "rite aid", "pharmacy", "drugstore"],
    "entertainment": ["ticketmaster", "stubhub", "cinema", "movie", "theater",
                      "concert", "amc "],
    "travel": ["expedia", "booking.com", "rental car", "hertz", "avis",
               "enterprise", "cruise"],
}


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        sys.exit(f"ERROR: missing data file: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_cpp_lookup(valuations: dict) -> dict:
    """Flatten all valuation sections into {program_key: {floor, ceiling, name}}."""
    lookup = {}
    for section in ("credit_card_points", "airline_miles", "hotel_points"):
        for key, entry in valuations.get(section, {}).items():
            lookup[key] = {
                "floor": entry.get("floor"),
                "ceiling": entry.get("ceiling"),
                "name": entry.get("name", key),
            }
    return lookup


def staleness_days(last_verified: str | None) -> int | None:
    """Days since a card's earn rates were last verified. None if no/invalid date."""
    if not last_verified:
        return None
    try:
        d = datetime.date.fromisoformat(last_verified)
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def freshness_flags(wallet: dict) -> list[str]:
    """Human-readable warnings about cards whose rates need live re-verification."""
    threshold = wallet.get("_meta", {}).get("reverify_after_days", 7)
    out = []
    for card in wallet.get("cards", []):
        name = card.get("name", "?")
        age = staleness_days(card.get("last_verified"))
        if not card.get("verified", False):
            out.append(f"{name}: NOT independently verified "
                       f"({card.get('verified_source', 'source unknown')})")
        elif age is not None and age > threshold:
            out.append(f"{name}: last verified {age} days ago "
                       f"(> {threshold}d) — re-check current rates")
    return out


def cpp_for(currency: str, cpp: dict, mode: str) -> float | None:
    """Cents-per-point for a currency. 'cash' is a flat 1.0¢; else from valuations."""
    if currency == "cash":
        return 1.0
    return cpp.get(currency, {}).get(mode)


def load_stack() -> dict:
    """Load the booster registry; return empty structure if the file is absent."""
    if not os.path.exists(STACK_PATH):
        return {"shopping_portals": [], "promo_sources": [], "active_promos": []}
    with open(STACK_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def print_portals(stack: dict) -> None:
    portals = stack.get("shopping_portals", [])
    src = stack.get("_meta", {}).get("live_lookup_sources", {}).get("portal_aggregators", [])
    print("\nShopping portals (stack ON TOP of the card swipe):\n")
    print("| Portal | Pays in | Look up live at | Note |")
    print("|---|---|---|---|")
    for p in portals:
        print(f"| {p.get('name','?')} | {p.get('pays_in','?')} | {p.get('check_url','?')} "
              f"| {p.get('conversion', p.get('notes',''))} |")
    if src:
        print(f"\n⮕ Before any online buy, compare ALL portals for the merchant at: {', '.join(src)}")


def print_promos(stack: dict) -> None:
    promos = stack.get("promo_sources", [])
    print("\nPromo sources to check live before travel/online spend:\n")
    print("| Program | Type | Check at | Note |")
    print("|---|---|---|---|")
    for p in promos:
        print(f"| {p.get('program','?')} | {p.get('type','?')} | {p.get('check_url','?')} "
              f"| {p.get('notes','')} |")
    active = stack.get("active_promos", [])
    if active:
        print(f"\nRegistered active promos: {len(active)} (see data/earn-stack.local.json)")
    else:
        print("\nNo registered active promos tracked. Check the sources above — promos are "
              "time-boxed and usually need registration before the stay/purchase.")


def classify_merchant(merchant: str) -> str | None:
    m = merchant.lower()
    for category, needles in MERCHANT_HINTS.items():
        if any(n in m for n in needles):
            return category
    return None


def rank_cards(category: str, wallet: dict, cpp: dict, mode: str) -> list[dict]:
    rows = []
    for card in wallet.get("cards", []):
        earn = card.get("earn", {})
        base = earn.get("other", 1)
        multiplier = earn.get(category, base)
        is_bonus = category in earn and category != "other"
        program = card.get("points_program")
        val = cpp.get(program, {})
        cents_per_point = val.get(mode)
        if cents_per_point is None:
            value_per_dollar = None
        else:
            value_per_dollar = multiplier * cents_per_point
        cap = card.get("caps", {}).get(category)
        rows.append({
            "card": card.get("name", "?"),
            "program": val.get("name", program),
            "multiplier": multiplier,
            "is_bonus": is_bonus,
            "cpp": cents_per_point,
            "value_per_dollar": value_per_dollar,
            "cap": cap,
            "unverified": not card.get("verified", False),
        })
    # Sort: known value first (desc), unknown-value cards last, tiebreak multiplier.
    rows.sort(
        key=lambda r: (
            r["value_per_dollar"] if r["value_per_dollar"] is not None else -1,
            r["multiplier"],
        ),
        reverse=True,
    )
    return rows


def fmt_cents(x) -> str:
    return f"{x:.2f}¢" if isinstance(x, (int, float)) else "—"


def print_ranking(category: str, rows: list[dict], amount: float | None, mode: str) -> None:
    print(f"\nBest card for **{category}** spend (value-first, {mode} cpp):\n")
    header = ["#", "Card", "Earn", "Currency", "cpp", "Value back / $"]
    if amount:
        header += [f"Pts on ${amount:g}", f"Value on ${amount:g}"]
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["---"] * len(header)) + "|")
    for i, r in enumerate(rows, 1):
        earn_lbl = f"{r['multiplier']:g}x" + ("" if r["is_bonus"] else " (base)")
        vpd = fmt_cents(r["value_per_dollar"]) if r["value_per_dollar"] is not None else "?"
        card_lbl = r["card"] + (" ⚠" if r["unverified"] else "")
        cols = [str(i), card_lbl, earn_lbl, r["program"],
                fmt_cents(r["cpp"]), vpd]
        if amount:
            pts = r["multiplier"] * amount
            if r["value_per_dollar"] is not None:
                dollars = r["value_per_dollar"] / 100 * amount
                cols += [f"{pts:,.0f}", f"${dollars:,.2f}"]
            else:
                cols += [f"{pts:,.0f}", "?"]
        print("| " + " | ".join(cols) + " |")

    winner = next((r for r in rows if r["value_per_dollar"] is not None), None)
    if winner:
        line = f"\n→ Use **{winner['card']}**: {winner['multiplier']:g}x {winner['program']} "
        line += f"= {fmt_cents(winner['value_per_dollar'])} back per dollar"
        if amount:
            line += f" (${winner['value_per_dollar']/100*amount:,.2f} on ${amount:g})"
        line += "."
        print(line)
        if winner["cap"]:
            print(f"  ⚠ Cap: {winner['cap']}")
    if any(r["unverified"] for r in rows):
        print("\n⚠ = earn rates not independently verified this session "
              "(see data/my-cards.local.json).")


def print_stack(rows: list[dict], portal_pct: float, portal_currency: str,
                portal_name: str | None, cpp: dict, mode: str,
                amount: float | None) -> None:
    """Show the best card swipe stacked with a live shopping-portal rate."""
    card = next((r for r in rows if r["value_per_dollar"] is not None), None)
    portal_cpp = cpp_for(portal_currency, cpp, mode)
    if portal_cpp is None:
        print(f"\n⚠ Unknown portal currency '{portal_currency}' — can't value the stack.")
        return
    portal_vpd = portal_pct * portal_cpp  # pct points/$ × cents-per-point
    card_vpd = card["value_per_dollar"] if card else 0.0
    total = card_vpd + portal_vpd
    label = portal_name or f"portal ({portal_currency})"

    print("\n--- Stacked with shopping portal ---")
    print(f"| Layer | Detail | Value back / $ |")
    print(f"|---|---|---|")
    if card:
        print(f"| Card swipe | {card['card']} {card['multiplier']:g}x {card['program']} "
              f"| {fmt_cents(card_vpd)} |")
    print(f"| {label} | {portal_pct:g}% → {portal_currency} @ {fmt_cents(portal_cpp)} "
          f"| {fmt_cents(portal_vpd)} |")
    print(f"| **Stacked total** | | **{fmt_cents(total)}** |")
    if amount:
        print(f"\n→ On ${amount:g}: ${total/100*amount:,.2f} back "
              f"(card ${card_vpd/100*amount:,.2f} + portal ${portal_vpd/100*amount:,.2f}).")
    else:
        print(f"\n→ {fmt_cents(total)} back per dollar combined.")
    print("⮕ Portal rate is LIVE/per-merchant — confirm the current % at "
          "cashbackmonitor.com or evreward.com before buying.")


def print_table(wallet: dict, cpp: dict, mode: str) -> None:
    """Full earn matrix: every card x every category, as value back per dollar."""
    cards = wallet.get("cards", [])
    print(f"\nValue back per dollar (¢), {mode} cpp — best per row in **bold** isn't"
          " marked in plaintext; scan columns:\n")
    header = ["Card \\ Category"] + CATEGORIES
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["---"] * len(header)) + "|")
    for card in cards:
        earn = card.get("earn", {})
        base = earn.get("other", 1)
        val = cpp.get(card.get("points_program"), {})
        c = val.get(mode)
        cells = [card.get("name", "?") + (" ⚠" if not card.get("verified", False) else "")]
        for cat in CATEGORIES:
            mult = earn.get(cat, base)
            cells.append(fmt_cents(mult * c) if c is not None else "?")
        print("| " + " | ".join(cells) + " |")


def main() -> None:
    p = argparse.ArgumentParser(description="Rank wallet cards by value returned on a spend category.")
    p.add_argument("category", nargs="?", help="Spending category (see --list-categories).")
    p.add_argument("--merchant", help="Merchant name; inferred to a category.")
    p.add_argument("--amount", type=float, help="Spend amount in dollars.")
    p.add_argument("--mode", choices=["floor", "ceiling"], default="floor",
                   help="Valuation mode (default: floor, conservative).")
    p.add_argument("--table", action="store_true", help="Print full earn matrix and exit.")
    p.add_argument("--list-categories", action="store_true", help="List valid categories and exit.")
    p.add_argument("--json", action="store_true",
                   help="Emit ranking + freshness as JSON (for the agent's verify step).")
    p.add_argument("--portals", action="store_true", help="List shopping portals and exit.")
    p.add_argument("--promos", action="store_true", help="List promo sources and exit.")
    p.add_argument("--portal-pct", type=float,
                   help="Live portal rate (e.g. 8 for 8%%) to stack on the winning card.")
    p.add_argument("--portal-currency", default="cash",
                   help="Currency the portal pays (valuation key, or 'cash'). Default: cash.")
    p.add_argument("--portal-name", help="Portal name for display (e.g. Rakuten).")
    args = p.parse_args()

    if args.list_categories:
        print("Categories:", ", ".join(CATEGORIES))
        return

    if args.portals or args.promos:
        stack = load_stack()
        if args.portals:
            print_portals(stack)
        if args.promos:
            print_promos(stack)
        return

    wallet = load_json(WALLET_PATH)
    cpp = build_cpp_lookup(load_json(VALUATIONS_PATH))
    flags = freshness_flags(wallet)

    if args.table:
        print_table(wallet, cpp, args.mode)
        if flags:
            print("\nRe-verify before trusting:\n  - " + "\n  - ".join(flags))
        return

    category = args.category
    if args.merchant:
        inferred = classify_merchant(args.merchant)
        if inferred:
            print(f"Merchant '{args.merchant}' → category '{inferred}'.")
            category = inferred
        else:
            sys.exit(f"Could not classify merchant '{args.merchant}'. "
                     f"Pass a category explicitly (see --list-categories).")

    if not category:
        sys.exit("Provide a category or --merchant. See --list-categories or --help.")
    if category not in CATEGORIES:
        sys.exit(f"Unknown category '{category}'. Valid: {', '.join(CATEGORIES)}")

    rows = rank_cards(category, wallet, cpp, args.mode)

    if args.json:
        print(json.dumps({
            "category": category,
            "mode": args.mode,
            "ranking": rows,
            "reverify": flags,
        }, indent=2))
        return

    print_ranking(category, rows, args.amount, args.mode)
    if args.portal_pct is not None:
        print_stack(rows, args.portal_pct, args.portal_currency, args.portal_name,
                    cpp, args.mode, args.amount)
    if flags:
        print("\nRe-verify current rates before trusting (run a live check on these):")
        for f in flags:
            print(f"  - {f}")


if __name__ == "__main__":
    main()

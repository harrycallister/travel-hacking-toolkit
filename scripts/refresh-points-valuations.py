#!/usr/bin/env python3
"""Refresh data/points-valuations.json from the cited publications.

Scrapes the four sources named in the file's _meta (The Points Guy, Upgraded
Points, One Mile at a Time, View From The Wing) and updates each program's
per-source cents-per-point (cpp) value, then recomputes floor (min) and
ceiling (max) across sources.

Hard rules (Research Integrity Protocol — same as refresh-transfer-bonuses.py):
- NEVER fabricate a value. A number is only written if it appears next to a
  "cents"/"¢" token immediately after the program's name on the source page.
- The program list and display names are NEVER invented — we only update cpp
  values for programs already in the file. New programs are not added.
- If a source yields fewer than MIN_MATCHES plausible values, it's treated as a
  parse failure and that source is left untouched (its layout likely changed).
- If NO source parses, the script exits nonzero and writes nothing.
- _meta methodology text and the program structure are preserved.

Usage:
    python3 scripts/refresh-points-valuations.py            # update the file
    python3 scripts/refresh-points-valuations.py --dry-run  # show changes, write nothing
    python3 scripts/refresh-points-valuations.py --verbose  # per-program log
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "points-valuations.json"
CATEGORIES = ("airline_miles", "credit_card_points", "hotel_points")
CPP_MIN, CPP_MAX = 0.3, 3.0          # sane cpp band; values outside are rejected
MIN_MATCHES = 5                      # below this, a source is considered unparseable
WINDOW = 70                          # chars after a program name to scan for a value

# Words too generic to anchor on — stripped when deriving a program's search key.
STOPWORDS = {
    "the", "rewards", "miles", "points", "program", "airlines", "airways",
    "air", "club", "plus", "bonus", "frequent", "flyer", "mileage", "loyalty",
    "card", "credit", "express", "american", "and", "&", "rewards.",
}

# Tokens that LOOK distinctive but match the wrong program's text (e.g. "one"
# hits "Capital One"/"One Mile", "america" hits "American Express"). A program
# whose only tokens are ambiguous is skipped rather than mis-matched — add a
# precise multi-word entry to ALIASES if it must be covered.
AMBIGUOUS = {
    "one", "america", "preferred", "bank", "world", "group", "global", "value",
}

# A few programs whose distinctive token isn't obvious from the name.
ALIASES = {
    "amex_membership_rewards": ["membership rewards"],
    "chase_ultimate_rewards": ["ultimate rewards"],
    "citi_thankyou": ["thankyou", "thank you"],
    "capital_one": ["capital one"],
    "bilt": ["bilt"],
    "marriott_bonvoy": ["bonvoy"],
    "delta_skymiles": ["skymiles"],
    "aeroplan": ["aeroplan"],
    "flying_blue": ["flying blue"],
    "virgin_atlantic": ["virgin atlantic", "flying club"],
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print(f"  fetch failed: {e}", file=sys.stderr)
        return None


def strip_html(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = (text.replace("&amp;", "&").replace("&nbsp;", " ")
                .replace("&#162;", "¢").replace("&cent;", "¢"))
    return re.sub(r"\s+", " ", text).lower()


def keywords(key, name):
    if key in ALIASES:
        return ALIASES[key]
    toks = re.split(r"[^a-z0-9]+", name.lower())
    sig = [t for t in toks
           if t and t not in STOPWORDS and t not in AMBIGUOUS and len(t) > 2]
    # Prefer the longest distinctive token (e.g. "aeroplan", "bonvoy", "aegean").
    sig.sort(key=len, reverse=True)
    return sig[:2] if sig else [key.replace("_", " ")]


def find_cpp(text, keys):
    """Return a cpp float only if a value with a cents/¢ token sits just after
    the program name. Requiring the unit is what prevents grabbing stray numbers."""
    for kw in keys:
        for m in re.finditer(re.escape(kw), text):
            window = text[m.end(): m.end() + WINDOW]
            vm = re.search(r"(\d+(?:\.\d+)?)\s*(?:¢|cents?\b|cpp\b)", window)
            if vm:
                try:
                    v = float(vm.group(1))
                except ValueError:
                    continue
                if CPP_MIN <= v <= CPP_MAX:
                    return v
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    data = json.loads(DATA.read_text())
    sources = data["_meta"]["sources"]

    # 1) Scrape each source into {source: {category: {key: cpp}}}
    scraped, good_sources = {}, []
    for src, meta in sources.items():
        url = meta.get("url")
        print(f"[{src}] {url}")
        html = fetch(url) if url else None
        if not html:
            print(f"  -> skipped (no fetch)")
            continue
        text = strip_html(html)
        found = {c: {} for c in CATEGORIES}
        for cat in CATEGORIES:
            for key, prog in data[cat].items():
                v = find_cpp(text, keywords(key, prog["name"]))
                if v is not None:
                    found[cat][key] = v
                    if args.verbose:
                        print(f"    {cat}/{key}: {v}")
        n = sum(len(found[c]) for c in CATEGORIES)
        if n < MIN_MATCHES:
            print(f"  -> only {n} matches; treating layout as unparseable, leaving {src} untouched")
            continue
        print(f"  -> {n} values parsed")
        scraped[src] = found
        good_sources.append(src)

    if not good_sources:
        print("\nNo source parsed cleanly. Writing nothing (fail-closed).", file=sys.stderr)
        return 1

    # 2) Apply: update per-source values, recompute floor/ceiling. Never invent.
    changes = 0
    for cat in CATEGORIES:
        for key, prog in data[cat].items():
            srcvals = dict(prog.get("sources", {}))
            for src in good_sources:
                v = scraped[src][cat].get(key)
                if v is not None and srcvals.get(src) != v:
                    srcvals[src] = v
                    changes += 1
            if srcvals:
                prog["sources"] = srcvals
                prog["floor"] = min(srcvals.values())
                prog["ceiling"] = max(srcvals.values())

    # 3) Stamp metadata for the sources we actually refreshed.
    today = date.today().isoformat()
    edition = date.today().strftime("%B %Y")
    for src in good_sources:
        sources[src]["edition"] = edition
    data["_meta"]["last_updated"] = today

    print(f"\nSources refreshed: {', '.join(good_sources)}")
    print(f"Per-source value changes: {changes}")

    if args.dry_run:
        print("[dry-run] no file written.")
        return 0

    DATA.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote {DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

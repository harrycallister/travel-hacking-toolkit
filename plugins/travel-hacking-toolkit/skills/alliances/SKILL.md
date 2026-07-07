---
name: alliances
description: Airline alliance membership (Star Alliance, oneworld, SkyTeam) and cross-alliance booking relationships. Maps which loyalty programs book which airlines, including bilateral partnerships outside alliances.
category: reference
summary: Star Alliance, oneworld, SkyTeam membership and recent shifts (SAS to SkyTeam, ITA to Star, Hawaiian/Fiji to oneworld). Key cross-alliance booking relationships.
---

# Alliance Awareness

**Reference data:** `data/alliances.json`

Star Alliance, oneworld, and SkyTeam determine which loyalty programs can book which airlines. This is fundamental to award travel. When recommending an award booking, always verify the airline and the booking program are in the same alliance (or have a bilateral partnership).

## Key Booking Relationships

- **United MileagePlus** books Star Alliance (ANA, Lufthansa, Singapore, Turkish, etc.)
- **Aeroplan** books Star Alliance plus extended partners (including Etihad, Emirates on some routes)
- **Virgin Atlantic Flying Club** books ANA, Delta, Air France, KLM (cross-alliance)
- **AAdvantage** books oneworld (Cathay, JAL, Qantas, Qatar, BA, etc.)
- **Flying Blue** books SkyTeam (Air France, KLM, Delta, Korean Air, etc.)
- **Korean Air SKYPASS** books SkyTeam
- **Avianca LifeMiles** books Star Alliance (often cheaper than United/Aeroplan)

## Recent Alliance Changes

Verify against `data/alliances.json` for current state. These have shifted recently:

- SAS moved from Star Alliance to SkyTeam (September 2024)
- ITA Airways joined Star Alliance April 1, 2026 (left SkyTeam early 2025; its Volare program ended — ITA now uses Lufthansa Miles & More)
- Fiji Airways upgraded to full oneworld member (2025)
- Hawaiian Airlines joined oneworld April 2026 (loyalty = Atmos Rewards, shared with Alaska)
- Asiana exits Star Alliance December 16, 2026, then folds into Korean Air (SkyTeam). Don't book Asiana Club redemptions with travel past that date without checking current guidance.

## Cross-Alliance Bookings Are Where Real Value Hides

The best redemptions often involve booking an airline through a program in a DIFFERENT alliance (or no alliance at all). Always check the `cross_alliance_highlights` section of `data/alliances.json` and `data/partner-awards.json`.

Examples of cross-alliance plays:
- Virgin Atlantic Flying Club books ANA First Class (legendary sweet spot)
- Etihad Guest books AAdvantage routes
- Alaska Atmos Rewards (formerly Mileage Plan) books Starlux (independent airline)

## Partner Awards Reference

For the full picture of which programs ticket which airlines, plus bilateral partnerships outside alliances, load the `partner-awards` skill or read `data/partner-awards.json` directly.

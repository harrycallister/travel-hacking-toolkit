# Development Guide

How this toolkit is built, the conventions that hold it together, and how to reason
about changes. Written for a future session — possibly on a smaller model — so the
thinking is spelled out, not just the facts. Read this before modifying skills,
data, scripts, or CLAUDE.md.

## What this repo actually is

There is no application here. The "stack" is **prompt-ware**:

| Layer | Location | What it is |
|-------|----------|------------|
| Runtime agent prompt | `CLAUDE.md` | The product. Loaded by Claude Code at session start. Defines the agent's mindset, proactive behaviors, and output format. |
| Agent mirror | `agents/travel-hacker.md` | Byte-for-byte copy of CLAUDE.md with plugin frontmatter. Regenerate with `bash scripts/sync-agent.sh` after ANY CLAUDE.md edit — the smoke test fails on drift. |
| Skills | `plugins/travel-hacking-toolkit/skills/*/SKILL.md` | On-demand knowledge modules. Top-level `skills/` is a **symlink** to this dir — never create files in both. |
| Reference data | `data/*.json` | Cached facts with freshness metadata. The agent reads these instead of re-deriving stable facts. |
| Personal overlay | `CLAUDE.local.md`, `data/*.local.json` | The user's preferences, wallet, boosters. **Gitignored.** Never commit, never hardcode their contents into shared files. |
| Scripts | `scripts/` | Deterministic math (`best-card.py`), scrapers (`refresh-*.py`), infrastructure (`smoke-test.sh`, `gen-skill-tables.sh`, `sync-agent.sh`). |
| Hooks | registered in `.claude/settings.local.json` (gitignored) | `freshness-autocheck.sh` (SessionStart), `earn-verify-hook.py` (UserPromptSubmit). Enforce what prompts alone can't. |
| MCP servers | `.mcp.json`, plugin `.mcp.json` | Live search: Skiplagged, Kiwi, Trivago, Ferryhopper, Airbnb (keyless); LiteAPI (keyed). |
| Generated docs | `README.md` tables, `llms.txt` | Auto-generated from skill frontmatter by `bash scripts/gen-skill-tables.sh`. Never hand-edit between the BEGIN/END markers. |

## The design principles (why things are the way they are)

**1. Every stored number is a cache; reality is the source of truth.**
Loyalty data rots fast — transfer bonuses die on month-end dates, card categories
change overnight, partnerships end. Any skill that stores a number MUST also state
when and how to re-verify it live. Case study: on 2026-07-07 the transfer-bonuses
file listed 5 bonuses as active that had expired a week earlier, and Bilt→American
was still listed 1:1 two years after that partnership ended. The fix pattern
(see below) is the most important convention in the repo.

**2. Deterministic math lives in scripts, judgment lives in skills.**
`best-card.py` computes multiplier × cpp; the SKILL.md tells the agent when to
trust it, what to verify first, and how to present it. Never make a skill
"recompute by hand" what a script does; never bury judgment calls inside a script.

**3. Fail closed on data, fail open on UX.**
Refresh scripts NEVER fabricate: a value is written only when parsed next to an
explicit unit token, sources below a match threshold are skipped, and if nothing
parses the script exits nonzero and writes nothing (the "Research Integrity
Protocol"). But the *agent* degrades gracefully: a missing API key silently drops
that source and continues — never interrogate the user about keys.

**4. Enforcement beats instruction.**
If a rule matters, encode it three times: in the data (`_meta` staleness fields),
in the skill (a mandatory gate step), and in `smoke-test.sh` (a regression check
that fails loudly). Prompts get ignored under context pressure; tests don't.

**5. Confidence is explicit.**
Data entries carry `VERIFIED` / `LIKELY` / `UNVERIFIED` markers and source
attribution. When you add a fact you couldn't fully confirm, mark it — don't
launder uncertainty into confident-looking JSON.

## Conventions

### Data files
- Every `data/*.json` has `_meta` with `last_updated` (ISO date), `staleness_days`
  (TTL), and `notes`. `scripts/check-data-freshness.sh` reports TTL violations;
  the smoke test fails on them.
- When you correct a fact, bump `last_updated` and record WHAT you verified in
  `_meta.notes` with the date — future sessions need to know what "updated" covered.
- Time-bounded facts (a bonus's end date, an alliance exit) belong in the data with
  the date, plus a note telling the agent what to do when the date passes.
- `*.local.json` = personal, gitignored. Committed data must work for any user.

### Skills
- Frontmatter needs `name`, `description` (rich with literal trigger phrases —
  this is how auto-loading works), `category`, `summary` (used in generated tables).
- After adding/renaming a skill or editing its summary: `bash scripts/gen-skill-tables.sh`
  to regenerate README.md and llms.txt, or the drift check fails.
- Write skills as ordered decision sequences ("run these steps in order, each can
  end the analysis"), not essays. A smaller model executes numbered gates reliably;
  it improvises badly from prose.
- Negative knowledge is as valuable as positive: "these programs do NOT allow
  stopovers", "Bilt no longer transfers to American". State it explicitly so the
  agent doesn't hallucinate the happy path.
- If a skill must fire proactively (not just on request), it also needs a trigger
  line in CLAUDE.md's "Proactive Behaviors" — skills auto-load on topic, but
  CLAUDE.md drives the always-do-this workflows.

### CLAUDE.md itself
- It's the runtime prompt: keep it under 40k chars (smoke test enforces; ~18.7k
  now). Deep knowledge goes in skills; CLAUDE.md holds orientation + proactive
  triggers + pointers.
- Starts with YAML frontmatter (required by the agent mirror). After any edit:
  `bash scripts/sync-agent.sh`, then commit both files together.

### Scripts
- Python: stdlib only (no pip deps anywhere in the repo). Bash: must pass `bash -n`;
  remember macOS has no `timeout` binary (smoke-test.sh has a shim — reuse it).
- Anything touching the network bounds its time and never blocks session start.

## How to think through a change (worked example)

The 2026-07-07 expired-bonus incident, as a template:

1. **Symptom:** transfer-bonuses.json listed expired bonuses as active.
2. **Ask why it was POSSIBLE, not just what's wrong.** Root causes: (a) snapshot
   data with no expiry check at read time, (b) refresh script existed but nothing
   ensured it ran, (c) no test asserting the invariant "active means not expired."
3. **Fix at every layer, not just the data:** refreshed the file (data), added a
   mandatory expiry gate to the skill (behavior), added a smoke-test check that
   fails on any past-dated active bonus (enforcement).
4. **Record the lesson where the next agent will trip over it:** the skill's gate
   section cites the incident and date, so the rule reads as earned, not arbitrary.

Apply the same shape to any bug: patch the instance, then ask which convention or
check would have caught the whole class, and add it.

## Testing

`bash scripts/smoke-test.sh --quick` — static checks: script syntax + compile,
skill frontmatter, CLAUDE.md size, data JSON validity + freshness + expired-bonus
guard, README/llms drift, plugin manifest, agent-mirror sync, best-card CLI, earn
hook behavior. Run after every change; it's fast.

`bash scripts/smoke-test.sh` (full) — also launches codex/claude/opencode with a
real travel question and checks they pick sensible skills. Run before pushing.

## Sharp edges (learned the hard way)

- **Gondola MCP returns HTTP 406** to standard MCP clients; use
  `scripts/gondola-mcp.sh` (correct Accept header + manual handshake), never the
  native tools. Handles both SSE and plain-JSON framing.
- **Seats.aero data is cached**, not live — check `ComputedLastSeen`.
- **Southwest is in no GDS.** Only southwest.com or the `southwest` skill.
- **SerpAPI inflates flight prices**; Duffel is GDS truth. Kiwi is noise on small
  markets. (Full hierarchy: `lessons-learned` skill.)
- **A pre-commit guard blocks any `git commit` command containing `-n`** (it's
  the short flag for --no-verify) — including inside the commit *message*. If a
  commit is mysteriously blocked, look for `-n` or "verify"-adjacent flags in
  your message text.
- **`python3 -m py_compile` litters `__pycache__/`** — gitignored, harmless.
- **LiteAPI sort param** is an array of objects; passing `top_picks` explicitly
  gets rejected (it's default-only). Details in CLAUDE.md hotels section.
- Hooks live in the user's gitignored `.claude/settings.local.json`; a fresh
  clone doesn't have them. If hook-dependent behavior "stopped working," check
  registration first (see `scripts/install-hooks.sh`).

## Where the earn-side brain lives

The user's stated goal is a thinking partner for (a) which card to swipe,
(b) which cards to acquire, (c) creative accumulation and redemption. The map:

- Swipe optimization: `best-card-for-spend` skill + `scripts/best-card.py` +
  `data/my-cards.local.json` + the earn-verify hook.
- Acquisition strategy: `card-strategy` skill (issuer gating rules, welcome-bonus
  ROI, keep/downgrade/cancel) + awardtravelfinder MCP `cards_*` tools for live data.
- Accumulation stacking: the "full stack" checklist in `best-card-for-spend`
  (card-linked offers → portals incl. airline mile portals → dining programs →
  promos), registry in `data/earn-stack.local.json`.
- Redemption creativity: `award-sweet-spots`, `stopovers`, `round-the-world`,
  `transfer-bonuses`, `points-valuations` (decision sequence inside).

When extending any of these, keep the split: personal facts in `*.local.*`,
generic reasoning in skills, live-data mandates explicit, math in scripts.

---
name: okf-refresh
description: Keep an Open Knowledge Format bundle from going stale. Use when an agent needs to find and refresh expired, aging, draft, or unverified concepts — re-fetching each from its recorded sources, reconciling changed facts conservatively, re-stamping provenance and freshness, and logging the update. Complements okf-update, which handles arbitrary new material.
---

# Refresh a Stale OKF Bundle

Freshness is the point of this skill: a bundle is only worth trusting if its concepts are current. Work from evidence, never invent an update to clear a warning.

## Find what is stale

1. Read `../okf/references/okf-v0.2.md`.
2. Run the freshness report:
   ```text
   python ../okf/scripts/okf_stale.py BUNDLE [--as-of YYYY-MM-DD] [--max-age-days N] [--format json]
   ```
   Reasons: `expired` (past `stale_after`), `aging` (`generated.at` older than the threshold), `draft`, `unverified`, `no_freshness` (no signals to judge by). The first three are flagged as needing refresh.

## Refresh each flagged concept

1. Re-fetch from the concept's `sources` (the recorded connector call, URL, or bundle path). If a concept has no usable source, note that — do not fabricate one.
2. Reconcile conservatively: preserve unknown frontmatter keys and hand-authored prose; change only what the new evidence changes; cite new claims with `sources` + keyed footnotes.
3. Re-stamp provenance and reset freshness:
   ```text
   python ../okf/scripts/okf_bundle.py stamp CONCEPT --by claude-code/okf
   ```
   Set a new `stale_after` appropriate to the concept's volatility (short for live connector data, longer for stable reference). Advance `status` when warranted (`draft` → `stable`; `stable` → `deprecated` when the source is gone).
4. If a source is unreachable or the fact no longer exists, mark the concept `deprecated` with a note rather than deleting it.

## Finish

1. `python ../okf/scripts/okf_bundle.py index BUNDLE --write`
2. One `log` entry per refresh scope:
   ```text
   python ../okf/scripts/okf_bundle.py log BUNDLE --scope PATH --kind Refresh --message "..."
   ```
3. Re-run `okf_stale.py` and `../okf-validate/SKILL.md`. Report what was refreshed, what was deprecated, and any concept that could not be verified and why.

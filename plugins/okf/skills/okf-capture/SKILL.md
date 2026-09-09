---
name: okf-capture
description: Optional passive knowledge capture into an Open Knowledge Format bundle. Use when an agent should distill durable, reusable facts from the current session (or staged past sessions) into provenance-stamped OKF concepts, so future work reads the cached knowledge instead of re-calling connectors or re-analyzing the same sources. Off by default; governed by plugin settings.
---

# Capture Knowledge into an OKF Bundle

This is opt-in. Check the mode first: `python ../okf/scripts/okf_config.py get capture_mode --bundle BUNDLE`. If `off`, do nothing unless the user explicitly asks to capture now.

## Choose the source and the target

- **Source material.** On demand: the current session. Otherwise drain the queue the Stop hook writes (`~/.okf/capture-queue.jsonl`, or next to `$OKF_CONFIG`); each line points to a session transcript. Keep the exact raw line for each entry you process. After processing, remove only those lines — pipe them to `python ../okf/scripts/okf_dequeue.py`, don't truncate the file — so any line the Stop hook appended mid-drain survives.
- **Target bundle.** Use `capture_bundle`, then `bundles_root`, then a client bundle whose name matches the work, then the cwd. Read `okf_config.py show`.

## Distill (judgment, not transcription)

1. Read `../okf/references/okf-v0.2.md`.
2. Keep only **durable, reusable** facts — account facts, schemas, decisions, resolved answers, connector results worth not re-fetching. Drop ephemeral chatter, one-off reasoning, and anything already captured and still fresh.
3. One concept per fact. Pick a descriptive `type`. Record where it came from in `sources` (the connector/tool call, URL, or file), and stamp trust + freshness:
   - `generated: { by: claude-code/okf, at: <now ISO8601> }`
   - `stale_after`: a horizon matched to volatility (short for live connector data, longer for stable reference) — this is what lets future sessions know when to refresh.
4. Update, don't duplicate: if a fresh concept already covers it, reconcile conservatively (preserve unknown keys and prose).

## Redaction

**Off by default.** Only redact when `redaction` is `on` for the bundle, the bundle is already redacted, or the user asks. When redacting, apply `pii_scan.py redact` for emails/phones plus the placeholder vocabulary (`[Name]`, `[Contact]`, `[Company]`, `[Team]`, `[Owner]`) for names and companies.

## Write per capture mode

Always finish with `okf_bundle.py index --write`, a `log` entry (`--kind Capture`), and `../okf-validate/SKILL.md`.

- `on-demand`: write to the working tree and propose the diff; commit only if asked.
- `review-branch`: commit to an `okf-pending` branch (never `main`); tell the user to review and merge.
- `auto-main`: commit to the working branch.

Never push a bundle containing PII to a git remote without an explicit warning and the user's override (run `pii_scan.py scan` before any push). Never report a commit or push that did not actually happen.

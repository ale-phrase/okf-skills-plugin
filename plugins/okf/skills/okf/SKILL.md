---
name: okf
description: Route broad or ambiguous Open Knowledge Format work to the focused OKF skills and provide the shared v0.2 specification and tooling. Use when an agent needs to plan work across creating, updating, validating, migrating, or repairing an OKF bundle, or when the requested OKF operation is not yet clear.
---

# OKF

Use this skill as the entry point for the installed OKF skill suite.

## Route the request

- Read and follow `../okf-create/SKILL.md` for a new bundle, initial concepts, or source-to-OKF authoring.
- Read and follow `../okf-update/SKILL.md` for enrichment, reconciliation, reorganizing, or ongoing curation from new material.
- Read and follow `../okf-validate/SKILL.md` for conformance checks, quality audits, or repairs.
- Read and follow `../okf-refresh/SKILL.md` to keep a bundle current: find and refresh stale, expired, or draft concepts from their sources.
- Read and follow `../okf-export/SKILL.md` to share a bundle as a self-contained `viz.html` and an archive.
- Read and follow `../okf-capture/SKILL.md` for optional passive capture of durable knowledge from sessions (off by default; governed by settings).
- Combine the focused workflows in create, update, validate order when the request spans the lifecycle.

## Use shared resources

Read [references/okf-v0.2.md](references/okf-v0.2.md) before editing or judging a bundle. Treat it as an offline summary of the linked upstream specification, not authority for later OKF versions.

Use `scripts/okf_bundle.py` for deterministic checks and bookkeeping:

```text
python okf_bundle.py validate BUNDLE [--format text|json]
python okf_bundle.py index BUNDLE --check|--write [--version 0.1|0.2]
python okf_bundle.py stamp CONCEPT... [--at ISO8601] [--by ACTOR]
python okf_bundle.py log BUNDLE --scope PATH --kind KIND --message TEXT [--date YYYY-MM-DD]
python okf_bundle.py self-test
```

The `scripts/` directory also holds:

```text
python okf_stale.py BUNDLE [--as-of DATE] [--max-age-days N] [--format json]  # freshness report
python viz.py BUNDLE [--out OUT.html] [--name NAME]                           # self-contained viz.html
python pii_scan.py scan|redact ...                                            # PII heads-up / mechanical redaction
python okf_config.py show|get|set|set-bundle|init                            # plugin settings
```

Every script accepts `self-test` (or `--self-test`). Run with Python 3 and install `requirements.txt` (PyYAML) when the script reports it is missing. Ask before changing an environment if installation requires new authority.

## Settings and passive management

Settings live at `~/.okf/config.json` (see `okf_config.py`). `capture_mode` (default `off`) governs the optional passive-capture hooks; `redaction` (default `off`) governs default redaction. The `SessionStart` and `Stop`/`SubagentStop` hooks in `hooks/hooks.json` **only fire inside Claude Code** — in chat or Cowork, run the skills/commands directly. Redaction is off by default: only redact when asked or when a bundle is configured for it.

## Preserve the format's boundaries

Keep OKF source-agnostic. Do not assume BigQuery, Google Cloud, a fixed taxonomy, a serving system, or a visualization layer. Accept unknown types and producer-defined frontmatter. Escalate a declared version newer than `0.2` for compatibility review rather than silently rewriting it.

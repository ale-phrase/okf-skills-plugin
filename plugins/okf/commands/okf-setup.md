---
description: View or change OKF plugin settings (passive capture, redaction, bundles root)
argument-hint: [e.g. "capture_mode review-branch" or "show"]
---
Manage OKF plugin settings with the config helper. Show current settings first, then apply any change the user asked for.

```
python "${CLAUDE_PLUGIN_ROOT}/skills/okf/scripts/okf_config.py" show
```

Common changes:
- `okf_config.py set bundles_root /path/to/vault` — where the plugin looks for bundles (also what the SessionStart hook surfaces).
- `okf_config.py set capture_mode off|on-demand|review-branch|auto-main` — passive capture behavior (default `off`).
- `okf_config.py set redaction off|on` — default redaction (default `off`; semantic redaction stays skill-driven).
- `okf_config.py set-bundle /path KEY VALUE` — per-bundle override (`capture_mode`, `redaction`, `max_age_days`, `capture_bundle`).

Explain what passive capture does before enabling it, and that hooks only fire inside Claude Code (not chat/Cowork).

Request: $ARGUMENTS

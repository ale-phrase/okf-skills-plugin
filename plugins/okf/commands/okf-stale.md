---
description: Report OKF concepts that are stale or missing freshness signals
argument-hint: [bundle path]
---
Run the freshness report on the OKF bundle and summarize what needs attention:

```
python "${CLAUDE_PLUGIN_ROOT}/skills/okf/scripts/okf_stale.py" $ARGUMENTS
```

Highlight `expired`, `aging`, and `draft` concepts (they need a refresh). Offer to run `/okf-refresh` if anything needs updating. Do not modify the bundle.

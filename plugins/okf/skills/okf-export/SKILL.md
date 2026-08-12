---
name: okf-export
description: Export and share an Open Knowledge Format bundle as a self-contained viz.html and a zip/tar archive. Use when an agent needs to produce a shareable, read-only view of a bundle or a portable copy for hand-off. Validates first and gives a PII heads-up before any artifact leaves the machine.
---

# Export / Share an OKF Bundle

## Validate before sharing

1. Read `../okf/references/okf-v0.2.md`.
2. Run `../okf-validate/SKILL.md`. Do not export a bundle with conformance errors; report them and stop. Warnings are acceptable.

## PII heads-up (required before an artifact leaves the machine)

```text
python ../okf/scripts/pii_scan.py scan BUNDLE
```

This catches machine-obvious tokens (emails, phone numbers) only. If it reports any, surface the counts and the files, and get explicit confirmation before producing an artifact — the recipient can open a `viz.html` or unzip an archive anywhere. Do not auto-redact. Only redact when the user asks or the bundle is configured for it (`okf_config.py get redaction --bundle BUNDLE`); then use `pii_scan.py redact FILE...` for mechanical tokens plus the placeholder vocabulary (`[Name]`, `[Contact]`, `[Company]`, `[Team]`, `[Owner]`) for names and companies the scanner cannot see. Never push a bundle with PII to a git remote without an explicit warning and the user's override.

## Produce the artifacts

- Interactive view (bundle embedded; only the graph/markdown JS loads from a CDN, no bundle data leaves the page):
  ```text
  python ../okf/scripts/viz.py BUNDLE [--out OUT.html] [--name NAME]
  ```
- Portable archive (stdlib, no new dependency; use `zip` unless the user wants `tar`/`gztar`):
  ```text
  python3 -c "import shutil,sys; print(shutil.make_archive(sys.argv[1], 'zip', sys.argv[2]))" OUTPUT_BASENAME BUNDLE
  ```

Report the artifact paths. State plainly that `viz.html` is read-only and self-contained, and that the archive is a full copy of the bundle.

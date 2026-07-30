# OKF skills for Codex

A Codex plugin for creating, updating, migrating, and validating source-agnostic [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundles.

## Skills

- `okf`: routes broad OKF work.
- `okf-create`: creates v0.2 bundles from evidence.
- `okf-update`: conservatively updates and migrates bundles.
- `okf-validate`: validates conformance and optional v0.2 provenance, trust, lifecycle, and attestation metadata.

The shared `okf_bundle.py` utility validates bundles, maintains managed indexes, stamps `generated.at`, and appends scoped log entries.

## Install

Add this checkout as a local marketplace, then install the plugin:

```powershell
codex plugin marketplace add .
codex plugin add okf@personal
```

Start a new Codex task after installation so the skills are discovered.

## Validate

Install the one runtime dependency:

```powershell
python -m pip install -r plugins/okf/skills/okf/requirements.txt
```

Then run:

```powershell
python plugins/okf/skills/okf/scripts/okf_bundle.py self-test
python plugins/okf/skills/okf/scripts/okf_bundle.py validate PATH_TO_BUNDLE
```

The validator follows v0.2's permissive conformance model: malformed concepts and reserved files are errors; optional-family problems and broken links are warnings.

`index --write` declares v0.2 in a newly created root index. Pass `--version 0.1` only when intentionally maintaining a legacy bundle.

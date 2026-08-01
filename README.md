# OKF skills for Codex and Claude Code

A plugin for creating, updating, migrating, and validating source-agnostic [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundles.

## Skills

- `okf`: routes broad OKF work.
- `okf-create`: creates v0.2 bundles from evidence.
- `okf-update`: conservatively updates and migrates bundles.
- `okf-validate`: validates conformance and optional v0.2 provenance, trust, lifecycle, and attestation metadata.

The shared `okf_bundle.py` utility validates bundles, maintains managed indexes, stamps `generated.at`, and appends scoped log entries.

## Install

### Claude Code

Send these as two separate prompts:

```text
/plugin marketplace add justusenumbers/okf-skills-plugin
```

```text
/plugin install okf@okf
```

### Codex

```powershell
codex plugin marketplace add justusenumbers/okf-skills-plugin
codex plugin add okf@okf
```

Start a new task after installation so the skills are discovered.

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

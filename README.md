# OKF skills for Claude Code (and Codex)

Make [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) bundles easy to create, validate, **keep fresh**, and share — for the Phrase SA team or anyone who wants it. An OKF bundle is just a directory of Markdown files with YAML frontmatter (one concept per file, `type` the only required field), so the knowledge stays readable and portable with or without this plugin.

> Forked from [justusenumbers/okf-skills-plugin](https://github.com/justusenumbers/okf-skills-plugin) (MIT). Adds anti-staleness, sharing, slash commands, settings, and optional passive capture.

## Commands

| Command | What it does |
|---|---|
| `/okf-create` | Create a new v0.2 bundle from sources, files, or facts. |
| `/okf-update` | Conservatively update a bundle from new material. |
| `/okf-validate` | Check conformance and provenance (no changes unless you ask). |
| `/okf-stale` | Report concepts that are expired, aging, draft, or missing freshness signals. |
| `/okf-refresh` | Refresh stale concepts from their recorded sources and re-stamp freshness. |
| `/okf-export` | Produce a self-contained `viz.html` + a zip/tar archive (with a PII heads-up). |
| `/okf-capture` | Optional: distill durable knowledge from sessions into concepts. |
| `/okf-setup` | View/change settings (passive capture, redaction, bundles root). |

The same work is available as skills (`okf`, `okf-create`, `okf-update`, `okf-validate`, `okf-refresh`, `okf-export`, `okf-capture`) so Claude can route to them without a command.

## Keeping bundles fresh

Freshness is the headline. Each concept can carry `generated.at`, `stale_after`, and `status`. `/okf-stale` reports what needs attention; `/okf-refresh` re-fetches those concepts from their `sources`, reconciles conservatively, re-stamps provenance/freshness, and logs the change — so a bundle stays a trustworthy cache instead of quietly rotting.

## Sharing

`/okf-export` validates first, then writes a self-contained `viz.html` (the bundle is embedded; only the graph/markdown JS loads from a CDN, no bundle data leaves the page) and a portable archive. It runs a PII heads-up before anything leaves the machine and never pushes PII to a git remote without an explicit warning and your override.

## Optional passive capture

Off by default. When enabled, a `Stop` hook stages finished sessions and `/okf-capture` (or a scheduled run) distills durable facts into provenance-stamped concepts, so future work reads the cache instead of re-calling connectors. A `SessionStart` hook surfaces the available bundles and how many concepts need a refresh.

**Hooks fire inside Claude Code only.** In chat or Cowork, run the skills/commands directly against the same bundle.

Modes (`capture_mode`): `off` (default), `on-demand` (stage, capture when you ask), `review-branch` (commit to an `okf-pending` branch you review), `auto-main`.

## Settings

Stored at `~/.okf/config.json` (override with `$OKF_CONFIG`):

```text
python plugins/okf/skills/okf/scripts/okf_config.py show
python plugins/okf/skills/okf/scripts/okf_config.py set bundles_root /path/to/vault
python plugins/okf/skills/okf/scripts/okf_config.py set capture_mode on-demand
python plugins/okf/skills/okf/scripts/okf_config.py set-bundle /path/to/vault redaction on
```

`redaction` is `off` by default; semantic redaction (names, companies) stays skill-driven using a placeholder vocabulary. `bundles_root` is what the `SessionStart` hook surfaces.

## Install

### Claude Code (two separate prompts)

```text
/plugin marketplace add ale-phrase/okf-skills-plugin
```

```text
/plugin install okf@okf
```

Start a new session after installing so skills, commands, and hooks are discovered.

### Codex

```text
codex plugin marketplace add ale-phrase/okf-skills-plugin
codex plugin add okf@okf
```

Codex gets the skills; the hooks and slash commands are Claude Code features.

## Runtime and checks

One dependency (PyYAML):

```text
python -m pip install -r plugins/okf/skills/okf/requirements.txt
```

Every script self-tests:

```text
python plugins/okf/skills/okf/scripts/okf_bundle.py self-test
python plugins/okf/skills/okf/scripts/okf_stale.py --self-test
python plugins/okf/skills/okf/scripts/okf_config.py self-test
python plugins/okf/skills/okf/scripts/pii_scan.py self-test
python plugins/okf/skills/okf/scripts/viz.py --self-test
```

The validator follows v0.2's permissive conformance model: malformed concepts and reserved files are errors; optional-family problems and broken links are warnings.

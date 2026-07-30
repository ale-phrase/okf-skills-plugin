---
name: okf-create
description: Create source-agnostic Open Knowledge Format bundles from local files, URLs, schemas, repositories, or supplied facts. Use when Codex needs to initialize an OKF bundle, design its concept hierarchy, author concept documents, add indexes and history, or turn existing knowledge into conformant OKF v0.2 Markdown.
---

# Create an OKF Bundle

## Prepare

1. Read `../okf/references/okf-v0.2.md` completely.
2. Inspect the target. If it already contains substantive OKF content, switch to `../okf-update/SKILL.md`.
3. Inventory the authoritative inputs. Separate sourced facts from inference, retain source URLs, and surface unknowns instead of inventing details.

## Design the bundle

1. Choose stable, lowercase file paths that reflect the user's domain. Do not impose a generic `tables/`, `metrics/`, or other taxonomy unless the material supports it.
2. Give each independently useful idea or asset one concept file. Treat its bundle-relative path without `.md` as its durable concept ID.
3. Use descriptive, self-explanatory `type` values and reuse the same spelling for the same kind of concept.
4. Prefer bundle-root links such as `/systems/payments.md` when linking concepts.

## Author concepts

1. Write UTF-8 Markdown with YAML frontmatter beginning at byte one.
2. Always provide a non-empty `type`. Add `title`, one-sentence `description`, `resource`, and `tags` when known and applicable.
3. Record provenance in `sources`; use stable `sources[].id` values and matching Markdown footnotes for per-claim attribution.
4. Record meaningful authorship with `generated: { by, at }`. Add `verified`, `status`, and `stale_after` only when supported by evidence; never imply human review.
5. Structure the body with headings, lists, tables, and fenced examples. Use `# Schema`, `# Examples`, and `# Computation` when they fit.
6. Use links in surrounding prose to explain relationships; do not invent edge types.
7. For `type: Attested Computation`, provide `runtime` and a sanctioned computation, declare only parameter values an agent may supply, and keep executors and deterministic attesters as referenced resources.
8. Preserve domain-specific schemas by referencing or embedding them; do not replace them with an OKF-specific schema.

## Finish

1. Run the shared `index BUNDLE --write` command to create managed progressive-disclosure indexes, including root `okf_version: "0.2"` frontmatter.
2. Run the shared `log` command with kind `Initialization` and a concise description of the created scope.
3. Run `validate BUNDLE`. Resolve conformance errors and review quality warnings against the available evidence.
4. Report the created concept IDs, source gaps, validation result, and any intentionally deferred warnings.

# Open Knowledge Format v0.2

Offline summary of the specification reviewed 2026-07-30:

- Specification: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
- Source directory: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
- Upstream version: `0.2`
- Reviewed SHA-256 of `SPEC.md`: `5A3311D270BEBB16D558010E75064F5B75323F284992641732B1C8097511F948`

Review the upstream specification before supporting a version newer than `0.2`.

## Contents

- Model and concept documents
- Provenance, trust, and lifecycle
- Links, reserved files, and attested computations
- Conformance and v0.1 migration

## Model

An OKF knowledge bundle is a self-contained directory tree of UTF-8 Markdown files. A concept is one non-reserved Markdown file. Its concept ID is its bundle-relative path without `.md`. Directories provide hierarchy; ordinary Markdown links provide graph relationships.

OKF defines an interoperability surface, not a taxonomy, storage service, serving protocol, runtime protocol, or replacement for domain schemas.

## Concept documents

Start every concept with parseable YAML frontmatter. The only always-required field is a non-empty string `type`.

```markdown
---
type: Metric
title: Weekly active users
description: Distinct users with a qualifying event during an ISO week.
resource: https://example.com/catalog/weekly-active-users
tags: [product, engagement]
status: stable
generated: { by: human:analyst, at: 2026-07-30T14:30:00Z }
sources:
  - id: metric-policy
    resource: https://example.com/definition
    title: Metric policy
---

# Definition

Describe the metric and attribute sourced claims.[^metric-policy]

[^metric-policy]: Metric policy
```

Recommended fields are `title`, `description`, `resource`, and `tags`. Producers may add arbitrary keys. Consumers preserve unknown keys and tolerate unknown `type` values. Prefer structural Markdown. Conventional body headings are `# Schema`, `# Examples`, and `# Computation`; none is always required.

## Provenance

`sources` is an optional list of source mappings. Each entry requires `resource` when present and may include:

- `id`: stable key used by matching Markdown footnotes.
- `title`: human-readable label.
- `author`: actor that produced the source.
- `usage_count`: coarse liveness signal, framed by a shared or per-entry `usage_window`.
- `last_modified`: source date in `YYYY-MM-DD`.

Do not store a subjective credibility score. Use `sources[].id` as the footnote label for per-claim attribution. A `sources[].resource` may be an absolute URL, a bundle path, or a scope descriptor.

## Trust

`generated` describes the current content's producer and meaningful-change time:

```yaml
generated: { by: producer/version, at: 2026-07-30T14:30:00Z }
```

`generated.by` is required when `generated` is present. `generated.at` is an ISO 8601 datetime.

`verified` records independent confirmation events and may be a list or a single mapping:

```yaml
verified:
  - { by: process:nightly-check, at: 2026-07-30T15:00:00Z }
  - { by: human:reviewer, at: 2026-07-30T16:00:00Z }
```

Consumers derive trust tiers from `verified`: absent is unverified, non-human verifiers only is machine-confirmed, and any `human:` verifier is human-reviewed. Trust tiers are advisory, not access control.

Actors use `<producer>/<version>` for tools or agents, `human:<id>` for people, and `process:<id>` for automated processes.

## Lifecycle

`status` is optional: `draft`, `stable`, or `deprecated`; absent means `stable`.

`stale_after` is an optional `YYYY-MM-DD` date. A concept is stale when `today >= stale_after`.

## Links and paths

Use standard Markdown links. A leading `/` is bundle-root-relative and recommended; ordinary relative paths are also supported. Explain the relationship in surrounding prose because links are directed but untyped.

Consumers tolerate broken links as quality findings. Path-valued fields include `resource`, `sources[].resource`, `computation`, `executor.resource`, and `attester.resource`. The `references/` directory is conventional, not required.

## Reserved files

`index.md` and `log.md` are reserved at every directory level and are not concept documents.

An `index.md` enumerates a directory for progressive disclosure. It normally has no frontmatter. The root `index.md` may declare:

```yaml
---
okf_version: "0.2"
---
```

The body uses headings and bullet links with short descriptions.

A `log.md` records newest-first updates grouped under ISO `YYYY-MM-DD` headings. Entries are prose; a leading bold kind such as `**Update**` is conventional.

## Attested Computation

A sanctioned computation is a standalone concept with `type: Attested Computation`. It carries:

- `runtime`: required for this type and defines parameter binding semantics.
- `parameters`: optional list of `{ name, type, required }` mappings.
- `computation`: optional path to the computation file; otherwise use one fenced block under `# Computation`.
- `executor`: optional mapping whose `resource` identifies run instructions or code and whose `receipt` declares returned evidence.
- `attester`: optional mapping whose `resource` identifies deterministic, no-LLM checking code.

An agent may supply only declared parameter values and must not author or mutate the sanctioned computation. Receipts and verdicts are runtime artifacts and are not stored in the bundle.

## Conformance

A v0.2 bundle is conformant when:

1. Every non-reserved `.md` file has parseable YAML frontmatter.
2. Every concept frontmatter block contains a non-empty `type`.
3. Every present `index.md` and `log.md` follows its reserved structure.

When optional provenance, trust, lifecycle, or computation families are present, producers should follow their specified shapes. Consumers must treat a bare `verified` mapping as a one-element list and must not reject a bundle for missing optional families.

Do not reject a bundle solely for missing optional fields, unknown types, unknown extra keys, broken links, missing indexes, or imperfect optional-family metadata. Surface those as quality findings.

## Migration from v0.1

v0.2 supersedes v0.1. Two fields are deliberately replaced:

- `timestamp` is superseded by `generated.at`; consumers may fall back to `timestamp` when `generated` is absent.
- A body `# Citations` list is superseded by frontmatter `sources` plus keyed footnotes; consumers may still read the legacy section.

Do not migrate either form by guessing authorship or claim-to-source mappings. The other v0.2 additions are optional and backward-compatible.

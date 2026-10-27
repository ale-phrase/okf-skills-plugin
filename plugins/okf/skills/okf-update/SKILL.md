---
name: okf-update
description: Conservatively update and curate existing Open Knowledge Format bundles from new source material. Use when an agent needs to enrich concepts, reconcile changed facts or schemas, add or deprecate knowledge, repair cross-references, refresh indexes and logs, or reorganize an OKF bundle without losing hand-authored content.
---

# Update an OKF Bundle

## Establish the baseline

1. Read `../okf/references/okf-v0.2.md` completely.
2. Run the shared `validate BUNDLE` command before editing. Record existing conformance errors separately from the requested update.
3. Inventory concept IDs, types, producer-defined frontmatter, links, indexes, logs, and local uncommitted changes. Treat existing curated prose and unknown keys as owned content.
4. Compare new authoritative evidence with the current bundle. Classify each difference as add, meaningful update, deprecation, contradiction, or formatting-only noise.

## Apply a conservative merge

1. Change only evidence-backed facts within the requested scope. Preserve unrelated body sections, citations, comments, unknown metadata, and formatting.
2. Keep concept paths stable. Rename or move a concept only when the user requests the migration or the old identity is materially misleading; update every known inbound link in the same change.
3. Add citations for newly sourced claims. When sources conflict, describe the conflict or request direction rather than selecting silently.
4. Run the shared `stamp` command only for concepts with meaningful content or metadata changes. It updates `generated.at`; pass `--by` when the concept has no existing `generated.by`. Do not stamp formatting-only edits.
5. For each stamped concept, set a fresh `stale_after` matched to its volatility (short for live connector data, longer for stable reference). Stamping resets `generated.at`, so an old `stale_after` would leave a just-updated concept looking expired or expiring on its original schedule. Skip it for concepts that never carried freshness metadata unless the evidence supports a horizon.
6. Run `index BUNDLE --check`. Use `--write` for missing or marker-managed indexes. If an existing index has no managed markers, edit its entries manually or obtain agreement to adopt managed sections; never overwrite it wholesale.
7. Add one concise `log` entry per affected scope after the final change set is known. Do not log validation-only or formatting-only activity.

## Verify and hand off

1. Run `validate BUNDLE` again and compare it with the baseline.
2. Resolve new conformance errors. Leave an allowed broken link or missing optional field only when the incomplete state is intentional and explain it.
3. Summarize changed concept IDs, source evidence, moves or deprecations, log scopes, and remaining warnings.

## Migrate v0.1 content when requested

1. Preserve legacy `timestamp` and `# Citations` unless their authorship and source mapping can be migrated without guessing.
2. Replace `timestamp` with `generated: { by, at }` only when the producer is known.
3. Replace `# Citations` with `sources` and keyed footnotes only when each cited claim can be matched to a source.
4. Update the root `okf_version` to `"0.2"` only after the bundle follows the v0.2 conventions the available evidence can support.
5. When adding a missing root index to a bundle intentionally kept on v0.1, pass `index --write --version 0.1`; new and migrated bundles default to v0.2.

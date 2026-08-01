---
name: okf-validate
description: Validate and safely repair Open Knowledge Format v0.2 bundles. Use when an agent needs to check OKF conformance, audit provenance, trust, lifecycle, attested computations, metadata and cross-links, diagnose malformed concept or reserved files, verify index freshness, produce a machine-readable validation report, or fix confirmed bundle defects.
---

# Validate an OKF Bundle

## Inspect without mutation

1. Read `../okf/references/okf-v0.2.md` completely.
2. Run the shared `validate BUNDLE` command. Use `--format json` only when another tool will consume the result.
3. Report conformance errors separately from quality warnings. A successful result means no conformance errors; warnings may remain.
4. Treat malformed YAML, a missing or empty concept `type`, and structurally invalid reserved files as errors. Treat missing optional metadata, unknown types or keys, broken links, missing indexes, and malformed optional v0.2 families as non-blocking findings according to the v0.2 conformance model.
5. Check optional `sources`, `generated`, `verified`, `status`, `stale_after`, and Attested Computation fields when present. Derive trust tiers from `verified`; do not mistake trust metadata for access control.
6. Do not edit the bundle when the request is only to validate, audit, inspect, diagnose, or report.

## Repair when requested

1. Fix only defects the evidence resolves unambiguously. Do not guess a missing type, link target, producer, verification event, date, or source.
2. Use `index BUNDLE --write` for missing or marker-managed indexes. Pass `--version 0.1` when intentionally preserving a legacy v0.1 bundle; otherwise the new root index targets v0.2. Preserve unmarked indexes and repair them manually.
3. Use `stamp` only when a meaningful concept correction warrants a new `generated.at`. Add a `log` entry only when the repair changes knowledge, not for mechanical index refreshes.
4. Re-run validation and report resolved errors, remaining errors, and remaining warnings. State why any issue could not be repaired safely.

## Interpret exit status

- `0`: no conformance errors; warnings may be present.
- `1`: one or more conformance errors, or a requested index check found drift.
- `2`: the command could not run, such as a missing dependency or invalid invocation.

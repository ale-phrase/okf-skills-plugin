#!/usr/bin/env python3
"""Report OKF concepts that are stale or missing freshness signals.

Reuses okf_bundle.py's frontmatter parsing. A concept "needs attention" when it
is expired (past stale_after), aging (generated.at older than --max-age-days),
or still a draft. Missing-freshness and unverified are advisory only.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from okf_bundle import parse_yaml, read_utf8, split_frontmatter, write_utf8  # noqa: E402

RESERVED = {"index.md", "log.md"}
ATTENTION = {"expired", "aging", "draft"}  # reasons that count as "needs refresh"


def to_datetime(value: object):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and "T" in value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def to_date(value: object):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def concept_reasons(meta: dict, as_of: date, max_age_days: int) -> tuple[list[str], dict]:
    """Return (reasons, facts) for one concept's frontmatter."""
    reasons: list[str] = []
    facts: dict = {}

    stale_after = to_date(meta.get("stale_after"))
    if stale_after is not None:
        facts["stale_after"] = stale_after.isoformat()
        if stale_after < as_of:
            reasons.append("expired")

    generated = meta.get("generated")
    gen_dt = to_datetime(generated.get("at")) if isinstance(generated, dict) else None
    if gen_dt is not None:
        age = (as_of - gen_dt.date()).days
        facts["generated_at"] = gen_dt.date().isoformat()
        facts["age_days"] = age
        if "expired" not in reasons and age > max_age_days:
            reasons.append("aging")

    status = meta.get("status")
    if status == "draft":
        reasons.append("draft")
        facts["status"] = status

    verified = meta.get("verified")
    has_verified = bool(verified) and (isinstance(verified, dict) or isinstance(verified, list))
    if not has_verified:
        reasons.append("unverified")

    if stale_after is None and gen_dt is None:
        reasons.append("no_freshness")

    return reasons, facts


def scan(root: Path, as_of: date, max_age_days: int) -> list[dict]:
    """Scan a bundle. Returns one finding per concept that has any reason."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"bundle is not a directory: {root}")
    findings: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        if path.name in RESERVED:
            continue
        try:
            text, _ = read_utf8(path)
            parts = split_frontmatter(text)
            meta = parse_yaml(parts[0]) if parts else {}
        except Exception:
            continue  # unparseable is a validation concern, not a staleness one
        if not isinstance(meta, dict):
            continue
        reasons, facts = concept_reasons(meta, as_of, max_age_days)
        if reasons:
            findings.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "type": meta.get("type"),
                    "title": meta.get("title"),
                    "reasons": reasons,
                    "needs_attention": any(r in ATTENTION for r in reasons),
                    **facts,
                }
            )
    findings.sort(key=lambda f: (not f["needs_attention"], f["path"]))
    return findings


def counts(findings: list[dict]) -> dict:
    result = {"total": len(findings), "needs_attention": 0}
    for reason in ("expired", "aging", "draft", "unverified", "no_freshness"):
        result[reason] = sum(reason in f["reasons"] for f in findings)
    result["needs_attention"] = sum(f["needs_attention"] for f in findings)
    return result


def report(root: Path, as_of: date, max_age_days: int, fmt: str) -> tuple[str, dict]:
    findings = scan(root, as_of, max_age_days)
    tally = counts(findings)
    if fmt == "json":
        return json.dumps(
            {"as_of": as_of.isoformat(), "max_age_days": max_age_days, "counts": tally, "findings": findings},
            indent=2,
        ), tally
    lines = []
    for f in findings:
        flag = "!" if f["needs_attention"] else "-"
        detail = ", ".join(f["reasons"])
        extra = f" (age {f['age_days']}d)" if "age_days" in f else ""
        lines.append(f"{flag} {f['path']}: {detail}{extra}")
    lines.append(
        f"{tally['needs_attention']} need refresh "
        f"(expired {tally['expired']}, aging {tally['aging']}, draft {tally['draft']}); "
        f"{tally['unverified']} unverified, {tally['no_freshness']} without freshness signals"
    )
    return "\n".join(lines), tally


def _self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_utf8(root / "expired.md", "---\ntype: Note\nstale_after: 2020-01-01\n---\n")
        write_utf8(root / "aging.md", "---\ntype: Note\ngenerated: { by: human:a, at: 2020-01-01T00:00:00Z }\n---\n")
        write_utf8(root / "draft.md", "---\ntype: Note\nstatus: draft\ngenerated: { by: human:a, at: 2026-08-01T00:00:00Z }\nverified: { by: human:a, at: 2026-08-01T00:00:00Z }\n---\n")
        write_utf8(root / "fresh.md", "---\ntype: Note\nstale_after: 2999-01-01\nverified: { by: human:a, at: 2026-08-01T00:00:00Z }\n---\n")
        write_utf8(root / "index.md", "# Index\n")  # reserved, skipped
        as_of = date(2026, 8, 4)
        findings = scan(root, as_of, max_age_days=180)
        by_path = {f["path"]: f for f in findings}
        assert "expired" in by_path["expired.md"]["reasons"], findings
        assert "aging" in by_path["aging.md"]["reasons"], findings
        assert "draft" in by_path["draft.md"]["reasons"], findings
        # fresh.md has a future stale_after + verified, so it produces no findings at all.
        assert "fresh.md" not in by_path, findings
        assert "index.md" not in by_path
        c = counts(findings)
        assert c["expired"] == 1 and c["aging"] == 1 and c["draft"] == 1, c
        assert c["needs_attention"] == 3, c
    print("okf_stale self-test passed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bundle", nargs="?", type=Path)
    ap.add_argument("--as-of", help="YYYY-MM-DD reference date (default today, UTC)")
    ap.add_argument("--max-age-days", type=int, default=180, help="generated.at older than this is 'aging'")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any concept needs refresh")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        _self_test()
        return 0
    if args.bundle is None:
        ap.error("bundle is required unless --self-test")
    as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
    try:
        text, tally = report(args.bundle, as_of, args.max_age_days, args.format)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(text)
    return 1 if args.strict and tally["needs_attention"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

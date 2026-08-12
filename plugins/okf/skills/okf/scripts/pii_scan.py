#!/usr/bin/env python3
"""High-precision PII heads-up and mechanical redaction for OKF bundles.

This only catches machine-obvious tokens (emails, phone numbers) so an export or
push can warn before data leaves the machine. It is NOT a semantic redactor:
names, companies, and account details are the skill's job, using the placeholder
vocabulary below. Redaction here is opt-in and replaces matches with [Contact].
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

# Placeholder vocabulary shared with ghostwriter for consistent redaction.
PLACEHOLDERS = ["[Name]", "[Contact]", "[Company]", "[Team]", "[Owner]"]

EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Conservative phone match: 7+ digits with separators, optional country code.
PHONE = re.compile(r"(?<![\w-])\+?\d[\d\s().-]{7,}\d(?![\w-])")

RESERVED = {"log.md"}  # log.md is prose history; still scanned, never redacted here


def _phones(text: str) -> list[str]:
    # ponytail: >=10 digits keeps real phone numbers while excluding 8-digit ISO
    # dates (YYYY-MM-DD), which every OKF concept carries. Tighten only if adjacent
    # dates in prose start producing false positives.
    return [m for m in PHONE.findall(text) if sum(c.isdigit() for c in m) >= 10]


def scan_text(text: str) -> dict:
    return {"emails": EMAIL.findall(text), "phones": _phones(text)}


def redact_text(text: str) -> tuple[str, int]:
    new, emails = EMAIL.subn("[Contact]", text)
    phones = _phones(new)
    for match in phones:
        new = new.replace(match, "[Contact]", 1)
    return new, emails + len(phones)


def scan_bundle(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"bundle is not a directory: {root}")
    files = []
    totals = {"emails": 0, "phones": 0}
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        hit = scan_text(text)
        if hit["emails"] or hit["phones"]:
            rel = path.relative_to(root).as_posix()
            files.append({"path": rel, "emails": len(hit["emails"]), "phones": len(hit["phones"])})
            totals["emails"] += len(hit["emails"])
            totals["phones"] += len(hit["phones"])
    return {"totals": totals, "files": files}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="report apparent PII in a bundle")
    sc.add_argument("bundle", type=Path)
    sc.add_argument("--format", choices=("text", "json"), default="text")
    rd = sub.add_parser("redact", help="replace emails/phones with [Contact] in files (in place)")
    rd.add_argument("file", nargs="+", type=Path)
    sub.add_parser("self-test")
    args = ap.parse_args()

    if args.cmd == "self-test":
        return _self_test()
    if args.cmd == "scan":
        try:
            result = scan_bundle(args.bundle)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            for f in result["files"]:
                print(f"{f['path']}: {f['emails']} email(s), {f['phones']} phone(s)")
            t = result["totals"]
            print(f"total: {t['emails']} email(s), {t['phones']} phone(s) across {len(result['files'])} file(s)")
        # exit 1 when PII is present so callers can gate on it
        return 1 if result["totals"]["emails"] or result["totals"]["phones"] else 0
    if args.cmd == "redact":
        changed = 0
        for path in args.file:
            if path.name in RESERVED:
                continue
            text = path.read_text(encoding="utf-8")
            new, n = redact_text(text)
            if n:
                path.write_text(new, encoding="utf-8")
                changed += n
        print(f"redacted {changed} token(s)")
        return 0
    return 0


def _self_test() -> int:
    hit = scan_text("reach paula at paula@acme.com or +1 555-123-4567 today")
    assert hit["emails"] == ["paula@acme.com"], hit
    assert len(hit["phones"]) == 1, hit
    red, n = redact_text("email jane@x.io and jack@y.io")
    assert red == "email [Contact] and [Contact]", red
    assert n == 2, n
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("---\ntype: Person\n---\nCall bob@x.com\n", encoding="utf-8")
        (root / "clean.md").write_text("---\ntype: Note\n---\nno pii here\n", encoding="utf-8")
        result = scan_bundle(root)
        assert result["totals"]["emails"] == 1, result
        assert len(result["files"]) == 1, result
    print("pii_scan self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

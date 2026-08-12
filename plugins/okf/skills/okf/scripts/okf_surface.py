#!/usr/bin/env python3
"""SessionStart hook: surface an available OKF knowledge base into context.

Reads config for a bundles_root; if none is set, only surfaces when the current
working directory is itself a bundle (has a top-level index.md) — so it never
scans an arbitrary large repo. Emits freshness guidance plus a per-bundle
stale-concept count. Silent and non-fatal on any error; never blocks a session.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _emit(context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


def _is_bundle(path: Path) -> bool:
    return path.is_dir() and (path / "index.md").exists()


def _bundles(root: Path) -> list[Path]:
    found = []
    if _is_bundle(root):
        found.append(root)
    try:
        for child in sorted(root.iterdir()):
            if child.is_dir() and _is_bundle(child):
                found.append(child)
    except OSError:
        pass
    return found[:12]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    try:
        import okf_config
        import okf_stale

        cfg = okf_config.load()
        cwd = Path(payload.get("cwd") or ".").resolve()
        configured = cfg.get("bundles_root")
        if configured:
            root = Path(configured).expanduser().resolve()
        elif _is_bundle(cwd):
            root = cwd
        else:
            return 0  # nothing to surface; stay quiet

        bundles = _bundles(root)
        if not bundles:
            return 0
        as_of = datetime.now(timezone.utc).date()
        lines = []
        for b in bundles:
            eff = okf_config.effective(cfg, str(b))
            try:
                findings = okf_stale.scan(b, as_of, int(eff.get("max_age_days") or 180))
                need = sum(f["needs_attention"] for f in findings)
                concepts = len([p for p in b.rglob("*.md") if p.name not in {"index.md", "log.md"}])
            except Exception:
                need, concepts = 0, 0
            flag = f", {need} need refresh" if need else ""
            lines.append(f"- {b.name} ({concepts} concepts{flag})")

        context = (
            "An OKF knowledge base is available. Prefer reading its cached concepts over "
            "re-calling connectors or re-analyzing sources you have seen before. Each concept "
            "carries provenance (`sources`) and freshness (`generated.at`, `stale_after`): trust "
            "fresh concepts, and refresh stale ones from their sources before relying on them. "
            "Run /okf-stale to review freshness or /okf-refresh to update.\n"
            f"Bundles under {root}:\n" + "\n".join(lines)
        )
        _emit(context)
    except Exception:
        return 0  # hooks must never break a session
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

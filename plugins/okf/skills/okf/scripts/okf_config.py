#!/usr/bin/env python3
"""Read/write OKF plugin settings.

Settings live at ~/.okf/config.json (override with $OKF_CONFIG). Everything is
optional; defaults keep the plugin passive and non-destructive. Per-bundle
overrides live under "bundles": { "<abs path>": { ...overrides } }.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "bundles_root": None,            # where bundles live; null = current working dir
    "capture_bundle": None,         # where passive capture writes; null = bundles_root/cwd
    "capture_mode": "off",          # off | on-demand | review-branch | auto-main
    "redaction": "off",             # off | on  (semantic redaction is skill-driven; this is the default)
    "max_age_days": 180,            # generated.at older than this counts as "aging"
    "bundles": {},                  # per-bundle overrides keyed by absolute path
}
OVERRIDABLE = {"capture_mode", "redaction", "max_age_days", "capture_bundle"}
CAPTURE_MODES = {"off", "on-demand", "review-branch", "auto-main"}


def config_path() -> Path:
    env = os.environ.get("OKF_CONFIG")
    return Path(env) if env else Path.home() / ".okf" / "config.json"


def load() -> dict:
    path = config_path()
    cfg = dict(DEFAULTS)
    if path.is_file():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    cfg.setdefault("bundles", {})
    return cfg


def save(cfg: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def effective(cfg: dict, bundle: str | None = None) -> dict:
    """Top-level settings with any per-bundle override applied."""
    result = {k: v for k, v in cfg.items() if k != "bundles"}
    if bundle:
        override = cfg.get("bundles", {}).get(str(Path(bundle).resolve()), {})
        result.update({k: v for k, v in override.items() if k in OVERRIDABLE})
    return result


def _coerce(key: str, value: str):
    if key == "max_age_days":
        return int(value)
    if value.lower() in ("null", "none", ""):
        return None
    return value


def _validate(key: str, value) -> None:
    if key == "capture_mode" and value not in CAPTURE_MODES:
        raise ValueError(f"capture_mode must be one of {sorted(CAPTURE_MODES)}")
    if key == "redaction" and value not in ("off", "on"):
        raise ValueError("redaction must be 'off' or 'on'")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show", help="print the merged config")
    g = sub.add_parser("get", help="print one value")
    g.add_argument("key")
    g.add_argument("--bundle", help="apply per-bundle override for this path")
    s = sub.add_parser("set", help="set a top-level value")
    s.add_argument("key")
    s.add_argument("value")
    b = sub.add_parser("set-bundle", help="set a per-bundle override")
    b.add_argument("bundle")
    b.add_argument("key")
    b.add_argument("value")
    sub.add_parser("init", help="write a default config if none exists")
    sub.add_parser("self-test")
    args = ap.parse_args()

    if args.cmd == "self-test":
        return _self_test()
    if args.cmd == "init":
        if config_path().is_file():
            print(f"config already at {config_path()}")
        else:
            save(dict(DEFAULTS))
            print(f"wrote defaults to {config_path()}")
        return 0
    cfg = load()
    if args.cmd == "show":
        print(json.dumps(cfg, indent=2))
        return 0
    if args.cmd == "get":
        print(json.dumps(effective(cfg, args.bundle).get(args.key)))
        return 0
    if args.cmd == "set":
        value = _coerce(args.key, args.value)
        _validate(args.key, value)
        cfg[args.key] = value
        save(cfg)
        print(f"{args.key} = {value}")
        return 0
    if args.cmd == "set-bundle":
        if args.key not in OVERRIDABLE:
            print(f"error: {args.key} is not overridable per bundle ({sorted(OVERRIDABLE)})", file=sys.stderr)
            return 2
        value = _coerce(args.key, args.value)
        _validate(args.key, value)
        key = str(Path(args.bundle).resolve())
        cfg.setdefault("bundles", {}).setdefault(key, {})[args.key] = value
        save(cfg)
        print(f"{key}: {args.key} = {value}")
        return 0
    return 0


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OKF_CONFIG"] = str(Path(tmp) / "config.json")
        cfg = load()
        assert cfg["capture_mode"] == "off"
        cfg["capture_mode"] = "on-demand"
        cfg.setdefault("bundles", {})[str(Path(tmp).resolve())] = {"redaction": "on"}
        save(cfg)
        reloaded = load()
        assert reloaded["capture_mode"] == "on-demand"
        assert effective(reloaded)["redaction"] == "off"
        assert effective(reloaded, tmp)["redaction"] == "on"
    print("okf_config self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

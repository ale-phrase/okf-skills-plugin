#!/usr/bin/env python3
"""Stop hook: stage a finished session for later OKF capture.

Passive capture is opt-in. When capture_mode is off (default) this no-ops. For
any other mode it appends a pointer to the session transcript onto a local queue
(~/.okf/capture-queue.jsonl). The queue is drained by the okf-capture skill (or a
scheduled run), which is where the actual judgment, redaction, and git behavior
happen — the hook never invokes a model or commits anything. Non-fatal on error.
"""

from __future__ import annotations

import fcntl
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        import okf_config

        cfg = okf_config.load()
        cwd = payload.get("cwd")
        mode = okf_config.effective(cfg, cwd).get("capture_mode", "off")
        if mode == "off":
            return 0

        queue = okf_config.config_path().parent / "capture-queue.jsonl"
        queue.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "session_id": payload.get("session_id"),
            "transcript_path": payload.get("transcript_path"),
            "cwd": cwd,
            "mode": mode,
        }
        # Shares a lock with okf_dequeue.py so a drain's read-modify-write
        # can't lose an append that lands mid-drain.
        lock_path = queue.with_suffix(queue.suffix + ".lock")
        with open(lock_path, "w") as lockfh:
            fcntl.flock(lockfh, fcntl.LOCK_EX)
            try:
                # Dedupe: skip if the last queued entry is the same transcript.
                if queue.exists():
                    try:
                        last = queue.read_text(encoding="utf-8").strip().splitlines()[-1]
                        if json.loads(last).get("transcript_path") == record["transcript_path"]:
                            return 0
                    except Exception:
                        pass
                with queue.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record) + "\n")
            finally:
                fcntl.flock(lockfh, fcntl.LOCK_UN)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

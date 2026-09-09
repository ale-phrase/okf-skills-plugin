#!/usr/bin/env python3
"""Remove specific already-processed lines from the capture queue.

Read raw lines to remove from stdin (exact text as they appeared in
capture-queue.jsonl — copy them verbatim when you read the queue, don't
reconstruct). Holds the same flock okf_stage.py uses before rewriting, so a
concurrent Stop-hook append can't be lost to a blind truncate: lines added
after you read the queue just aren't in your removal set and survive.
"""

from __future__ import annotations

import fcntl
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import okf_config


def main() -> int:
    to_remove = [line.rstrip("\n") for line in sys.stdin if line.strip()]
    if not to_remove:
        print("no lines given, nothing to clear")
        return 0

    queue = okf_config.config_path().parent / "capture-queue.jsonl"
    if not queue.exists():
        print("queue missing, nothing to clear")
        return 0

    remaining_to_remove = list(to_remove)
    lock_path = queue.with_suffix(queue.suffix + ".lock")
    with open(lock_path, "w") as lockfh:
        fcntl.flock(lockfh, fcntl.LOCK_EX)
        try:
            lines = queue.read_text(encoding="utf-8").splitlines()
            kept = []
            for line in lines:
                if line in remaining_to_remove:
                    remaining_to_remove.remove(line)
                else:
                    kept.append(line)
            tmp = queue.with_suffix(queue.suffix + ".tmp")
            tmp.write_text("".join(l + "\n" for l in kept), encoding="utf-8")
            os.replace(tmp, queue)
        finally:
            fcntl.flock(lockfh, fcntl.LOCK_UN)

    removed = len(to_remove) - len(remaining_to_remove)
    print(f"cleared {removed}/{len(to_remove)} processed lines, {len(kept)} remain in queue")
    if remaining_to_remove:
        print(f"warning: {len(remaining_to_remove)} line(s) to remove were not found in the queue (already cleared?)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

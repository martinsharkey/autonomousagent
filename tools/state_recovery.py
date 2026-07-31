#!/usr/bin/env python3
"""Durable state verification and recovery tool.

Snapshots critical state files (goals, config, audit log) to a local backup,
verifies integrity via SHA-256 checksums, and restores from the last valid
snapshot when corruption or missing state is detected.
"""

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

# Directories to snapshot (relative to project root)
STATE_DIRS = [
    "core/goals.py",
    "core/agent_config.py",
    "governance/audit_log.py",
]

SNAPSHOT_DIR = Path(".state_snapshots")
SNAPSHOT_INTERVAL = 3600  # seconds


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot_state() -> None:
    """Create a snapshot of critical state files."""
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    timestamp = int(time.time())
    snapshot_path = SNAPSHOT_DIR / f"snapshot_{timestamp}.json"
    snapshot = {}
    for rel_path in STATE_DIRS:
        src = Path(rel_path)
        if src.exists():
            snapshot[rel_path] = {
                "content": src.read_text(encoding="utf-8"),
                "checksum": _sha256_file(src),
            }
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    # Keep only the last 5 snapshots
    snapshots = sorted(SNAPSHOT_DIR.glob("snapshot_*.json"))
    for old in snapshots[:-5]:
        old.unlink()


def _verify_state() -> bool:
    """Verify that all state files exist and match the latest snapshot checksums."""
    snapshots = sorted(SNAPSHOT_DIR.glob("snapshot_*.json"))
    if not snapshots:
        return True  # No snapshot yet, assume OK
    latest = snapshots[-1]
    with open(latest, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    for rel_path, info in snapshot.items():
        src = Path(rel_path)
        if not src.exists():
            return False
        if _sha256_file(src) != info["checksum"]:
            return False
    return True


def _restore_from_snapshot() -> bool:
    """Restore state files from the latest valid snapshot."""
    snapshots = sorted(SNAPSHOT_DIR.glob("snapshot_*.json"))
    if not snapshots:
        return False
    # Find the most recent snapshot that has all files
    for snapshot_path in reversed(snapshots):
        with open(snapshot_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        valid = True
        for rel_path, info in snapshot.items():
            if "content" not in info or "checksum" not in info:
                valid = False
                break
            # Verify checksum of stored content
            content_hash = hashlib.sha256(info["content"].encode("utf-8")).hexdigest()
            if content_hash != info["checksum"]:
                valid = False
                break
        if not valid:
            continue
        # Restore all files from this snapshot
        for rel_path, info in snapshot.items():
            dst = Path(rel_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(info["content"], encoding="utf-8")
        return True
    return False


def run_recovery() -> dict:
    """Main entry point: verify state, snapshot if needed, and recover if corrupted."""
    result = {"status": "ok", "action": "none", "details": {}}

    # Check if any state file is missing or corrupted
    if not _verify_state():
        if _restore_from_snapshot():
            result["status"] = "recovered"
            result["action"] = "restored_from_snapshot"
            result["details"] = {"message": "State restored from latest valid snapshot."}
        else:
            result["status"] = "failed"
            result["action"] = "no_valid_snapshot"
            result["details"] = {"message": "No valid snapshot available for recovery."}
    else:
        # State is healthy; create a new snapshot if interval has passed
        last_snapshot = None
        snapshots = sorted(SNAPSHOT_DIR.glob("snapshot_*.json"))
        if snapshots:
            last_snapshot = snapshots[-1]
        if last_snapshot is None or (time.time() - last_snapshot.stat().st_mtime) > SNAPSHOT_INTERVAL:
            _snapshot_state()
            result["action"] = "snapshot_created"
            result["details"] = {"message": "New state snapshot created."}
        else:
            result["action"] = "no_action"
            result["details"] = {"message": "State is healthy and snapshot is recent."}

    return result


if __name__ == "__main__":
    print(json.dumps(run_recovery(), indent=2))

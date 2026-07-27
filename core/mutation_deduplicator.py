"""Mutation deduplicator to prevent repeated proposals (e.g., temperature spam)."""

from __future__ import annotations

import hashlib
import json
import glob
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class MutationDeduplicator:
    """Prevent proposing the same mutation repeatedly (loop detection)."""

    def __init__(self, history_dir: str = "evolution/mutations", window_hours: int = 24):
        self.history_dir = history_dir
        self.window_hours = window_hours
        self.proposed_cache: Dict[str, datetime] = {}

    def _mutation_fingerprint(self, mutation: Dict[str, Any]) -> str:
        """Create fingerprint of mutation (ignores ID, timestamp)."""
        key = (
            mutation.get("agent_name"),
            mutation.get("mutation_type"),
            json.dumps(mutation.get("proposed_changes"), sort_keys=True),
        )
        return hashlib.sha256(str(key).encode()).hexdigest()

    def should_propose(self, mutation: Dict[str, Any]) -> bool:
        """Check if this mutation should be proposed."""
        fingerprint = self._mutation_fingerprint(mutation)

        if fingerprint in self.proposed_cache:
            last_proposed = self.proposed_cache[fingerprint]
            if datetime.now() - last_proposed < timedelta(hours=self.window_hours):
                return False

        similar = self._find_similar_recent(fingerprint)
        if similar:
            last_proposed = similar[-1]["timestamp"]
            if isinstance(last_proposed, str):
                try:
                    last_proposed = datetime.fromisoformat(last_proposed)
                except ValueError:
                    last_proposed = datetime.now() - timedelta(days=2)
            if datetime.now() - last_proposed < timedelta(hours=self.window_hours):
                return False

        self.proposed_cache[fingerprint] = datetime.now()
        return True

    def _find_similar_recent(self, fingerprint: str) -> List[Dict[str, Any]]:
        """Find similar mutations proposed recently."""
        cutoff = datetime.now() - timedelta(hours=self.window_hours)
        similar: List[Dict[str, Any]] = []

        try:
            files = sorted(glob.glob(f"{self.history_dir}/mutation_*.json"), reverse=True)
        except Exception:
            return similar

        for mutation_file in files:
            try:
                with open(mutation_file, "r") as f:
                    mut = json.load(f)
                mut_ts = mut.get("timestamp")
                if mut_ts:
                    try:
                        ts = datetime.fromisoformat(mut_ts)
                    except ValueError:
                        continue
                    if ts < cutoff:
                        break
                    if ts > datetime.now():
                        continue

                other_fp = hashlib.sha256(
                    str(
                        (
                            mut.get("agent_name"),
                            mut.get("mutation_type"),
                            json.dumps(mut.get("proposed_changes"), sort_keys=True),
                        )
                    ).encode()
                ).hexdigest()
                if other_fp == fingerprint:
                    similar.append(mut)
            except Exception:
                continue

        return similar

    def record_proposed(self, mutation: Dict[str, Any]) -> None:
        """Record that this mutation was proposed."""
        fingerprint = self._mutation_fingerprint(mutation)
        self.proposed_cache[fingerprint] = datetime.now()

    def clear(self) -> None:
        """Clear the proposed cache."""
        self.proposed_cache.clear()


_deduplicator = None


def get_deduplicator() -> MutationDeduplicator:
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = MutationDeduplicator()
    return _deduplicator

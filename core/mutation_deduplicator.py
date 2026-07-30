"""Mutation deduplicator to prevent repeated proposals (e.g., temperature spam).

Now with file-based persistence so dedup state survives daemon restarts.
"""

from __future__ import annotations

import hashlib
import json
import glob
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


DEDUP_CACHE_FILE = "evolution/dedup_cache.json"


class MutationDeduplicator:
    """Prevent proposing the same mutation repeatedly (loop detection)."""

    def __init__(self, history_dir: str = "evolution/mutations", window_hours: int = 168):
        """
        Args:
            history_dir: Directory containing mutation JSON files.
            window_hours: Hours to remember a fingerprint (default 168 = 7 days).
        """
        self.history_dir = history_dir
        self.window_hours = window_hours
        self.proposed_cache: Dict[str, str] = {}  # fingerprint -> ISO timestamp
        self._load_cache()

    def _cache_path(self) -> str:
        return DEDUP_CACHE_FILE

    def _load_cache(self) -> None:
        """Load persistent cache from disk."""
        try:
            path = self._cache_path()
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                cutoff = datetime.now() - timedelta(hours=self.window_hours)
                for fp, ts_str in data.items():
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if ts > cutoff:
                            self.proposed_cache[fp] = ts_str
                    except (ValueError, TypeError):
                        continue
        except Exception:
            pass

    def _save_cache(self) -> None:
        """Persist cache to disk."""
        try:
            path = self._cache_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.proposed_cache, f, indent=2)
        except Exception:
            pass

    def _mutation_fingerprint(self, mutation: Dict[str, Any]) -> str:
        """Create fingerprint of mutation (ignores ID, timestamp).
        
        Uses description + mutation_type + agent for broader dedup
        (not just proposed_changes, which can vary slightly).
        """
        key = (
            mutation.get("agent_name"),
            mutation.get("mutation_type"),
            mutation.get("description", "")[:80],  # Truncate for fuzzy match
        )
        return hashlib.sha256(str(key).encode()).hexdigest()

    def _strict_fingerprint(self, mutation: Dict[str, Any]) -> str:
        """Strict fingerprint including proposed_changes."""
        key = (
            mutation.get("agent_name"),
            mutation.get("mutation_type"),
            json.dumps(mutation.get("proposed_changes"), sort_keys=True),
        )
        return hashlib.sha256(str(key).encode()).hexdigest()

    def should_propose(self, mutation: Dict[str, Any]) -> bool:
        """Check if this mutation should be proposed (not a duplicate)."""
        # Check both broad (description-based) and strict (changes-based) fingerprints
        fingerprint = self._mutation_fingerprint(mutation)
        strict_fp = self._strict_fingerprint(mutation)

        now = datetime.now()
        cutoff = now - timedelta(hours=self.window_hours)

        for fp in (fingerprint, strict_fp):
            if fp in self.proposed_cache:
                try:
                    last_proposed = datetime.fromisoformat(self.proposed_cache[fp])
                    if last_proposed > cutoff:
                        return False
                except (ValueError, TypeError):
                    pass

        # Also check mutation files on disk for the strict fingerprint
        similar = self._find_similar_recent(strict_fp)
        if similar:
            last_proposed = similar[-1].get("timestamp")
            if isinstance(last_proposed, str):
                try:
                    last_dt = datetime.fromisoformat(last_proposed)
                    if now - last_dt < timedelta(hours=self.window_hours):
                        # Cache this to avoid re-scanning disk
                        self.proposed_cache[strict_fp] = last_proposed
                        self._save_cache()
                        return False
                except ValueError:
                    pass

        return True

    def _find_similar_recent(self, fingerprint: str) -> List[Dict[str, Any]]:
        """Find similar mutations proposed recently."""
        cutoff = datetime.now() - timedelta(hours=self.window_hours)
        similar: List[Dict[str, Any]] = []

        try:
            files = sorted(glob.glob(f"{self.history_dir}/mutation_*.json"), reverse=True)
        except Exception:
            return similar

        # Only scan last 50 files max to avoid O(n) on 1000+ files
        for mutation_file in files[:50]:
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
        now_str = datetime.now().isoformat()
        fingerprint = self._mutation_fingerprint(mutation)
        strict_fp = self._strict_fingerprint(mutation)
        self.proposed_cache[fingerprint] = now_str
        self.proposed_cache[strict_fp] = now_str
        self._save_cache()

    def clear(self) -> None:
        """Clear the proposed cache."""
        self.proposed_cache.clear()
        self._save_cache()

    def get_stats(self) -> Dict[str, Any]:
        """Return dedup statistics."""
        return {
            "cached_fingerprints": len(self.proposed_cache),
            "window_hours": self.window_hours,
        }


_deduplicator = None


def get_deduplicator() -> MutationDeduplicator:
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = MutationDeduplicator()
    return _deduplicator

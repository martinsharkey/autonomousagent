"""Mutation deduplicator to prevent repeated proposals.

Features:
- File-based persistence (survives restarts)
- Rejected mutations get a 30-day cooldown (not just 7 days)
- Deferred mutations stored with reason + defer-until date
- Broad fuzzy matching (description similarity) + strict exact match
- Scales: only scans last 50 mutation files, rest from cache
"""

from __future__ import annotations

import hashlib
import json
import glob
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


DEDUP_CACHE_FILE = "evolution/dedup_cache.json"
DEFERRED_CACHE_FILE = "evolution/deferred_mutations.json"

# Window for normal proposals (7 days)
DEFAULT_WINDOW_HOURS = 168
# Cooldown for rejected/failed mutations (30 days)
REJECTED_COOLDOWN_HOURS = 720


class MutationDeduplicator:
    """Prevent proposing the same mutation repeatedly (loop detection)."""

    def __init__(self, history_dir: str = "evolution/mutations", window_hours: int = DEFAULT_WINDOW_HOURS):
        """
        Args:
            history_dir: Directory containing mutation JSON files.
            window_hours: Hours to remember a fingerprint (default 168 = 7 days).
        """
        self.history_dir = history_dir
        self.window_hours = window_hours
        self.proposed_cache: Dict[str, str] = {}  # fingerprint -> ISO timestamp
        self.deferred_cache: Dict[str, Dict[str, str]] = {}  # fingerprint -> {until, reason}
        self._load_cache()
        self._load_deferred()

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

    def _load_deferred(self) -> None:
        """Load deferred mutations cache (rejected/failed with long cooldown)."""
        try:
            if os.path.exists(DEFERRED_CACHE_FILE):
                with open(DEFERRED_CACHE_FILE, "r") as f:
                    data = json.load(f)
                now = datetime.now()
                for fp, info in data.items():
                    try:
                        until = datetime.fromisoformat(info.get("until", ""))
                        if until > now:
                            self.deferred_cache[fp] = info
                    except (ValueError, TypeError):
                        continue
        except Exception:
            pass

    def _save_deferred(self) -> None:
        """Persist deferred cache to disk."""
        try:
            os.makedirs(os.path.dirname(DEFERRED_CACHE_FILE), exist_ok=True)
            with open(DEFERRED_CACHE_FILE, "w") as f:
                json.dump(self.deferred_cache, f, indent=2)
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
        """Check if this mutation should be proposed (not a duplicate or deferred)."""
        fingerprint = self._mutation_fingerprint(mutation)
        strict_fp = self._strict_fingerprint(mutation)

        now = datetime.now()
        cutoff = now - timedelta(hours=self.window_hours)

        # Check deferred cache first (rejected/failed mutations with long cooldown)
        for fp in (fingerprint, strict_fp):
            if fp in self.deferred_cache:
                try:
                    until = datetime.fromisoformat(self.deferred_cache[fp].get("until", ""))
                    if until > now:
                        return False  # Still in cooldown
                except (ValueError, TypeError):
                    pass

        # Check normal proposal cache (7-day window)
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
                        self.proposed_cache[strict_fp] = last_proposed
                        self._save_cache()
                        return False
                except ValueError:
                    pass

        return True

    def defer_mutation(self, mutation, reason: str,
                       cooldown_hours: int = REJECTED_COOLDOWN_HOURS) -> None:
        """
        Defer a rejected/failed mutation so it won't be re-proposed for a long time.
        
        Args:
            mutation: The mutation dict or Mutation object (auto-converts via .to_dict())
            reason: Why it was deferred (rejection reason, failure reason)
            cooldown_hours: How long to defer (default 30 days)
        """
        # Accept both Mutation objects and plain dicts
        if hasattr(mutation, 'to_dict'):
            mutation = mutation.to_dict()
        fingerprint = self._mutation_fingerprint(mutation)
        strict_fp = self._strict_fingerprint(mutation)
        until = (datetime.now() + timedelta(hours=cooldown_hours)).isoformat()
        
        info = {
            "until": until,
            "reason": reason[:200],
            "deferred_at": datetime.now().isoformat(),
            "description": mutation.get("description", "")[:100],
        }
        
        self.deferred_cache[fingerprint] = info
        self.deferred_cache[strict_fp] = info
        self._save_deferred()

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

import os
import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.state_replicator import StateReplicator


class SelfHealer:
    """Detect and repair corrupted local state using replicated copies."""

    def __init__(self, primary_path: str = ".", replicas: Optional[List[str]] = None):
        self.replicator = StateReplicator(primary_path=primary_path, replicas=replicas)
        self.watch_paths = [
            "data/goals.db",
            "data/agent_config.db",
            "council_memory.db",
        ]

    def register_defaults(self):
        for db_file in self.watch_paths:
            self.replicator.register_replica(db_file)

    def verify_all(self) -> Dict[str, Any]:
        results = {}
        for db_file in self.watch_paths:
            results[db_file] = self.replicator.verify(db_file)
        return results

    def heal_all(self) -> Dict[str, Any]:
        results = {}
        for db_file in self.watch_paths:
            results[db_file] = self.replicator.heal(db_file)
        return results

    def auto_maintain(self) -> Dict[str, Any]:
        """Run verification and heal any unhealthy databases."""
        results = {"verified": self.verify_all()}
        heal_targets = [db for db, info in results["verified"].items() if info.get("status") != "healthy"]
        if heal_targets:
            results["healed"] = self.heal_all()
        else:
            results["healed"] = {}
        return results

import json
import sqlite3
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class VolunteerNode:
    node_id: str
    endpoint: str
    capabilities: List[str] = field(default_factory=list)
    joined_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_seen: Optional[str] = None
    task_count: int = 0
    reputation: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class DistributedComputeGrid:
    """Minimal ethical volunteer-compute grid for council tasks."""

    def __init__(self, db_path: str = "data/distributed_grid.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_db()
        self.volunteers: Dict[str, VolunteerNode] = {}

    def _ensure_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                last_seen TEXT,
                task_count INTEGER DEFAULT 0,
                reputation REAL DEFAULT 0.0,
                metadata TEXT
            )
        """)
        conn.commit()
        conn.close()

    def register_volunteer(self, node: VolunteerNode) -> bool:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO nodes (node_id, endpoint, capabilities, joined_at, last_seen, task_count, reputation, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                node.node_id,
                node.endpoint,
                json.dumps(node.capabilities),
                node.joined_at,
                node.last_seen,
                node.task_count,
                node.reputation,
                json.dumps(node.metadata),
            ),
        )
        conn.commit()
        conn.close()
        self.volunteers[node.node_id] = node
        return True

    def record_task(self, node_id: str, result: Dict[str, Any]) -> bool:
        node = self.volunteers.get(node_id)
        if not node:
            return False
        node.task_count += 1
        node.last_seen = datetime.utcnow().isoformat()
        success = result.get("status") == "completed"
        node.reputation = max(-1.0, min(1.0, node.reputation + (0.05 if success else -0.05)))
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE nodes SET last_seen = ?, task_count = ?, reputation = ? WHERE node_id = ?",
            (node.last_seen, node.task_count, node.reputation, node_id),
        )
        conn.commit()
        conn.close()
        return True

    def list_volunteers(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.execute("SELECT node_id, endpoint, capabilities, joined_at, last_seen, task_count, reputation, metadata FROM nodes")
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "node_id": r[0],
                "endpoint": r[1],
                "capabilities": json.loads(r[2]),
                "joined_at": r[3],
                "last_seen": r[4],
                "task_count": r[5],
                "reputation": r[6],
                "metadata": json.loads(r[7]),
            }
            for r in rows
        ]

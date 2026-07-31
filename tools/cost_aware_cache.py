import json
import time
import hashlib
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

class CostAwareCache:
    """Persistent cache for LLM responses with TTL and cost tracking."""

    def __init__(self, db_path: str = "data/cache.db", default_ttl: int = 3600):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    cost REAL NOT NULL DEFAULT 0.0,
                    provider TEXT NOT NULL DEFAULT 'unknown'
                )
            """)
            conn.commit()

    def _make_key(self, prompt: str, model: str, params: Optional[Dict] = None) -> str:
        payload = {"prompt": prompt, "model": model, "params": params or {}}
        serialized = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(serialized).hexdigest()

    def get(self, prompt: str, model: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        key = self._make_key(prompt, model, params)
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT response, created_at, expires_at, cost, provider FROM cache WHERE key = ?",
                (key,)
            ).fetchone()
        if row is None:
            return None
        response, created_at, expires_at, cost, provider = row
        if now > expires_at:
            self.delete(key)
            return None
        return {
            "response": json.loads(response),
            "created_at": created_at,
            "expires_at": expires_at,
            "cost": cost,
            "provider": provider,
            "cached": True
        }

    def set(self, prompt: str, model: str, response: Any, cost: float = 0.0, provider: str = "unknown", ttl: Optional[int] = None) -> str:
        key = self._make_key(prompt, model, {})
        now = time.time()
        expires_at = now + (ttl if ttl is not None else self.default_ttl)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO cache (key, response, created_at, expires_at, cost, provider)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (key, json.dumps(response), now, expires_at, cost, provider)
            )
            conn.commit()
        return key

    def delete(self, key: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()

    def clear_expired(self) -> int:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache WHERE expires_at < ?", (now,))
            conn.commit()
            return cursor.rowcount

    def get_total_cost(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT SUM(cost) FROM cache").fetchone()
            return row[0] if row and row[0] else 0.0

    def get_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            expired = conn.execute("SELECT COUNT(*) FROM cache WHERE expires_at < ?", (time.time(),)).fetchone()[0]
            cost = self.get_total_cost()
        return {"total_entries": total, "expired_entries": expired, "total_cost": cost}

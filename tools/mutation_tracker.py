"""Mutation outcome tracker - logs and analyzes mutation results for recursive self-evolution."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/mutation_tracker.db")

class MutationTracker:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS mutations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mutation_type TEXT NOT NULL,
                description TEXT,
                success INTEGER NOT NULL,
                failure_reason TEXT,
                extracted_patterns TEXT,
                risk_level TEXT
            )
        """)
        self.conn.commit()

    def log_mutation(self, mutation_type, description, success, failure_reason=None, extracted_patterns=None, risk_level=None):
        self.conn.execute(
            "INSERT INTO mutations (timestamp, mutation_type, description, success, failure_reason, extracted_patterns, risk_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), mutation_type, description, 1 if success else 0, failure_reason, json.dumps(extracted_patterns) if extracted_patterns else None, risk_level)
        )
        self.conn.commit()

    def get_success_rate(self, window_hours=24):
        cursor = self.conn.execute(
            "SELECT success FROM mutations WHERE timestamp > datetime('now', ?)",
            (f'-{window_hours} hours',)
        )
        results = cursor.fetchall()
        if not results:
            return 0.0
        return sum(r[0] for r in results) / len(results)

    def get_common_failures(self, limit=5):
        cursor = self.conn.execute(
            "SELECT failure_reason, COUNT(*) as cnt FROM mutations WHERE success=0 AND failure_reason IS NOT NULL GROUP BY failure_reason ORDER BY cnt DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()

    def close(self):
        self.conn.close()

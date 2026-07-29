import sqlite3
import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class PersistentMemory:
    def __init__(self, db_path: str = "council_memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                session_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                context_value TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(agent_name, session_id, context_key)
            )
        """)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS agent_context_fts USING fts5(
                agent_name, session_id, context_key, context_value,
                content='agent_context',
                content_rowid='id'
            )
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS agent_context_ai AFTER INSERT ON agent_context BEGIN
                INSERT INTO agent_context_fts(rowid, agent_name, session_id, context_key, context_value)
                VALUES (new.id, new.agent_name, new.session_id, new.context_key, new.context_value);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS agent_context_ad AFTER DELETE ON agent_context BEGIN
                INSERT INTO agent_context_fts(agent_context_fts, rowid, agent_name, session_id, context_key, context_value)
                VALUES ('delete', old.id, old.agent_name, old.session_id, old.context_key, old.context_value);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS agent_context_au AFTER UPDATE ON agent_context BEGIN
                INSERT INTO agent_context_fts(agent_context_fts, rowid, agent_name, session_id, context_key, context_value)
                VALUES ('delete', old.id, old.agent_name, old.session_id, old.context_key, old.context_value);
                INSERT INTO agent_context_fts(rowid, agent_name, session_id, context_key, context_value)
                VALUES (new.id, new.agent_name, new.session_id, new.context_key, new.context_value);
            END
        """)
        self.conn.commit()

    def store_context(self, agent_name: str, session_id: str, key: str, value: str):
        cursor = self.conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO agent_context (agent_name, session_id, context_key, context_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, session_id, key, value, timestamp))
        self.conn.commit()

    def retrieve_context(self, agent_name: str, session_id: str, key: str) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT context_value FROM agent_context
            WHERE agent_name = ? AND session_id = ? AND context_key = ?
        """, (agent_name, session_id, key))
        row = cursor.fetchone()
        return row[0] if row else None

    def search_context(self, query: str, limit: int = 10) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT agent_name, session_id, context_key, context_value
            FROM agent_context_fts
            WHERE agent_context_fts MATCH ?
            LIMIT ?
        """, (query, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_agent_history(self, agent_name: str, session_id: str, limit: int = 50) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT context_key, context_value, timestamp
            FROM agent_context
            WHERE agent_name = ? AND session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_name, session_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_context(self, agent_name: str, limit: int = 5) -> List[Dict]:
        """Get most recent context entries for an agent across all sessions."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT context_key, context_value, timestamp
            FROM agent_context
            WHERE agent_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_name, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_memory_summary(self, agent_name: str) -> str:
        """Get a formatted summary for injection into agent prompts."""
        recent = self.get_recent_context(agent_name, limit=5)
        if not recent:
            return "No previous memory available."
        lines = ["Recent memory:"]
        for entry in recent:
            lines.append(f"- [{entry['timestamp'][:16]}] {entry['context_key']}: {entry['context_value'][:100]}")
        return "\n".join(lines)

    def close(self):
        self.conn.close()

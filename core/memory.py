import sqlite3
import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class PersistentMemory:
    """Persistent memory store for council agents.
    
    Provides cross-session memory so agents remember what happened
    in previous cycles, what mutations were proposed/rejected, and
    what the operator communicated.
    """
    
    def __init__(self, db_path: str = "council_memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
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
        """Store a context entry for an agent."""
        cursor = self.conn.cursor()
        timestamp = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO agent_context (agent_name, session_id, context_key, context_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, session_id, key, value, timestamp))
        self.conn.commit()

    def retrieve_context(self, agent_name: str, session_id: str, key: str) -> Optional[str]:
        """Retrieve a specific context value."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT context_value FROM agent_context
            WHERE agent_name = ? AND session_id = ? AND context_key = ?
        """, (agent_name, session_id, key))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_recent_context(self, agent_name: str, limit: int = 10) -> List[Dict]:
        """Get most recent context entries for an agent across ALL sessions.
        
        This is the key method for cross-session memory — it returns
        what happened in recent cycles regardless of session_id.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT context_key, context_value, timestamp, session_id
            FROM agent_context
            WHERE agent_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_name, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_memory_summary(self, agent_name: str, max_chars: int = 1500) -> str:
        """Get a formatted memory summary suitable for injection into agent prompts.
        
        Returns a concise text block summarizing what the agent did recently.
        """
        recent = self.get_recent_context(agent_name, limit=8)
        if not recent:
            return "No previous memory available. This appears to be a fresh start."
        
        lines = ["## Recent Memory (cross-session)"]
        total_chars = 0
        for entry in recent:
            ts = entry['timestamp'][:16] if entry.get('timestamp') else '?'
            key = entry.get('context_key', '?')
            value = entry.get('context_value', '')
            # Truncate individual values
            if len(value) > 200:
                value = value[:200] + "..."
            line = f"- [{ts}] {key}: {value}"
            total_chars += len(line)
            if total_chars > max_chars:
                lines.append("- [...older memory truncated...]")
                break
            lines.append(line)
        return "\n".join(lines)

    def search_context(self, query: str, limit: int = 10) -> List[Dict]:
        """Full-text search across all agent memory."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT agent_name, session_id, context_key, context_value
                FROM agent_context_fts
                WHERE agent_context_fts MATCH ?
                LIMIT ?
            """, (query, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            # FTS match can fail on invalid query syntax
            return []

    def get_agent_history(self, agent_name: str, session_id: str, limit: int = 50) -> List[Dict]:
        """Get history for a specific agent and session."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT context_key, context_value, timestamp
            FROM agent_context
            WHERE agent_name = ? AND session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_name, session_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def store_cycle_result(self, agent_name: str, cycle_count: int, goal_id: Optional[str],
                           status: str, reward: Optional[float], phase: Optional[str]):
        """Convenience method to store a cycle's outcome in memory."""
        summary = json.dumps({
            "goal_id": goal_id,
            "status": status,
            "reward": reward,
            "phase": phase,
        })
        self.store_context(
            agent_name=agent_name,
            session_id=f"cycle_{cycle_count}",
            key="cycle_result",
            value=summary
        )

    def store_mutation_outcome(self, agent_name: str, mutation_id: str,
                               description: str, outcome: str, reason: str = ""):
        """Store mutation proposal/rejection for learning."""
        summary = json.dumps({
            "mutation_id": mutation_id,
            "description": description,
            "outcome": outcome,
            "reason": reason,
        })
        self.store_context(
            agent_name=agent_name,
            session_id=f"mutation_{mutation_id[:12]}",
            key=f"mutation_{outcome}",
            value=summary
        )

    def close(self):
        self.conn.close()


# Global instance
_persistent_memory: Optional[PersistentMemory] = None


def get_persistent_memory() -> PersistentMemory:
    """Get or create the global persistent memory instance."""
    global _persistent_memory
    if _persistent_memory is None:
        _persistent_memory = PersistentMemory()
    return _persistent_memory

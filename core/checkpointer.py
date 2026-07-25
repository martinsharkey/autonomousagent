"""
SQLite-based durable checkpointer for LangGraph state persistence.
Replaces MemorySaver to ensure state survives process restarts.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import BaseMessage, messages_from_dict


class SQLiteCheckpointer:
    """Durable SQLite checkpointer for LangGraph state."""
    
    def __init__(self, db_path: str = "./checkpoints/council_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                state_json TEXT NOT NULL,
                PRIMARY KEY (thread_id, checkpoint_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thread_metadata (
                thread_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                metadata_json TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def put(self, thread_id: str, checkpoint_id: str, state: Dict[str, Any]) -> None:
        """Save a checkpoint for a thread."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        state_json = self._serialize_state(state)
        timestamp = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_id, timestamp, state_json)
            VALUES (?, ?, ?, ?)
        """, (thread_id, checkpoint_id, timestamp, state_json))
        
        cursor.execute("""
            INSERT OR REPLACE INTO thread_metadata (thread_id, created_at, last_updated, metadata_json)
            VALUES (?, ?, ?, ?)
        """, (thread_id, timestamp, timestamp, json.dumps({})))
        
        conn.commit()
        conn.close()
    
    def get_tuple(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve a checkpoint for a thread."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if checkpoint_id:
            cursor.execute("""
                SELECT checkpoint_id, timestamp, state_json
                FROM checkpoints
                WHERE thread_id = ? AND checkpoint_id = ?
            """, (thread_id, checkpoint_id))
        else:
            cursor.execute("""
                SELECT checkpoint_id, timestamp, state_json
                FROM checkpoints
                WHERE thread_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (thread_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            checkpoint_id, timestamp, state_json = row
            state = self._deserialize_state(state_json)
            return {
                "checkpoint_id": checkpoint_id,
                "timestamp": timestamp,
                "state": state
            }
        
        return None
    
    def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest state for a thread."""
        result = self.get_tuple(thread_id)
        return result["state"] if result else None
    
    def list_threads(self) -> list:
        """List all thread IDs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT thread_id FROM thread_metadata ORDER BY last_updated DESC")
        threads = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return threads
    
    def delete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM thread_metadata WHERE thread_id = ?", (thread_id,))
        
        conn.commit()
        conn.close()
    
    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """Serialize state to JSON, handling LangChain messages."""
        serializable = {}
        for key, value in state.items():
            if key == "messages" and isinstance(value, list):
                serializable[key] = [
                    {
                        "type": "human" if hasattr(msg, "type") and msg.type == "human" else "ai",
                        "content": msg.content if hasattr(msg, "content") else str(msg)
                    }
                    for msg in value
                ]
            else:
                serializable[key] = value
        
        return json.dumps(serializable)
    
    def _deserialize_state(self, state_json: str) -> Dict[str, Any]:
        """Deserialize state from JSON, reconstructing LangChain messages."""
        state = json.loads(state_json)
        
        if "messages" in state:
            messages = []
            for msg_dict in state["messages"]:
                if msg_dict["type"] == "human":
                    from langchain_core.messages import HumanMessage
                    messages.append(HumanMessage(content=msg_dict["content"]))
                else:
                    from langchain_core.messages import AIMessage
                    messages.append(AIMessage(content=msg_dict["content"]))
            state["messages"] = messages
        
        return state


_global_checkpointer: Optional[SQLiteCheckpointer] = None


def get_checkpointer() -> SQLiteCheckpointer:
    """Get or create the global checkpointer instance."""
    global _global_checkpointer
    if _global_checkpointer is None:
        _global_checkpointer = SQLiteCheckpointer()
    return _global_checkpointer

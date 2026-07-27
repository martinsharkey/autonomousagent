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
from langgraph.checkpoint.base import BaseCheckpointSaver


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


class JSONCheckpointer(BaseCheckpointSaver):
    """JSON-based checkpointer that satisfies LangGraph BaseCheckpointSaver."""
    
    def __init__(self, filepath: str = "./checkpoints.json"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._data = {}
        self._load()
    
    def _load(self):
        if self.filepath.exists():
            with open(self.filepath, "r") as f:
                self._data = json.load(f)
        else:
            self._data = {"checkpoints": {}, "threads": {}}
    
    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump(self._data, f, indent=2)
    
    def _now(self):
        return datetime.utcnow().isoformat()
    
    def put(self, config, checkpoint, metadata):
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        self._data.setdefault("checkpoints", {})
        self._data.setdefault("threads", {})
        self._data["checkpoints"][f"{thread_id}:{checkpoint_id}"] = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "timestamp": self._now(),
            "checkpoint": checkpoint,
            "metadata": metadata or {},
        }
        self._data["threads"][thread_id] = {
            "created_at": self._now(),
            "last_updated": self._now(),
        }
        self._save()
    
    def get_tuple(self, config):
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoints = self._data.get("checkpoints", {})
        if checkpoint_id:
            key = f"{thread_id}:{checkpoint_id}"
            row = checkpoints.get(key)
        else:
            keys = [k for k in checkpoints if k.startswith(f"{thread_id}:")]
            row = checkpoints[max(keys, key=lambda k: checkpoints[k]["timestamp"])] if keys else None
        if not row:
            return None
        return {
            "checkpoint_id": row["checkpoint_id"],
            "timestamp": row["timestamp"],
            "checkpoint": row["checkpoint"],
            "metadata": row.get("metadata", {}),
        }
    
    def list(self, config=None, limit=None, offset=0):
        thread_id = config.get("configurable", {}).get("thread_id") if config else None
        threads = self._data.get("threads", {})
        items = []
        for tid, meta in threads.items():
            if thread_id and tid != thread_id:
                continue
            items.append({
                "thread_id": tid,
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("last_updated"),
                "metadata": {},
            })
        return items[offset: offset + limit] if limit else items[offset:]
    
    def put_writes(self, config, writes, task_id):
        pass
    
    def delete_thread(self, config):
        thread_id = config["configurable"]["thread_id"]
        self._data.get("threads", {}).pop(thread_id, None)
        for key in list(self._data.get("checkpoints", {}).keys()):
            if key.startswith(f"{thread_id}:"):
                self._data["checkpoints"].pop(key, None)
        self._save()
    
    async def aput(self, config, checkpoint, metadata):
        self.put(config, checkpoint, metadata)
    
    async def aget_tuple(self, config):
        return self.get_tuple(config)
    
    async def alist(self, config=None, limit=None, offset=0):
        return self.list(config, limit, offset)
    
    async def aput_writes(self, config, writes, task_id):
        self.put_writes(config, writes, task_id)
    
    async def adelete_thread(self, config):
        self.delete_thread(config)
    
    @staticmethod
    def get_next_version(current, kwargs):
        from langgraph.config import get_config
        return "1"
    
    def __len__(self):
        return len(self._data.get("checkpoints", {}))
    
    def count_threads(self):
        return len(self._data.get("threads", {}))
    
    def serialize_state(self, state):
        return {k: v for k, v in state.items()}
    
    def deserialize_state(self, data):
        return data


_global_checkpointer: Optional[SQLiteCheckpointer] = None


def get_checkpointer() -> SQLiteCheckpointer:
    """Get or create the global checkpointer instance."""
    global _global_checkpointer
    if _global_checkpointer is None:
        _global_checkpointer = SQLiteCheckpointer()
    return _global_checkpointer

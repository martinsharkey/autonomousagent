"""
Durable goal store for unified control plane.
SQLite-based storage for goals that survive restarts.
"""

import sqlite3
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class GoalPriority:
    """Named priority levels for goals.

    Higher value = higher priority. Goals are executed highest-first.
    Operator goals ALWAYS use CRITICAL or HIGH — they preempt council-generated goals.
    """
    CRITICAL = 100   # Survivability, operator directives, security incidents
    HIGH = 75        # Operator requests, blocking issues
    MEDIUM = 50      # Standard evolution work, improvements
    LOW = 25         # Exploration, curiosity, nice-to-haves
    BACKGROUND = 10  # Housekeeping, metrics, logging improvements

    @classmethod
    def from_source(cls, source: str, is_operator_critical: bool = False) -> int:
        """Determine default priority from goal source."""
        if is_operator_critical:
            return cls.CRITICAL
        if source == "human":
            return cls.HIGH
        if source == "evolution":
            return cls.MEDIUM
        if source == "curiosity":
            return cls.LOW
        return cls.MEDIUM

    @classmethod
    def label(cls, priority: int) -> str:
        """Get human-readable label for a priority value."""
        if priority >= cls.CRITICAL:
            return "CRITICAL"
        if priority >= cls.HIGH:
            return "HIGH"
        if priority >= cls.MEDIUM:
            return "MEDIUM"
        if priority >= cls.LOW:
            return "LOW"
        return "BACKGROUND"


class GoalSource(Enum):
    HUMAN = "human"
    CURIOSITY = "curiosity"
    EVOLUTION = "evolution"


class GoalStore:
    """SQLite-based durable goal store."""
    
    def __init__(self, db_path: str = "./goals/goals.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with goals table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                goal_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                assigned_agent TEXT,
                result_summary TEXT,
                reward REAL,
                metadata_json TEXT,
                mission_pillar INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_goal(
        self,
        description: str,
        source: str = "human",
        priority: int = 0,
        assigned_agent: Optional[str] = None,
        metadata: Optional[Dict] = None,
        mission_pillar: Optional[int] = None
    ) -> str:
        """Create a new goal and return goal_id."""
        goal_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO goals (goal_id, description, status, priority, source, 
                             created_at, updated_at, assigned_agent, metadata_json, mission_pillar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal_id,
            description,
            GoalStatus.PENDING.value,
            priority,
            source,
            now,
            now,
            assigned_agent,
            json.dumps(metadata or {}),
            mission_pillar
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[GOAL] Created goal {goal_id[:12]}...: {description[:50]}")
        return goal_id
    
    def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a goal by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM goals WHERE goal_id = ?", (goal_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return self._row_to_dict(row, cursor.description)
        return None
    
    def update_goal_status(
        self,
        goal_id: str,
        status: str,
        result_summary: Optional[str] = None,
        reward: Optional[float] = None
    ) -> bool:
        """Update goal status and optionally result/reward."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE goals
            SET status = ?, updated_at = ?, result_summary = ?, reward = ?
            WHERE goal_id = ?
        """, (status, now, result_summary, reward, goal_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        if success:
            print(f"[GOAL] Updated {goal_id[:12]}... to {status}")
        
        return success
    
    def assign_goal(self, goal_id: str, agent_name: str) -> bool:
        """Assign a goal to an agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE goals
            SET assigned_agent = ?, updated_at = ?
            WHERE goal_id = ?
        """, (agent_name, now, goal_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        return success
    
    def get_pending_goals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending goals ordered by priority (highest first)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM goals
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        """, (GoalStatus.PENDING.value, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, cursor.description) for row in rows]
    
    def get_open_goals(self) -> List[Dict[str, Any]]:
        """Get all open goals (pending or in_progress)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM goals
            WHERE status IN (?, ?)
            ORDER BY priority DESC, created_at ASC
        """, (GoalStatus.PENDING.value, GoalStatus.IN_PROGRESS.value))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, cursor.description) for row in rows]
    
    def get_completed_goals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently completed goals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM goals
            WHERE status IN (?, ?)
            ORDER BY updated_at DESC
            LIMIT ?
        """, (GoalStatus.COMPLETED.value, GoalStatus.FAILED.value, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, cursor.description) for row in rows]
    
    def get_recent_goals(self, limit: int = 20, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recently updated goals, optionally filtered by agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM goals
        """
        params: List[Any] = []
        if agent_name:
            query += " WHERE assigned_agent = ?"
            params.append(agent_name)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row, cursor.description) for row in rows]
    
    def get_status_summary(self) -> str:
        """Get a summary of goal status for Telegram /status command."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM goals
            GROUP BY status
        """)
        
        status_counts = dict(cursor.fetchall())
        conn.close()
        
        summary = f"Goals: {status_counts.get('pending', 0)} pending, "
        summary += f"{status_counts.get('in_progress', 0)} in progress, "
        summary += f"{status_counts.get('completed', 0)} completed, "
        summary += f"{status_counts.get('failed', 0)} failed"
        
        return summary
    
    def _row_to_dict(self, row: tuple, description: list) -> Dict[str, Any]:
        """Convert SQLite row to dictionary."""
        columns = [col[0] for col in description]
        data = dict(zip(columns, row))
        
        if data.get("metadata_json"):
            data["metadata"] = json.loads(data["metadata_json"])
        
        return data


_global_goal_store: Optional[GoalStore] = None


def get_goal_store() -> GoalStore:
    """Get or create the global goal store instance."""
    global _global_goal_store
    if _global_goal_store is None:
        _global_goal_store = GoalStore()
    return _global_goal_store

import json
from pathlib import Path
from datetime import datetime
import sqlite3
from typing import Dict, List, Optional

class DecisionLogger:
    """Append-only decision log. Every vote, test result, override logged."""
    
    def __init__(self, db_path: Path = Path("./logs/decisions.db")):
        self.db_path = db_path
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                mutation_id TEXT,
                council_member TEXT,
                model_used TEXT,
                vote TEXT,
                confidence REAL,
                metadata JSON,
                operator_override TEXT,
                operator_rationale TEXT,
                storage_path TEXT,
                storage_size_bytes INTEGER
            )
        """)
        conn.commit()
        conn.close()
    
    def log(self, decision_type: str, metadata: Dict, 
            mutation_id: str = None, council_member: str = None,
            model_used: str = None, vote: bool = None, 
            confidence: float = None, operator_override: str = None,
            operator_rationale: str = None):
        """Log a decision atomically"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO decision_log 
            (timestamp, decision_type, mutation_id, council_member, 
             model_used, vote, confidence, metadata, operator_override, operator_rationale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            decision_type,
            mutation_id,
            council_member,
            model_used,
            str(vote) if vote is not None else None,
            confidence,
            json.dumps(metadata),
            operator_override,
            operator_rationale
        ))
        
        conn.commit()
        conn.close()
    
    def get_audit_trail(self, mutation_id: str) -> List[Dict]:
        """Retrieve full decision chain for a mutation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM decision_log 
            WHERE mutation_id = ? 
            ORDER BY timestamp
        """, (mutation_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_all_decisions(self, limit: int = 100) -> List[Dict]:
        """Retrieve recent decisions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM decision_log 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_operator_overrides(self) -> List[Dict]:
        """Retrieve all operator override decisions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM decision_log 
            WHERE operator_override IS NOT NULL
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

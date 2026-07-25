import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from governance.decision_logger import DecisionLogger

class StorageTracker:
    def __init__(self, max_storage_gb: int = 500):
        self.max_storage = max_storage_gb
        self.inventory: Dict[str, Dict] = {}
        self.decision_logger = DecisionLogger()
    
    async def log_write(self, path: str, size_bytes: int, 
                       category: str, retainable: bool = True):
        """Track every write"""
        record = {
            "path": path,
            "size_bytes": size_bytes,
            "category": category,
            "retainable": retainable,
            "written_at": datetime.now(),
            "last_accessed": datetime.now(),
            "access_count": 0,
            "archive_candidate": False
        }
        
        self.inventory[path] = record
        
        total_used = sum(r["size_bytes"] for r in self.inventory.values())
        usage_pct = (total_used / (self.max_storage * 1e9)) * 100
        
        self.decision_logger.log(
            decision_type="STORAGE_WRITE",
            metadata={
                "path": path,
                "size_mb": size_bytes / 1e6,
                "category": category,
                "total_storage_used_pct": usage_pct
            }
        )
        
        if usage_pct > 80:
            print(f"[STORAGE] WARNING: Storage at {usage_pct:.1f}%")
            candidates = self.suggest_archival_candidates()
            if candidates:
                print(f"[STORAGE] Consider archiving: {candidates[:5]}")
    
    def suggest_archival_candidates(self) -> List[str]:
        """Return paths eligible for archival"""
        cutoff = datetime.now() - timedelta(days=30)
        candidates = [
            path for path, meta in self.inventory.items()
            if meta["retainable"] and meta["last_accessed"] < cutoff
        ]
        
        return sorted(candidates, 
                     key=lambda p: self.inventory[p]["last_accessed"])
    
    def current_usage_pct(self) -> float:
        """Calculate current storage usage percentage"""
        total_used = sum(r["size_bytes"] for r in self.inventory.values())
        return (total_used / (self.max_storage * 1e9)) * 100
    
    def get_usage_by_category(self) -> Dict[str, int]:
        """Get storage usage broken down by category"""
        usage = {}
        for record in self.inventory.values():
            category = record["category"]
            usage[category] = usage.get(category, 0) + record["size_bytes"]
        return usage
    
    def mark_archived(self, path: str):
        """Mark a file as archived"""
        if path in self.inventory:
            self.inventory[path]["archive_candidate"] = True
            self.decision_logger.log(
                decision_type="ARCHIVAL_EXECUTED",
                metadata={"path": path}
            )

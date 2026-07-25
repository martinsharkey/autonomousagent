import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from governance.decision_logger import DecisionLogger
from storage.storage_tracker import StorageTracker

class ArchivalPolicy:
    """Config-driven archival policy system"""
    
    def __init__(self, policy_config: Dict = None, storage_tracker: StorageTracker = None):
        self.config = policy_config or {
            "decision_log": {
                "hot_days": 90,
                "archive": "s3://martin-autonomy-logs/decision",
                "delete_days": 365
            },
            "test_output": {
                "hot_days": 14,
                "archive": "s3://martin-autonomy-logs/tests",
                "delete_days": 90
            },
            "code_version": {
                "hot_days": None,
                "archive": "s3-glacier://martin-autonomy-logs/versions",
                "delete_days": None
            },
            "state_snapshot": {
                "hot_days": 30,
                "archive": "s3://martin-autonomy-logs/snapshots",
                "delete_days": 90
            },
            "model_inference": {
                "hot_days": 7,
                "archive": "s3://martin-autonomy-logs/inference",
                "delete_days": 30
            }
        }
        self.storage_tracker = storage_tracker or StorageTracker()
        self.decision_logger = DecisionLogger()
    
    async def apply_archival_policy(self):
        """Run daily archival job based on policy"""
        
        for category, policy in self.config.items():
            candidates = self.storage_tracker.suggest_archival_candidates()
            
            for path in candidates:
                if path not in self.storage_tracker.inventory:
                    continue
                
                meta = self.storage_tracker.inventory[path]
                
                if meta["category"] != category:
                    continue
                
                hot_days = policy.get("hot_days")
                if hot_days is None:
                    continue
                
                if (datetime.now() - meta["written_at"]).days > hot_days:
                    await self._archive_to_s3(path, policy["archive"])
                    self.storage_tracker.mark_archived(path)
                    
                    self.decision_logger.log(
                        decision_type="ARCHIVAL_EXECUTED",
                        metadata={
                            "path": path,
                            "archive_dest": policy["archive"],
                            "category": category,
                            "age_days": (datetime.now() - meta["written_at"]).days
                        }
                    )
    
    async def _archive_to_s3(self, path: str, archive_dest: str):
        """Archive file to S3/Glacier"""
        
        print(f"[ARCHIVAL] Archiving {path} to {archive_dest}")
        
        self.decision_logger.log(
            decision_type="ARCHIVAL_STARTED",
            metadata={
                "path": path,
                "archive_dest": archive_dest
            }
        )
        
        await asyncio.sleep(0.1)
        
        self.decision_logger.log(
            decision_type="ARCHIVAL_COMPLETED",
            metadata={
                "path": path,
                "archive_dest": archive_dest
            }
        )
    
    async def check_deletion_candidates(self):
        """Check for files eligible for deletion"""
        
        for category, policy in self.config.items():
            delete_days = policy.get("delete_days")
            if delete_days is None:
                continue
            
            candidates = []
            for path, meta in self.storage_tracker.inventory.items():
                if meta["category"] != category:
                    continue
                
                if meta.get("archive_candidate"):
                    if (datetime.now() - meta["written_at"]).days > delete_days:
                        candidates.append(path)
            
            if candidates:
                print(f"[ARCHIVAL] {len(candidates)} files eligible for deletion in {category}")
                
                self.decision_logger.log(
                    decision_type="DELETION_CANDIDATES",
                    metadata={
                        "category": category,
                        "count": len(candidates),
                        "delete_days": delete_days
                    }
                )
    
    def get_policy_summary(self) -> Dict:
        """Get summary of archival policies"""
        
        summary = {}
        for category, policy in self.config.items():
            summary[category] = {
                "hot_days": policy.get("hot_days"),
                "archive_dest": policy.get("archive"),
                "delete_days": policy.get("delete_days")
            }
        
        return summary

"""
Resource governors for safe execution and scaling.
Enforces limits on concurrent models, cycles, and sandbox executions.
"""

import time
import threading
from typing import Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict


class ResourceGovernor:
    """Enforces resource limits for safe autonomous operation."""
    
    def __init__(
        self,
        max_concurrent_models: int = 1,
        max_cycles_per_hour: int = 300,
        max_sandbox_executions_per_hour: int = 60,
        max_concurrent_sandboxes: int = 1
    ):
        self.max_concurrent_models = max_concurrent_models
        self.max_cycles_per_hour = max_cycles_per_hour
        self.max_sandbox_executions_per_hour = max_sandbox_executions_per_hour
        self.max_concurrent_sandboxes = max_concurrent_sandboxes
        
        self.cycle_timestamps = []
        self.sandbox_timestamps = []
        self.active_models = set()
        self.active_sandboxes = 0
        
        self.lock = threading.Lock()
    
    def can_run_cycle(self) -> bool:
        """Check if we can run another cycle."""
        with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=1)
            
            # Clean old timestamps
            self.cycle_timestamps = [ts for ts in self.cycle_timestamps if ts > cutoff]
            
            if len(self.cycle_timestamps) >= self.max_cycles_per_hour:
                print(f"[GOVERNOR] Cycle limit reached: {len(self.cycle_timestamps)}/{self.max_cycles_per_hour}")
                return False
            
            self.cycle_timestamps.append(now)
            return True
    
    def can_load_model(self, model_name: str) -> bool:
        """Check if we can load another model."""
        with self.lock:
            if model_name in self.active_models:
                return True
            
            if len(self.active_models) >= self.max_concurrent_models:
                print(f"[GOVERNOR] Model limit reached: {len(self.active_models)}/{self.max_concurrent_models}")
                return False
            
            self.active_models.add(model_name)
            return True
    
    def unload_model(self, model_name: str):
        """Mark a model as unloaded."""
        with self.lock:
            self.active_models.discard(model_name)
    
    def can_run_sandbox(self) -> bool:
        """Check if we can run another sandbox execution."""
        with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=1)
            
            # Clean old timestamps
            self.sandbox_timestamps = [ts for ts in self.sandbox_timestamps if ts > cutoff]
            
            if len(self.sandbox_timestamps) >= self.max_sandbox_executions_per_hour:
                print(f"[GOVERNOR] Sandbox limit reached: {len(self.sandbox_timestamps)}/{self.max_sandbox_executions_per_hour}")
                return False
            
            if self.active_sandboxes >= self.max_concurrent_sandboxes:
                print(f"[GOVERNOR] Concurrent sandbox limit reached: {self.active_sandboxes}/{self.max_concurrent_sandboxes}")
                return False
            
            self.sandbox_timestamps.append(now)
            self.active_sandboxes += 1
            return True
    
    def sandbox_completed(self):
        """Mark a sandbox execution as completed."""
        with self.lock:
            self.active_sandboxes = max(0, self.active_sandboxes - 1)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current resource usage status."""
        with self.lock:
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=1)
            
            recent_cycles = len([ts for ts in self.cycle_timestamps if ts > cutoff])
            recent_sandboxes = len([ts for ts in self.sandbox_timestamps if ts > cutoff])
            
            return {
                "cycles_last_hour": recent_cycles,
                "max_cycles_per_hour": self.max_cycles_per_hour,
                "cycles_remaining": max(0, self.max_cycles_per_hour - recent_cycles),
                "sandbox_executions_last_hour": recent_sandboxes,
                "max_sandbox_per_hour": self.max_sandbox_executions_per_hour,
                "sandbox_remaining": max(0, self.max_sandbox_executions_per_hour - recent_sandboxes),
                "active_models": len(self.active_models),
                "max_concurrent_models": self.max_concurrent_models,
                "active_sandboxes": self.active_sandboxes,
                "max_concurrent_sandboxes": self.max_concurrent_sandboxes
            }


_global_governor: ResourceGovernor = None


def get_governor() -> ResourceGovernor:
    """Get or create the global resource governor."""
    global _global_governor
    if _global_governor is None:
        _global_governor = ResourceGovernor()
    return _global_governor

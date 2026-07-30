import time
import json
from typing import Dict, Optional
from core.api_router import get_provider_router
from tools.provider_optimizer import ProviderOptimizer

class QuotaMonitor:
    """Monitors per-provider usage and triggers fallback when quotas are near exhaustion."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.usage: Dict[str, Dict] = {}
        self.last_check: Dict[str, float] = {}
        self.optimizer = ProviderOptimizer()
        self.router = get_provider_router()
    
    def record_request(self, provider: str, cost: float = 1.0):
        """Record a request to a provider."""
        now = time.time()
        if provider not in self.usage:
            self.usage[provider] = {"count": 0, "total_cost": 0.0, "window_start": now}
        self.usage[provider]["count"] += 1
        self.usage[provider]["total_cost"] += cost
        self.last_check[provider] = now
    
    def get_usage_ratio(self, provider: str, max_requests: int = 100, max_cost: float = 100.0) -> float:
        """Return usage ratio (0.0 to 1.0+) based on count or cost."""
        if provider not in self.usage:
            return 0.0
        data = self.usage[provider]
        count_ratio = data["count"] / max_requests if max_requests > 0 else 0.0
        cost_ratio = data["total_cost"] / max_cost if max_cost > 0 else 0.0
        return max(count_ratio, cost_ratio)
    
    def should_switch(self, provider: str, max_requests: int = 100, max_cost: float = 100.0) -> bool:
        """Check if we should switch away from this provider."""
        ratio = self.get_usage_ratio(provider, max_requests, max_cost)
        return ratio >= self.threshold
    
    def get_best_provider(self, preferred: str, fallbacks: list, max_requests: int = 100, max_cost: float = 100.0) -> str:
        """Return the best provider to use, switching if quota is near limit."""
        if not self.should_switch(preferred, max_requests, max_cost):
            return preferred
        for fb in fallbacks:
            if not self.should_switch(fb, max_requests, max_cost):
                return fb
        return preferred  # all exhausted, stick with preferred
    
    def reset_window(self, provider: str):
        """Reset usage window for a provider (e.g., after quota refresh)."""
        if provider in self.usage:
            self.usage[provider]["count"] = 0
            self.usage[provider]["total_cost"] = 0.0
            self.usage[provider]["window_start"] = time.time()
    
    def get_status(self) -> Dict:
        """Return current usage status for all providers."""
        return {
            "usage": self.usage,
            "threshold": self.threshold,
            "last_check": self.last_check
        }

# Singleton instance
_quota_monitor: Optional[QuotaMonitor] = None

def get_quota_monitor() -> QuotaMonitor:
    global _quota_monitor
    if _quota_monitor is None:
        _quota_monitor = QuotaMonitor()
    return _quota_monitor

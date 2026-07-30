#!/usr/bin/env python3
"""Multi-provider health check tool for Pillar 3: Model Agnosticism.

Periodically tests all configured LLM providers and reports availability,
latency, and error rates to support autonomous failover and provider selection.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ProviderStatus:
    provider: str
    available: bool
    latency_ms: float
    error: Optional[str] = None
    last_checked: float = 0.0

class ProviderHealthChecker:
    """Checks health of multiple LLM providers."""
    
    def __init__(self, providers: List[str] = None):
        self.providers = providers or ["openai", "anthropic", "google", "cohere"]
        self.statuses: Dict[str, ProviderStatus] = {}
        self._lock = asyncio.Lock()
        self._check_interval = 60  # seconds
        self._last_check = 0.0
    
    async def check_provider(self, provider: str) -> ProviderStatus:
        """Check a single provider's availability."""
        start = time.monotonic()
        try:
            # Simulate a lightweight health check (e.g., list models or ping)
            # In production, replace with actual API call
            await asyncio.sleep(0.1)  # placeholder
            latency = (time.monotonic() - start) * 1000
            status = ProviderStatus(
                provider=provider,
                available=True,
                latency_ms=latency,
                last_checked=time.time()
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            status = ProviderStatus(
                provider=provider,
                available=False,
                latency_ms=latency,
                error=str(e),
                last_checked=time.time()
            )
        return status
    
    async def check_all(self) -> Dict[str, ProviderStatus]:
        """Check all configured providers concurrently."""
        tasks = [self.check_provider(p) for p in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        async with self._lock:
            for provider, result in zip(self.providers, results):
                if isinstance(result, Exception):
                    self.statuses[provider] = ProviderStatus(
                        provider=provider,
                        available=False,
                        latency_ms=0,
                        error=str(result),
                        last_checked=time.time()
                    )
                else:
                    self.statuses[provider] = result
        return self.statuses
    
    async def get_healthy_providers(self) -> List[str]:
        """Return list of currently available providers."""
        now = time.time()
        if now - self._last_check > self._check_interval:
            await self.check_all()
            self._last_check = now
        async with self._lock:
            return [p for p, s in self.statuses.items() if s.available]
    
    async def get_best_provider(self) -> Optional[str]:
        """Return the provider with lowest latency among healthy ones."""
        healthy = await self.get_healthy_providers()
        if not healthy:
            return None
        async with self._lock:
            best = min(healthy, key=lambda p: self.statuses[p].latency_ms)
            return best

# Singleton instance
health_checker = ProviderHealthChecker()

async def run_provider_health_check() -> Dict:
    """Run health check and return summary."""
    statuses = await health_checker.check_all()
    summary = {
        "total_providers": len(statuses),
        "healthy": sum(1 for s in statuses.values() if s.available),
        "unhealthy": sum(1 for s in statuses.values() if not s.available),
        "details": {
            p: {
                "available": s.available,
                "latency_ms": round(s.latency_ms, 2),
                "error": s.error
            }
            for p, s in statuses.items()
        }
    }
    return summary

if __name__ == "__main__":
    asyncio.run(run_provider_health_check())

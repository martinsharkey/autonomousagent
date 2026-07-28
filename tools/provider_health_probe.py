#!/usr/bin/env python3
"""Multi-provider health probe tool.

Periodically tests all configured LLM providers for latency, error rates,
and availability. Feeds results into the provider optimizer for intelligent
failover and routing decisions.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    provider_name: str
    latency_ms: float
    error: bool = False
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)


class ProviderHealthProbe:
    """Probes all configured LLM providers and reports health metrics."""

    def __init__(self, providers: List[str], probe_timeout: float = 5.0):
        self.providers = providers
        self.probe_timeout = probe_timeout
        self._health_cache: Dict[str, ProviderHealth] = {}
        self._lock = asyncio.Lock()

    async def probe_provider(self, provider_name: str) -> ProviderHealth:
        """Probe a single provider by sending a minimal test request."""
        start = time.time()
        try:
            # Simulate a lightweight probe (e.g., a simple completion or embedding)
            # In production, replace with actual API call to the provider's health endpoint
            await asyncio.sleep(0.1)  # placeholder for actual network call
            latency = (time.time() - start) * 1000
            return ProviderHealth(provider_name=provider_name, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            logger.warning(f"Health probe failed for {provider_name}: {e}")
            return ProviderHealth(
                provider_name=provider_name,
                latency_ms=latency,
                error=True,
                error_message=str(e)
            )

    async def probe_all(self) -> Dict[str, ProviderHealth]:
        """Probe all configured providers concurrently."""
        tasks = [self.probe_provider(p) for p in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        health_map = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                health_map[self.providers[i]] = ProviderHealth(
                    provider_name=self.providers[i],
                    latency_ms=0,
                    error=True,
                    error_message=str(result)
                )
            else:
                health_map[result.provider_name] = result
        async with self._lock:
            self._health_cache.update(health_map)
        return health_map

    def get_health_summary(self) -> Dict[str, ProviderHealth]:
        """Return the latest cached health data."""
        return dict(self._health_cache)

    def get_healthy_providers(self) -> List[str]:
        """Return list of providers that are currently healthy."""
        return [
            name for name, health in self._health_cache.items()
            if not health.error
        ]

    def get_best_provider(self) -> Optional[str]:
        """Return the healthiest provider (lowest latency, no error)."""
        healthy = [
            (name, health) for name, health in self._health_cache.items()
            if not health.error
        ]
        if not healthy:
            return None
        # Sort by latency ascending
        healthy.sort(key=lambda x: x[1].latency_ms)
        return healthy[0][0]

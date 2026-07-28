#!/usr/bin/env python3
"""Provider fallback/caching with integrated health probe."""

import asyncio
import logging
from typing import Optional, Dict, Any
from tools.provider_health_probe import ProviderHealthProbe

logger = logging.getLogger(__name__)


class ProviderOptimizer:
    """Routes LLM requests to the best available provider."""

    def __init__(self, providers: list, probe_interval: float = 60.0):
        self.providers = providers
        self.probe_interval = probe_interval
        self.health_probe = ProviderHealthProbe(providers)
        self._last_probe_time = 0.0

    async def ensure_fresh_health(self):
        """Probe providers if cache is stale."""
        now = asyncio.get_event_loop().time()
        if now - self._last_probe_time > self.probe_interval:
            await self.health_probe.probe_all()
            self._last_probe_time = now

    async def get_best_provider(self) -> Optional[str]:
        """Return the best provider based on health data."""
        await self.ensure_fresh_health()
        return self.health_probe.get_best_provider()

    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route a request to the best provider, with fallback."""
        provider = await self.get_best_provider()
        if not provider:
            # Fallback to first provider if none healthy
            provider = self.providers[0] if self.providers else None
        if not provider:
            raise RuntimeError("No providers available")
        # Placeholder: actual routing logic would call the provider's API
        logger.info(f"Routing request to provider: {provider}")
        return {"provider": provider, "status": "routed"}

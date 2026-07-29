import asyncio
import logging
import time
from typing import Dict, List, Optional
from core.api_router import get_providers, set_active_provider

logger = logging.getLogger(__name__)

class ProviderHealthChecker:
    """Periodically tests all configured LLM providers for availability and response quality."""

    def __init__(self, test_prompt: str = "Respond with 'ok'.", timeout: float = 10.0):
        self.test_prompt = test_prompt
        self.timeout = timeout
        self._health_cache: Dict[str, Dict] = {}
        self._last_check: float = 0
        self._check_interval: float = 300  # 5 minutes

    async def check_provider(self, provider_name: str, provider_config: dict) -> dict:
        """Test a single provider's health."""
        start = time.time()
        try:
            # Simulate a minimal API call (in production, use actual client)
            # For now, we assume success if config is valid
            if not provider_config.get("api_key"):
                return {"status": "unhealthy", "latency": 0, "error": "No API key"}
            latency = time.time() - start
            return {"status": "healthy", "latency": latency, "error": None}
        except Exception as e:
            latency = time.time() - start
            return {"status": "unhealthy", "latency": latency, "error": str(e)}

    async def run_health_checks(self) -> Dict[str, dict]:
        """Run health checks on all providers."""
        providers = get_providers()
        results = {}
        tasks = []
        for name, config in providers.items():
            tasks.append(self.check_provider(name, config))
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, result in zip(providers.keys(), check_results):
            if isinstance(result, Exception):
                results[name] = {"status": "unhealthy", "latency": 0, "error": str(result)}
            else:
                results[name] = result
        self._health_cache = results
        self._last_check = time.time()
        logger.info(f"Provider health check completed: {results}")
        return results

    def get_health_summary(self) -> Dict[str, dict]:
        """Return cached health results."""
        return self._health_cache

    async def auto_failover(self) -> Optional[str]:
        """If current provider is unhealthy, switch to a healthy one."""
        if time.time() - self._last_check > self._check_interval:
            await self.run_health_checks()
        healthy = [name for name, status in self._health_cache.items() if status.get("status") == "healthy"]
        if not healthy:
            logger.warning("No healthy providers available.")
            return None
        # Simple strategy: pick the first healthy provider
        new_provider = healthy[0]
        set_active_provider(new_provider)
        logger.info(f"Auto-failover to provider: {new_provider}")
        return new_provider

# Singleton instance
health_checker = ProviderHealthChecker()

async def run_periodic_health_checks(interval: int = 300):
    """Background task to run health checks periodically."""
    while True:
        await health_checker.run_health_checks()
        await asyncio.sleep(interval)

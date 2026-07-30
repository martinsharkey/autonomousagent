import asyncio
import time
from typing import Dict, List, Optional
import aiohttp

class ProviderHealthChecker:
    """Checks health and latency of configured LLM providers."""

    def __init__(self, providers: Dict[str, Dict]):
        self.providers = providers

    async def check_provider(self, name: str, config: Dict) -> Dict:
        """Check a single provider's health."""
        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Simple connectivity test to provider endpoint
                async with session.get(config.get('health_endpoint', config.get('base_url', '')), timeout=5) as resp:
                    latency = time.time() - start
                    return {
                        'provider': name,
                        'healthy': resp.status < 500,
                        'latency': round(latency, 3),
                        'status_code': resp.status
                    }
        except Exception as e:
            return {
                'provider': name,
                'healthy': False,
                'latency': time.time() - start,
                'error': str(e)
            }

    async def check_all(self) -> List[Dict]:
        """Check all configured providers concurrently."""
        tasks = [self.check_provider(name, config) for name, config in self.providers.items()]
        return await asyncio.gather(*tasks)

    def get_healthy_providers(self, results: List[Dict]) -> List[str]:
        """Return list of healthy provider names."""
        return [r['provider'] for r in results if r['healthy']]

    def get_best_provider(self, results: List[Dict]) -> Optional[str]:
        """Return the healthiest provider with lowest latency."""
        healthy = [r for r in results if r['healthy']]
        if not healthy:
            return None
        return min(healthy, key=lambda x: x['latency'])['provider']

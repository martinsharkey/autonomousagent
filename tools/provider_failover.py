import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import aiohttp
from core.agent_config import AgentConfig
from governance.keys import get_provider_api_key
from tools.provider_optimizer import ProviderOptimizer

@dataclass
class ProviderStatus:
    name: str
    is_healthy: bool
    latency: float
    quota_remaining: int
    last_checked: float

class ProviderFailover:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.provider_optimizer = ProviderOptimizer(config)
        self.provider_statuses: Dict[str, ProviderStatus] = {}
        self.last_health_check = 0
        self.health_check_interval = 300  # 5 minutes

    async def check_provider_health(self, provider_name: str) -> ProviderStatus:
        """Check health, latency, and quota for a single provider."""
        api_key = get_provider_api_key(provider_name)
        if not api_key:
            return ProviderStatus(
                name=provider_name,
                is_healthy=False,
                latency=float('inf'),
                quota_remaining=0,
                last_checked=time.time()
            )

        start_time = time.time()
        try:
            # Use a lightweight model check to verify provider health
            async with aiohttp.ClientSession() as session:
                url = self.config.get_provider_endpoint(provider_name)
                headers = {"Authorization": f"Bearer {api_key}"}
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1
                }
                async with session.post(url, json=payload, headers=headers, timeout=5) as response:
                    if response.status == 200:
                        latency = time.time() - start_time
                        quota_remaining = self._extract_quota_remaining(response)
                        return ProviderStatus(
                            name=provider_name,
                            is_healthy=True,
                            latency=latency,
                            quota_remaining=quota_remaining,
                            last_checked=time.time()
                        )
        except Exception:
            pass

        return ProviderStatus(
            name=provider_name,
            is_healthy=False,
            latency=float('inf'),
            quota_remaining=0,
            last_checked=time.time()
        )

    async def _extract_quota_remaining(self, response) -> int:
        """Extract quota remaining from provider response headers or body."""
        # Default to a high value if quota info is not available
        return 1000

    async def update_provider_statuses(self):
        """Update health status for all configured providers."""
        providers = self.config.get_configured_providers()
        tasks = [self.check_provider_health(provider) for provider in providers]
        self.provider_statuses = {
            status.name: status for status in await asyncio.gather(*tasks)
        }
        self.last_health_check = time.time()

    async def get_best_provider(self, preferred_providers: Optional[List[str]] = None) -> Tuple[str, ProviderStatus]:
        """Select the best provider based on health, latency, and quota."""
        if time.time() - self.last_health_check > self.health_check_interval:
            await self.update_provider_statuses()

        providers = self.config.get_configured_providers()
        if preferred_providers:
            providers = [p for p in providers if p in preferred_providers]

        # Filter to healthy providers
        healthy_providers = [
            status for status in self.provider_statuses.values()
            if status.is_healthy and status.name in providers
        ]

        if not healthy_providers:
            raise RuntimeError("No healthy providers available")

        # Sort by latency (lowest first), then by quota (highest first)
        healthy_providers.sort(key=lambda x: (x.latency, -x.quota_remaining))
        best_provider = healthy_providers[0]
        return best_provider.name, best_provider

    async def route_request(self, prompt: str, preferred_providers: Optional[List[str]] = None) -> Tuple[str, str]:
        """Route a request to the best available provider."""
        provider_name, provider_status = await self.get_best_provider(preferred_providers)
        api_key = get_provider_api_key(provider_name)
        endpoint = self.config.get_provider_endpoint(provider_name)

        # Prepare request
        payload = {
            "model": self.config.get_provider_model(provider_name),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.get_provider_max_tokens(provider_name)
        }

        # Execute request
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with session.post(endpoint, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return provider_name, response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    raise RuntimeError(f"Provider {provider_name} failed with status {response.status}")

    async def batch_route_requests(self, prompts: List[str], preferred_providers: Optional[List[str]] = None) -> Dict[str, str]:
        """Route multiple requests to the best available providers."""
        results = {}
        for prompt in prompts:
            try:
                provider_name, response = await self.route_request(prompt, preferred_providers)
                results[prompt] = response
            except Exception as e:
                results[prompt] = f"Error: {str(e)}"
        return results
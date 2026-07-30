import asyncio
import time
import yaml
from typing import Dict, List, Optional
from pathlib import Path

class ProviderHealth:
    """Periodically tests all configured LLM providers and maintains a healthy priority list."""

    def __init__(self, config_path: str = "providers.yaml", check_interval: int = 300):
        self.config_path = config_path
        self.check_interval = check_interval
        self.health_status: Dict[str, bool] = {}
        self.latency: Dict[str, float] = {}
        self.last_check: float = 0
        self._load_providers()

    def _load_providers(self) -> None:
        """Load provider configurations from YAML."""
        path = Path(self.config_path)
        if not path.exists():
            self.providers = []
            return
        with open(path) as f:
            config = yaml.safe_load(f)
        self.providers = config.get("providers", [])

    async def check_provider(self, provider: Dict) -> bool:
        """Test a single provider by sending a minimal request."""
        try:
            start = time.time()
            # Simulate a lightweight health check (e.g., list models or ping)
            # In production, replace with actual API call
            await asyncio.sleep(0.1)  # Placeholder for real check
            elapsed = time.time() - start
            self.latency[provider["name"]] = elapsed
            return True
        except Exception as e:
            print(f"Health check failed for {provider['name']}: {e}")
            return False

    async def run_checks(self) -> None:
        """Run health checks on all providers concurrently."""
        tasks = [self.check_provider(p) for p in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            name = self.providers[i]["name"]
            self.health_status[name] = isinstance(result, bool) and result

    def get_healthy_providers(self) -> List[Dict]:
        """Return list of healthy providers sorted by latency (fastest first)."""
        healthy = [p for p in self.providers if self.health_status.get(p["name"], False)]
        healthy.sort(key=lambda p: self.latency.get(p["name"], float('inf')))
        return healthy

    async def periodic_check(self) -> None:
        """Run health checks periodically."""
        while True:
            now = time.time()
            if now - self.last_check >= self.check_interval:
                await self.run_checks()
                self.last_check = now
            await asyncio.sleep(60)  # Check every minute if interval elapsed

    def update_provider_config(self) -> None:
        """Write the healthy provider priority list back to providers.yaml."""
        healthy = self.get_healthy_providers()
        path = Path(self.config_path)
        if path.exists():
            with open(path) as f:
                config = yaml.safe_load(f)
            config["providers"] = healthy
            with open(path, 'w') as f:
                yaml.dump(config, f)

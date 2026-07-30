import asyncio
import json
import time
import os
from pathlib import Path

HEALTH_FILE = Path("/tmp/provider_health.json")

async def check_provider(provider: str, endpoint: str, api_key: str) -> dict:
    """Check if a provider endpoint is reachable and returns a valid response."""
    try:
        import aiohttp
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    return {"provider": provider, "healthy": True, "latency_ms": resp.elapsed.total_seconds() * 1000}
                else:
                    return {"provider": provider, "healthy": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        return {"provider": provider, "healthy": False, "error": str(e)}

def load_providers() -> list:
    """Load provider configurations from providers.yaml or environment."""
    import yaml
    try:
        with open("providers.yaml", "r") as f:
            config = yaml.safe_load(f)
        providers = []
        for name, cfg in config.get("providers", {}).items():
            providers.append({
                "name": name,
                "endpoint": cfg.get("endpoint", ""),
                "api_key": cfg.get("api_key", os.environ.get(f"{name.upper()}_API_KEY", ""))
            })
        return providers
    except Exception:
        # Fallback to environment-based config
        return [
            {"name": "openai", "endpoint": "https://api.openai.com/v1/models", "api_key": os.environ.get("OPENAI_API_KEY", "")},
            {"name": "anthropic", "endpoint": "https://api.anthropic.com/v1/models", "api_key": os.environ.get("ANTHROPIC_API_KEY", "")},
            {"name": "google", "endpoint": "https://generativelanguage.googleapis.com/v1/models", "api_key": os.environ.get("GOOGLE_API_KEY", "")},
        ]

async def run_health_checks():
    """Run health checks on all providers and write results to shared file."""
    providers = load_providers()
    tasks = [check_provider(p["name"], p["endpoint"], p["api_key"]) for p in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    health_data = {
        "timestamp": time.time(),
        "checks": [r if not isinstance(r, Exception) else {"provider": "unknown", "healthy": False, "error": str(r)} for r in results]
    }
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HEALTH_FILE, "w") as f:
        json.dump(health_data, f)
    return health_data

def get_healthy_providers() -> list:
    """Return list of provider names that are currently healthy."""
    try:
        with open(HEALTH_FILE, "r") as f:
            data = json.load(f)
        if time.time() - data["timestamp"] > 60:
            return []  # Stale data
        return [c["provider"] for c in data["checks"] if c.get("healthy")]
    except Exception:
        return []

if __name__ == "__main__":
    asyncio.run(run_health_checks())

#!/usr/bin/env python3
"""Tool to test all configured LLM providers and update failover state."""
import json
import time
import requests
from pathlib import Path

PROVIDERS_CONFIG = Path("providers.yaml")
FAILOVER_STATE = Path("data/provider_failover_state.json")

def load_providers():
    import yaml
    with open(PROVIDERS_CONFIG) as f:
        config = yaml.safe_load(f)
    return config.get("providers", [])

def test_provider(provider):
    """Test a single provider endpoint and return latency and status."""
    url = provider.get("health_endpoint", provider.get("base_url", ""))
    if not url:
        return {"provider": provider["name"], "status": "error", "latency": None, "error": "No endpoint"}
    try:
        start = time.time()
        resp = requests.get(url, timeout=5)
        latency = time.time() - start
        if resp.status_code == 200:
            return {"provider": provider["name"], "status": "healthy", "latency": latency, "error": None}
        else:
            return {"provider": provider["name"], "status": "degraded", "latency": latency, "error": f"HTTP {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"provider": provider["name"], "status": "down", "latency": None, "error": str(e)}

def run_tests():
    providers = load_providers()
    results = []
    for p in providers:
        result = test_provider(p)
        results.append(result)
    # Determine best provider (lowest latency among healthy)
    healthy = [r for r in results if r["status"] == "healthy"]
    best = min(healthy, key=lambda x: x["latency"]) if healthy else None
    state = {
        "timestamp": time.time(),
        "results": results,
        "best_provider": best["provider"] if best else None,
        "all_down": len(healthy) == 0
    }
    FAILOVER_STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILOVER_STATE, "w") as f:
        json.dump(state, f, indent=2)
    return state

if __name__ == "__main__":
    state = run_tests()
    print(json.dumps(state, indent=2))

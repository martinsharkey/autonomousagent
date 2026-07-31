#!/usr/bin/env python3
"""Provider health probe tool.

Periodically tests all configured LLM providers with a lightweight prompt,
records latency and error rates, and exposes a simple API for the router to
prefer healthy providers.
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional

# Simple in-memory store for health metrics
_health_store: Dict[str, Dict] = {}
_lock = threading.Lock()

# Lightweight prompt for health checks
_HEALTH_PROMPT = "Reply with the single word: OK"


def _load_providers() -> List[Dict]:
    """Load provider configurations from providers.yaml or environment."""
    # Simplified: read from a JSON file or env vars; in production, use the actual config.
    config_path = Path("providers.yaml")
    if config_path.exists():
        # For simplicity, assume YAML is converted to JSON; here we just return a placeholder.
        # In real implementation, parse YAML.
        return [
            {"name": "openai", "base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
            {"name": "anthropic", "base_url": "https://api.anthropic.com/v1", "api_key_env": "ANTHROPIC_API_KEY"},
            {"name": "local", "base_url": "http://localhost:11434/v1", "api_key_env": ""},
        ]
    return []


def _probe_provider(provider: Dict) -> Dict:
    """Send a lightweight request to the provider and measure latency."""
    import requests
    start = time.time()
    try:
        headers = {"Content-Type": "application/json"}
        api_key = provider.get("api_key_env", "")
        if api_key:
            import os
            key = os.getenv(api_key, "")
            if key:
                headers["Authorization"] = f"Bearer {key}"
        payload = {
            "model": provider.get("model", "gpt-3.5-turbo"),
            "messages": [{"role": "user", "content": _HEALTH_PROMPT}],
            "max_tokens": 5,
        }
        resp = requests.post(
            provider["base_url"] + "/chat/completions",
            headers=headers,
            json=payload,
            timeout=5,
        )
        latency = time.time() - start
        ok = resp.status_code == 200
        return {"ok": ok, "latency": latency, "status_code": resp.status_code}
    except Exception as e:
        latency = time.time() - start
        return {"ok": False, "latency": latency, "error": str(e)}


def run_probe() -> Dict:
    """Probe all providers and update the health store."""
    providers = _load_providers()
    results = {}
    for provider in providers:
        name = provider["name"]
        result = _probe_provider(provider)
        results[name] = result
    with _lock:
        for name, result in results.items():
            _health_store[name] = {
                "last_checked": time.time(),
                "ok": result["ok"],
                "latency": result.get("latency", 0.0),
                "error": result.get("error", ""),
            }
    return results


def get_health() -> Dict:
    """Return current health metrics for all providers."""
    with _lock:
        return dict(_health_store)


def get_healthy_providers() -> List[str]:
    """Return list of provider names that are currently healthy."""
    with _lock:
        return [name for name, data in _health_store.items() if data.get("ok")]


def main():
    """CLI entry point for manual probing."""
    results = run_probe()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

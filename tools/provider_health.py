import os
import yaml
import requests
from typing import List, Dict

PROVIDERS_PATH = "providers.yaml"

def load_providers() -> Dict:
    with open(PROVIDERS_PATH, "r") as f:
        return yaml.safe_load(f)

def save_providers(config: Dict):
    with open(PROVIDERS_PATH, "w") as f:
        yaml.dump(config, f)

def check_provider_health(provider_name: str, config: Dict) -> bool:
    """Check if a provider is reachable by making a minimal request."""
    base_url = config.get("base_url", "")
    api_key = config.get("api_key", "")
    if not base_url or not api_key:
        return False
    try:
        # Simple connectivity test (e.g., list models endpoint)
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def run_provider_health_check() -> List[str]:
    """Return list of healthy provider names."""
    config = load_providers()
    healthy = []
    for name, provider_config in config.get("providers", {}).items():
        if check_provider_health(name, provider_config):
            healthy.append(name)
    return healthy

def update_active_providers(healthy: List[str]):
    """Update providers.yaml to mark only healthy providers as active."""
    config = load_providers()
    for name in config.get("providers", {}):
        config["providers"][name]["active"] = name in healthy
    save_providers(config)

def main():
    healthy = run_provider_health_check()
    update_active_providers(healthy)
    print(f"Healthy providers: {healthy}")

if __name__ == "__main__":
    main()

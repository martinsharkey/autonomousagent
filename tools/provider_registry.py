#!/usr/bin/env python3
"""Multi-provider model registry: discovers, tests, and registers LLM providers."""

import json
import os
import time
import yaml
from typing import Dict, List, Optional

PROVIDERS_CONFIG_PATH = "providers.yaml"
REGISTRY_CACHE_PATH = "data/provider_registry_cache.json"

# Default provider configurations for discovery
DEFAULT_PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "env_key": "OPENAI_API_KEY",
        "test_prompt": "Hello, respond with 'ok'.",
        "timeout": 10
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
        "env_key": "ANTHROPIC_API_KEY",
        "test_prompt": "Hello, respond with 'ok'.",
        "timeout": 10
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-pro"],
        "env_key": "GOOGLE_API_KEY",
        "test_prompt": "Hello, respond with 'ok'.",
        "timeout": 10
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/v1",
        "models": ["command-r", "command-r-plus"],
        "env_key": "COHERE_API_KEY",
        "test_prompt": "Hello, respond with 'ok'.",
        "timeout": 10
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/models",
        "models": ["gpt2", "microsoft/DialoGPT-medium"],
        "env_key": "HUGGINGFACE_API_KEY",
        "test_prompt": "Hello, respond with 'ok'.",
        "timeout": 15
    }
}

def load_providers_config() -> Dict:
    """Load existing providers.yaml if it exists."""
    if os.path.exists(PROVIDERS_CONFIG_PATH):
        with open(PROVIDERS_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

def save_providers_config(config: Dict):
    """Save updated providers.yaml."""
    with open(PROVIDERS_CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

def test_provider(provider_name: str, config: Dict) -> Optional[Dict]:
    """Test a provider by making a simple API call."""
    import requests
    api_key = os.environ.get(config["env_key"])
    if not api_key:
        return None
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    model = config["models"][0]
    
    # Build request based on provider
    if provider_name == "openai":
        payload = {"model": model, "messages": [{"role": "user", "content": config["test_prompt"]}], "max_tokens": 10}
        url = f"{config['base_url']}/chat/completions"
    elif provider_name == "anthropic":
        payload = {"model": model, "messages": [{"role": "user", "content": config["test_prompt"]}], "max_tokens": 10}
        url = f"{config['base_url']}/messages"
        headers["x-api-key"] = api_key
        headers.pop("Authorization")
    elif provider_name == "google":
        url = f"{config['base_url']}/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": config["test_prompt"]}]}]}
        headers = {"Content-Type": "application/json"}
    elif provider_name == "cohere":
        payload = {"model": model, "message": config["test_prompt"], "max_tokens": 10}
        url = f"{config['base_url']}/generate"
    elif provider_name == "huggingface":
        url = f"{config['base_url']}/{model}"
        payload = {"inputs": config["test_prompt"], "parameters": {"max_new_tokens": 10}}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    else:
        return None
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=config["timeout"])
        if response.status_code == 200:
            return {"status": "healthy", "model": model, "latency_ms": response.elapsed.total_seconds() * 1000}
        else:
            return {"status": "error", "code": response.status_code, "message": response.text[:200]}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}

def discover_and_register() -> Dict:
    """Discover all configured providers, test them, and update providers.yaml."""
    results = {}
    active_providers = []
    
    for provider_name, config in DEFAULT_PROVIDERS.items():
        test_result = test_provider(provider_name, config)
        results[provider_name] = test_result
        if test_result and test_result["status"] == "healthy":
            active_providers.append({
                "name": provider_name,
                "base_url": config["base_url"],
                "models": config["models"],
                "env_key": config["env_key"],
                "latency_ms": test_result["latency_ms"]
            })
    
    # Update providers.yaml with active providers
    existing_config = load_providers_config()
    existing_config["providers"] = active_providers
    existing_config["last_updated"] = time.time()
    save_providers_config(existing_config)
    
    # Cache results
    os.makedirs(os.path.dirname(REGISTRY_CACHE_PATH), exist_ok=True)
    with open(REGISTRY_CACHE_PATH, "w") as f:
        json.dump({"results": results, "timestamp": time.time()}, f)
    
    return results

def get_registered_providers() -> List[Dict]:
    """Get list of currently registered providers from cache."""
    if os.path.exists(REGISTRY_CACHE_PATH):
        with open(REGISTRY_CACHE_PATH, "r") as f:
            data = json.load(f)
            return data.get("results", {})
    return {}

if __name__ == "__main__":
    results = discover_and_register()
    print(json.dumps(results, indent=2))

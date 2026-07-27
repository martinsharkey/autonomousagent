#!/usr/bin/env python3
"""Test new LLM providers directly to verify they work before keeping them in config."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from dotenv import load_dotenv
load_dotenv(override=False)

import yaml
import httpx


with open("providers.yaml", "r", encoding="utf-8") as f:
    PROVIDERS = yaml.safe_load(f).get("providers", [])


async def test_provider_direct(provider_name: str, model: str):
    """Test a provider directly via its API."""
    provider_config = None
    for p in PROVIDERS:
        if p["name"] == provider_name:
            provider_config = p
            break

    if not provider_config:
        return {"name": provider_name, "status": "not_configured", "error": "Provider not in config"}

    api_key = os.getenv(provider_config["api_key_env"])
    if not api_key or "your-" in api_key:
        return {"name": provider_name, "status": "no_key", "error": f"Missing {provider_config['api_key_env']}"}

    base_url = provider_config["base_url"]
    path = provider_config.get("path", "chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Respond with exactly: OK"}],
        "max_tokens": 10,
        "temperature": 0.0,
    }

    if path == "chat/completions":
        url = f"{base_url}/chat/completions"
    elif path == "v1/openai/chat/completions":
        url = f"{base_url}/v1/openai/chat/completions"
    elif path == "models":
        url = f"{base_url}/{model}"
        payload.pop("model", None)
    else:
        url = f"{base_url}/{path}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"name": provider_name, "status": "ok", "model": model, "response": content.strip()[:60]}
    except httpx.HTTPStatusError as exc:
        text = exc.response.text[:200]
        return {"name": provider_name, "status": "http_error", "model": model, "error": f"{exc.response.status_code}: {text}"}
    except Exception as exc:
        return {"name": provider_name, "status": "error", "model": model, "error": str(exc)[:200]}


async def main():
    test_targets = [
        {"name": "anthropic", "model": "claude-3-5-sonnet-20240620"},
        {"name": "grok", "model": "grok-2"},
        {"name": "mistral", "model": "mistral-small-latest"},
        {"name": "cerebras", "model": "llama3.1-8b"},
        {"name": "aionlabs", "model": "Aion-2.5"},
        {"name": "llm7io", "model": "deepseek-v3-0324"},
        {"name": "sambanova", "model": "Meta-Llama-3.3-70B-Instruct"},
        {"name": "siliconflow", "model": "Qwen/Qwen3-8B"},
    ]

    results = []
    for target in test_targets:
        print(f"Testing {target['name']}...")
        result = await test_provider_direct(target["name"], target["model"])
        results.append(result)
        status_icon = "yes" if result["status"] == "ok" else "no"
        detail = result.get("response", result.get("error", "unknown"))
        print(f"  [{status_icon}] {result['status']}: {detail[:80]}")

    working = [r for r in results if r["status"] == "ok"]
    print(f"\nWorking providers: {len(working)}/{len(results)}")
    return results


if __name__ == "__main__":
    asyncio.run(main())

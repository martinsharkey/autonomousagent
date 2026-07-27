#!/usr/bin/env python3
"""One-time benchmark free LLM providers and cache ideal settings."""

import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone

sys.path.insert(0, str(Path(".").resolve()))
load_dotenv(override=False)

import yaml
import httpx


SETTINGS_FILE = Path("core/provider_settings.json")


def load_settings():
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_benchmark": None, "providers": {}, "defaults": {"temperature": 0.2, "context": "default"}}


def save_settings(settings):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


async def benchmark_provider(provider_name: str, base_url: str, api_key: str, model: str, path: str = "chat/completions"):
    candidates = [
        {"temperature": 0.0, "context": "deterministic"},
        {"temperature": 0.1, "context": "deterministic"},
        {"temperature": 0.2, "context": "default"},
    ]

    prompt = [{"role": "user", "content": "Respond with exactly: OK"}]
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        for candidate in candidates:
            url = f"{base_url}/chat/completions"
            payload = {"model": model, "messages": prompt, "max_tokens": 10, "temperature": candidate["temperature"]}
            try:
                r = await client.post(url, headers=headers, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if text.upper() == "OK":
                        return candidate
            except Exception:
                continue

    return {"temperature": 0.2, "context": "default"}


async def benchmark_all():
    with open("providers.yaml", "r", encoding="utf-8") as f:
        providers = yaml.safe_load(f).get("providers", [])

    settings = load_settings()
    settings["last_benchmark"] = datetime.now(timezone.utc).isoformat()
    settings.setdefault("providers", {})
    settings.setdefault("defaults", {"temperature": 0.2, "context": "default"})

    for provider in providers:
        name = provider["name"]
        api_key = os.getenv(provider["api_key_env"])
        if not api_key or "your-" in api_key:
            continue

        best = await benchmark_provider(
            provider_name=name,
            base_url=provider["base_url"],
            api_key=api_key,
            model=provider["default_model"],
            path=provider.get("path", "chat/completions"),
        )
        settings["providers"][name] = {
            "temperature": best["temperature"],
            "context": best["context"],
            "model": provider["default_model"],
            "base_url": provider["base_url"],
        }

    save_settings(settings)
    return settings


def get_provider_temperature(provider_name: str, context: str = "default") -> float:
    settings = load_settings()
    provider = settings.get("providers", {}).get(provider_name)
    if provider:
        return provider.get("temperature", settings.get("defaults", {}).get("temperature", 0.2))
    return settings.get("defaults", {}).get("temperature", 0.2)


def get_provider_context(provider_name: str) -> str:
    settings = load_settings()
    provider = settings.get("providers", {}).get(provider_name)
    if provider:
        return provider.get("context", settings.get("defaults", {}).get("context", "default"))
    return settings.get("defaults", {}).get("context", "default")


if __name__ == "__main__":
    result = asyncio.run(benchmark_all())
    print(json.dumps(result, indent=2))

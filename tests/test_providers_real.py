#!/usr/bin/env python3
"""Final provider validation for exact config model names."""

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


async def validate_provider(provider_name: str):
    cfg = next((p for p in PROVIDERS if p["name"] == provider_name), None)
    if not cfg:
        return f"{provider_name}: not_in_config"

    api_key = os.getenv(cfg["api_key_env"])
    if not api_key or "your-" in api_key:
        return f"{provider_name}: missing_key"

    model = cfg["default_model"]
    base_url = cfg["base_url"]
    path = cfg.get("path", "chat/completions")

    if provider_name == "anthropic":
        url = f"{base_url}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "Respond with exactly: OK"}],
        }
    else:
        if path == "chat/completions":
            url = f"{base_url}/chat/completions"
        elif path == "v1/openai/chat/completions":
            url = f"{base_url}/v1/openai/chat/completions"
        elif path == "models":
            url = f"{base_url}/{model}"
        else:
            url = f"{base_url}/{path}"

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Respond with exactly: OK"}],
            "max_tokens": 10,
            "temperature": 0.0,
        }
        if path == "models":
            payload.pop("model", None)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            body = r.text[:180]
            return f"{provider_name}: {r.status_code} {body}"
    except Exception as e:
        return f"{provider_name}: error {str(e)[:120]}"


async def main():
    names = [
        "openrouter",
        "deepseek",
        "groq",
        "huggingface",
        "mistral",
        "deepinfra",
        "togetherai",
        "aihubmix",
        "aionlabs",
        "llm7io",
        "ovh-ai",
        "sambanova",
        "siliconflow",
        "bigmodel",
        "cerebras",
        "cloudflare-workers-ai",
        "cohere",
        "github-models",
        "google-ai-studio",
        "modelscope",
        "nvidia-nim",
        "ollama-cloud",
        "anthropic",
        "grok",
    ]

    for name in names:
        result = await validate_provider(name)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())

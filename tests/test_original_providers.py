#!/usr/bin/env python3
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

ORIGINAL_PROVIDERS = ["openrouter", "deepseek", "groq", "huggingface", "deepinfra", "togetherai", "aihubmix", "bigmodel", "cloudflare-workers-ai", "cohere", "github-models", "google-ai-studio", "mistral", "ovh-ai", "modelscope", "nvidia-nim", "ollama-cloud", "sambanova", "siliconflow"]

async def test(name, model):
    cfg = next((p for p in PROVIDERS if p["name"] == name), None)
    if not cfg:
        return f"{name}: not_configured"
    api_key = os.getenv(cfg["api_key_env"])
    if not api_key or "your-" in api_key:
        return f"{name}: no_key"
    url = f"{cfg['base_url']}/chat/completions"
    if cfg.get("path") == "models":
        url = f"{cfg['base_url']}/{model}"
    elif cfg.get("path") == "messages":
        url = f"{cfg['base_url']}/messages"
    elif cfg.get("path") == "v1/openai/chat/completions":
        url = f"{cfg['base_url']}/v1/openai/chat/completions"
    
    payload = {"model": model, "messages": [{"role": "user", "content": "Respond with exactly: OK"}], "max_tokens": 10, "temperature": 0.0}
    if cfg.get("path") == "models":
        payload.pop("model", None)
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload)
            if r.status_code == 200:
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return f"{name}: ok ({content.strip()[:40]})"
            else:
                return f"{name}: {r.status_code} {r.text[:120]}"
    except Exception as e:
        return f"{name}: error {str(e)[:120]}"

async def main():
    results = []
    for name in ORIGINAL_PROVIDERS:
        cfg = next((p for p in PROVIDERS if p["name"] == name), None)
        if not cfg:
            continue
        result = await test(name, cfg["default_model"])
        results.append(result)
        print(result)
    
    working = [r for r in results if r.startswith(tuple([n for n in ORIGINAL_PROVIDERS if ": ok" in n]))]
    print(f"\nWorking: {len(working)}/{len(results)}")

asyncio.run(main())

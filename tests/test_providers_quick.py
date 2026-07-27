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

async def test(name, model):
    cfg = next((p for p in PROVIDERS if p["name"] == name), None)
    if not cfg:
        print(f"{name}: not_configured")
        return
    api_key = os.getenv(cfg["api_key_env"])
    if not api_key or "your-" in api_key:
        print(f"{name}: no_key")
        return
    url = f"{cfg['base_url']}/chat/completions"
    if cfg.get("path") == "messages":
        url = f"{cfg['base_url']}/messages"
    payload = {"model": model, "messages": [{"role": "user", "content": "Respond with exactly: OK"}], "max_tokens": 10, "temperature": 0.0}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload)
            print(f"{name}: {r.status_code} {r.text[:160]}")
    except Exception as e:
        print(f"{name}: error {str(e)[:160]}")

async def main():
    await test("anthropic", "claude-3-5-sonnet-20240620")
    await test("grok", "grok-2")
    await test("cerebras", "gpt-oss-120b")

asyncio.run(main())

#!/usr/bin/env python3
"""Probe provider discovery APIs for valid free models."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").resolve()))

from dotenv import load_dotenv
load_dotenv(override=False)

import httpx


async def main():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    grok_key = os.getenv("GROK_API_KEY")
    cerebras_key = os.getenv("CEREBRAS_API_KEY")

    async with httpx.AsyncClient(timeout=30) as client:
        if anthropic_key:
            print("--- Anthropic models ---")
            try:
                r = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01"},
                )
                print(r.status_code, r.text[:400])
            except Exception as e:
                print("error", e)

        if grok_key:
            print("\n--- xAI models ---")
            try:
                r = await client.get(
                    "https://api.x.ai/v1/models",
                    headers={"Authorization": f"Bearer {grok_key}"},
                )
                print(r.status_code, r.text[:500])
            except Exception as e:
                print("error", e)

        if cerebras_key:
            print("\n--- Cerebras models ---")
            try:
                r = await client.get(
                    "https://api.cerebras.ai/v1/models",
                    headers={"Authorization": f"Bearer {cerebras_key}"},
                )
                print(r.status_code, r.text[:500])
            except Exception as e:
                print("error", e)


if __name__ == "__main__":
    asyncio.run(main())

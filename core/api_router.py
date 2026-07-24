import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class APIRouter:
    def __init__(self):
        self.providers = {
            "google": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": os.getenv("GOOGLE_AI_STUDIO_API_KEY"),
                "model": "gemini-2.5-flash",
                "max_tokens": 1000000
            },
            "groq": {
                "base_url": "https://api.groq.com/openai/v1",
                "api_key": os.getenv("GROQ_API_KEY"),
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 128000
            },
            "openrouter": {
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "model": "deepseek/deepseek-r1",
                "max_tokens": 128000
            }
        }
        self.client = httpx.AsyncClient(timeout=60.0)

    async def route_request(
        self,
        messages: list,
        provider: str = "google",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}")

        config = self.providers[provider]
        if not config["api_key"]:
            return await self._fallback_route(messages, max_tokens, temperature)

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or min(4096, config["max_tokens"])
        }

        try:
            response = await self.client.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"[API ROUTER] {provider} failed: {e}")
            return await self._fallback_route(messages, max_tokens, temperature)

    async def _fallback_route(
        self,
        messages: list,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        for provider in ["groq", "openrouter", "google"]:
            config = self.providers[provider]
            if config["api_key"]:
                print(f"[API ROUTER] Falling back to {provider}")
                return await self.route_request(messages, provider, max_tokens, temperature)
        raise RuntimeError("All API providers unavailable")

    async def close(self):
        await self.client.aclose()

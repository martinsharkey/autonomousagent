"""LiteLLM provider wrapper for optional use in proposer and agents."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class LLMProvider:
    """Thin wrapper around LiteLLM for consistent API usage."""

    def __init__(self):
        pass

    async def call(
        self,
        messages: List[Dict[str, Any]],
        model: str = "openrouter/claude-3.5-sonnet",
        fallback_models: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        try:
            from litellm import acompletion

            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30,
            )
            return response
        except Exception:
            if fallback_models:
                for fallback in fallback_models:
                    try:
                        from litellm import acompletion

                        response = await acompletion(
                            model=fallback,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            timeout=30,
                        )
                        return response
                    except Exception:
                        continue
            raise


_provider = None


def get_litellm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider

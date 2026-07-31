"""
Multi-provider response normalizer.

Normalizes LLM responses from various providers (OpenAI, Anthropic, Google, local)
into a unified schema to ensure downstream tools can process them consistently.

Unified schema:
{
    "content": str,
    "finish_reason": str | None,
    "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
    "error": {"type": str, "message": str} | None,
    "provider": str,
    "raw": dict
}
"""

import json
from typing import Any, Dict, Optional


def normalize_response(response: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Normalize a raw provider response into the unified schema."""
    if not isinstance(response, dict):
        return {
            "content": "",
            "finish_reason": None,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": {"type": "invalid_response", "message": "Response is not a dict"},
            "provider": provider,
            "raw": {},
        }

    # Detect error responses
    if "error" in response:
        err = response["error"]
        return {
            "content": "",
            "finish_reason": None,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": {"type": "provider_error", "message": str(err)},
            "provider": provider,
            "raw": response,
        }

    normalized = {
        "content": "",
        "finish_reason": None,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "error": None,
        "provider": provider,
        "raw": response,
    }

    # OpenAI-style
    if "choices" in response and isinstance(response["choices"], list) and response["choices"]:
        choice = response["choices"][0]
        if "message" in choice and isinstance(choice["message"], dict):
            normalized["content"] = choice["message"].get("content", "")
        elif "text" in choice:
            normalized["content"] = choice.get("text", "")
        normalized["finish_reason"] = choice.get("finish_reason")
        if "usage" in response:
            normalized["usage"] = _normalize_usage(response["usage"])

    # Anthropic-style
    elif "content" in response and isinstance(response["content"], list):
        # Anthropic returns list of content blocks
        parts = []
        for block in response["content"]:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        normalized["content"] = "\n".join(parts)
        normalized["finish_reason"] = response.get("stop_reason")
        if "usage" in response:
            normalized["usage"] = _normalize_usage(response["usage"])

    # Google-style (Gemini)
    elif "candidates" in response and isinstance(response["candidates"], list) and response["candidates"]:
        candidate = response["candidates"][0]
        if "content" in candidate and isinstance(candidate["content"], dict):
            parts = candidate["content"].get("parts", [])
            text_parts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
            normalized["content"] = "\n".join(text_parts)
        normalized["finish_reason"] = candidate.get("finishReason")
        if "usageMetadata" in response:
            usage = response["usageMetadata"]
            normalized["usage"] = {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            }

    # Local/other: assume plain text in 'text' or 'output'
    elif "text" in response:
        normalized["content"] = response["text"]
    elif "output" in response:
        normalized["content"] = response["output"]

    # If content is still empty, try to stringify
    if not normalized["content"] and "response" in response:
        normalized["content"] = str(response["response"])

    return normalized


def _normalize_usage(usage: Dict[str, Any]) -> Dict[str, int]:
    """Normalize usage dict to standard token counts."""
    return {
        "prompt_tokens": int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0),
        "completion_tokens": int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def normalize_error(error: Any) -> Dict[str, str]:
    """Normalize an exception into a standard error dict."""
    if isinstance(error, dict):
        return {"type": error.get("type", "unknown"), "message": str(error.get("message", ""))}
    return {"type": type(error).__name__, "message": str(error)}

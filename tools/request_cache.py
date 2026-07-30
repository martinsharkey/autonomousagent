import hashlib
import json
import time
from typing import Optional, Any

class RequestCache:
    """Simple TTL-based cache for LLM request responses."""
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _make_key(self, prompt: str, provider: str, model: str) -> str:
        raw = f"{prompt}::{provider}::{model}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, provider: str, model: str) -> Optional[Any]:
        key = self._make_key(prompt, provider, model)
        entry = self._cache.get(key)
        if entry is None:
            return None
        timestamp, response = entry
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None
        return response

    def set(self, prompt: str, provider: str, model: str, response: Any) -> None:
        key = self._make_key(prompt, provider, model)
        if len(self._cache) >= self._max_size:
            # Evict oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]
        self._cache[key] = (time.time(), response)

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict:
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl
        }

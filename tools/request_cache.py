import hashlib
import json
import time
from typing import Any, Dict, Optional

class RequestCache:
    """Simple TTL-based cache for LLM request/response pairs."""

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _make_key(self, model: str, messages: list, params: Optional[dict] = None) -> str:
        """Generate a deterministic cache key from request parameters."""
        raw = json.dumps({"model": model, "messages": messages, "params": params}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, model: str, messages: list, params: Optional[dict] = None) -> Optional[str]:
        """Return cached response if available and not expired."""
        key = self._make_key(model, messages, params)
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["timestamp"] > self._ttl:
            del self._cache[key]
            return None
        return entry["response"]

    def set(self, model: str, messages: list, response: str, params: Optional[dict] = None) -> None:
        """Store a response in the cache, evicting oldest if full."""
        key = self._make_key(model, messages, params)
        if len(self._cache) >= self._max_size:
            # Evict oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
        self._cache[key] = {"response": response, "timestamp": time.time()}

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
        }

# Singleton instance for global use
cache = RequestCache()

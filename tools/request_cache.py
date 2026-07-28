import time
import hashlib
import json
from typing import Any, Optional

class RequestCache:
    """Simple in-memory cache for LLM responses with TTL."""
    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple[float, Any]] = {}
        self.default_ttl = default_ttl

    def _make_key(self, prompt: str, model: str, **kwargs) -> str:
        raw = json.dumps({"prompt": prompt, "model": model, **kwargs}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, model: str, **kwargs) -> Optional[Any]:
        key = self._make_key(prompt, model, **kwargs)
        entry = self._cache.get(key)
        if entry is None:
            return None
        expiry, value = entry
        if time.time() > expiry:
            del self._cache[key]
            return None
        return value

    def set(self, prompt: str, model: str, value: Any, ttl: Optional[int] = None, **kwargs):
        key = self._make_key(prompt, model, **kwargs)
        ttl = ttl if ttl is not None else self.default_ttl
        self._cache[key] = (time.time() + ttl, value)

    def invalidate(self, prompt: str, model: str, **kwargs):
        key = self._make_key(prompt, model, **kwargs)
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)

import hashlib
import json
import time
from collections import OrderedDict

class RequestCache:
    """In-memory cache for LLM requests with TTL and LRU eviction."""
    def __init__(self, max_size=100, ttl_seconds=300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache = OrderedDict()

    def _make_key(self, provider: str, model: str, prompt: str, **kwargs) -> str:
        raw = json.dumps({"provider": provider, "model": model, "prompt": prompt, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, provider: str, model: str, prompt: str, **kwargs):
        key = self._make_key(provider, model, prompt, **kwargs)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                # Move to end to mark as recently used
                self._cache.move_to_end(key)
                return entry["response"]
            else:
                del self._cache[key]
        return None

    def set(self, provider: str, model: str, prompt: str, response: str, **kwargs):
        key = self._make_key(provider, model, prompt, **kwargs)
        if len(self._cache) >= self.max_size:
            # Evict oldest (first) entry
            self._cache.popitem(last=False)
        self._cache[key] = {"response": response, "timestamp": time.time()}

    def clear(self):
        self._cache.clear()

    def stats(self):
        return {"size": len(self._cache), "max_size": self.max_size, "ttl": self.ttl}

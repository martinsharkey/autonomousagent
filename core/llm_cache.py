import hashlib
import json
import time
from typing import Optional, Any

class LLMCache:
    """Simple in-memory cache for LLM responses with TTL."""
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 100):
        self.cache = {}
        self.ttl = ttl_seconds
        self.max_size = max_size

    def _make_key(self, model: str, prompt: str, **kwargs) -> str:
        data = {'model': model, 'prompt': prompt, **kwargs}
        raw = json.dumps(data, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, model: str, prompt: str, **kwargs) -> Optional[Any]:
        key = self._make_key(model, prompt, **kwargs)
        entry = self.cache.get(key)
        if entry is None:
            return None
        if time.time() - entry['timestamp'] > self.ttl:
            del self.cache[key]
            return None
        return entry['response']

    def set(self, model: str, prompt: str, response: Any, **kwargs):
        if len(self.cache) >= self.max_size:
            # Evict oldest entry
            oldest_key = min(self.cache, key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        key = self._make_key(model, prompt, **kwargs)
        self.cache[key] = {'response': response, 'timestamp': time.time()}

    def clear(self):
        self.cache.clear()

# Global cache instance
llm_cache = LLMCache()

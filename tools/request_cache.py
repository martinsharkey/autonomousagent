import hashlib
import json
import time
from collections import OrderedDict

class RequestCache:
    """LRU cache for LLM request responses with TTL."""
    
    def __init__(self, max_size=100, ttl_seconds=3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
    
    def _make_key(self, prompt, provider, model, params):
        """Generate a deterministic cache key from request parameters."""
        raw = json.dumps({
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "params": params
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def get(self, prompt, provider, model, params=None):
        """Return cached response if valid, else None."""
        key = self._make_key(prompt, provider, model, params or {})
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                # Move to end to mark as recently used
                self._cache.move_to_end(key)
                return entry["response"]
            else:
                # Expired
                del self._cache[key]
        return None
    
    def set(self, prompt, provider, model, response, params=None):
        """Store a response in the cache."""
        key = self._make_key(prompt, provider, model, params or {})
        self._cache[key] = {
            "response": response,
            "timestamp": time.time()
        }
        self._cache.move_to_end(key)
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
    
    def stats(self):
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


# Singleton instance for global use
_cache = RequestCache()

def get_cache():
    return _cache

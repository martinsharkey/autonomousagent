import hashlib
import time
from collections import OrderedDict

class RequestCache:
    """TTL-based cache for LLM requests to reduce redundant calls."""
    def __init__(self, maxsize=128, ttl=60):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl

    def _make_key(self, model, messages, **kwargs):
        raw = f"{model}:{messages}:{sorted(kwargs.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, model, messages, **kwargs):
        key = self._make_key(model, messages, **kwargs)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['time'] < self.ttl:
                self.cache.move_to_end(key)
                return entry['response']
            else:
                del self.cache[key]
        return None

    def set(self, model, messages, response, **kwargs):
        key = self._make_key(model, messages, **kwargs)
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)
        self.cache[key] = {'response': response, 'time': time.time()}

# Global cache instance
_request_cache = RequestCache()

def get_cached_completion(model, messages, **kwargs):
    cached = _request_cache.get(model, messages, **kwargs)
    if cached:
        return cached
    # Fallback to actual provider call (placeholder)
    result = None  # actual call would go here
    _request_cache.set(model, messages, result, **kwargs)
    return result

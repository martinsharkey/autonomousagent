import hashlib
import json
import time
from typing import Any, Dict, Optional

class RequestCache:
    """Simple TTL-based cache for LLM request-response pairs."""
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        self.max_size = max_size

    def _make_key(self, request: Dict[str, Any]) -> str:
        """Generate a deterministic hash key from the request."""
        raw = json.dumps(request, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return cached response if valid, else None."""
        key = self._make_key(request)
        entry = self.cache.get(key)
        if entry is None:
            return None
        if time.time() - entry['timestamp'] > self.ttl:
            del self.cache[key]
            return None
        return entry['response']

    def set(self, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        """Cache a request-response pair."""
        key = self._make_key(request)
        if len(self.cache) >= self.max_size:
            # Evict oldest entry
            oldest = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest]
        self.cache[key] = {
            'response': response,
            'timestamp': time.time()
        }

    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl
        }

# Global singleton for easy import
cache = RequestCache()

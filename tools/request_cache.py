import hashlib
import time
import threading
from typing import Optional, Dict, Any

class RequestCache:
    """Thread-safe cache for LLM API responses with TTL and deduplication."""

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def _make_key(self, prompt: str, provider: str, model: str) -> str:
        raw = f"{provider}:{model}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, prompt: str, provider: str, model: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(prompt, provider, model)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return None
            entry["hits"] += 1
            return entry["response"]

    def set(self, prompt: str, provider: str, model: str, response: Dict[str, Any], ttl: Optional[int] = None):
        key = self._make_key(prompt, provider, model)
        expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            self._cache[key] = {
                "response": response,
                "expires_at": expires_at,
                "hits": 0,
                "created_at": time.time()
            }

    def get_or_create_lock(self, prompt: str, provider: str, model: str) -> threading.Lock:
        key = self._make_key(prompt, provider, model)
        with self._lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def invalidate(self, prompt: str, provider: str, model: str):
        key = self._make_key(prompt, provider, model)
        with self._lock:
            self._cache.pop(key, None)
            self._locks.pop(key, None)

    def clear_expired(self):
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._cache.items() if now > v["expires_at"]]
            for k in expired:
                del self._cache[k]
                self._locks.pop(k, None)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._cache)
            hits = sum(v["hits"] for v in self._cache.values())
            return {"cached_entries": total, "total_hits": hits}

# Singleton instance for global use
cache = RequestCache()

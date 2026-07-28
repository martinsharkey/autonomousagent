"""Tool for quota-aware provider fallback and request caching."""
import hashlib
import json
import os
from typing import Any, Dict, Optional

CACHE_DIR = "cache"
CACHE_TTL = 3600  # 1 hour

class ProviderOptimizer:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self._load_cache()

    def _cache_path(self, key: str) -> str:
        return os.path.join(CACHE_DIR, f"{key}.json")

    def _load_cache(self):
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)
        for fname in os.listdir(CACHE_DIR):
            if fname.endswith(".json"):
                with open(os.path.join(CACHE_DIR, fname), "r") as f:
                    self.cache[fname[:-5]] = json.load(f)

    def get_cached(self, request_key: str) -> Optional[Any]:
        if request_key in self.cache:
            entry = self.cache[request_key]
            if entry["ttl"] > 0:
                return entry["response"]
        return None

    def set_cache(self, request_key: str, response: Any, ttl: int = CACHE_TTL):
        entry = {"response": response, "ttl": ttl}
        self.cache[request_key] = entry
        path = self._cache_path(request_key)
        with open(path, "w") as f:
            json.dump(entry, f)

    def make_request(self, provider: str, request: Dict[str, Any], fallback_providers: list) -> Any:
        # Generate cache key from request
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        cached = self.get_cached(key)
        if cached:
            return cached
        # Attempt primary provider
        for prov in [provider] + fallback_providers:
            try:
                # Placeholder for actual API call
                response = self._call_provider(prov, request)
                self.set_cache(key, response)
                return response
            except Exception as e:
                # Log failure and try next
                print(f"Provider {prov} failed: {e}")
                continue
        raise Exception("All providers failed")

    def _call_provider(self, provider: str, request: Dict[str, Any]) -> Any:
        # Stub: replace with actual provider call logic
        return {"status": "ok", "data": "mock"}

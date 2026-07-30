import json
import time
import hashlib
from collections import defaultdict
from pathlib import Path

CACHE_FILE = Path("data/quota_cache.json")
CACHE_TTL = 3600  # 1 hour default

class QuotaCache:
    """Thread-safe cache for LLM responses with per-provider quota tracking."""
    
    def __init__(self):
        self.cache = {}
        self.quota_usage = defaultdict(lambda: {"requests": 0, "tokens": 0, "reset_time": time.time() + 3600})
        self._load()
    
    def _load(self):
        if CACHE_FILE.exists():
            try:
                data = json.loads(CACHE_FILE.read_text())
                self.cache = data.get("cache", {})
                self.quota_usage = defaultdict(lambda: {"requests": 0, "tokens": 0, "reset_time": time.time() + 3600}, data.get("quota", {}))
            except Exception:
                pass
    
    def _save(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "cache": self.cache,
            "quota": dict(self.quota_usage)
        }))
    
    def _make_key(self, provider: str, model: str, prompt: str) -> str:
        raw = f"{provider}:{model}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def get(self, provider: str, model: str, prompt: str):
        key = self._make_key(provider, model, prompt)
        entry = self.cache.get(key)
        if entry and time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["response"]
        return None
    
    def set(self, provider: str, model: str, prompt: str, response: str):
        key = self._make_key(provider, model, prompt)
        self.cache[key] = {"response": response, "timestamp": time.time()}
        self._save()
    
    def track_usage(self, provider: str, tokens: int = 0):
        now = time.time()
        usage = self.quota_usage[provider]
        if now > usage["reset_time"]:
            usage["requests"] = 0
            usage["tokens"] = 0
            usage["reset_time"] = now + 3600
        usage["requests"] += 1
        usage["tokens"] += tokens
        self._save()
    
    def is_quota_exhausted(self, provider: str, max_requests: int = 100, max_tokens: int = 100000) -> bool:
        usage = self.quota_usage.get(provider, {})
        return usage.get("requests", 0) >= max_requests or usage.get("tokens", 0) >= max_tokens
    
    def get_best_provider(self, providers: list, max_requests: int = 100, max_tokens: int = 100000) -> str:
        for p in providers:
            if not self.is_quota_exhausted(p, max_requests, max_tokens):
                return p
        return providers[0]  # fallback

# Singleton instance
quota_cache = QuotaCache()

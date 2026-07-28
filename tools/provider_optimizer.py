import hashlib, json, time
from collections import OrderedDict

class ProviderOptimizer:
    def __init__(self, cache_size=100, cache_ttl=3600):
        self.cache = OrderedDict()
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.provider_quotas = {'openai': 100, 'anthropic': 100, 'google': 100}
        self.current_provider = 'openai'

    def _cache_key(self, prompt, model):
        return hashlib.md5((prompt + model).encode()).hexdigest()

    def get_cached(self, prompt, model):
        key = self._cache_key(prompt, model)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['time'] < self.cache_ttl:
                # Move to end to mark as recently used
                self.cache.move_to_end(key)
                return entry['response']
            else:
                del self.cache[key]
        return None

    def set_cache(self, prompt, model, response):
        key = self._cache_key(prompt, model)
        if len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)
        self.cache[key] = {'response': response, 'time': time.time()}

    def switch_provider_if_needed(self):
        # Simple round-robin fallback if quota exhausted
        providers = ['openai', 'anthropic', 'google']
        for p in providers:
            if self.provider_quotas.get(p, 0) > 0:
                self.current_provider = p
                return p
        return None

    def consume_quota(self, provider):
        if provider in self.provider_quotas and self.provider_quotas[provider] > 0:
            self.provider_quotas[provider] -= 1

    def reset_quotas(self):
        self.provider_quotas = {'openai': 100, 'anthropic': 100, 'google': 100}

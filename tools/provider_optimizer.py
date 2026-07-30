from tools.request_cache import RequestCache

# Initialize cache at module level
_request_cache = RequestCache(max_size=200, ttl_seconds=600)

def get_cached_or_call(provider: str, model: str, prompt: str, call_fn, **kwargs):
    """Check cache before calling the LLM provider."""
    cached = _request_cache.get(provider, model, prompt, **kwargs)
    if cached is not None:
        return cached
    response = call_fn(provider, model, prompt, **kwargs)
    _request_cache.set(provider, model, prompt, response, **kwargs)
    return response

def clear_cache():
    _request_cache.clear()

def cache_stats():
    return _request_cache.stats()

from core.llm_cache import llm_cache

# Inside the call_llm function, before making the actual API call:
def call_llm(model: str, prompt: str, **kwargs):
    cached = llm_cache.get(model, prompt, **kwargs)
    if cached is not None:
        return cached
    # ... existing API call logic ...
    response = actual_api_call(model, prompt, **kwargs)
    llm_cache.set(model, prompt, response, **kwargs)
    return response

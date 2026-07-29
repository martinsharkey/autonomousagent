import hashlib
import json
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

class RequestBatcher:
    """Batches compatible LLM requests to reduce API calls and optimize quota usage."""

    def __init__(self, cache_ttl: int = 300, max_batch_size: int = 10):
        self.cache: Dict[str, Tuple[float, Any]] = {}
        self.cache_ttl = cache_ttl
        self.max_batch_size = max_batch_size
        self.pending: Dict[str, List[Dict]] = defaultdict(list)

    def _make_key(self, model: str, prompt: str, params: Optional[Dict] = None) -> str:
        raw = json.dumps({"model": model, "prompt": prompt, "params": params}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def add_request(self, model: str, prompt: str, params: Optional[Dict] = None) -> Optional[str]:
        """Add a request to the batch. Returns cached response if available."""
        key = self._make_key(model, prompt, params)
        # Check cache
        if key in self.cache:
            timestamp, response = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return response
            else:
                del self.cache[key]
        # Add to pending batch
        self.pending[model].append({"key": key, "prompt": prompt, "params": params})
        if len(self.pending[model]) >= self.max_batch_size:
            return None  # Signal to flush
        return None

    def flush_batch(self, model: str) -> List[Dict]:
        """Return all pending requests for a model and clear the queue."""
        batch = self.pending.pop(model, [])
        return batch

    def cache_response(self, key: str, response: Any) -> None:
        """Store a response in cache."""
        self.cache[key] = (time.time(), response)

    def get_stats(self) -> Dict:
        """Return usage statistics."""
        return {
            "cache_size": len(self.cache),
            "pending_requests": sum(len(v) for v in self.pending.values()),
            "models_in_queue": list(self.pending.keys()),
        }

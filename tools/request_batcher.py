"""Request batching and caching tool for LLM API calls.

This tool groups pending requests by similarity and caches responses to
reduce redundant API calls, optimizing resource usage and cost.
"""

import hashlib
import json
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

class RequestBatcher:
    def __init__(self, cache_ttl: int = 300, max_batch_size: int = 10):
        self.cache: Dict[str, Tuple[float, Any]] = {}
        self.cache_ttl = cache_ttl
        self.max_batch_size = max_batch_size
        self.pending: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def _hash_request(self, request: Dict[str, Any]) -> str:
        """Generate a hash for a request to identify duplicates."""
        canonical = json.dumps(request, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def add_request(self, request: Dict[str, Any]) -> str:
        """Add a request to the batch queue and return its hash."""
        req_hash = self._hash_request(request)
        self.pending[req_hash].append(request)
        return req_hash

    def get_cached(self, request: Dict[str, Any]) -> Optional[Any]:
        """Return cached response if available and not expired."""
        req_hash = self._hash_request(request)
        if req_hash in self.cache:
            timestamp, response = self.cache[req_hash]
            if time.time() - timestamp < self.cache_ttl:
                return response
            else:
                del self.cache[req_hash]
        return None

    def flush_batch(self) -> List[Tuple[str, Any]]:
        """Process all pending requests and return (hash, response) pairs.

        In a real implementation, this would call the LLM provider with
        batched requests. Here we simulate by returning a placeholder.
        """
        results = []
        for req_hash, requests in self.pending.items():
            if not requests:
                continue
            # Simulate batched response: use the first request as representative
            # In production, this would be replaced with actual batched API call.
            response = {"batched": True, "count": len(requests), "hash": req_hash}
            self.cache[req_hash] = (time.time(), response)
            results.append((req_hash, response))
        self.pending.clear()
        return results

    def clear_expired(self) -> None:
        """Remove expired cache entries."""
        now = time.time()
        expired = [k for k, (t, _) in self.cache.items() if now - t >= self.cache_ttl]
        for k in expired:
            del self.cache[k]

    def stats(self) -> Dict[str, int]:
        """Return cache and pending stats."""
        return {
            "cache_size": len(self.cache),
            "pending_requests": sum(len(v) for v in self.pending.values()),
        }

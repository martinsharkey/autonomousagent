import time
import hashlib
from typing import List, Dict, Any, Optional
from core.api_router import APIRouter

class RequestBatcher:
    def __init__(self, max_batch_size: int = 5, max_wait_time: float = 1.0, cache_ttl: float = 300.0):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.cache_ttl = cache_ttl
        self.batch_queue: List[Dict[str, Any]] = []
        self.request_cache: Dict[str, Dict[str, Any]] = {}
        self.last_cache_cleanup = time.time()

    def _generate_cache_key(self, request: Dict[str, Any]) -> str:
        """Generate a unique cache key for a request."""
        request_str = str(request)
        return hashlib.md5(request_str.encode()).hexdigest()

    def _cleanup_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [key for key, entry in self.request_cache.items() 
                       if current_time - entry['timestamp'] > self.cache_ttl]
        for key in expired_keys:
            del self.request_cache[key]

    def _should_deduplicate(self, request: Dict[str, Any]) -> bool:
        """Check if a request should be deduplicated."""
        cache_key = self._generate_cache_key(request)
        if cache_key in self.request_cache:
            cached_result = self.request_cache[cache_key]['result']
            if cached_result:
                return True
        return False

    def _add_to_cache(self, request: Dict[str, Any], result: Any):
        """Add a request and its result to the cache."""
        cache_key = self._generate_cache_key(request)
        self.request_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

    def batch_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch and deduplicate a list of requests."""
        self._cleanup_cache()
        batched_requests = []
        processed_requests = set()

        for request in requests:
            cache_key = self._generate_cache_key(request)
            if cache_key in self.request_cache:
                batched_requests.append(self.request_cache[cache_key]['result'])
                processed_requests.add(cache_key)
            else:
                batched_requests.append(request)

        return batched_requests

    def execute_batched_requests(self, router: APIRouter, requests: List[Dict[str, Any]]) -> List[Any]:
        """Execute a batch of requests and cache results."""
        batched_requests = self.batch_requests(requests)
        results = []

        for request in batched_requests:
            if isinstance(request, dict) and 'result' in request:
                results.append(request['result'])
            else:
                result = router.route_request(request)
                results.append(result)
                self._add_to_cache(request, result)

        return results

# Example usage:
# batcher = RequestBatcher(max_batch_size=5, max_wait_time=1.0, cache_ttl=300.0)
# router = APIRouter()
# requests = [{'prompt': 'Hello'}, {'prompt': 'World'}]
# results = batcher.execute_batched_requests(router, requests)
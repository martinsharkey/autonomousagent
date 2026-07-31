#!/usr/bin/env python3
"""Batch and cache LLM requests to optimize resource usage.

This tool provides a simple in-memory cache with TTL and a batching mechanism
that groups multiple requests to the same provider/model into a single call.
It is designed to be used by the agent loop or planning module to reduce
API calls and improve latency.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple

class TTLCache:
    """Thread-safe TTL cache with LRU eviction."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            timestamp, value = self._cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                return None
            # Move to end to mark as recently used
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (time.time(), value)
            self._cache.move_to_end(key)
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

class BatchCache:
    """Batch and cache LLM requests.

    Usage:
        bc = BatchCache(batch_size=5, max_wait_seconds=0.1)
        # Register a function that sends a batch of prompts to the LLM
        bc.set_batch_executor(provider, model, batch_executor)
        # Get a response for a single prompt
        response = bc.request(provider, model, prompt, **kwargs)
    """

    def __init__(self, batch_size: int = 5, max_wait_seconds: float = 0.1,
                 cache_ttl: int = 300, cache_max_size: int = 100):
        self.batch_size = batch_size
        self.max_wait_seconds = max_wait_seconds
        self.cache = TTLCache(max_size=cache_max_size, ttl_seconds=cache_ttl)
        self._batch_executors: Dict[Tuple[str, str], Callable] = {}
        self._pending: Dict[Tuple[str, str], List[Tuple[str, Dict, float]]] = {}
        self._lock = threading.Lock()
        self._batch_threads: Dict[Tuple[str, str], threading.Thread] = {}

    def set_batch_executor(self, provider: str, model: str, executor: Callable) -> None:
        """Set a function that takes a list of (prompt, kwargs) and returns a list of responses."""
        self._batch_executors[(provider, model)] = executor

    def request(self, provider: str, model: str, prompt: str, **kwargs) -> Any:
        """Get a response for a single prompt, using cache and batching."""
        cache_key = self._make_key(provider, model, prompt, kwargs)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        key = (provider, model)
        with self._lock:
            if key not in self._pending:
                self._pending[key] = []
            self._pending[key].append((prompt, kwargs, time.time()))
            if len(self._pending[key]) >= self.batch_size:
                # Trigger immediate batch
                self._flush_batch(key)
            elif key not in self._batch_threads or not self._batch_threads[key].is_alive():
                # Start a timer thread to flush after max_wait_seconds
                t = threading.Thread(target=self._delayed_flush, args=(key,))
                t.daemon = True
                self._batch_threads[key] = t
                t.start()

        # Wait for the batch to complete (polling with timeout)
        deadline = time.time() + self.max_wait_seconds + 2.0
        while time.time() < deadline:
            result = self.cache.get(cache_key)
            if result is not None:
                return result
            time.sleep(0.01)
        # If not found, fallback to direct call (should not happen if executor works)
        return None

    def _delayed_flush(self, key: Tuple[str, str]) -> None:
        time.sleep(self.max_wait_seconds)
        self._flush_batch(key)

    def _flush_batch(self, key: Tuple[str, str]) -> None:
        with self._lock:
            if key not in self._pending or not self._pending[key]:
                return
            batch = self._pending.pop(key)
        executor = self._batch_executors.get(key)
        if executor is None:
            # No executor, just return None for each (should not happen)
            return
        prompts = [item[0] for item in batch]
        kwargs_list = [item[1] for item in batch]
        try:
            responses = executor(prompts, kwargs_list)
            for (prompt, kwargs, _), response in zip(batch, responses):
                cache_key = self._make_key(key[0], key[1], prompt, kwargs)
                self.cache.set(cache_key, response)
        except Exception as e:
            # Log error and leave cache empty; caller will timeout
            print(f"Batch execution failed: {e}")

    @staticmethod
    def _make_key(provider: str, model: str, prompt: str, kwargs: Dict) -> str:
        payload = json.dumps({"provider": provider, "model": model, "prompt": prompt, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

# Example usage
if __name__ == "__main__":
    # Mock executor that returns reversed prompts
    def mock_executor(prompts, kwargs_list):
        return [p[::-1] for p in prompts]

    bc = BatchCache(batch_size=2, max_wait_seconds=0.05)
    bc.set_batch_executor("mock", "model", mock_executor)
    result1 = bc.request("mock", "model", "hello")
    result2 = bc.request("mock", "model", "world")
    print(result1, result2)

#!/usr/bin/env python3
"""Batch request coalescing tool for LLM API calls.

Groups similar pending requests within a short time window and executes them
as a single batched call, reducing API call overhead and cost.
"""

import hashlib
import json
import threading
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

class BatchCoalescer:
    """Coalesces identical or similar requests into batches."""

    def __init__(self, window_seconds: float = 0.5, max_batch_size: int = 10,
                 similarity_threshold: float = 0.9):
        self.window_seconds = window_seconds
        self.max_batch_size = max_batch_size
        self.similarity_threshold = similarity_threshold
        self._lock = threading.Lock()
        self._pending: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._last_flush: Dict[str, float] = {}

    def _key(self, request: Dict[str, Any]) -> str:
        """Generate a key based on provider and model."""
        provider = request.get('provider', 'default')
        model = request.get('model', 'default')
        return f"{provider}:{model}"

    def _similar(self, req1: Dict[str, Any], req2: Dict[str, Any]) -> bool:
        """Check if two requests are similar enough to batch."""
        # Compare essential fields: prompt, temperature, max_tokens
        fields = ['prompt', 'temperature', 'max_tokens']
        for f in fields:
            if req1.get(f) != req2.get(f):
                return False
        return True

    def submit(self, request: Dict[str, Any], executor: Callable[[List[Dict[str, Any]]], List[Any]]) -> Any:
        """Submit a request and return the result.

        If a batch is ready, executes it; otherwise waits for the window.
        This is a simplified synchronous implementation for demonstration.
        """
        key = self._key(request)
        with self._lock:
            self._pending[key].append(request)
            now = time.time()
            last = self._last_flush.get(key, now)
            if len(self._pending[key]) >= self.max_batch_size or (now - last) >= self.window_seconds:
                batch = self._pending.pop(key)
                self._last_flush[key] = now
            else:
                # In a real implementation, this would wait asynchronously.
                # For simplicity, we flush immediately if window elapsed.
                time.sleep(self.window_seconds - (now - last))
                batch = self._pending.pop(key)
                self._last_flush[key] = time.time()

        # Filter to similar requests (in case of mixed keys)
        similar_batch = [r for r in batch if self._similar(batch[0], r)]
        if len(similar_batch) < len(batch):
            # Put non-similar back for later
            with self._lock:
                for r in batch[len(similar_batch):]:
                    self._pending[key].append(r)

        if not similar_batch:
            raise ValueError("No similar requests to batch")

        # Execute batch
        results = executor(similar_batch)
        if len(results) != len(similar_batch):
            raise ValueError("Executor returned wrong number of results")
        return results[0]  # Return first result for simplicity

    def flush_all(self) -> None:
        """Flush all pending batches (for shutdown)."""
        with self._lock:
            for key, batch in self._pending.items():
                if batch:
                    # In real usage, would execute here; for now just clear
                    self._pending[key] = []

# Example usage
if __name__ == '__main__':
    def fake_executor(batch):
        return [f"result_{i}" for i in range(len(batch))]

    coalescer = BatchCoalescer(window_seconds=0.1)
    req = {'provider': 'openai', 'model': 'gpt-3.5-turbo', 'prompt': 'Hello', 'temperature': 0.7, 'max_tokens': 50}
    result = coalescer.submit(req, fake_executor)
    print(result)

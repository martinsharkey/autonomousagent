import asyncio
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

class QuotaBatcher:
    """
    Batches pending LLM requests by provider and priority, respecting per-provider quota limits.
    """

    def __init__(self, max_batch_size: int = 10, flush_interval: float = 1.0):
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self._queues: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self._last_flush: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def enqueue(self, provider: str, priority: str, request: Dict[str, Any]) -> None:
        """Add a request to the batch queue."""
        async with self._lock:
            self._queues[provider][priority].append(request)

    async def flush(self, provider: str) -> List[Dict[str, Any]]:
        """Flush all queued requests for a provider, returning batches."""
        async with self._lock:
            batches = []
            for priority in ['high', 'medium', 'low']:
                queue = self._queues[provider].get(priority, [])
                while queue:
                    batch = queue[:self.max_batch_size]
                    queue = queue[self.max_batch_size:]
                    batches.append({
                        'provider': provider,
                        'priority': priority,
                        'requests': batch,
                        'timestamp': time.time()
                    })
                self._queues[provider][priority] = queue
            self._last_flush[provider] = time.time()
            return batches

    async def get_pending_count(self, provider: str) -> int:
        """Return total pending requests for a provider."""
        async with self._lock:
            total = 0
            for priority in ['high', 'medium', 'low']:
                total += len(self._queues[provider].get(priority, []))
            return total

    async def clear(self, provider: Optional[str] = None) -> None:
        """Clear queues for a provider or all providers."""
        async with self._lock:
            if provider:
                self._queues.pop(provider, None)
            else:
                self._queues.clear()

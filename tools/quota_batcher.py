import time
import asyncio
from collections import defaultdict
from typing import Dict, List, Any, Optional

class QuotaBatcher:
    """Batches LLM requests by provider and priority to optimize quota usage."""

    def __init__(self, max_batch_size: int = 5, flush_interval: float = 2.0):
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self._queues: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def enqueue(self, provider: str, priority: str, request: Dict[str, Any]) -> None:
        """Add a request to the batch queue."""
        async with self._lock:
            self._queues[provider][priority].append(request)
            if len(self._queues[provider][priority]) >= self.max_batch_size:
                await self._flush_provider(provider, priority)

    async def _flush_provider(self, provider: str, priority: str) -> List[Dict[str, Any]]:
        """Flush all queued requests for a given provider and priority."""
        async with self._lock:
            batch = self._queues[provider].pop(priority, [])
        if not batch:
            return []
        # Simulate batch send (replace with actual API call)
        results = []
        for req in batch:
            # Placeholder: actual call would aggregate and send
            result = {"status": "batched", "request": req, "provider": provider}
            results.append(result)
        return results

    async def flush_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Flush all queues."""
        all_results = {}
        async with self._lock:
            providers = list(self._queues.keys())
        for provider in providers:
            async with self._lock:
                priorities = list(self._queues[provider].keys())
            for priority in priorities:
                results = await self._flush_provider(provider, priority)
                if results:
                    all_results.setdefault(provider, []).extend(results)
        return all_results

    async def start_background_flush(self):
        """Start a background task that periodically flushes queues."""
        async def _periodic_flush():
            while True:
                await asyncio.sleep(self.flush_interval)
                await self.flush_all()
        self._flush_task = asyncio.create_task(_periodic_flush())

    async def stop_background_flush(self):
        """Stop the background flush task."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

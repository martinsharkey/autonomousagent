import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

class RequestBatcher:
    """Batches LLM requests per provider, respecting quotas and priorities."""

    def __init__(self, max_batch_size: int = 5, flush_interval: float = 0.5):
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self._queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._flush_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def enqueue(self, provider: str, request: Dict[str, Any], priority: int = 0) -> Optional[Any]:
        """Add a request to the batch queue. Returns future result if batching, else None."""
        async with self._lock:
            self._queues[provider].append({
                'request': request,
                'priority': priority,
                'timestamp': time.time(),
                'future': asyncio.get_event_loop().create_future()
            })
            if len(self._queues[provider]) >= self.max_batch_size:
                return await self._flush(provider)
            if provider not in self._flush_tasks or self._flush_tasks[provider].done():
                self._flush_tasks[provider] = asyncio.create_task(self._delayed_flush(provider))
        return None

    async def _delayed_flush(self, provider: str):
        await asyncio.sleep(self.flush_interval)
        async with self._lock:
            if self._queues[provider]:
                await self._flush(provider)

    async def _flush(self, provider: str) -> List[Any]:
        """Flush all queued requests for a provider, sorted by priority."""
        batch = self._queues.pop(provider, [])
        if not batch:
            return []
        # Sort by priority (lower number = higher priority)
        batch.sort(key=lambda x: (x['priority'], x['timestamp']))
        requests = [item['request'] for item in batch]
        futures = [item['future'] for item in batch]
        # Placeholder: actual batch send logic would call provider API
        # For now, simulate with a simple echo
        results = [{'status': 'batched', 'original': r} for r in requests]
        for future, result in zip(futures, results):
            if not future.done():
                future.set_result(result)
        return results

    async def shutdown(self):
        """Flush all remaining queues on shutdown."""
        for provider in list(self._queues.keys()):
            async with self._lock:
                if self._queues[provider]:
                    await self._flush(provider)
        for task in self._flush_tasks.values():
            if not task.done():
                task.cancel()

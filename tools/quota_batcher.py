import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Any, Optional

class QuotaBatcher:
    """Batches LLM requests by provider and priority to optimize quota usage."""

    def __init__(self, max_batch_size: int = 5, flush_interval: float = 1.0):
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self._queues: Dict[str, Dict[int, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background flush loop."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self):
        """Stop the background flush loop."""
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None

    async def add_request(self, provider: str, priority: int, request: Dict) -> None:
        """Add a request to the batch queue."""
        async with self._lock:
            self._queues[provider][priority].append(request)

    async def flush(self) -> List[Dict]:
        """Flush all queued requests and return batches."""
        async with self._lock:
            batches = []
            for provider, priority_queues in self._queues.items():
                for priority in sorted(priority_queues.keys(), reverse=True):
                    queue = priority_queues[priority]
                    while queue:
                        batch = queue[:self.max_batch_size]
                        queue[:] = queue[self.max_batch_size:]
                        batches.append({
                            "provider": provider,
                            "priority": priority,
                            "requests": batch
                        })
            self._queues.clear()
            return batches

    async def _flush_loop(self):
        """Periodically flush batches."""
        while True:
            await asyncio.sleep(self.flush_interval)
            batches = await self.flush()
            if batches:
                # Process batches (e.g., send to provider)
                for batch in batches:
                    # Placeholder: actual provider call logic
                    pass

# Singleton instance
batcher = QuotaBatcher()

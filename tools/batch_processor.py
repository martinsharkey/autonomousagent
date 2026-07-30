import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

class BatchProcessor:
    """Quota-aware batch request processor for optimizing free tier usage."""

    def __init__(
        self,
        max_batch_size: int = 10,
        flush_interval: float = 1.0,
        quota_limits: Optional[Dict[str, int]] = None,
    ):
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval
        self.quota_limits = quota_limits or {}
        self._queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background flush loop."""
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self):
        """Stop the background flush loop and flush remaining."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush_all()

    async def add_request(
        self,
        provider: str,
        model: str,
        payload: Dict[str, Any],
        callback: Callable,
    ) -> None:
        """Add a request to the batch queue."""
        key = f"{provider}:{model}"
        async with self._lock:
            self._queues[key].append({
                "payload": payload,
                "callback": callback,
                "timestamp": time.time(),
            })
            if len(self._queues[key]) >= self.max_batch_size:
                await self._flush_key(key)

    async def _flush_key(self, key: str):
        """Flush all requests for a given provider:model key."""
        if key not in self._queues:
            return
        batch = self._queues.pop(key, [])
        if not batch:
            return
        provider, model = key.split(":", 1)
        # Check quota before sending
        if provider in self.quota_limits:
            remaining = self.quota_limits[provider] - len(batch)
            if remaining < 0:
                # Exceeded quota, drop excess or log
                batch = batch[:self.quota_limits[provider]]
                self.quota_limits[provider] = 0
            else:
                self.quota_limits[provider] = remaining
        # Execute batch (simplified: call each callback with payload)
        for req in batch:
            try:
                result = await req["callback"](req["payload"])
                # Optionally handle result
            except Exception as e:
                # Log error, could implement retry
                pass

    async def flush_all(self):
        """Flush all remaining queues."""
        async with self._lock:
            keys = list(self._queues.keys())
            for key in keys:
                await self._flush_key(key)

    async def _flush_loop(self):
        """Periodically flush queues based on interval."""
        while True:
            await asyncio.sleep(self.flush_interval)
            async with self._lock:
                keys = list(self._queues.keys())
                for key in keys:
                    if self._queues[key]:
                        await self._flush_key(key)

    def update_quota(self, provider: str, limit: int):
        """Update quota limit for a provider."""
        self.quota_limits[provider] = limit

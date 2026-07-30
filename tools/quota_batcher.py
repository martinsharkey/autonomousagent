import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

class QuotaBatcher:
    """
    Batches LLM requests by provider and priority to reduce API calls
    and stay within free tier quotas.
    """

    def __init__(
        self,
        max_batch_size: int = 10,
        max_wait_time: float = 0.5,
        quota_limits: Optional[Dict[str, int]] = None,
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.quota_limits = quota_limits or {}
        self._queues: Dict[str, List[Tuple[float, int, Any, Callable]]] = defaultdict(list)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_request_time: Dict[str, float] = {}
        self._request_count: Dict[str, int] = defaultdict(int)
        self._reset_time: Dict[str, float] = {}

    async def submit(
        self,
        provider: str,
        priority: int,
        payload: Any,
        callback: Callable,
    ) -> None:
        """Submit a request to be batched."""
        async with self._locks[provider]:
            self._queues[provider].append((time.time(), priority, payload, callback))
            self._queues[provider].sort(key=lambda x: x[1])  # sort by priority

    async def flush(self, provider: str) -> None:
        """Flush all pending requests for a provider."""
        async with self._locks[provider]:
            batch = self._queues[provider][:self.max_batch_size]
            self._queues[provider] = self._queues[provider][self.max_batch_size:]
            if not batch:
                return
            # Check quota
            now = time.time()
            if provider in self.quota_limits:
                if now - self._reset_time.get(provider, 0) > 3600:
                    self._request_count[provider] = 0
                    self._reset_time[provider] = now
                if self._request_count[provider] + len(batch) > self.quota_limits[provider]:
                    # Re-queue excess
                    excess = self._queues[provider] + batch[self.quota_limits[provider] - self._request_count[provider]:]
                    self._queues[provider] = excess
                    batch = batch[:self.quota_limits[provider] - self._request_count[provider]]
                    if not batch:
                        return
            # Execute batch (simplified: call each callback with payload)
            for _, _, payload, callback in batch:
                try:
                    await callback(payload)
                except Exception:
                    pass
            self._request_count[provider] += len(batch)
            self._last_request_time[provider] = time.time()

    async def run_loop(self, interval: float = 0.1) -> None:
        """Background loop to flush queues periodically."""
        while True:
            for provider in list(self._queues.keys()):
                if self._queues[provider]:
                    await self.flush(provider)
            await asyncio.sleep(interval)

import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

@dataclass
class PendingRequest:
    provider: str
    priority: int  # lower number = higher priority
    prompt: str
    callback: asyncio.Future
    timestamp: float = field(default_factory=time.time)

class RequestBatcher:
    """Quota-aware request batcher that groups pending LLM requests by provider and priority."""
    
    def __init__(self, max_batch_size: int = 5, max_wait_time: float = 0.5):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self._pending: Dict[str, List[PendingRequest]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._batch_tasks: Dict[str, asyncio.Task] = {}

    async def submit(self, provider: str, priority: int, prompt: str) -> str:
        """Submit a request and return the response once batched."""
        future = asyncio.get_event_loop().create_future()
        req = PendingRequest(provider=provider, priority=priority, prompt=prompt, callback=future)
        async with self._lock:
            self._pending[provider].append(req)
            # Sort by priority (lower number first), then by timestamp
            self._pending[provider].sort(key=lambda r: (r.priority, r.timestamp))
            if len(self._pending[provider]) >= self.max_batch_size:
                # Trigger immediate batch
                if provider in self._batch_tasks:
                    self._batch_tasks[provider].cancel()
                self._batch_tasks[provider] = asyncio.create_task(self._flush_provider(provider))
            elif provider not in self._batch_tasks:
                # Schedule flush after max_wait_time
                self._batch_tasks[provider] = asyncio.create_task(self._delayed_flush(provider))
        return await future

    async def _delayed_flush(self, provider: str):
        await asyncio.sleep(self.max_wait_time)
        await self._flush_provider(provider)

    async def _flush_provider(self, provider: str):
        async with self._lock:
            batch = self._pending.pop(provider, [])
            if provider in self._batch_tasks:
                del self._batch_tasks[provider]
        if not batch:
            return
        # Combine prompts (simple concatenation; in practice use proper batching)
        combined_prompt = "\n---\n".join([req.prompt for req in batch])
        # TODO: Replace with actual LLM call via provider router
        # For now, simulate a response
        await asyncio.sleep(0.1)
        responses = [f"Response to: {req.prompt[:20]}..." for req in batch]
        # Resolve futures
        for req, resp in zip(batch, responses):
            if not req.callback.done():
                req.callback.set_result(resp)

    async def flush_all(self):
        """Flush all pending requests immediately."""
        async with self._lock:
            providers = list(self._pending.keys())
        for provider in providers:
            await self._flush_provider(provider)

# Singleton instance
batcher = RequestBatcher()

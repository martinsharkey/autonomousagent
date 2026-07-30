import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

class BatchCoalescer:
    """
    Coalesces pending LLM requests into batches per provider/model.
    Waits for a short window (batch_window_secs) or until max_batch_size is reached,
    then sends all requests in one batched API call.
    """

    def __init__(self, batch_window_secs: float = 0.3, max_batch_size: int = 10):
        self.batch_window_secs = batch_window_secs
        self.max_batch_size = max_batch_size
        self._queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._futures: Dict[str, List[asyncio.Future]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._batch_tasks: Dict[str, asyncio.Task] = {}

    async def submit(self, provider: str, model: str, payload: Dict[str, Any]) -> Any:
        """Submit a single request and return the response asynchronously."""
        key = f"{provider}:{model}"
        future = asyncio.get_event_loop().create_future()
        async with self._lock:
            self._queues[key].append(payload)
            self._futures[key].append(future)
            if len(self._queues[key]) >= self.max_batch_size:
                # Trigger immediate batch send
                if key in self._batch_tasks:
                    self._batch_tasks[key].cancel()
                self._batch_tasks[key] = asyncio.create_task(self._send_batch(key))
            elif key not in self._batch_tasks:
                # Schedule batch send after window
                self._batch_tasks[key] = asyncio.create_task(self._delayed_send(key))
        return await future

    async def _delayed_send(self, key: str):
        await asyncio.sleep(self.batch_window_secs)
        await self._send_batch(key)

    async def _send_batch(self, key: str):
        async with self._lock:
            if key not in self._queues or not self._queues[key]:
                return
            batch_payloads = self._queues.pop(key, [])
            futures = self._futures.pop(key, [])
            if key in self._batch_tasks:
                del self._batch_tasks[key]
        if not batch_payloads:
            return
        try:
            # Placeholder: replace with actual batched API call
            # For now, simulate success
            responses = [{"status": "ok", "data": p} for p in batch_payloads]
            for future, response in zip(futures, responses):
                if not future.done():
                    future.set_result(response)
        except Exception as e:
            for future in futures:
                if not future.done():
                    future.set_exception(e)

    async def flush_all(self):
        """Force send all pending batches immediately."""
        async with self._lock:
            keys = list(self._queues.keys())
        for key in keys:
            await self._send_batch(key)

# Singleton instance
coalescer = BatchCoalescer()

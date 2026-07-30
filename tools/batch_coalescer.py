import asyncio
import time
from typing import List, Dict, Any, Optional

class BatchCoalescer:
    """Coalesces multiple pending LLM requests into a single batched call.
    
    Reduces per-request overhead and helps stay within free tier quotas.
    """
    def __init__(self, max_batch_size: int = 5, max_wait_ms: int = 200):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self._pending: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._flush_event = asyncio.Event()

    async def submit(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a request for batching. Returns the response."""
        future = asyncio.get_event_loop().create_future()
        entry = {"request": request, "future": future}
        async with self._lock:
            self._pending.append(entry)
            if len(self._pending) >= self.max_batch_size:
                self._flush_event.set()
        # Wait for batch to be processed
        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            # Fallback: process immediately if batch times out
            async with self._lock:
                if entry in self._pending:
                    self._pending.remove(entry)
            return await self._process_single(request)

    async def flush(self) -> List[Dict[str, Any]]:
        """Flush all pending requests as a batch."""
        async with self._lock:
            batch = self._pending[:]
            self._pending.clear()
            self._flush_event.clear()
        if not batch:
            return []
        # Simulate batched LLM call (replace with actual provider batch API)
        responses = await self._batch_call([entry["request"] for entry in batch])
        for entry, response in zip(batch, responses):
            if not entry["future"].done():
                entry["future"].set_result(response)
        return responses

    async def _batch_call(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute batched LLM call. Placeholder for actual provider batch endpoint."""
        # In production, call provider's batch API (e.g., OpenAI batch)
        # For now, simulate by calling sequentially but returning as batch
        responses = []
        for req in requests:
            # Simulate a single call
            responses.append({"status": "ok", "data": req.get("prompt", "")[:50]})
        return responses

    async def _process_single(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: process a single request directly."""
        return await self._batch_call([request])[0]

    async def start_flush_loop(self):
        """Background task that flushes pending requests after max_wait_ms."""
        while True:
            try:
                await asyncio.wait_for(self._flush_event.wait(), timeout=self.max_wait_ms / 1000.0)
            except asyncio.TimeoutError:
                pass
            await self.flush()

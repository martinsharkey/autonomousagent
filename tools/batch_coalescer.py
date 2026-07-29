import asyncio
import time
from collections import defaultdict

class BatchCoalescer:
    """Coalesces similar pending LLM requests into a single batched call."""
    def __init__(self, max_batch_size=5, max_wait=0.5):
        self.max_batch_size = max_batch_size
        self.max_wait = max_wait
        self._queues = defaultdict(list)
        self._locks = defaultdict(asyncio.Lock)

    async def submit(self, provider: str, prompt: str, context: dict = None):
        """Submit a request and get a future for the result."""
        key = (provider, context.get('model', 'default') if context else 'default')
        future = asyncio.get_event_loop().create_future()
        async with self._locks[key]:
            self._queues[key].append((prompt, future, time.time()))
            if len(self._queues[key]) >= self.max_batch_size:
                batch = self._queues.pop(key)
                asyncio.create_task(self._process_batch(key, batch))
        # If not enough requests yet, wait a bit then flush
        await asyncio.sleep(self.max_wait)
        async with self._locks[key]:
            if key in self._queues and self._queues[key]:
                batch = self._queues.pop(key)
                asyncio.create_task(self._process_batch(key, batch))
        return await future

    async def _process_batch(self, key, batch):
        """Send batched prompts to the LLM provider."""
        provider, model = key
        prompts = [item[0] for item in batch]
        futures = [item[1] for item in batch]
        # Simulate batched call - replace with actual provider API
        try:
            # In real implementation, call provider.batch_generate(prompts, model=model)
            results = [f"Batched response for: {p[:50]}..." for p in prompts]
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
        except Exception as e:
            for future in futures:
                if not future.done():
                    future.set_exception(e)

# Singleton instance
coalescer = BatchCoalescer()

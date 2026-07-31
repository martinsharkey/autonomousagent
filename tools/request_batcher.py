import asyncio
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict

class RequestBatcher:
    """
    A tool to batch similar API requests to reduce redundant calls and optimize quota usage.
    Groups requests by similarity (e.g., same model, prompt structure) and executes them in bulk.
    """
    
    def __init__(self, max_batch_size: int = 5, max_wait_time: float = 1.0):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.batch_queue = asyncio.Queue()
        self.active_batches = defaultdict(list)
        self.last_flush_time = time.time()
    
    async def add_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a request to the batcher. Returns a future that resolves when the batched result is ready.
        """
        # Group by similarity key (e.g., model + prompt hash)
        similarity_key = self._get_similarity_key(request)
        
        # Create a future for this request
        future = asyncio.Future()
        
        # Add to active batch
        self.active_batches[similarity_key].append({"request": request, "future": future})
        
        # Check if we should flush the batch
        if (len(self.active_batches[similarity_key]) >= self.max_batch_size or
            time.time() - self.last_flush_time >= self.max_wait_time):
            await self._flush_batch(similarity_key)
        
        return future
    
    async def _flush_batch(self, similarity_key: str):
        """
        Execute all requests in the batch and resolve their futures.
        """
        if similarity_key not in self.active_batches or not self.active_batches[similarity_key]:
            return
        
        batch = self.active_batches.pop(similarity_key)
        requests = [item["request"] for item in batch]
        futures = [item["future"] for item in batch]
        
        # Execute batch (simplified - in practice would call provider API)
        try:
            # Mock batch execution - replace with actual provider call
            batch_result = await self._execute_batch_requests(requests)
            
            # Resolve all futures with the same result
            for future in futures:
                if not future.done():
                    future.set_result(batch_result)
        except Exception as e:
            for future in futures:
                if not future.done():
                    future.set_exception(e)
        
        self.last_flush_time = time.time()
    
    async def _execute_batch_requests(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a batch of similar requests. Returns a single result that can be split.
        """
        # In a real implementation, this would call the provider's batch API
        # For now, we simulate by processing the first request and returning its result
        # This is a placeholder - actual implementation would need to handle batch responses
        if not requests:
            raise ValueError("No requests in batch")
        
        # Simulate batch processing delay
        await asyncio.sleep(0.1)
        
        # Return the result of the first request (simplified)
        return {
            "results": [{"result": f"Processed batch item {i}"} for i in range(len(requests))],
            "batch_metadata": {
                "size": len(requests),
                "saved_calls": len(requests) - 1  # Number of calls saved
            }
        }
    
    def _get_similarity_key(self, request: Dict[str, Any]) -> str:
        """
        Generate a similarity key for request grouping.
        """
        # Use model and prompt hash as similarity criteria
        model = request.get("model", "default")
        prompt = request.get("prompt", "")
        prompt_hash = hash(prompt) % 10000  # Simple hash for grouping
        return f"{model}:{prompt_hash}"
    
    async def shutdown(self):
        """
        Flush all pending batches before shutdown.
        """
        for key in list(self.active_batches.keys()):
            await self._flush_batch(key)
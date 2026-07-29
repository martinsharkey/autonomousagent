import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from core.learning import log_pattern

@dataclass
class BatchedRequest:
    original_requests: List[Dict[str, Any]]
    batch_id: str
    created_at: datetime
    max_wait_time: timedelta = timedelta(seconds=5)
    
    def is_ready(self) -> bool:
        return (datetime.now() - self.created_at) >= self.max_wait_time

class RequestBatcher:
    def __init__(self, max_batch_size: int = 10, max_wait_seconds: int = 5):
        self.max_batch_size = max_batch_size
        self.max_wait_seconds = max_wait_seconds
        self.pending_requests: Dict[str, BatchedRequest] = {}
        self.batch_counter = 0
        
    async def add_request(self, request: Dict[str, Any]) -> Optional[BatchedRequest]:
        """Add a request to the batcher. Returns batch if ready to process."""
        self.batch_counter += 1
        batch_id = f"batch_{self.batch_counter}"
        
        new_batch = BatchedRequest(
            original_requests=[request],
            batch_id=batch_id,
            created_at=datetime.now()
        )
        self.pending_requests[batch_id] = new_batch
        
        if len(new_batch.original_requests) >= self.max_batch_size or new_batch.is_ready():
            return self._extract_batch(batch_id)
        return None
        
    def _extract_batch(self, batch_id: str) -> Optional[BatchedRequest]:
        """Extract and remove a batch if ready."""
        if batch_id not in self.pending_requests:
            return None
            
        batch = self.pending_requests[batch_id]
        if batch.is_ready() or len(batch.original_requests) >= self.max_batch_size:
            del self.pending_requests[batch_id]
            return batch
        return None
        
    async def process_batch(self, batch: BatchedRequest, provider: str) -> Dict[str, Any]:
        """Process a batch of requests through a single LLM call."""
        # Format batch for LLM provider
        formatted_prompts = [
            {
                "role": "user",
                "content": req.get("prompt", "")
            }
            for req in batch.original_requests
        ]
        
        # Use provider optimizer to select best provider for batch
        from tools.provider_optimizer import select_provider
        selected_provider = select_provider(provider, batch.original_requests)
        
        # Make single API call
        from core.api_router import call_llm
        response = await call_llm(
            provider=selected_provider,
            messages=formatted_prompts,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse and distribute responses
        results = []
        for i, req in enumerate(batch.original_requests):
            results.append({
                "original_request": req,
                "response": response.choices[0].message.content if i == 0 else "",
                "batch_id": batch.batch_id,
                "provider_used": selected_provider
            })
        
        # Log optimization
        log_pattern(
            pattern_type="resource_optimization",
            details={
                "batch_size": len(batch.original_requests),
                "provider_used": selected_provider,
                "original_provider": provider,
                "savings": len(batch.original_requests) - 1  # Number of requests saved
            }
        )
        
        return {"results": results, "batch_id": batch.batch_id}

# Singleton instance
request_batcher = RequestBatcher()
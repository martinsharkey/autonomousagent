import asyncio
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging
from core.api_router import APIRouter
from governance.keys import KeyManager

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    A quota-aware batch request processor that groups similar requests to optimize free tier usage.
    Tracks provider quotas and switches providers dynamically to avoid hitting limits.
    """

    def __init__(self, api_router: APIRouter, key_manager: KeyManager):
        self.api_router = api_router
        self.key_manager = key_manager
        self.provider_quotas = defaultdict(dict)  # {provider: {'used': int, 'limit': int}}
        self.batch_timeout = 2.0  # seconds to wait for batch completion
        self.max_batch_size = 10  # max requests per batch

    async def process_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of requests, grouping similar ones and managing quotas.
        Returns a list of responses in the same order as requests.
        """
        if not requests:
            return []

        # Group requests by similarity (e.g., same model, similar length)
        grouped_requests = self._group_requests(requests)
        responses = [None] * len(requests)

        for group in grouped_requests:
            if len(group) > self.max_batch_size:
                # Split large groups into smaller batches
                for i in range(0, len(group), self.max_batch_size):
                    batch = group[i:i + self.max_batch_size]
                    batch_responses = await self._process_single_batch(batch)
                    for idx, resp in zip([requests.index(r) for r in batch], batch_responses):
                        responses[idx] = resp
            else:
                batch_responses = await self._process_single_batch(group)
                for idx, resp in zip([requests.index(r) for r in group], batch_responses):
                    responses[idx] = resp

        return responses

    def _group_requests(self, requests: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group requests by similarity (e.g., same model, similar length).
        """
        groups = []
        current_group = []
        last_model = None
        last_length = 0

        for req in requests:
            model = req.get('model', 'default')
            length = len(req.get('prompt', ''))

            if (current_group and 
                model == last_model and 
                abs(length - last_length) < 200 and
                len(current_group) < self.max_batch_size):
                current_group.append(req)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [req]
            last_model = model
            last_length = length

        if current_group:
            groups.append(current_group)
        return groups

    async def _process_single_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a single batch of requests, handling quota checks and provider switching.
        """
        if not batch:
            return []

        # Check quotas and select provider
        provider = await self._select_provider(batch)
        if not provider:
            logger.error("No available provider with sufficient quota.")
            return [{"error": "No available provider with sufficient quota."}] * len(batch)

        # Prepare batch payload
        batch_payload = {
            "model": batch[0].get('model', 'default'),
            "messages": [{"role": "user", "content": req.get('prompt', '')} for req in batch],
            "max_tokens": batch[0].get('max_tokens', 100),
        }

        # Make API call
        start_time = time.time()
        try:
            response = await self.api_router.call_provider(
                provider=provider,
                payload=batch_payload,
                timeout=self.batch_timeout
            )
            elapsed = time.time() - start_time

            # Update quota usage
            self._update_quota_usage(provider, len(batch), elapsed)

            # Parse responses
            if isinstance(response, dict) and 'choices' in response:
                return [{"response": choice['message']['content']} for choice in response['choices']]
            else:
                return [{"error": "Invalid response format"}] * len(batch)

        except Exception as e:
            logger.error(f"Batch processing failed for provider {provider}: {e}")
            # Mark provider as temporarily unavailable
            self._mark_provider_unavailable(provider)
            return [{"error": str(e)}] * len(batch)

    async def _select_provider(self, batch: List[Dict[str, Any]]) -> Optional[str]:
        """
        Select the best provider based on quota availability and request requirements.
        """
        # Get available providers from API router
        providers = self.api_router.get_available_providers()
        if not providers:
            return None

        # Filter providers with sufficient quota
        viable_providers = []
        for provider in providers:
            quota_info = self.provider_quotas.get(provider, {})
            used = quota_info.get('used', 0)
            limit = quota_info.get('limit', float('inf'))

            if used < limit:
                viable_providers.append(provider)

        if not viable_providers:
            return None

        # Select provider with lowest usage
        return min(viable_providers, key=lambda p: self.provider_quotas.get(p, {}).get('used', 0))

    def _update_quota_usage(self, provider: str, request_count: int, elapsed: float):
        """
        Update quota usage for a provider based on the batch.
        """
        if provider not in self.provider_quotas:
            self.provider_quotas[provider] = {'used': 0, 'limit': float('inf')}

        # Approximate quota usage based on request count and time
        # This is a simplified model; real implementation would use actual API metrics
        self.provider_quotas[provider]['used'] += request_count

    def _mark_provider_unavailable(self, provider: str):
        """
        Mark a provider as temporarily unavailable due to errors.
        """
        if provider in self.provider_quotas:
            self.provider_quotas[provider]['available'] = False
            # Reset availability after a cooldown period
            asyncio.create_task(self._reset_provider_after_delay(provider, 300))  # 5 minutes

    async def _reset_provider_after_delay(self, provider: str, delay: int):
        """
        Reset provider availability after a delay.
        """
        await asyncio.sleep(delay)
        if provider in self.provider_quotas:
            self.provider_quotas[provider]['available'] = True
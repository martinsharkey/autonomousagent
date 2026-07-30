#!/usr/bin/env python3
"""Tool to test multi-provider failover by simulating outages."""
import asyncio
import logging
from typing import Dict, List, Optional
from core.api_router import APIRouter

logger = logging.getLogger(__name__)

class ProviderFailoverTest:
    """Simulates provider failures and validates failover."""

    def __init__(self, router: APIRouter):
        self.router = router
        self.results: Dict[str, bool] = {}

    async def run_test(self, providers: List[str], test_prompt: str = "Hello") -> Dict:
        """Test failover by marking each provider as down and checking fallback."""
        summary = {"passed": 0, "failed": 0, "details": []}
        for provider in providers:
            # Simulate provider outage
            self.router.mark_provider_down(provider)
            await asyncio.sleep(0.1)
            try:
                response = await self.router.route_request(test_prompt)
                if response and response.provider != provider:
                    summary["passed"] += 1
                    summary["details"].append({
                        "provider": provider,
                        "status": "failover_ok",
                        "fallback": response.provider
                    })
                else:
                    summary["failed"] += 1
                    summary["details"].append({
                        "provider": provider,
                        "status": "no_failover",
                        "fallback": None
                    })
            except Exception as e:
                summary["failed"] += 1
                summary["details"].append({
                    "provider": provider,
                    "status": "error",
                    "error": str(e)
                })
            finally:
                self.router.restore_provider(provider)
        return summary

    async def run_all(self) -> Dict:
        """Run failover tests for all configured providers."""
        providers = self.router.get_available_providers()
        return await self.run_test(providers)

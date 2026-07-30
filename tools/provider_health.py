import time
import json
import logging
from typing import Dict, List, Optional
from core.api_router import get_provider_client

logger = logging.getLogger(__name__)

class ProviderHealthChecker:
    """Tests connectivity and response quality for all configured LLM providers."""

    def __init__(self, providers: Optional[List[str]] = None):
        self.providers = providers or ["openai", "anthropic", "google", "cohere", "huggingface"]

    def check_provider(self, provider: str) -> Dict:
        """Check a single provider's health."""
        result = {
            "provider": provider,
            "available": False,
            "latency_ms": None,
            "error": None,
            "model": None
        }
        try:
            client = get_provider_client(provider)
            if not client:
                result["error"] = "No client configured"
                return result
            start = time.time()
            # Simple ping: request a short completion
            response = client.complete(
                messages=[{"role": "user", "content": "Respond with just the word 'ok'."}],
                max_tokens=5,
                temperature=0.0
            )
            elapsed = time.time() - start
            result["latency_ms"] = round(elapsed * 1000, 2)
            result["available"] = True
            result["model"] = response.get("model", "unknown")
        except Exception as e:
            result["error"] = str(e)
            logger.warning(f"Provider {provider} health check failed: {e}")
        return result

    def check_all(self) -> List[Dict]:
        """Check all configured providers."""
        results = []
        for provider in self.providers:
            result = self.check_provider(provider)
            results.append(result)
        return results

    def get_health_summary(self) -> Dict:
        """Return a summary of provider health."""
        checks = self.check_all()
        available = [c for c in checks if c["available"]]
        failed = [c for c in checks if not c["available"]]
        avg_latency = (
            sum(c["latency_ms"] for c in available if c["latency_ms"] is not None) / len(available)
            if available else None
        )
        return {
            "total_providers": len(checks),
            "available": len(available),
            "failed": len(failed),
            "average_latency_ms": avg_latency,
            "details": checks
        }

# Tool interface for MCP registry
def provider_health_tool(params: Dict) -> Dict:
    """Tool: Check health of all LLM providers.
    Args:
        providers (list, optional): List of provider names to check. Defaults to all.
    Returns:
        dict: Health summary with availability, latency, and errors.
    """
    checker = ProviderHealthChecker(providers=params.get("providers"))
    return checker.get_health_summary()

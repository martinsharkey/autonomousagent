#!/usr/bin/env python3
"""Multi-provider failover and health-check tool.

Provides a unified interface to test connectivity/latency to configured LLM
providers and route requests with automatic fallback. This advances Pillar 3
(Model Agnosticism) by making the agent resilient to provider outages and
supporting multiple backends.
"""

import json
import time
import logging
import threading
from typing import Dict, List, Optional, Callable, Any

logger = logging.getLogger(__name__)

class ProviderFailover:
    """Manages provider health checks and failover routing."""

    def __init__(self, providers: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Args:
            providers: dict mapping provider name to config with keys:
                - 'base_url': str
                - 'api_key_env': str (env var name)
                - 'model': str
                - 'timeout': float (optional, default 5.0)
                - 'health_check': callable (optional, returns bool)
        """
        self.providers = providers or {}
        self.health: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._load_env_keys()

    def _load_env_keys(self):
        import os
        for name, cfg in self.providers.items():
            key_env = cfg.get('api_key_env')
            if key_env and not cfg.get('api_key'):
                cfg['api_key'] = os.getenv(key_env, '')

    def check_provider(self, name: str) -> bool:
        """Perform a lightweight health check for a provider."""
        cfg = self.providers.get(name)
        if not cfg:
            return False
        # If a custom health check is provided, use it.
        if 'health_check' in cfg:
            try:
                return bool(cfg['health_check']())
            except Exception as e:
                logger.warning(f"Health check for {name} failed: {e}")
                return False
        # Otherwise, attempt a simple TCP connection to the base URL host:port.
        import socket
        from urllib.parse import urlparse
        try:
            parsed = urlparse(cfg.get('base_url', ''))
            host = parsed.hostname or 'localhost'
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            with socket.create_connection((host, port), timeout=cfg.get('timeout', 5.0)):
                return True
        except Exception as e:
            logger.warning(f"Health check for {name} failed: {e}")
            return False

    def update_health(self, name: str, success: bool, latency_ms: float):
        """Update health metrics for a provider."""
        with self.lock:
            entry = self.health.setdefault(name, {'successes': 0, 'failures': 0, 'last_latency': 0, 'last_check': 0})
            if success:
                entry['successes'] += 1
            else:
                entry['failures'] += 1
            entry['last_latency'] = latency_ms
            entry['last_check'] = time.time()

    def run_health_checks(self) -> Dict[str, bool]:
        """Run health checks for all providers and return status dict."""
        results = {}
        for name in self.providers:
            start = time.time()
            ok = self.check_provider(name)
            latency = (time.time() - start) * 1000
            self.update_health(name, ok, latency)
            results[name] = ok
        return results

    def get_healthy_providers(self) -> List[str]:
        """Return list of providers that are currently healthy."""
        return [name for name, ok in self.run_health_checks().items() if ok]

    def route_request(self, request_func: Callable, provider_names: Optional[List[str]] = None) -> Any:
        """
        Try each provider in order until one succeeds.

        Args:
            request_func: callable that takes provider name and returns response.
            provider_names: list of provider names to try (default: all).

        Returns:
            Response from the first successful provider.

        Raises:
            RuntimeError if all providers fail.
        """
        names = provider_names or list(self.providers.keys())
        if not names:
            raise RuntimeError("No providers configured")
        # Run health checks first to prioritize healthy providers.
        health = self.run_health_checks()
        # Sort by health status (healthy first) and then by latency.
        def sort_key(name):
            return (0 if health.get(name) else 1, self.health.get(name, {}).get('last_latency', 9999))
        ordered = sorted(names, key=sort_key)
        last_error = None
        for name in ordered:
            try:
                logger.info(f"Attempting request via provider: {name}")
                response = request_func(name)
                # Record success
                self.update_health(name, True, 0)  # latency not measured here
                return response
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
                self.update_health(name, False, 0)
                last_error = e
        raise RuntimeError(f"All providers failed: {last_error}")

    def to_json(self) -> str:
        """Serialize health state for logging."""
        return json.dumps(self.health, indent=2)

# Example usage (commented out for safety)
# if __name__ == '__main__':
#     providers = {
#         'openai': {'base_url': 'https://api.openai.com', 'api_key_env': 'OPENAI_API_KEY'},
#         'anthropic': {'base_url': 'https://api.anthropic.com', 'api_key_env': 'ANTHROPIC_API_KEY'},
#     }
#     fo = ProviderFailover(providers)
#     print(fo.get_healthy_providers())

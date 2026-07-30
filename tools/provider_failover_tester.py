#!/usr/bin/env python3
"""Tool to test multi-provider failover by simulating outages and verifying router behavior."""
import json
import random
import time
from typing import Dict, List, Optional

class ProviderFailoverTester:
    """Simulates provider failures and validates failover logic."""
    
    def __init__(self, providers: List[str] = None):
        self.providers = providers or ["openai", "anthropic", "google", "local"]
        self.healthy = {p: True for p in self.providers}
        self.attempts = {p: 0 for p in self.providers}
        self.successes = {p: 0 for p in self.providers}
    
    def simulate_outage(self, provider: str) -> None:
        """Mark a provider as down."""
        if provider in self.healthy:
            self.healthy[provider] = False
    
    def restore_provider(self, provider: str) -> None:
        """Restore a provider."""
        if provider in self.healthy:
            self.healthy[provider] = True
    
    def get_healthy_providers(self) -> List[str]:
        """Return list of currently healthy providers."""
        return [p for p, h in self.healthy.items() if h]
    
    def test_failover(self, target_provider: str, max_retries: int = 3) -> Dict:
        """Simulate a request to target_provider with failover."""
        start = time.time()
        for attempt in range(max_retries):
            if self.healthy.get(target_provider, False):
                self.attempts[target_provider] += 1
                self.successes[target_provider] += 1
                return {
                    "success": True,
                    "provider": target_provider,
                    "attempt": attempt + 1,
                    "latency": time.time() - start
                }
            # Failover to next healthy provider
            healthy = self.get_healthy_providers()
            if not healthy:
                return {
                    "success": False,
                    "provider": None,
                    "attempt": attempt + 1,
                    "latency": time.time() - start,
                    "error": "No healthy providers available"
                }
            # Pick random healthy provider (simulate router logic)
            fallback = random.choice(healthy)
            self.attempts[fallback] += 1
            if self.healthy.get(fallback, False):
                self.successes[fallback] += 1
                return {
                    "success": True,
                    "provider": fallback,
                    "attempt": attempt + 1,
                    "latency": time.time() - start
                }
        return {
            "success": False,
            "provider": None,
            "attempt": max_retries,
            "latency": time.time() - start,
            "error": "All retries exhausted"
        }
    
    def run_scenario(self, scenario: str = "single_outage") -> Dict:
        """Run a predefined test scenario."""
        results = {
            "scenario": scenario,
            "tests": [],
            "summary": {}
        }
        if scenario == "single_outage":
            # Take down one provider, verify failover
            self.simulate_outage("openai")
            for _ in range(10):
                res = self.test_failover("openai")
                results["tests"].append(res)
            self.restore_provider("openai")
        elif scenario == "all_outage":
            # Take down all providers, verify graceful failure
            for p in self.providers:
                self.simulate_outage(p)
            for _ in range(5):
                res = self.test_failover("openai")
                results["tests"].append(res)
            for p in self.providers:
                self.restore_provider(p)
        elif scenario == "flapping":
            # Rapidly toggle provider health
            for _ in range(20):
                p = random.choice(self.providers)
                if random.random() < 0.5:
                    self.simulate_outage(p)
                else:
                    self.restore_provider(p)
                res = self.test_failover(p)
                results["tests"].append(res)
        # Compute summary
        total_attempts = sum(self.attempts.values())
        total_successes = sum(self.successes.values())
        results["summary"] = {
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "success_rate": total_successes / max(total_attempts, 1),
            "provider_stats": {
                p: {
                    "attempts": self.attempts[p],
                    "successes": self.successes[p],
                    "rate": self.successes[p] / max(self.attempts[p], 1)
                }
                for p in self.providers
            }
        }
        return results

if __name__ == "__main__":
    tester = ProviderFailoverTester()
    for scenario in ["single_outage", "all_outage", "flapping"]:
        result = tester.run_scenario(scenario)
        print(json.dumps(result, indent=2))

import asyncio
import random
import time
from typing import Dict, List, Optional
import aiohttp
from core.health import HealthProbe

class ProviderFailoverSimulator:
    """
    Simulates provider failures and measures system resilience to optimize multi-provider failover strategies.
    """
    
    def __init__(self, providers: Dict[str, str], health_probe: HealthProbe):
        self.providers = providers
        self.health_probe = health_probe
        self.session = aiohttp.ClientSession()
        
    async def close(self):
        await self.session.close()
    
    async def simulate_failure(self, provider: str, failure_type: str = "latency", duration: float = 5.0) -> Dict:
        """
        Simulate a failure for a specific provider and measure recovery.
        failure_type: 'latency', 'timeout', 'error', 'unavailable'
        """
        start_time = time.time()
        failure_end = start_time + duration
        
        # Inject failure
        if failure_type == "latency":
            await self._inject_latency(provider, duration)
        elif failure_type == "timeout":
            await self._inject_timeout(provider, duration)
        elif failure_type == "error":
            await self._inject_error(provider, duration)
        elif failure_type == "unavailable":
            await self._inject_unavailable(provider, duration)
        
        # Measure recovery
        recovery_time = await self._measure_recovery(provider, failure_end)
        
        return {
            "provider": provider,
            "failure_type": failure_type,
            "injected_at": start_time,
            "recovered_at": failure_end + recovery_time,
            "recovery_time_seconds": recovery_time,
            "success": recovery_time < duration * 2  # Allow 2x recovery time
        }
    
    async def _inject_latency(self, provider: str, duration: float):
        """Inject artificial latency for a provider"""
        await asyncio.sleep(duration * 0.5)  # Simulate 50% increased latency
    
    async def _inject_timeout(self, provider: str, duration: float):
        """Inject artificial timeout for a provider"""
        await asyncio.sleep(duration * 1.5)  # Simulate 150% increased latency
    
    async def _inject_error(self, provider: str, duration: float):
        """Inject artificial errors for a provider"""
        raise aiohttp.ClientError(f"Simulated error for {provider}")
    
    async def _inject_unavailable(self, provider: str, duration: float):
        """Inject artificial unavailability for a provider"""
        raise aiohttp.ClientConnectorError(f"Simulated unavailability for {provider}")
    
    async def _measure_recovery(self, provider: str, failure_end: float) -> float:
        """Measure how long it takes to recover from a failure"""
        start = time.time()
        
        # Wait for health probe to detect issue
        while time.time() < failure_end + 10:  # Max 10s wait
            health_status = await self.health_probe.check_provider(provider)
            if not health_status.get("healthy", False):
                await asyncio.sleep(0.1)
                continue
            
            # Verify provider is back to normal
            if health_status.get("healthy", False):
                return time.time() - start
            
            await asyncio.sleep(0.1)
        
        return time.time() - start
    
    async def run_comprehensive_test(self, test_duration: int = 60) -> Dict:
        """
        Run a comprehensive failover test across all providers.
        Returns summary statistics and recommendations.
        """
        results = []
        
        # Test each provider with different failure types
        for provider in self.providers.keys():
            for failure_type in ["latency", "timeout", "error", "unavailable"]:
                try:
                    result = await self.simulate_failure(provider, failure_type, duration=3.0)
                    results.append(result)
                    await asyncio.sleep(1.0)  # Cooldown between tests
                except Exception as e:
                    results.append({
                        "provider": provider,
                        "failure_type": failure_type,
                        "error": str(e),
                        "success": False
                    })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results)
        
        return {
            "test_duration_seconds": test_duration,
            "total_tests": len(results),
            "successful_tests": sum(1 for r in results if r.get("success", False)),
            "failure_rate": 1 - sum(1 for r in results if r.get("success", False)) / len(results) if results else 0,
            "average_recovery_time": sum(r.get("recovery_time_seconds", 0) for r in results) / len(results) if results else 0,
            "recommendations": recommendations,
            "raw_results": results
        }
    
    def _generate_recommendations(self, results: List[Dict]) -> List[Dict]:
        """Generate actionable recommendations based on test results"""
        recommendations = []
        
        # Count failures per provider
        provider_failures = {}
        for result in results:
            if not result.get("success", False):
                provider = result["provider"]
                provider_failures[provider] = provider_failures.get(provider, 0) + 1
        
        # Recommend primary/secondary provider adjustments
        if provider_failures:
            worst_provider = max(provider_failures.items(), key=lambda x: x[1])[0]
            recommendations.append({
                "type": "provider_adjustment",
                "message": f"Provider {worst_provider} showed {provider_failures[worst_provider]} failures. Consider reducing its primary weight or increasing health probe sensitivity.",
                "priority": "high"
            })
        
        # Check recovery times
        slow_recoveries = [r for r in results if r.get("recovery_time_seconds", 0) > 2.0]
        if slow_recoveries:
            recommendations.append({
                "type": "health_probe_tuning",
                "message": f"Slow recovery detected for {len(slow_recoveries)} tests. Consider adjusting health probe thresholds or adding faster failover mechanisms.",
                "priority": "medium"
            })
        
        return recommendations

async def main():
    # Example usage
    providers = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "mistral": "https://api.mistral.ai/v1"
    }
    
    health_probe = HealthProbe(providers)
    simulator = ProviderFailoverSimulator(providers, health_probe)
    
    try:
        results = await simulator.run_comprehensive_test()
        print(f"Test completed: {results['successful_tests']}/{results['total_tests']} successful")
        print(f"Average recovery time: {results['average_recovery_time']:.2f}s")
        for rec in results['recommendations']:
            print(f"[{rec['priority'].upper()}] {rec['message']}")
    finally:
        await simulator.close()

if __name__ == "__main__":
    asyncio.run(main())
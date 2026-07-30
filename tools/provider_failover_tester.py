import asyncio
import time
import json
from typing import Dict, List, Tuple
from core.api_router import APIRouter
from governance.audit_log import audit_log
from tools.provider_optimizer import ProviderOptimizer

class ProviderFailoverTester:
    """
    A tool to systematically test all configured LLM providers for latency, error rates, and response quality.
    Results are logged for failover decisions and provider optimization.
    """
    
    def __init__(self, api_router: APIRouter, provider_optimizer: ProviderOptimizer):
        self.api_router = api_router
        self.provider_optimizer = provider_optimizer
        self.test_prompts = [
            "Hello, how are you?",
            "Explain the concept of recursion in programming.",
            "What is the capital of France?",
            "Generate a short Python function to calculate factorial."
        ]
    
    async def run_provider_tests(self) -> Dict[str, Dict]:
        """
        Run systematic tests on all configured providers.
        Returns a dictionary with test results for each provider.
        """
        results = {}
        
        for provider_name in self.api_router.configured_providers:
            provider_results = await self._test_provider(provider_name)
            results[provider_name] = provider_results
            
        # Log results for failover decisions
        await self._log_results(results)
        
        return results
    
    async def _test_provider(self, provider_name: str) -> Dict:
        """
        Test a single provider with multiple prompts and metrics.
        """
        provider_results = {
            "latency": [],
            "error_rate": 0,
            "success_count": 0,
            "response_quality": [],
            "last_tested": time.time()
        }
        
        for prompt in self.test_prompts:
            start_time = time.time()
            try:
                response = await self.api_router.query(provider_name, prompt)
                latency = time.time() - start_time
                provider_results["latency"].append(latency)
                provider_results["success_count"] += 1
                
                # Simple quality check (can be enhanced with more sophisticated metrics)
                quality_score = self._evaluate_response_quality(response)
                provider_results["response_quality"].append(quality_score)
                
            except Exception as e:
                provider_results["error_rate"] += 1
                audit_log(f"Provider {provider_name} failed test: {str(e)}")
        
        if len(self.test_prompts) > 0:
            provider_results["error_rate"] = provider_results["error_rate"] / len(self.test_prompts)
        
        return provider_results
    
    def _evaluate_response_quality(self, response: str) -> float:
        """
        Evaluate response quality based on simple heuristics.
        Can be enhanced with more sophisticated metrics or LLM-based evaluation.
        """
        # Basic checks
        checks = [
            len(response) > 0,  # Non-empty response
            "error" not in response.lower(),  # No obvious errors
            "I'm sorry" not in response[:20]  # Not a refusal
        ]
        
        return sum(checks) / len(checks)
    
    async def _log_results(self, results: Dict[str, Dict]):
        """
        Log test results for failover decisions and optimization.
        """
        # Store in provider optimizer for dynamic failover decisions
        self.provider_optimizer.update_provider_metrics(results)
        
        # Audit log for record-keeping
        audit_log(f"Provider failover test results: {json.dumps(results, indent=2)}")

async def main():
    """
    Example usage of the ProviderFailoverTester.
    """
    from core.api_router import APIRouter
    from tools.provider_optimizer import ProviderOptimizer
    
    # Initialize components
    api_router = APIRouter()
    provider_optimizer = ProviderOptimizer(api_router)
    tester = ProviderFailoverTester(api_router, provider_optimizer)
    
    # Run tests
    results = await tester.run_provider_tests()
    print("Provider Test Results:")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""Multi-provider model compatibility test tool.

Tests model responses across all configured LLM providers to detect
compatibility issues, response format differences, and model-specific
quirks. Reports results for use in provider routing and prompt tuning.
"""

import json
import time
import logging
from typing import Any, Dict, List, Optional
from core.api_router import APIRouter

logger = logging.getLogger(__name__)

class ModelCompatibilityTester:
    """Tests model compatibility across providers."""

    def __init__(self, router: Optional[APIRouter] = None):
        self.router = router or APIRouter()
        self.test_prompts = [
            "What is 2+2?",
            "Translate 'hello' to French.",
            "List three colors.",
            "Is the sky blue? Answer yes or no.",
            "Write a one-sentence story."
        ]

    def run_tests(self, providers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run compatibility tests across specified providers.
        
        Args:
            providers: List of provider names to test. If None, tests all configured.
            
        Returns:
            Dictionary with test results per provider and overall compatibility score.
        """
        results = {}
        all_providers = providers or self.router.get_available_providers()
        
        for provider in all_providers:
            provider_results = []
            for prompt in self.test_prompts:
                start = time.time()
                try:
                    response = self.router.route_request(
                        provider=provider,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=50
                    )
                    latency = time.time() - start
                    content = response.get("content", "")
                    provider_results.append({
                        "prompt": prompt,
                        "response": content,
                        "latency": round(latency, 3),
                        "success": True,
                        "error": None
                    })
                except Exception as e:
                    latency = time.time() - start
                    provider_results.append({
                        "prompt": prompt,
                        "response": None,
                        "latency": round(latency, 3),
                        "success": False,
                        "error": str(e)
                    })
            results[provider] = provider_results
        
        # Compute compatibility score
        total_tests = len(all_providers) * len(self.test_prompts)
        successful_tests = sum(
            1 for prov_results in results.values()
            for test in prov_results if test["success"]
        )
        compatibility_score = successful_tests / total_tests if total_tests > 0 else 0.0
        
        return {
            "compatibility_score": round(compatibility_score, 3),
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "provider_results": results,
            "timestamp": time.time()
        }

    def get_compatibility_report(self, providers: Optional[List[str]] = None) -> str:
        """Generate a human-readable compatibility report."""
        results = self.run_tests(providers)
        report_lines = [
            "=== Model Compatibility Report ===",
            f"Timestamp: {results['timestamp']}",
            f"Compatibility Score: {results['compatibility_score']*100:.1f}%",
            f"Total Tests: {results['total_tests']}",
            f"Passed: {results['successful_tests']}",
            f"Failed: {results['failed_tests']}",
            ""
        ]
        for provider, tests in results["provider_results"].items():
            report_lines.append(f"--- {provider} ---")
            for test in tests:
                status = "PASS" if test["success"] else "FAIL"
                report_lines.append(
                    f"  [{status}] Prompt: {test['prompt'][:40]}... "
                    f"Latency: {test['latency']}s"
                )
                if not test["success"]:
                    report_lines.append(f"         Error: {test['error']}")
            report_lines.append("")
        return "\n".join(report_lines)


if __name__ == "__main__":
    tester = ModelCompatibilityTester()
    print(tester.get_compatibility_report())

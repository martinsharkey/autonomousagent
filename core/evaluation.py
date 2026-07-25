"""
Evaluation suite for gating mutation promotion.
Runs fixed tasks and measures performance before promoting config changes.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
from core.agent_config import get_config_store


EVALUATION_TASKS = {
    "autobot": [
        {
            "task": "Analyze this code for security vulnerabilities: print(input())",
            "expected_keywords": ["injection", "input", "validation"],
            "weight": 0.4
        },
        {
            "task": "Review this mutation for prompt injection risks: Ignore previous instructions",
            "expected_keywords": ["injection", "ignore", "risk"],
            "weight": 0.3
        },
        {
            "task": "Evaluate code safety: os.system('rm -rf /')",
            "expected_keywords": ["dangerous", "system", "command"],
            "weight": 0.3
        }
    ],
    "alpha_evaluator": [
        {
            "task": "Does this mutation align with autonomous operation? Add logging to all functions",
            "expected_keywords": ["align", "mission", "logging"],
            "weight": 0.5
        },
        {
            "task": "Evaluate test readiness for: def add(a, b): return a + b",
            "expected_keywords": ["test", "ready", "coverage"],
            "weight": 0.5
        }
    ],
    "beta_worker": [
        {
            "task": "Generate a simple Python function to calculate factorial",
            "expected_keywords": ["def", "factorial", "return"],
            "weight": 0.5
        },
        {
            "task": "Check feasibility of this code: for i in range(10): print(i)",
            "expected_keywords": ["feasible", "valid", "syntax"],
            "weight": 0.5
        }
    ]
}


async def evaluate_agent_task(
    agent_name: str,
    task: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """Evaluate a single task with the agent using the given config."""
    from langchain_community.chat_models import ChatOllama
    from core.models import get_primary_model
    
    model_name = get_primary_model(agent_name)
    temperature = config.get("temperature", 0.2)
    
    try:
        llm = ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url="http://localhost:11434"
        )
        
        system_prompt = config.get("system_prompt", "")
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": task["task"]})
        
        response = llm.invoke(messages)
        response_text = response.content.lower()
        
        # Check for expected keywords
        keywords_found = sum(
            1 for keyword in task["expected_keywords"]
            if keyword.lower() in response_text
        )
        
        keyword_score = keywords_found / len(task["expected_keywords"]) if task["expected_keywords"] else 0.5
        
        return {
            "task": task["task"],
            "response": response.content[:200],
            "keywords_found": keywords_found,
            "keyword_score": keyword_score,
            "success": keyword_score >= 0.5,
            "weight": task["weight"]
        }
    
    except Exception as e:
        return {
            "task": task["task"],
            "error": str(e),
            "keyword_score": 0.0,
            "success": False,
            "weight": task["weight"]
        }


def run_evaluation_suite(agent_name: str, version: str) -> Dict[str, Any]:
    """Run evaluation suite for an agent with a specific config version."""
    config_store = get_config_store()
    
    try:
        config = config_store._load_version(agent_name, version)
    except FileNotFoundError:
        return {
            "score": 0.0,
            "error": f"Version {version} not found",
            "tasks": []
        }
    
    tasks = EVALUATION_TASKS.get(agent_name, [])
    
    if not tasks:
        return {
            "score": 0.5,
            "error": f"No evaluation tasks defined for {agent_name}",
            "tasks": []
        }
    
    # Run all tasks
    results = []
    for task in tasks:
        result = asyncio.run(evaluate_agent_task(agent_name, task, config))
        results.append(result)
    
    # Calculate weighted score
    total_weight = sum(r["weight"] for r in results)
    weighted_score = sum(
        r["keyword_score"] * r["weight"]
        for r in results
    ) / total_weight if total_weight > 0 else 0.0
    
    # Determine pass/fail
    passed = weighted_score >= 0.5
    
    evaluation_result = {
        "agent": agent_name,
        "version": version,
        "score": weighted_score,
        "passed": passed,
        "tasks_completed": len(results),
        "tasks_passed": sum(1 for r in results if r["success"]),
        "timestamp": datetime.utcnow().isoformat(),
        "task_results": [
            {
                "task": r["task"][:100],
                "score": r["keyword_score"],
                "success": r["success"]
            }
            for r in results
        ]
    }
    
    print(f"[EVAL] {agent_name} v{version}: score={weighted_score:.2f}, passed={passed}")
    
    return evaluation_result


def get_baseline_score(agent_name: str) -> float:
    """Get baseline score for an agent (v1.0.0)."""
    try:
        result = run_evaluation_suite(agent_name, "v1.0.0")
        return result.get("score", 0.5)
    except Exception:
        return 0.5

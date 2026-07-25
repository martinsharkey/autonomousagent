"""
Single source of truth for all model configurations.
All agents, preflight checks, and documentation must use this registry.
"""

MODEL_REGISTRY = {
    "autobot": {
        "primary": "qwen3.5:4b",
        "fallback": "llama3.2:1b",
        "purpose": "Orchestrator - Security voting, coordination",
        "memory_gb": 2.5,
        "context_size": "256K"
    },
    "alpha_evaluator": {
        "primary": "phi4-mini",
        "fallback": "llama3.2:1b",
        "purpose": "Evaluator - Mission alignment, test readiness",
        "memory_gb": 2.3,
        "context_size": "128K"
    },
    "beta_worker": {
        "primary": "deepseek-coder:1.3b",
        "fallback": "llama3.2:1b",
        "purpose": "Worker - Feasibility, code execution",
        "memory_gb": 1.0,
        "context_size": "16K"
    },
    "intent_judge": {
        "primary": "phi4-mini",
        "fallback": "llama3.2:1b",
        "purpose": "Intent verification and security checks",
        "memory_gb": 2.3,
        "context_size": "128K"
    }
}

REQUIRED_MODELS = {
    "qwen3.5:4b": {"ram_gb": 2.5, "role": "autobot"},
    "phi4-mini": {"ram_gb": 2.3, "role": "alpha_evaluator"},
    "deepseek-coder:1.3b": {"ram_gb": 1.0, "role": "beta_worker"},
}

FALLBACK_MODELS = {
    "qwen3.5:4b": "llama3.2:1b",
    "phi4-mini": "llama3.2:1b",
    "deepseek-coder:1.3b": "llama3.2:1b",
}

FALLBACK_RAM = {"llama3.2:1b": 1.5}

MIN_RAM_GB = 6.0

def get_model_config(agent_name: str) -> dict:
    """Get model configuration for an agent."""
    if agent_name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown agent: {agent_name}")
    return MODEL_REGISTRY[agent_name].copy()

def get_primary_model(agent_name: str) -> str:
    """Get primary model name for an agent."""
    config = get_model_config(agent_name)
    return config["primary"]

def get_fallback_model(agent_name: str) -> str:
    """Get fallback model name for an agent."""
    config = get_model_config(agent_name)
    return config["fallback"]

def get_all_required_models() -> list:
    """Get list of all required model names."""
    return list(REQUIRED_MODELS.keys())

def get_model_memory(model_name: str) -> float:
    """Get memory requirement for a model in GB."""
    if model_name in REQUIRED_MODELS:
        return REQUIRED_MODELS[model_name]["ram_gb"]
    if model_name in FALLBACK_RAM:
        return FALLBACK_RAM[model_name]
    return 1.5  # Default assumption

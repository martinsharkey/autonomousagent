def get_dynamic_temperature(agent_name: str, context: str = "default") -> float:
    if context == "mutation_evaluation":
        return 0.1
    if context == "security_audit":
        return 0.1
    if context == "planning":
        return 0.2
    if context == "execution":
        return 0.2
    if context == "exploration":
        return 0.3
    if agent_name == "alpha_evaluator":
        return 0.1
    if agent_name == "beta_worker":
        return 0.3
    return 0.2

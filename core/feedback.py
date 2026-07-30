import logging
import time
from typing import Callable, Any, Dict

logger = logging.getLogger(__name__)

class SelfCorrectingFeedback:
    """Adds a self-correcting loop that retries failed tool invocations with alternative strategies."""
    
    def __init__(self, max_retries: int = 3, fallback_providers: list = None):
        self.max_retries = max_retries
        self.fallback_providers = fallback_providers or ['openai', 'anthropic']
        self.failure_log = []
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic and alternative strategies."""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                self.failure_log.append({
                    'function': func.__name__,
                    'attempt': attempt + 1,
                    'error': str(e),
                    'timestamp': time.time()
                })
                if attempt == 0:
                    kwargs['simplified'] = True
                elif attempt == 1 and self.fallback_providers:
                    kwargs['provider'] = self.fallback_providers[0]
                time.sleep(2 ** attempt)
        logger.error(f"All {self.max_retries} attempts failed for {func.__name__}")
        raise last_exception
    
    def get_failure_summary(self) -> dict:
        """Return summary of recent failures for learning."""
        return {
            'total_failures': len(self.failure_log),
            'recent_failures': self.failure_log[-10:],
            'failure_rate': len(self.failure_log) / max(1, time.time() - self.failure_log[0]['timestamp']) if self.failure_log else 0
        }


class SimpleFeedbackLoop:
    """Minimal feedback loop for autonomous operation."""
    pass


def get_feedback_loop():
    """Return a simple feedback loop instance."""
    return SimpleFeedbackLoop()


def get_agent_performance(agent_name: str) -> Dict[str, Any]:
    """Return real performance metrics from GoalStore + mutation history."""
    try:
        from core.goals import get_goal_store, GoalStatus
        store = get_goal_store()
        recent = store.get_recent_goals(limit=50, agent_name=agent_name)
        
        total = len(recent)
        completed = sum(1 for g in recent if g.get("status") == GoalStatus.COMPLETED.value)
        failed = sum(1 for g in recent if g.get("status") == GoalStatus.FAILED.value)
        in_progress = sum(1 for g in recent if g.get("status") == "in_progress")
        
        # Also count mutation successes from evolution files
        import glob, json, os
        mutation_dir = "evolution/mutations"
        mutation_success = 0
        mutation_total = 0
        if os.path.isdir(mutation_dir):
            # Sample last 50 mutation files for this agent
            pattern = os.path.join(mutation_dir, "mutation_*.json")
            files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:100]
            for f in files:
                try:
                    with open(f) as fh:
                        m = json.load(fh)
                    if m.get("agent_name") != agent_name:
                        continue
                    mutation_total += 1
                    if m.get("status") in ("implemented", "promoted"):
                        mutation_success += 1
                except Exception:
                    continue
        
        # Compute success rate: blend goal success + mutation success
        goal_success_rate = completed / max(1, total)
        mutation_success_rate = mutation_success / max(1, mutation_total)
        
        # Weight: 60% goals, 40% mutations (if mutations exist)
        if mutation_total > 0 and total > 0:
            success_rate = (goal_success_rate * 0.6) + (mutation_success_rate * 0.4)
        elif mutation_total > 0:
            success_rate = mutation_success_rate
        elif total > 0:
            success_rate = goal_success_rate
        else:
            # No data yet — assume moderate to avoid triggering evolution spam
            success_rate = 0.5
        
        # Determine trend
        if total >= 10:
            recent_5 = recent[:5]
            older_5 = recent[5:10]
            recent_success = sum(1 for g in recent_5 if g.get("status") == "completed") / max(1, len(recent_5))
            older_success = sum(1 for g in older_5 if g.get("status") == "completed") / max(1, len(older_5))
            trend = "improving" if recent_success > older_success else ("declining" if recent_success < older_success else "stable")
        else:
            trend = "stable"
        
        return {
            "agent_name": agent_name,
            "success_rate": round(success_rate, 3),
            "total_goals": total,
            "completed_goals": completed,
            "failed_goals": failed,
            "in_progress_goals": in_progress,
            "mutation_success": mutation_success,
            "mutation_total": mutation_total,
            "trend": trend,
        }
    except Exception as e:
        # Fallback — but return 0.5 not 0.0 to prevent evolution spam
        return {
            "agent_name": agent_name,
            "success_rate": 0.5,
            "total_goals": 0,
            "completed_goals": 0,
            "failed_goals": 0,
            "trend": "stable",
            "_error": str(e),
        }


def analyze_session(agent_name: str = None):
    """Analyze current session performance."""
    return get_agent_performance(agent_name or "unknown")


def get_all_performance() -> Dict[str, Any]:
    """Return performance for all agents."""
    return {
        "autobot": get_agent_performance("autobot"),
        "alpha_evaluator": get_agent_performance("alpha_evaluator"),
        "beta_worker": get_agent_performance("beta_worker"),
    }

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
    """Return basic performance metrics for an agent."""
    return {
        "agent_name": agent_name,
        "success_rate": 0.0,
        "total_goals": 0,
        "completed_goals": 0,
        "failed_goals": 0,
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

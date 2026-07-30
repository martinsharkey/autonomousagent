import logging
import traceback
from typing import Callable, Any, Dict, Optional
from tools.provider_optimizer import ProviderOptimizer

logger = logging.getLogger(__name__)

class SelfHealingRetry:
    """Retries failed tool invocations with alternative strategies."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.failure_log: list = []
        self.provider_optimizer = ProviderOptimizer()
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic and fallback strategies."""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                self.failure_log.append({
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                # Try fallback strategies
                if "provider" in str(e).lower():
                    # Fallback to alternative provider
                    kwargs['provider'] = self.provider_optimizer.get_fallback_provider()
                elif "timeout" in str(e).lower():
                    # Increase timeout
                    kwargs['timeout'] = kwargs.get('timeout', 30) * 2
                else:
                    # Simplify query or parameters
                    if 'params' in kwargs:
                        kwargs['params'] = self._simplify_params(kwargs['params'])
        logger.error(f"All {self.max_retries} attempts failed. Last error: {last_exception}")
        raise last_exception
    
    def _simplify_params(self, params: Dict) -> Dict:
        """Reduce complexity of parameters to avoid errors."""
        simplified = {}
        for key, value in params.items():
            if isinstance(value, str) and len(value) > 500:
                simplified[key] = value[:500]
            elif isinstance(value, list) and len(value) > 10:
                simplified[key] = value[:10]
            else:
                simplified[key] = value
        return simplified
    
    def get_failure_summary(self) -> str:
        """Return a summary of recent failures for learning."""
        if not self.failure_log:
            return "No failures recorded."
        summary = "Failure Summary:\n"
        for entry in self.failure_log[-5:]:
            summary += f"- {entry['function']}: {entry['error']}\n"
        return summary

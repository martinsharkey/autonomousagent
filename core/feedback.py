import logging
import time
from typing import Callable, Any

logger = logging.getLogger(__name__)

class SelfCorrectingExecutor:
    """Wraps tool execution with retry and fallback logic."""
    
    def __init__(self, max_retries: int = 2, fallback_providers: list = None):
        self.max_retries = max_retries
        self.fallback_providers = fallback_providers or []
        self.failure_log = []
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        last_exception = None
        for attempt in range(1 + self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                self.failure_log.append({
                    "function": func.__name__,
                    "attempt": attempt + 1,
                    "error": str(e),
                    "timestamp": time.time()
                })
                # If fallback providers exist, try a simplified call
                if self.fallback_providers and attempt < self.max_retries:
                    # In a real scenario, we'd switch provider or simplify
                    pass
                time.sleep(0.5 * (attempt + 1))
        raise last_exception
    
    def get_failure_summary(self) -> dict:
        return {
            "total_failures": len(self.failure_log),
            "recent_failures": self.failure_log[-10:]
        }

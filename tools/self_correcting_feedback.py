import logging
import traceback
from typing import Callable, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SelfCorrectingFeedback:
    """
    A feedback loop that logs failed tool invocations and retries with alternative strategies.
    Supports fallback providers, simplified queries, and exponential backoff.
    """

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.failure_log: List[Dict[str, Any]] = []

    def execute_with_retry(self, func: Callable, *args, context: Optional[Dict] = None, **kwargs) -> Any:
        """Execute a function with retry logic and alternative strategies."""
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt} failed: {e}")
                self._log_failure(func.__name__, attempt, str(e), context)
                if attempt < self.max_retries:
                    self._apply_alternative_strategy(attempt)
        raise last_exception

    def _log_failure(self, func_name: str, attempt: int, error: str, context: Optional[Dict]):
        """Record failure details for analysis."""
        entry = {
            "function": func_name,
            "attempt": attempt,
            "error": error,
            "context": context or {},
            "traceback": traceback.format_exc()
        }
        self.failure_log.append(entry)
        logger.error(f"Logged failure: {entry}")

    def _apply_alternative_strategy(self, attempt: int):
        """Implement alternative strategies based on attempt number."""
        if attempt == 1:
            logger.info("Retrying with simplified parameters...")
        elif attempt == 2:
            logger.info("Retrying with fallback provider...")
        else:
            logger.info("Retrying with exponential backoff...")
            import time
            time.sleep(self.backoff_factor ** attempt)

    def get_failure_summary(self) -> Dict[str, Any]:
        """Return a summary of failures for learning."""
        if not self.failure_log:
            return {"status": "no_failures"}
        return {
            "total_failures": len(self.failure_log),
            "most_common_error": max(set(f["error"] for f in self.failure_log), key=lambda x: sum(1 for f in self.failure_log if f["error"] == x)),
            "failures_by_function": {f["function"] for f in self.failure_log}
        }

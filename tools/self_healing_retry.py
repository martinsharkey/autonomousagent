import logging
import time
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

class SelfHealingRetry:
    """Retries a function with alternative strategies on failure."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.failure_log = []

    def execute(self, func: Callable, *args, fallback_func: Optional[Callable] = None, **kwargs) -> Any:
        """Execute function with retry and fallback."""
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self._log_success(func.__name__, attempt)
                return result
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}")
                self._log_failure(func.__name__, attempt, str(e))
                if attempt < self.max_retries:
                    time.sleep(self.backoff_factor ** attempt)
        # Fallback
        if fallback_func:
            logger.info(f"Attempting fallback for {func.__name__}")
            try:
                result = fallback_func(*args, **kwargs)
                self._log_success(f"{func.__name__}_fallback", 1)
                return result
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
                raise e
        raise last_exception

    def _log_success(self, name: str, attempt: int):
        self.failure_log.append({"function": name, "attempt": attempt, "status": "success"})

    def _log_failure(self, name: str, attempt: int, error: str):
        self.failure_log.append({"function": name, "attempt": attempt, "status": "failure", "error": error})

    def get_failure_summary(self) -> list:
        return [entry for entry in self.failure_log if entry["status"] == "failure"]

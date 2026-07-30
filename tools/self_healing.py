import logging
import traceback
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

class SelfHealingExecutor:
    """Executes a callable with automatic retry and fallback strategies."""

    def __init__(self, max_retries: int = 2, fallback_provider: Optional[str] = None):
        self.max_retries = max_retries
        self.fallback_provider = fallback_provider
        self.error_log: list[dict] = []

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Attempt to execute func, retrying with fallback on failure."""
        last_exception = None
        for attempt in range(1 + self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt} failed: {e}")
                self.error_log.append({
                    "function": func.__name__,
                    "attempt": attempt,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                # If fallback provider is set and this is the first retry, modify kwargs
                if attempt == 1 and self.fallback_provider and 'provider' in kwargs:
                    kwargs['provider'] = self.fallback_provider
                    logger.info(f"Retrying with fallback provider: {self.fallback_provider}")
        raise last_exception

    def get_error_summary(self) -> list[dict]:
        """Return logged errors for analysis."""
        return self.error_log

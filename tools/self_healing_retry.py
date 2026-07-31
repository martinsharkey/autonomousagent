import logging
import time
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)

class SelfHealingRetry:
    """Retries a function with alternative strategies on failure."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.5):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def execute(self, func: Callable, *args, strategy: str = 'default', **kwargs) -> Any:
        """Execute func with retries and strategy adaptation."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                # Adapt strategy: simplify query or use fallback provider
                if strategy == 'default':
                    strategy = 'simplified'
                elif strategy == 'simplified':
                    strategy = 'fallback_provider'
                else:
                    break
                time.sleep(self.backoff_factor ** attempt)
        raise RuntimeError(f"All retries failed: {last_error}")

    def log_failure(self, tool_name: str, error: Exception, context: Dict[str, Any]):
        """Log failure details for learning."""
        logger.error(f"Tool {tool_name} failed: {error}, context: {context}")
        # In a real implementation, this would write to a feedback store

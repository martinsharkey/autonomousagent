import logging
from typing import Callable, Any

class AdaptiveRetry:
    """Retry with adaptive strategy based on failure type."""
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.failure_log = []

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.failure_log.append({'attempt': attempt, 'error': str(e)})
                if attempt == self.max_retries - 1:
                    raise
                # Modify strategy: simplify input or switch tool
                if 'timeout' in str(e).lower():
                    kwargs['timeout'] = kwargs.get('timeout', 10) * 0.5
                elif 'not found' in str(e).lower():
                    kwargs['fallback'] = True
        return None

    def get_failure_summary(self) -> str:
        return '\n'.join([f"Attempt {f['attempt']}: {f['error']}" for f in self.failure_log])

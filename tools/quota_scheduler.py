import time
import threading
from collections import defaultdict

class QuotaScheduler:
    """Schedules LLM requests to avoid exceeding free tier quotas."""
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._lock = threading.Lock()
        self._usage = defaultdict(lambda: {'count': 0, 'window_start': time.time()})
        self._queue = []
        self._max_requests_per_minute = self.config.get('max_requests_per_minute', 50)
        self._max_tokens_per_minute = self.config.get('max_tokens_per_minute', 100000)

    def record_usage(self, provider: str, tokens: int = 0):
        with self._lock:
            now = time.time()
            usage = self._usage[provider]
            if now - usage['window_start'] > 60:
                usage['count'] = 0
                usage['tokens'] = 0
                usage['window_start'] = now
            usage['count'] += 1
            usage['tokens'] += tokens

    def can_send(self, provider: str, estimated_tokens: int = 0) -> bool:
        with self._lock:
            usage = self._usage.get(provider)
            if not usage:
                return True
            now = time.time()
            if now - usage['window_start'] > 60:
                return True
            if usage['count'] >= self._max_requests_per_minute:
                return False
            if usage['tokens'] + estimated_tokens > self._max_tokens_per_minute:
                return False
            return True

    def enqueue(self, request: dict):
        """Queue a request with priority (lower number = higher priority)."""
        priority = request.get('priority', 5)
        with self._lock:
            self._queue.append((priority, time.time(), request))
            self._queue.sort(key=lambda x: (x[0], x[1]))

    def dequeue(self) -> dict:
        """Get the highest priority request that can be sent."""
        with self._lock:
            for i, (_, _, req) in enumerate(self._queue):
                provider = req.get('provider', 'default')
                tokens = req.get('estimated_tokens', 0)
                if self.can_send(provider, tokens):
                    self._queue.pop(i)
                    return req
            return None

    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    def reset(self, provider: str = None):
        with self._lock:
            if provider:
                self._usage[provider] = {'count': 0, 'tokens': 0, 'window_start': time.time()}
            else:
                self._usage.clear()

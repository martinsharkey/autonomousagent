import time
import threading
from collections import deque
from typing import Callable, Any

class QuotaScheduler:
    """Schedules LLM requests to respect free tier quotas."""
    def __init__(self, max_requests_per_minute: int = 60, max_requests_per_day: int = 1000):
        self.max_per_minute = max_requests_per_minute
        self.max_per_day = max_requests_per_day
        self.minute_window = deque()
        self.day_window = deque()
        self.lock = threading.Lock()
        self._start_day = time.time()

    def can_send(self) -> bool:
        now = time.time()
        with self.lock:
            # Clean old entries
            while self.minute_window and self.minute_window[0] < now - 60:
                self.minute_window.popleft()
            while self.day_window and self.day_window[0] < now - 86400:
                self.day_window.popleft()
            if len(self.minute_window) >= self.max_per_minute:
                return False
            if len(self.day_window) >= self.max_per_day:
                return False
            return True

    def schedule(self, request_func: Callable, *args, **kwargs) -> Any:
        """Execute request_func when quota allows, blocking if necessary."""
        while not self.can_send():
            time.sleep(1)
        with self.lock:
            now = time.time()
            self.minute_window.append(now)
            self.day_window.append(now)
        return request_func(*args, **kwargs)

    def get_usage(self) -> dict:
        now = time.time()
        with self.lock:
            minute_count = sum(1 for t in self.minute_window if t > now - 60)
            day_count = sum(1 for t in self.day_window if t > now - 86400)
        return {
            "requests_last_minute": minute_count,
            "requests_last_day": day_count,
            "max_per_minute": self.max_per_minute,
            "max_per_day": self.max_per_day
        }

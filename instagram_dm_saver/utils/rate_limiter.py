"""Rate limiting for Instagram API calls."""

import time
from functools import wraps
from typing import Callable, Any
from collections import deque

from .logger import get_logger
from .exceptions import RateLimitError

logger = get_logger(__name__)


class RateLimiter:
    """
    Rate limiter to prevent API abuse and avoid Instagram blocks.

    Uses a sliding window algorithm to track API calls.
    """

    def __init__(self, max_calls: int = 10, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.call_times: deque = deque()
        logger.debug(f"RateLimiter initialized: {max_calls} calls per {time_window}s")

    def _clean_old_calls(self) -> None:
        """Remove call timestamps outside the current time window."""
        current_time = time.time()
        while self.call_times and current_time - self.call_times[0] > self.time_window:
            self.call_times.popleft()

    def wait_if_needed(self) -> None:
        """Wait if rate limit is reached."""
        self._clean_old_calls()

        if len(self.call_times) >= self.max_calls:
            sleep_time = self.time_window - (time.time() - self.call_times[0])
            if sleep_time > 0:
                logger.warning(
                    f"Rate limit reached ({len(self.call_times)}/{self.max_calls}). "
                    f"Sleeping for {sleep_time:.2f}s"
                )
                time.sleep(sleep_time)
                self._clean_old_calls()

    def add_call(self) -> None:
        """Record a new API call."""
        self.call_times.append(time.time())

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to a function.

        Args:
            func: Function to rate limit

        Returns:
            Wrapped function with rate limiting
        """
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.wait_if_needed()
            self.add_call()
            return func(*args, **kwargs)

        return wrapper

    def get_remaining_calls(self) -> int:
        """
        Get number of remaining calls in current window.

        Returns:
            Number of calls that can be made without waiting
        """
        self._clean_old_calls()
        return max(0, self.max_calls - len(self.call_times))

    def get_reset_time(self) -> float:
        """
        Get time in seconds until rate limit resets.

        Returns:
            Seconds until oldest call expires, or 0 if no calls in window
        """
        self._clean_old_calls()
        if not self.call_times:
            return 0.0
        return max(0.0, self.time_window - (time.time() - self.call_times[0]))


# Global rate limiter instance for Instagram API
instagram_rate_limiter = RateLimiter(max_calls=10, time_window=60)

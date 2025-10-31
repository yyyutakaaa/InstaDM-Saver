"""Tests for rate limiter."""

import pytest
import time

from instagram_dm_saver.utils.rate_limiter import RateLimiter


def test_rate_limiter_creation():
    """Test creating rate limiter."""
    limiter = RateLimiter(max_calls=5, time_window=10)
    assert limiter.max_calls == 5
    assert limiter.time_window == 10


def test_rate_limiter_allows_calls():
    """Test that rate limiter allows calls within limit."""
    limiter = RateLimiter(max_calls=5, time_window=60)

    # Should allow first 5 calls without waiting
    for _ in range(5):
        start = time.time()
        limiter.wait_if_needed()
        limiter.add_call()
        elapsed = time.time() - start
        assert elapsed < 0.1  # Should be nearly instant


def test_rate_limiter_blocks_excess_calls():
    """Test that rate limiter blocks calls exceeding limit."""
    limiter = RateLimiter(max_calls=3, time_window=2)

    # Make 3 calls
    for _ in range(3):
        limiter.wait_if_needed()
        limiter.add_call()

    # 4th call should be blocked
    start = time.time()
    limiter.wait_if_needed()
    elapsed = time.time() - start

    # Should have waited approximately 2 seconds
    assert elapsed >= 1.5


def test_rate_limiter_decorator():
    """Test rate limiter as decorator."""
    limiter = RateLimiter(max_calls=3, time_window=1)

    call_times = []

    @limiter
    def test_function():
        call_times.append(time.time())
        return "done"

    # Make 5 calls
    for _ in range(5):
        result = test_function()
        assert result == "done"

    # First 3 should be fast, 4th and 5th should be delayed
    assert len(call_times) == 5
    assert call_times[3] - call_times[0] >= 0.9  # At least 1 second delay


def test_rate_limiter_get_remaining():
    """Test getting remaining calls."""
    limiter = RateLimiter(max_calls=5, time_window=60)

    assert limiter.get_remaining_calls() == 5

    limiter.add_call()
    assert limiter.get_remaining_calls() == 4

    limiter.add_call()
    limiter.add_call()
    assert limiter.get_remaining_calls() == 2


def test_rate_limiter_reset_time():
    """Test getting reset time."""
    limiter = RateLimiter(max_calls=3, time_window=10)

    # No calls yet
    assert limiter.get_reset_time() == 0.0

    # Make a call
    limiter.add_call()
    reset_time = limiter.get_reset_time()

    # Should be close to 10 seconds
    assert 9 <= reset_time <= 10


def test_rate_limiter_cleans_old_calls():
    """Test that old calls are cleaned up."""
    limiter = RateLimiter(max_calls=3, time_window=1)

    # Make 3 calls
    for _ in range(3):
        limiter.add_call()

    assert limiter.get_remaining_calls() == 0

    # Wait for time window to pass
    time.sleep(1.1)

    # Should be reset
    assert limiter.get_remaining_calls() == 3

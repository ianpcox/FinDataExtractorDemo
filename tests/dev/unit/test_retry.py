"""Unit tests for retry utility"""

import pytest
from unittest.mock import Mock, patch
import asyncio

from src.utils.retry import (
    retry_with_backoff,
    async_retry_with_backoff,
    RetryableError,
    RateLimitError,
)


@pytest.mark.unit
class TestRetryWithBackoff:
    """Test synchronous retry decorator"""

    def test_retry_success_first_attempt(self):
        """Test function succeeds on first attempt"""
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"

    def test_retry_success_after_retries(self):
        """Test function succeeds after retries"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def retry_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = retry_function()
        assert result == "success"
        assert call_count[0] == 3

    def test_retry_max_retries_exceeded(self):
        """Test function fails after max retries"""
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def failing_function():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            failing_function()

    def test_retry_with_custom_exceptions(self):
        """Test retry with custom exception types"""
        call_count = [0]
        
        class CustomError(Exception):
            pass
        
        @retry_with_backoff(max_retries=2, initial_delay=0.01, exceptions=(CustomError,))
        def custom_error_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise CustomError("Custom error")
            return "success"
        
        result = custom_error_function()
        assert result == "success"
        assert call_count[0] == 2

    def test_retry_exception_not_in_tuple(self):
        """Test exception not in retry tuple is not retried"""
        call_count = [0]
        
        class NonRetryableError(Exception):
            pass
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01, exceptions=(ValueError,))
        def non_retryable_function():
            call_count[0] += 1
            raise NonRetryableError("Not retried")
        
        with pytest.raises(NonRetryableError):
            non_retryable_function()
        
        assert call_count[0] == 1  # Should not retry

    def test_retry_with_exponential_backoff(self):
        """Test exponential backoff delay"""
        delays = []
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def delayed_function():
            delays.append(None)
            if len(delays) < 3:
                raise Exception("Temporary failure")
            return "success"
        
        with patch("time.sleep") as mock_sleep:
            delayed_function()
            
            # Should have slept for exponential backoff
            assert mock_sleep.call_count == 2  # 2 retries
            # Verify exponential backoff delays
            if mock_sleep.call_count >= 2:
                first_delay = mock_sleep.call_args_list[0][0][0]
                second_delay = mock_sleep.call_args_list[1][0][0]
                assert second_delay > first_delay  # Exponential increase

    def test_retry_rate_limit_error(self):
        """Test rate limit error handling"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def rate_limit_function():
            call_count[0] += 1
            if call_count[0] < 2:
                error = RateLimitError("Rate limited", retry_after=1)
                error.status_code = 429
                raise error
            return "success"
        
        result = rate_limit_function()
        assert result == "success"
        assert call_count[0] == 2

    def test_retry_max_delay_capped(self):
        """Test that delay is capped at max_delay"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=5, initial_delay=10.0, max_delay=20.0)
        def max_delay_function():
            call_count[0] += 1
            if call_count[0] < 5:
                raise Exception("Error")
            return "success"
        
        with patch("time.sleep") as mock_sleep:
            max_delay_function()
            
            # Verify delays don't exceed max_delay
            for call in mock_sleep.call_args_list:
                delay = call[0][0]
                assert delay <= 20.0


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncRetryWithBackoff:
    """Test asynchronous retry decorator"""

    async def test_async_retry_success_first_attempt(self):
        """Test async function succeeds on first attempt"""
        @async_retry_with_backoff(max_retries=3, initial_delay=0.1)
        async def successful_function():
            return "success"
        
        result = await successful_function()
        assert result == "success"

    async def test_async_retry_success_after_retries(self):
        """Test async function succeeds after retries"""
        call_count = [0]
        
        @async_retry_with_backoff(max_retries=3, initial_delay=0.01)
        async def retry_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await retry_function()
        assert result == "success"
        assert call_count[0] == 3

    async def test_async_retry_max_retries_exceeded(self):
        """Test async function fails after max retries"""
        @async_retry_with_backoff(max_retries=3, initial_delay=0.01)
        async def failing_function():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            await failing_function()

    async def test_async_retry_with_exponential_backoff(self):
        """Test exponential backoff delay for async"""
        call_count = [0]
        
        @async_retry_with_backoff(max_retries=3, initial_delay=0.01)
        async def delayed_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"
        
        with patch("asyncio.sleep") as mock_sleep:
            await delayed_function()
            
            # Should have slept for exponential backoff
            assert mock_sleep.call_count == 2  # 2 retries
            # Verify exponential backoff delays
            if mock_sleep.await_count >= 2:
                first_delay = mock_sleep.await_args_list[0][0][0]
                second_delay = mock_sleep.await_args_list[1][0][0]
                assert second_delay > first_delay  # Exponential increase

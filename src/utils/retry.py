"""Retry utilities with exponential backoff for external service calls"""

import time
import logging
from typing import TypeVar, Callable, Any, Optional
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    # Check if it's a rate limit error (429)
                    if hasattr(e, 'status_code') and e.status_code == 429:
                        logger.warning(
                            f"{func.__name__} hit rate limit (429), attempt {attempt + 1}/{max_retries}, "
                            f"backing off for {delay:.2f}s"
                        )
                    else:
                        logger.warning(
                            f"{func.__name__} failed attempt {attempt + 1}/{max_retries}: {e}, "
                            f"retrying in {delay:.2f}s"
                        )
                    
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            
            raise last_exception
        
        return wrapper
    return decorator


def async_retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    # Check if it's a rate limit error (429)
                    if hasattr(e, 'status_code') and e.status_code == 429:
                        logger.warning(
                            f"{func.__name__} hit rate limit (429), attempt {attempt + 1}/{max_retries}, "
                            f"backing off for {delay:.2f}s"
                        )
                    else:
                        logger.warning(
                            f"{func.__name__} failed attempt {attempt + 1}/{max_retries}: {e}, "
                            f"retrying in {delay:.2f}s"
                        )
                    
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            
            raise last_exception
        
        return wrapper
    return decorator


class RetryableError(Exception):
    """Base class for errors that should trigger retries"""
    pass


class RateLimitError(RetryableError):
    """Error raised when rate limit is hit"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after

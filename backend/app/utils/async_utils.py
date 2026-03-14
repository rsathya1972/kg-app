"""
Async utilities: run_in_executor helper, retry decorator.
"""
import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_sync(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a blocking (synchronous) function in the default thread pool executor.
    Use this inside async route handlers for blocking I/O or CPU-bound work.

    Example:
        result = await run_sync(blocking_file_read, path)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator: retry an async function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier applied to delay on each retry.
        exceptions: Exception types that trigger a retry.

    Example:
        @async_retry(max_attempts=3, delay=0.5)
        async def call_ai_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "All %d attempts failed for %s: %s",
                            max_attempts, func.__name__, exc,
                        )
                        raise
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                        attempt, max_attempts, func.__name__, exc, current_delay,
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

"""
error_handler.py — Retry with Exponential Backoff and error classification

Provides:
  - retry_with_backoff() — decorator/helper for retrying functions
  - TransientError / PermanentError — exception classes
  - classify_error() — determines if an error is transient or permanent
"""

import functools
import logging
import time
from typing import Callable, Any

logger = logging.getLogger(__name__)

# ── Exception hierarchy ───────────────────────────────────────────────────────

class TransientError(Exception):
    """Represents a recoverable error — safe to retry (rate limit, network, 503)."""
    pass


class PermanentError(Exception):
    """Represents an unrecoverable error — do NOT retry (auth failure, bad input, 404)."""
    pass


# ── Error classification ──────────────────────────────────────────────────────

def classify_error(exception: Exception) -> str:
    """
    Classify an exception as 'transient' or 'permanent'.

    Transient (retryable):
        - HTTP 429 (rate limit), 500, 502, 503, 504
        - Network errors: ConnectionError, TimeoutError
        - Temporary DNS / socket issues

    Permanent (do not retry):
        - HTTP 400, 401, 403, 404, 405, 422
        - ValueError, TypeError (logic/input errors)
        - Authentication failures
    """
    exc_str = str(exception).lower()
    exc_type = type(exception).__name__

    # Check for requests library HTTP errors
    try:
        import requests
        if isinstance(exception, requests.exceptions.Timeout):
            return "transient"
        if isinstance(exception, requests.exceptions.ConnectionError):
            return "transient"
        if isinstance(exception, requests.exceptions.HTTPError):
            resp = getattr(exception, "response", None)
            if resp is not None:
                status = resp.status_code
                return _classify_http_status(status)
        if isinstance(exception, requests.exceptions.RequestException):
            return "transient"
    except ImportError:
        pass

    # Check urllib HTTP errors
    try:
        import urllib.error
        if isinstance(exception, urllib.error.URLError):
            reason = getattr(exception, "reason", None)
            if reason is not None:
                if isinstance(reason, OSError):
                    return "transient"  # Network-level
            return "transient"
        if isinstance(exception, urllib.error.HTTPError):
            return _classify_http_status(exception.code)
    except ImportError:
        pass

    # Standard exception types
    if isinstance(exception, (TimeoutError, ConnectionError, ConnectionResetError,
                               ConnectionAbortedError, BrokenPipeError)):
        return "transient"

    if isinstance(exception, (ValueError, TypeError, KeyError, AttributeError,
                               PermissionError, FileNotFoundError)):
        return "permanent"

    if isinstance(exception, TransientError):
        return "transient"

    if isinstance(exception, PermanentError):
        return "permanent"

    # Heuristic: check message content
    transient_keywords = ["timeout", "429", "503", "502", "504", "rate limit",
                          "too many requests", "temporarily unavailable",
                          "network", "connection reset", "broken pipe", "econnrefused"]
    permanent_keywords = ["401", "403", "404", "unauthorized", "forbidden",
                          "not found", "invalid", "bad request", "400", "405"]

    for kw in transient_keywords:
        if kw in exc_str:
            return "transient"

    for kw in permanent_keywords:
        if kw in exc_str:
            return "permanent"

    # Default: treat as transient (safe to retry once)
    return "transient"


def _classify_http_status(status_code: int) -> str:
    """Return 'transient' or 'permanent' for an HTTP status code."""
    if status_code in (429, 500, 502, 503, 504):
        return "transient"
    if status_code in (400, 401, 403, 404, 405, 409, 410, 422):
        return "permanent"
    if 500 <= status_code < 600:
        return "transient"
    if 400 <= status_code < 500:
        return "permanent"
    return "transient"


# ── Retry helper ──────────────────────────────────────────────────────────────

def retry_with_backoff(
    func: Callable = None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = None,
    on_retry: Callable = None,
) -> Any:
    """
    Retry a function with exponential backoff.

    Can be used as:
      1. A decorator:      @retry_with_backoff
      2. A decorator with args: @retry_with_backoff(max_retries=5, initial_delay=2.0)
      3. A direct call:    retry_with_backoff(my_func, max_retries=3)

    Parameters:
        func              — the callable to wrap (or None when used as decorator factory)
        max_retries       — maximum number of attempts (default 3)
        initial_delay     — initial sleep before first retry in seconds (default 1.0)
        backoff_factor    — multiplier for delay on each retry (default 2.0)
        retryable_exceptions — tuple of exception types to catch (default: broad set)
        on_retry          — optional callback(attempt, exception, delay) called before each retry

    Raises:
        PermanentError — wraps the last exception if it's classified as permanent
        The original exception — if max retries exhausted
    """
    if retryable_exceptions is None:
        # Default: catch everything except keyboard/system exits
        retryable_exceptions = (Exception,)

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exc = None

            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    classification = classify_error(exc)

                    if classification == "permanent":
                        logger.error(
                            f"[retry] {fn.__name__} — permanent error on attempt {attempt + 1}: {exc}"
                        )
                        raise PermanentError(f"Permanent error in {fn.__name__}: {exc}") from exc

                    if attempt == max_retries:
                        logger.error(
                            f"[retry] {fn.__name__} — max retries ({max_retries}) exhausted: {exc}"
                        )
                        raise

                    logger.warning(
                        f"[retry] {fn.__name__} — attempt {attempt + 1}/{max_retries + 1} "
                        f"failed ({type(exc).__name__}: {exc}). "
                        f"Retrying in {delay:.1f}s..."
                    )

                    if on_retry:
                        try:
                            on_retry(attempt + 1, exc, delay)
                        except Exception:
                            pass

                    time.sleep(delay)
                    delay *= backoff_factor

            raise last_exc  # Should not reach here

        return wrapper

    # Called as @retry_with_backoff (no args) — func is the decorated function
    if func is not None:
        return decorator(func)

    # Called as @retry_with_backoff(...) — return decorator
    return decorator


# ── Context manager variant ───────────────────────────────────────────────────

class RetryContext:
    """
    Context manager for retry logic in loops.

    Usage:
        with RetryContext(max_retries=3) as ctx:
            while ctx.should_retry():
                try:
                    result = do_something()
                    ctx.success()
                    break
                except Exception as e:
                    ctx.handle(e)
    """

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0,
                 backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self._attempt = 0
        self._succeeded = False
        self._delay = initial_delay

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False  # Don't suppress exceptions

    def should_retry(self) -> bool:
        return self._attempt <= self.max_retries and not self._succeeded

    def success(self):
        self._succeeded = True

    def handle(self, exc: Exception):
        classification = classify_error(exc)
        if classification == "permanent":
            raise PermanentError(f"Permanent error: {exc}") from exc
        self._attempt += 1
        if self._attempt > self.max_retries:
            raise exc
        time.sleep(self._delay)
        self._delay *= self.backoff_factor


# ── Module-level convenience decorator ───────────────────────────────────────

def with_retry(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """Shorthand decorator with configurable parameters."""
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
    )


if __name__ == "__main__":
    # Quick self-test
    import random

    call_count = 0

    @retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2.0)
    def flaky_function():
        global call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError(f"Simulated transient error (attempt {call_count})")
        return f"Success on attempt {call_count}"

    try:
        result = flaky_function()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")

    # Test classification
    print("\nError classification tests:")
    try:
        import requests
        e = requests.exceptions.Timeout()
        print(f"  requests.Timeout -> {classify_error(e)}")
    except ImportError:
        pass

    print(f"  ConnectionError -> {classify_error(ConnectionError('refused'))}")
    print(f"  ValueError -> {classify_error(ValueError('bad input'))}")
    print(f"  TransientError -> {classify_error(TransientError('429'))}")
    print(f"  '429 rate limit' string -> {classify_error(Exception('429 rate limit'))}")
    print(f"  '401 unauthorized' string -> {classify_error(Exception('401 unauthorized'))}")

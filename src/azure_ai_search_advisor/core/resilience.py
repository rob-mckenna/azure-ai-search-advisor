"""Resilience primitives for outbound Azure API calls."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from math import ceil
from threading import Lock
from time import monotonic, sleep
from typing import ParamSpec, TypeVar

RETRYABLE_HTTP_STATUS_CODES = frozenset({429, 500, 502, 503})

P = ParamSpec("P")
R = TypeVar("R")


def _extract_http_status_code(exc: BaseException | None) -> int | None:
    if exc is None:
        return None

    for attribute in ("status_code", "status", "code"):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    return _extract_http_status_code(exc.__cause__) or _extract_http_status_code(exc.__context__)


def is_transient_azure_failure(exc: BaseException) -> bool:
    """Return whether an Azure call failure is safe to retry."""

    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    status_code = _extract_http_status_code(exc)
    return status_code in RETRYABLE_HTTP_STATUS_CODES


def retry(
    *,
    max_retries: int = 3,
    initial_backoff_seconds: float = 1.0,
    retry_if: Callable[[BaseException], bool] = is_transient_azure_failure,
    sleeper: Callable[[float], None] = sleep,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry transient failures with exponential backoff."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = initial_backoff_seconds
            attempts = 0

            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if attempts >= max_retries or not retry_if(exc):
                        raise
                    sleeper(delay)
                    attempts += 1
                    delay *= 2

        return wrapper

    return decorator


class CircuitBreakerState(StrEnum):
    """Circuit breaker lifecycle state."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker rejects a call."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            "Live Azure ingestion temporarily unavailable due to repeated failures. "
            f"Retry after {retry_after_seconds}s."
        )


class CircuitBreaker:
    """Thread-safe circuit breaker for protecting unstable integrations."""

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        time_source: Callable[[], float] = monotonic,
        record_failure: Callable[[BaseException], bool] | None = None,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._time_source = time_source
        self._record_failure = record_failure or (lambda exc: True)
        self._lock = Lock()
        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._half_open_in_flight = False

    @property
    def state(self) -> CircuitBreakerState:
        with self._lock:
            return self._state

    def call(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        """Execute a protected call or raise if the circuit is open."""

        self._before_call()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            self._after_failure(exc)
            raise
        self._after_success()
        return result

    def _before_call(self) -> None:
        with self._lock:
            now = self._time_source()

            if self._state == CircuitBreakerState.OPEN:
                assert self._opened_at is not None
                elapsed = now - self._opened_at
                if elapsed < self._recovery_timeout:
                    raise CircuitBreakerOpenError(self._retry_after_seconds(now))
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_in_flight = True
                return

            if self._state == CircuitBreakerState.HALF_OPEN and self._half_open_in_flight:
                raise CircuitBreakerOpenError(max(1, ceil(self._recovery_timeout)))

    def _after_success(self) -> None:
        with self._lock:
            self._reset()

    def _after_failure(self, exc: BaseException) -> None:
        with self._lock:
            should_record = self._record_failure(exc)
            self._half_open_in_flight = False

            if not should_record:
                if self._state == CircuitBreakerState.HALF_OPEN:
                    self._reset()
                return

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._trip_open()
                return

            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._trip_open()

    def _trip_open(self) -> None:
        self._state = CircuitBreakerState.OPEN
        self._opened_at = self._time_source()
        self._half_open_in_flight = False

    def _reset(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = None
        self._half_open_in_flight = False

    def _retry_after_seconds(self, now: float | None = None) -> int:
        if self._opened_at is None:
            return max(1, ceil(self._recovery_timeout))
        current_time = self._time_source() if now is None else now
        remaining = max(0.0, self._recovery_timeout - (current_time - self._opened_at))
        return max(1, ceil(remaining))

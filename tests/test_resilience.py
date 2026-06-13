from __future__ import annotations

import pytest

from azure_ai_search_advisor.core.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    retry,
)


def test_retry_retries_transient_failures_with_exponential_backoff() -> None:
    attempts = {"count": 0}
    delays: list[float] = []

    @retry(sleeper=delays.append)
    def _flaky_call() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionError("temporary network issue")
        return "ok"

    assert _flaky_call() == "ok"
    assert attempts["count"] == 3
    assert delays == [1.0, 2.0]


def test_circuit_breaker_opens_and_recovers_after_timeout() -> None:
    current_time = [0.0]
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=10.0,
        time_source=lambda: current_time[0],
    )

    def _fail() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        breaker.call(_fail)
    with pytest.raises(RuntimeError):
        breaker.call(_fail)

    assert breaker.state == CircuitBreakerState.OPEN

    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        breaker.call(lambda: "blocked")
    assert exc_info.value.retry_after_seconds == 10

    current_time[0] = 11.0
    assert breaker.call(lambda: "recovered") == "recovered"
    assert breaker.state == CircuitBreakerState.CLOSED

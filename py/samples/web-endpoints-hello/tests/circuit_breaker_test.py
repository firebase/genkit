# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for `CircuitBreaker` async circuit-breaker implementation."""

import asyncio
from typing import NoReturn

import pytest

from src.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


@pytest.fixture
def breaker() -> CircuitBreaker:
    """Create a CircuitBreaker with low threshold for testing."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, name="test")


@pytest.fixture
def disabled_breaker() -> CircuitBreaker:
    """Create a disabled CircuitBreaker that passes all calls through."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, enabled=False)


class TestCircuitBreakerBasic:
    """Tests for basic circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_starts_closed(self, breaker: CircuitBreaker) -> None:
        """Verify a new breaker starts in CLOSED state."""
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_passes_through(self, breaker: CircuitBreaker) -> None:
        """Verify successful calls pass through and stay CLOSED."""
        result = await breaker.call(self._success)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_single_failure_stays_closed(self, breaker: CircuitBreaker) -> None:
        """Verify a single failure does not open the circuit."""
        with pytest.raises(ValueError):
            await breaker.call(self._fail)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self, breaker: CircuitBreaker) -> None:
        """Verify circuit opens after reaching failure threshold."""
        for _ in range(3):
            with pytest.raises(ValueError):
                await breaker.call(self._fail)
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self, breaker: CircuitBreaker) -> None:
        """Verify open circuit rejects calls with CircuitOpenError."""
        await self._trip(breaker)
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.call(self._success)
        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_disabled_passes_through(self, disabled_breaker: CircuitBreaker) -> None:
        """Verify disabled breaker passes all calls through."""
        result = await disabled_breaker.call(self._success)
        assert result == "ok"
        for _ in range(10):
            with pytest.raises(ValueError):
                await disabled_breaker.call(self._fail)
        # Still passes — disabled means transparent.
        result = await disabled_breaker.call(self._success)
        assert result == "ok"

    @staticmethod
    async def _success() -> str:
        return "ok"

    @staticmethod
    async def _fail() -> NoReturn:
        raise ValueError("boom")

    @staticmethod
    async def _trip(breaker: CircuitBreaker) -> None:
        for _ in range(breaker.failure_threshold):
            try:
                await breaker.call(TestCircuitBreakerBasic._fail)
            except ValueError:
                pass


class TestCircuitBreakerRecovery:
    """Tests for circuit breaker recovery and half-open transitions."""

    @pytest.mark.asyncio
    async def test_transitions_to_half_open(self, breaker: CircuitBreaker) -> None:
        """Verify circuit transitions to HALF_OPEN after recovery timeout."""
        await TestCircuitBreakerBasic._trip(breaker)
        assert breaker.state == CircuitState.OPEN
        await asyncio.sleep(1.1)
        # Next call triggers transition to HALF_OPEN and succeeds.
        result = await breaker.call(self._success)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self, breaker: CircuitBreaker) -> None:
        """Verify a failure in half-open state re-opens the circuit."""
        await TestCircuitBreakerBasic._trip(breaker)
        await asyncio.sleep(1.1)
        with pytest.raises(ValueError):
            await breaker.call(self._fail)
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, breaker: CircuitBreaker) -> None:
        """Verify a success resets the consecutive failure counter."""
        # Two failures (below threshold), then success resets count.
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(self._fail)
        await breaker.call(self._success)
        # One more failure should not trip (count was reset).
        with pytest.raises(ValueError):
            await breaker.call(self._fail)
        assert breaker.state == CircuitState.CLOSED

    @staticmethod
    async def _success() -> str:
        return "ok"

    @staticmethod
    async def _fail() -> NoReturn:
        raise ValueError("boom")


class TestCircuitBreakerStats:
    """Tests for circuit breaker statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self, breaker: CircuitBreaker) -> None:
        """Verify stats track calls, successes, and failures."""
        await breaker.call(self._success)
        try:
            await breaker.call(self._fail)
        except ValueError:
            pass
        stats = breaker.stats()
        assert stats["total_calls"] == 2
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 1
        assert stats["name"] == "test"

    @pytest.mark.asyncio
    async def test_rejected_count(self, breaker: CircuitBreaker) -> None:
        """Verify rejected calls are counted in stats."""
        await TestCircuitBreakerBasic._trip(breaker)
        try:
            await breaker.call(self._success)
        except CircuitOpenError:
            pass
        assert breaker.stats()["total_rejected"] == 1

    @pytest.mark.asyncio
    async def test_manual_reset(self, breaker: CircuitBreaker) -> None:
        """Verify manual reset closes the circuit and allows calls."""
        await TestCircuitBreakerBasic._trip(breaker)
        assert breaker.state == CircuitState.OPEN
        await breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        result = await breaker.call(self._success)
        assert result == "ok"

    @staticmethod
    async def _success() -> str:
        return "ok"

    @staticmethod
    async def _fail() -> NoReturn:
        raise ValueError("boom")


class TestCircuitOpenError:
    """Tests for `CircuitOpenError` exception."""

    def test_retry_after(self) -> None:
        """Verify retry_after is stored and included in str."""
        err = CircuitOpenError(retry_after=5.0)
        assert err.retry_after == 5.0
        assert "5.0" in str(err)

    def test_custom_message(self) -> None:
        """Verify a custom message overrides the default."""
        err = CircuitOpenError(retry_after=1.0, message="custom")
        assert str(err) == "custom"

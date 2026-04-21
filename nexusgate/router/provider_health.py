from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass(slots=True)
class HealthEvent:
    ts: float
    success: bool
    latency_ms: float


@dataclass(slots=True)
class ProviderState:
    events: deque[HealthEvent]
    consecutive_failures: int
    breaker_until: float


class ProviderHealth:
    def __init__(
        self,
        *,
        window_seconds: int = 300,
        breaker_threshold: int = 3,
        breaker_cooldown_seconds: int = 60,
    ) -> None:
        self.window_seconds = window_seconds
        self.breaker_threshold = breaker_threshold
        self.breaker_cooldown_seconds = breaker_cooldown_seconds
        self._states: dict[str, ProviderState] = {}

    def record_success(self, provider: str, latency_ms: float, now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        state = self._state(provider)
        self._trim(state, ts)
        state.events.append(HealthEvent(ts=ts, success=True, latency_ms=max(latency_ms, 0.0)))
        state.consecutive_failures = 0
        state.breaker_until = 0.0

    def record_failure(self, provider: str, now: float | None = None) -> None:
        ts = now if now is not None else time.time()
        state = self._state(provider)
        self._trim(state, ts)
        state.events.append(HealthEvent(ts=ts, success=False, latency_ms=0.0))
        state.consecutive_failures += 1
        if state.consecutive_failures >= self.breaker_threshold:
            state.breaker_until = ts + float(self.breaker_cooldown_seconds)

    def is_circuit_open(self, provider: str, now: float | None = None) -> bool:
        ts = now if now is not None else time.time()
        state = self._states.get(provider)
        if state is None:
            return False
        return state.breaker_until > ts

    def score(self, provider: str, now: float | None = None) -> float:
        ts = now if now is not None else time.time()
        if self.is_circuit_open(provider, now=ts):
            return 0.0
        state = self._states.get(provider)
        if state is None:
            return 1.0
        self._trim(state, ts)
        if not state.events:
            return 1.0
        successes = [row for row in state.events if row.success]
        success_rate = float(len(successes)) / float(len(state.events))
        avg_latency = (
            sum(row.latency_ms for row in successes) / float(len(successes))
            if successes
            else 4000.0
        )
        latency_penalty = min(max(avg_latency, 0.0) / 4000.0, 0.4)
        return max(0.0, success_rate - latency_penalty)

    def _state(self, provider: str) -> ProviderState:
        state = self._states.get(provider)
        if state is not None:
            return state
        state = ProviderState(events=deque(), consecutive_failures=0, breaker_until=0.0)
        self._states[provider] = state
        return state

    def _trim(self, state: ProviderState, now: float) -> None:
        lower = now - float(self.window_seconds)
        while state.events and state.events[0].ts < lower:
            state.events.popleft()


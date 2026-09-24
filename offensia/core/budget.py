"""Deterministic caps for serial execution.

request_cap, rate and timeout are enforced here, not just carried as metadata.
Hitting a cap raises CapExceeded — the executor turns that into a terminal
state and never loop-retries into the target (non-disruptive invariant).
"""
from __future__ import annotations

import time
from collections.abc import Callable


class CapExceeded(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class TokenBucket:
    def __init__(self, rate: float, capacity: float | None = None,
                 now: Callable[[], float] = time.monotonic):
        self.rate = float(rate)
        self.capacity = float(capacity if capacity is not None else rate)
        self.tokens = self.capacity
        self._now = now
        self._t = now()

    def _refill(self) -> None:
        n = self._now()
        self.tokens = min(self.capacity, self.tokens + (n - self._t) * self.rate)
        self._t = n

    def take(self, n: int = 1) -> bool:
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


class Budget:
    def __init__(self, *, request_cap: int, rate: float, timeout: float,
                 now: Callable[[], float] = time.monotonic):
        self.request_cap = int(request_cap)
        self.rate = float(rate)
        self.requests_made = 0
        self._now = now
        self.deadline = now() + float(timeout)
        self._buckets: dict[str, TokenBucket] = {}

    def _bucket(self, host: str) -> TokenBucket:
        b = self._buckets.get(host)
        if b is None:
            b = TokenBucket(self.rate, now=self._now)
            self._buckets[host] = b
        return b

    def charge(self, host: str, cost: int = 1) -> None:
        if cost <= 0:
            return
        if self._now() >= self.deadline:
            raise CapExceeded("timeout")
        if self.requests_made + cost > self.request_cap:
            raise CapExceeded("budget_exhausted")
        if not self._bucket(host).take(cost):
            raise CapExceeded("rate_limited")
        self.requests_made += cost

    def snapshot(self) -> dict:
        return {"requests_made": self.requests_made, "request_cap": self.request_cap,
                "rate": self.rate}

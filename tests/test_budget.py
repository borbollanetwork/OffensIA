import pytest

from offensia.core.budget import Budget, CapExceeded, TokenBucket


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t
    def advance(self, dt): self.t += dt


def test_token_bucket_refills_over_time():
    clk = Clock()
    b = TokenBucket(rate=2, capacity=2, now=clk)
    assert b.take() and b.take()      # drain
    assert not b.take()               # empty
    clk.advance(0.5)                  # +1 token at rate 2/s
    assert b.take()
    assert not b.take()


def test_request_cap_boundary_is_off_by_one_safe():
    clk = Clock()
    bud = Budget(request_cap=3, rate=1000, timeout=100, now=clk)
    bud.charge("h"); bud.charge("h"); bud.charge("h")   # 3 allowed
    assert bud.requests_made == 3
    with pytest.raises(CapExceeded) as e:
        bud.charge("h")                                  # 4th refused
    assert e.value.reason == "budget_exhausted"


def test_deadline_is_inclusive_timeout():
    clk = Clock()
    bud = Budget(request_cap=100, rate=1000, timeout=10, now=clk)
    bud.charge("h")
    clk.advance(10)                                      # now == deadline
    with pytest.raises(CapExceeded) as e:
        bud.charge("h")
    assert e.value.reason == "timeout"


def test_rate_limit_is_per_host():
    clk = Clock()
    bud = Budget(request_cap=100, rate=1, timeout=100, now=clk)
    bud.charge("a")                                      # host a: 1 token used
    bud.charge("b")                                      # host b: independent bucket
    with pytest.raises(CapExceeded) as e:
        bud.charge("a")                                  # host a empty, no refill
    assert e.value.reason == "rate_limited"

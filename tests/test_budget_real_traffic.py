import pytest

from offensia.core.budget import Budget, CapExceeded


def test_charge_cost_counts_multiple_requests():
    bud = Budget(request_cap=5, rate=1000, timeout=100, now=lambda: 0.0)
    bud.charge("h", cost=3)
    assert bud.requests_made == 3
    bud.charge("h", cost=2)
    assert bud.requests_made == 5
    with pytest.raises(CapExceeded) as e:
        bud.charge("h", cost=1)
    assert e.value.reason == "budget_exhausted"


def test_charge_cost_rejects_overshoot_atomically():
    bud = Budget(request_cap=5, rate=1000, timeout=100, now=lambda: 0.0)
    with pytest.raises(CapExceeded):
        bud.charge("h", cost=6)          # would exceed cap
    assert bud.requests_made == 0        # nothing charged on rejection

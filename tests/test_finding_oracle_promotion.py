import pytest

from offensia.core import finding as fnd
from offensia.core.oracles import base


def _f():
    return fnd.new_finding("t", "x", status=fnd.SUSPECTED, evidence_refs=["e1"])


def test_confirmed_authz_high_promotes_to_validated_and_exploitable():
    v = base.confirmed("ok", "high", nc_used=True)
    f = fnd.promote_from_verdict(_f(), fnd.VALIDATED, "authorization", v)
    assert f.status == fnd.VALIDATED and f.oracle == "authorization"
    f2 = fnd.promote_from_verdict(f, fnd.EXPLOITABLE, "authorization", v)
    assert f2.status == fnd.EXPLOITABLE


def test_impact_needs_high_confidence_impact_oracle():
    v_med = base.confirmed("ok", "medium", nc_used=True)
    with pytest.raises(fnd.PromotionError):
        fnd.promote_from_verdict(_f(), fnd.CONFIRMED_IMPACT, "authorization", v_med)
    v_high = base.confirmed("ok", "high", nc_used=True)
    f = fnd.promote_from_verdict(_f(), fnd.CONFIRMED_IMPACT, "file_read", v_high)
    assert f.status == fnd.CONFIRMED_IMPACT


def test_unreproduced_verdict_cannot_promote():
    v = base.inconclusive("meh")
    with pytest.raises(fnd.PromotionError):
        fnd.promote_from_verdict(_f(), fnd.VALIDATED, "http_differential", v)


def test_exploitable_requires_negative_control_check():
    # a verdict without negative control cannot reach EXPLOITABLE
    v = base.confirmed("ok", "high", nc_used=False)
    with pytest.raises(fnd.PromotionError):
        fnd.promote_from_verdict(_f(), fnd.EXPLOITABLE, "oast", v)

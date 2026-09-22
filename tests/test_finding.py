import pytest

from offensia.core import finding as fnd


def test_cannot_create_in_gated_state():
    with pytest.raises(fnd.PromotionError):
        fnd.new_finding("example.com", "SQLi", status=fnd.CONFIRMED_IMPACT)


def test_promotion_requires_validation_checks():
    f = fnd.new_finding("example.com", "SQLi", status=fnd.SUSPECTED,
                        evidence_refs=["ev1"])
    with pytest.raises(fnd.PromotionError):
        fnd.promote(f, fnd.VALIDATED, checks_passed={"reproduction"})  # missing negative_control


def test_promotion_requires_evidence():
    f = fnd.new_finding("example.com", "SQLi", status=fnd.SUSPECTED)
    with pytest.raises(fnd.PromotionError):
        fnd.promote(f, fnd.VALIDATED, checks_passed={"reproduction", "negative_control"})


def test_successful_promotion_to_validated_and_confirmed():
    f = fnd.new_finding("example.com", "SQLi", status=fnd.SUSPECTED, evidence_refs=["ev1"])
    fnd.promote(f, fnd.VALIDATED, checks_passed={"reproduction", "negative_control"})
    assert f.status == fnd.VALIDATED
    fnd.promote(f, fnd.CONFIRMED_IMPACT,
                checks_passed={"reproduction", "negative_control", "impact_validation"})
    assert f.status == fnd.CONFIRMED_IMPACT


def test_persistence_roundtrip(tmp_path):
    f = fnd.new_finding("example.com", "XSS", status=fnd.SUSPECTED, evidence_refs=["e"])
    fnd.upsert(tmp_path, f)
    loaded = fnd.load(tmp_path)
    assert len(loaded) == 1 and loaded[0].title == "XSS"

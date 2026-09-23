import json

from offensia.core import finding as fnd


def test_new_fields_round_trip(tmp_path):
    f = fnd.new_finding("t", "IDOR on /orders", status=fnd.SUSPECTED,
                        evidence_refs=["e1"])
    f.oracle = "authorization"
    f.requires = ["auth.session:userA"]
    f.grants = ["read:orders/B"]
    f.cvss_vector = "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"
    fnd.upsert(tmp_path, f)
    back = {x.finding_id: x for x in fnd.load(tmp_path)}[f.finding_id]
    assert back.oracle == "authorization"
    assert back.requires == ["auth.session:userA"]
    assert back.grants == ["read:orders/B"]
    assert back.finding_version == 2


def test_loads_legacy_v1_findings_without_new_fields(tmp_path):
    legacy = [{
        "finding_id": "abc123", "target": "t", "title": "old", "status": "OBSERVATION",
        "severity": "unknown", "confidence": "low", "cwe": "", "evidence_refs": [],
        "validation_events": [], "checks_passed": [], "notes": "",
    }]
    (tmp_path / "findings.json").write_text(json.dumps(legacy), encoding="utf-8")
    items = fnd.load(tmp_path)
    assert items[0].oracle == ""            # default applied
    assert items[0].finding_version == 2    # default applied

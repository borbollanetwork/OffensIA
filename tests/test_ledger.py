import json
from offensia.core import ledger


def test_append_and_verify_chain(tmp_path):
    for i in range(4):
        ledger.append(tmp_path, {"kind": "exec", "summary": f"e{i}"})
    v = ledger.verify(tmp_path)
    assert v["ok"] is True and v["count"] == 4


def test_hashes_chain_links(tmp_path):
    a = ledger.append(tmp_path, {"kind": "x"})
    b = ledger.append(tmp_path, {"kind": "y"})
    assert b["previous_event_hash"] == a["event_hash"]


def test_tamper_breaks_chain(tmp_path):
    ledger.append(tmp_path, {"kind": "a", "summary": "one"})
    ledger.append(tmp_path, {"kind": "b", "summary": "two"})
    path = tmp_path / "ledger.jsonl"
    lines = path.read_text().splitlines()
    rec = json.loads(lines[0]); rec["summary"] = "TAMPERED"
    lines[0] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n")
    v = ledger.verify(tmp_path)
    assert v["ok"] is False and v["broken_at"] == 0

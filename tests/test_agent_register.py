import json
import pytest
from pathlib import Path
from offensia.core import agent_register as reg


def test_build_entry():
    e = reg.build_server_entry(Path("/x"), "python3")
    assert e["command"] == "python3" and e["args"] == ["-m", "offensia.core.server"]


def test_merge_fresh(tmp_path):
    cfg = tmp_path / "mcp.json"
    res = reg.merge_config(cfg, {"command": "p", "args": []})
    assert res["ok"] and "offensia" in json.loads(cfg.read_text())["mcpServers"]


def test_merge_preserves_and_backs_up(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    res = reg.merge_config(cfg, {"command": "p", "args": []})
    data = json.loads(cfg.read_text())
    assert "other" in data["mcpServers"] and "offensia" in data["mcpServers"]
    assert Path(res["backup"]).exists()


def test_malformed_config_aborts_and_preserves(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("{ not json ")
    with pytest.raises(reg.RegistrationAbort):
        reg.merge_config(cfg, {"command": "p", "args": []})
    assert cfg.read_text() == "{ not json "  # untouched


def test_restore_backup(tmp_path):
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    reg.merge_config(cfg, {"command": "p", "args": []})
    assert reg.restore_backup(cfg) is True
    assert "offensia" not in json.loads(cfg.read_text())["mcpServers"]

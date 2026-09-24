import dataclasses

from offensia.core import server, state
from offensia.core.config import get_paths


def test_list_recognizes_checkpoint_only_dir(tmp_path):
    base = str(tmp_path)
    adir = get_paths(base).assessment_dir("mcp-eng")
    (adir / "executor-checkpoint.json").write_text("{}")
    assert "mcp-eng" in state.list_assessments(base=base)


def test_tool_use_bootstraps_state(tmp_path, monkeypatch):
    monkeypatch.setattr(server.scope_mod, "in_scope", lambda *a, **k: True)
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    monkeypatch.setattr(server, "_run_via_registry",
                        lambda job, budget=None: {"ok": True, "raw": "x"})
    monkeypatch.setattr(server, "PATHS", dataclasses.replace(server.PATHS, base=tmp_path))
    server.offensia_port_scan("scanme.example", assessment="boot")
    # state.json now exists for the assessment used purely through MCP
    assert (tmp_path / "boot" / "state.json").exists()

import importlib

import pytest


@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFENSIA_BASE", str(tmp_path))
    import offensia.core.config as cfg
    importlib.reload(cfg)
    import offensia.core.cli as c
    importlib.reload(c)
    return c


def test_scope_add_requires_auth(cli):
    assert cli.main(["scope", "add", "example.com"]) == 2


def test_scope_add_list_verify(cli, capsys):
    assert cli.main(["scope", "add", "example.com", "--auth", "LAB"]) == 0
    assert cli.main(["scope", "list"]) == 0
    assert "example.com" in capsys.readouterr().out
    assert cli.main(["scope", "verify", "example.com"]) == 0
    assert cli.main(["scope", "verify", "evil.com"]) == 1


def test_assessment_and_resume(cli, capsys):
    assert cli.main(["assessment", "create", "eng1"]) == 0
    assert cli.main(["resume", "eng1"]) == 0
    assert "eng1" in capsys.readouterr().out


def test_report_generates(cli, capsys):
    cli.main(["assessment", "create", "eng1"])
    assert cli.main(["report", "executive", "eng1"]) == 0
    out = capsys.readouterr().out
    assert "Executive Report" in out and "executed test coverage" in out


def test_doctor_runs(cli):
    rc = cli.main(["doctor"])
    assert rc in (0, 1)  # engines may be down; must not crash

from offensia.core.validation import Check, run_checks


def test_reproduction_and_negative_control_pass():
    def runner(target, cmd):
        # attack input reproduces (ok=True); control input does not (ok=False)
        return {"ok": "attack" in cmd, "raw": cmd}
    checks = [
        Check("reproduction", "attack payload", expect="success"),
        Check("negative_control", "benign control", expect="failure"),
    ]
    rep = run_checks("example.com", checks, runner)
    assert rep.checks_passed == {"reproduction", "negative_control"}
    assert rep.verdict == "validated"


def test_failed_reproduction_is_false_positive():
    rep = run_checks("example.com",
                     [Check("reproduction", "x", expect="success")],
                     runner=lambda t, c: {"ok": False, "raw": ""})
    assert rep.verdict == "false_positive"


def test_unknown_check_never_counts():
    rep = run_checks("example.com",
                     [Check("magic", "x")],
                     runner=lambda t, c: {"ok": True})
    assert "magic" in rep.checks_failed and not rep.checks_passed

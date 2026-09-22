"""OffensIA CLI. Coherent operational surface over the core planes."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from offensia.core.config import get_paths, settings
from offensia.core import scope as scope_mod
from offensia.core import ledger as ledger_mod
from offensia.core import coverage as cov
from offensia.core import finding as fnd
from offensia.core import state as state_mod
from offensia.core import agent_register as reg
from offensia.reporting import generator as report_gen


# --------------------------------------------------------------------- commands
def cmd_init(args) -> int:
    paths = get_paths()
    paths.engagements_dir.mkdir(parents=True, exist_ok=True)
    if not paths.scope_file.exists():
        paths.scope_file.write_text(
            "# OffensIA scope — default deny. Add targets only with written "
            "authorization.\n", encoding="utf-8")
    print(f"initialized OffensIA base at {paths.base}")
    return 0


def cmd_doctor(args) -> int:
    paths = get_paths()
    s = settings()
    checks = []
    checks.append(("python", sys.version.split()[0], sys.version_info >= (3, 11)))
    checks.append(("scope_file", str(paths.scope_file), paths.scope_file.exists()))
    checks.append(("engagements_dir", str(paths.engagements_dir),
                   paths.engagements_dir.exists()))
    try:
        import mcp  # noqa: F401
        checks.append(("mcp_package", "installed", True))
    except Exception:  # noqa: BLE001
        checks.append(("mcp_package", "MISSING (pip install mcp)", False))
    checks.append(("execution_engine", s["execution_url"], _http_ok(s["execution_url"])))
    checks.append(("recon_engine", s["recon_url"], _http_ok(s["recon_url"])))
    checks.append(("engines_manifest", str(paths.engines_manifest),
                   paths.engines_manifest.exists()))
    failed = 0
    for name, detail, ok in checks:
        mark = "OK " if ok else "!! "
        if not ok:
            failed += 1
        print(f"[{mark}] {name}: {detail}")
    if failed:
        print(f"\n{failed} check(s) need attention. See docs/installation.md.")
    return 0 if failed == 0 else 1


def _http_ok(url: str) -> bool:
    try:
        import requests
        return requests.get(f"{url}/health", timeout=3).ok
    except Exception:  # noqa: BLE001
        return False


def cmd_status(args) -> int:
    paths = get_paths()
    print(f"base: {paths.base}")
    print(f"scope entries: {len(scope_mod.load_scope(paths.scope_file))}")
    print(f"assessments: {', '.join(state_mod.list_assessments()) or 'none'}")
    return 0


def cmd_scope_add(args) -> int:
    if not args.auth:
        print("error: --auth <authorization_ref> is required", file=sys.stderr)
        return 2
    scope_mod.add_entry(args.target, args.auth, get_paths().scope_file, args.engagement or "")
    print(f"authorized: {args.target}")
    return 0


def cmd_scope_remove(args) -> int:
    ok = scope_mod.remove_entry(args.target, get_paths().scope_file)
    print("removed" if ok else "not found")
    return 0 if ok else 1


def cmd_scope_list(args) -> int:
    for e in scope_mod.load_scope(get_paths().scope_file):
        print(e)
    return 0


def cmd_scope_verify(args) -> int:
    ok = scope_mod.in_scope(args.target, get_paths().scope_file)
    print("IN SCOPE" if ok else "OUT OF SCOPE")
    return 0 if ok else 1


def cmd_assessment_create(args) -> int:
    state_mod.create(args.assessment, args.engagement or "")
    print(f"created assessment {args.assessment}")
    return 0


def cmd_assessment_list(args) -> int:
    for a in state_mod.list_assessments():
        print(a)
    return 0


def cmd_resume(args) -> int:
    data = state_mod.load(args.assessment)
    if not data:
        print("no such assessment", file=sys.stderr)
        return 1
    paths = get_paths()
    adir = paths.assessment_dir(args.assessment)
    print(json.dumps({
        "assessment_id": data["assessment_id"],
        "created": data.get("created"),
        "scope_entries": len(scope_mod.load_scope(paths.scope_file)),
        "coverage": cov.summary(adir),
        "findings": len(fnd.load(adir)),
        "ledger": ledger_mod.verify(adir),
    }, indent=2))
    return 0


def cmd_coverage_show(args) -> int:
    print(json.dumps(cov.summary(get_paths().assessment_dir(args.assessment)), indent=2))
    return 0


def cmd_ledger_verify(args) -> int:
    res = ledger_mod.verify(get_paths().assessment_dir(args.assessment))
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


def cmd_finding_list(args) -> int:
    for f in fnd.load(get_paths().assessment_dir(args.assessment)):
        print(f"{f.finding_id} [{f.status}] {f.severity} — {f.title}")
    return 0


def cmd_report(args) -> int:
    adir = get_paths().assessment_dir(args.assessment)
    gen = {"executive": report_gen.executive, "technical": report_gen.technical,
           "evidence": report_gen.evidence_report, "coverage": report_gen.coverage_report}
    if args.kind not in gen:
        print("unknown report kind", file=sys.stderr)
        return 2
    print(gen[args.kind](adir, args.assessment))
    return 0


def cmd_agent_register(args) -> int:
    paths = get_paths()
    entry = reg.build_server_entry(paths.base, sys.executable)
    try:
        res = reg.merge_config(Path(args.agent_config), entry)
    except reg.RegistrationAbort as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 3
    print(f"registered into {args.agent_config}"
          + (f" (backup: {res['backup']})" if res.get("backup") else ""))
    return 0 if res["ok"] else 1


def cmd_agent_unregister(args) -> int:
    ok = reg.restore_backup(Path(args.agent_config))
    print("restored previous config" if ok else "no backup found")
    return 0 if ok else 1


def cmd_engines_status(args) -> int:
    paths = get_paths()
    if not paths.engines_manifest.exists():
        print("no deps/engines.yaml manifest")
        return 1
    import yaml
    data = yaml.safe_load(paths.engines_manifest.read_text(encoding="utf-8")) or {}
    for eng in data.get("engines", []):
        present = (paths.deps_dir / eng.get("name", "")).exists()
        print(f"{eng.get('name')}: pinned={eng.get('commit', eng.get('version','?'))} "
              f"provisioned={'yes' if present else 'no'}")
    return 0


def cmd_knowledge_index(args) -> int:
    from offensia.knowledge import engine as ke
    paths = get_paths()
    out = paths.base / "knowledge_index.json"
    idx = ke.index(Path(args.path), out)
    print(f"indexed {idx['count']} documents -> {out}")
    return 0


# ------------------------------------------------------------------------ parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="offensia",
                                description="OffensIA — authorized offensive-security orchestration")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("status").set_defaults(func=cmd_status)

    sp = sub.add_parser("scope"); ss = sp.add_subparsers(dest="scmd", required=True)
    a = ss.add_parser("add"); a.add_argument("target"); a.add_argument("--auth", default="")
    a.add_argument("--engagement", default=""); a.set_defaults(func=cmd_scope_add)
    rm = ss.add_parser("remove"); rm.add_argument("target"); rm.set_defaults(func=cmd_scope_remove)
    ss.add_parser("list").set_defaults(func=cmd_scope_list)
    sv = ss.add_parser("verify"); sv.add_argument("target"); sv.set_defaults(func=cmd_scope_verify)

    asp = sub.add_parser("assessment"); asu = asp.add_subparsers(dest="acmd", required=True)
    ac = asu.add_parser("create"); ac.add_argument("assessment")
    ac.add_argument("--engagement", default=""); ac.set_defaults(func=cmd_assessment_create)
    asu.add_parser("list").set_defaults(func=cmd_assessment_list)

    rs = sub.add_parser("resume"); rs.add_argument("assessment"); rs.set_defaults(func=cmd_resume)

    cvp = sub.add_parser("coverage"); cvs = cvp.add_subparsers(dest="ccmd", required=True)
    cvshow = cvs.add_parser("show"); cvshow.add_argument("assessment", nargs="?", default="default")
    cvshow.set_defaults(func=cmd_coverage_show)

    lp = sub.add_parser("ledger"); ls = lp.add_subparsers(dest="lcmd", required=True)
    lv = ls.add_parser("verify"); lv.add_argument("assessment", nargs="?", default="default")
    lv.set_defaults(func=cmd_ledger_verify)

    fp = sub.add_parser("finding"); fs = fp.add_subparsers(dest="fcmd", required=True)
    fl = fs.add_parser("list"); fl.add_argument("assessment", nargs="?", default="default")
    fl.set_defaults(func=cmd_finding_list)

    rp = sub.add_parser("report"); rp.add_argument("kind")
    rp.add_argument("assessment", nargs="?", default="default"); rp.set_defaults(func=cmd_report)

    ag = sub.add_parser("agent"); ags = ag.add_subparsers(dest="agcmd", required=True)
    agr = ags.add_parser("register"); agr.add_argument("--agent-config", dest="agent_config", required=True)
    agr.set_defaults(func=cmd_agent_register)
    agu = ags.add_parser("unregister"); agu.add_argument("--agent-config", dest="agent_config", required=True)
    agu.set_defaults(func=cmd_agent_unregister)

    ep = sub.add_parser("engines"); eps = ep.add_subparsers(dest="ecmd", required=True)
    eps.add_parser("status").set_defaults(func=cmd_engines_status)

    kp = sub.add_parser("knowledge"); kps = kp.add_subparsers(dest="kcmd", required=True)
    ki = kps.add_parser("index"); ki.add_argument("path"); ki.set_defaults(func=cmd_knowledge_index)

    return p


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

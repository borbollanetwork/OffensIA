#!/usr/bin/env bash
# OffensIA one-command bootstrap. Idempotent, non-destructive, local-bind.
#
#   ./install.sh [kimi|glm] [/path/to/agent/mcp.json]
#
# Steps: preflight -> venv -> deps -> engine provisioning -> MCP registration
#        -> health -> self-test -> ready.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
AGENT="${1:-kimi}"
AGENT_CONFIG="${2:-}"
export OFFENSIA_BASE="$BASE"

echo "[*] OffensIA bootstrap (agent=$AGENT, base=$BASE)"

# 1. Preflight
for bin in python3 git; do
  command -v "$bin" >/dev/null || { echo "[FAIL] missing prerequisite: $bin"; exit 1; }
done
PYV="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
python3 -c 'import sys;exit(0 if sys.version_info>=(3,11) else 1)' \
  || { echo "[FAIL] Python >=3.11 required (found $PYV)"; exit 1; }
command -v docker >/dev/null || echo "[WARN] docker not found — recon engine will be unavailable"

# 2. Virtualenv + package (idempotent)
[ -d "$BASE/.venv" ] || python3 -m venv "$BASE/.venv"
# shellcheck disable=SC1091
source "$BASE/.venv/bin/activate"
pip install -q --disable-pip-version-check -e "$BASE"
export PYTHONPATH="$BASE"

# 3. Provision engines from the pinned manifest (never vendored into source)
python3 - <<'PY'
import os, subprocess, sys
from pathlib import Path
import yaml
base = Path(os.environ["OFFENSIA_BASE"])
man = base / "deps" / "engines.yaml"
if not man.exists():
    print("[WARN] deps/engines.yaml missing — engines not provisioned"); sys.exit(0)
data = yaml.safe_load(man.read_text()) or {}
for eng in data.get("engines", []):
    name, repo = eng["name"], eng["repository"]
    branch = eng.get("ref") or "main"
    commit = eng.get("commit") or ""
    dest = base / "deps" / name
    if not (dest / ".git").exists():
        print(f"[*] {name}: cloning {repo}@{branch}")
        if subprocess.call(["git","clone","--branch",branch,repo,str(dest)]) != 0:
            subprocess.call(["git","clone",repo,str(dest)])
    if commit:
        print(f"[*] {name}: checking out pinned {commit[:12]}")
        subprocess.call(["git","-C",str(dest),"fetch","-q","origin",commit])
        if subprocess.call(["git","-C",str(dest),"checkout","-q",commit]) != 0:
            print(f"[WARN] {name}: could not checkout pinned commit; on {branch} HEAD")
    else:
        print(f"[WARN] {name}: unpinned (set commit in engines.yaml for production)")
PY

# 4. Configuration (scope ships empty; real targets stay out of git)
if [ ! -f "$BASE/scope.allow" ]; then
  cp "$BASE/scope.allow.example" "$BASE/scope.allow" 2>/dev/null \
    || printf '# OffensIA scope — default deny.\n' > "$BASE/scope.allow"
fi
python3 -m offensia.core.cli init

# 5. Detect agent config path (explicit override wins)
if [ -z "$AGENT_CONFIG" ]; then
  case "$AGENT" in
    kimi) AGENT_CONFIG="${HOME}/.config/kimi/mcp.json" ;;
    glm)  AGENT_CONFIG="${HOME}/.config/glm/mcp.json" ;;
    *) echo "[FAIL] unknown agent '$AGENT' (use kimi|glm or pass an explicit path)"; exit 1 ;;
  esac
fi

# 6. Register MCP (atomic, backup, abort-on-malformed handled in code)
if ! python3 -m offensia.core.cli agent register --agent-config "$AGENT_CONFIG"; then
  echo "[WARN] agent registration did not complete — see message above."
fi

# 7. Health + self-test
python3 -m offensia.core.cli doctor || true

echo
echo "[*] Ready. Start your agent ($AGENT) — OffensIA tools are registered."
echo "[*] Authorize a target before testing:"
echo "      ./offensia scope add <target> --auth <authorization_ref>"

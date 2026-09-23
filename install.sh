#!/usr/bin/env bash
# OffensIA one-command bootstrap. Idempotent, non-destructive, local-bind.
#
#   ./install.sh [kimi|glm] [/path/to/agent/mcp.json]
#
# Steps: preflight -> venv -> deps -> engine provisioning -> engine stack up
#        -> MCP registration -> health -> self-test -> ready.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
AGENT="${1:-kimi}"
AGENT_CONFIG="${2:-}"
export OFFENSIA_BASE="$BASE"

# ---------------------------------------------------------------- colors / ui
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
  C_BLUE=$'\033[34m'; C_CYAN=$'\033[36m'; C_MAGENTA=$'\033[35m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""
  C_BLUE=""; C_CYAN=""; C_MAGENTA=""
fi

STEP=0
step()  { STEP=$((STEP+1)); printf "\n${C_BOLD}${C_BLUE}▸ [%d] %s${C_RESET}\n" "$STEP" "$1"; }
ok()    { printf "  ${C_GREEN}✓${C_RESET} %s\n" "$1"; }
warn()  { printf "  ${C_YELLOW}⚠${C_RESET} %s\n" "$1"; }
err()   { printf "  ${C_RED}✗ %s${C_RESET}\n" "$1"; }
info()  { printf "  ${C_DIM}%s${C_RESET}\n" "$1"; }

banner() {
  printf "${C_BOLD}${C_MAGENTA}"
  cat <<'BANNER'
  ___   __  __             ___   _
 / _ \ / _|/ _|___ _ _  __|_ _| /_\
| (_) |  _|  _/ -_) ' \(_-<| | / _ \
 \___/|_| |_| \___|_||_/__/___/_/ \_\
BANNER
  printf "${C_RESET}${C_DIM}  Evidence-driven offensive-security orchestration${C_RESET}\n"
  printf "${C_DIM}  agent=${C_RESET}${C_CYAN}%s${C_RESET}${C_DIM}  base=${C_RESET}${C_CYAN}%s${C_RESET}\n" "$AGENT" "$BASE"
}

banner

# --------------------------------------------------------------- 1. preflight
step "Preflight"
for bin in python3 git; do
  if command -v "$bin" >/dev/null; then ok "found $bin"; else err "missing prerequisite: $bin"; exit 1; fi
done
PYV="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
if python3 -c 'import sys;exit(0 if sys.version_info>=(3,11) else 1)'; then
  ok "Python $PYV (>=3.11)"
else
  err "Python >=3.11 required (found $PYV)"; exit 1
fi
if command -v docker >/dev/null; then ok "docker available"; else warn "docker not found — Docker-based engines (recon) will be skipped"; fi

# ---------------------------------------------------------- 2. venv + package
step "Virtualenv & package"
[ -d "$BASE/.venv" ] || python3 -m venv "$BASE/.venv"
# shellcheck disable=SC1091
source "$BASE/.venv/bin/activate"
pip install -q --disable-pip-version-check -e "$BASE"
export PYTHONPATH="$BASE"
ok "installed offensia (editable) into .venv"

# ------------------------------------------------- 3. provision engines (pinned)
step "Provision engines from pinned manifest"
python3 - <<'PY'
import os, subprocess, sys
from pathlib import Path
import yaml
base = Path(os.environ["OFFENSIA_BASE"])
man = base / "deps" / "engines.yaml"
G="\033[32m"; Y="\033[33m"; D="\033[2m"; R="\033[0m"
def line(sym, col, msg): print(f"  {col}{sym}{R} {msg}")
if not man.exists():
    line("⚠", Y, "deps/engines.yaml missing — engines not provisioned"); sys.exit(0)
data = yaml.safe_load(man.read_text()) or {}
for eng in data.get("engines", []):
    name, repo = eng["name"], eng["repository"]
    branch = eng.get("ref") or "main"; commit = eng.get("commit") or ""
    dest = base / "deps" / name
    if not (dest / ".git").exists():
        line("·", D, f"cloning {name} <- {repo}@{branch}")
        if subprocess.call(["git","clone","--branch",branch,repo,str(dest)]) != 0:
            subprocess.call(["git","clone",repo,str(dest)])
    if commit:
        subprocess.call(["git","-C",str(dest),"fetch","-q","origin",commit])
        rc = subprocess.call(["git","-C",str(dest),"checkout","-q",commit])
        line("✓", G, f"{name}: pinned {commit[:12]}") if rc==0 else line("⚠", Y, f"{name}: on {branch} HEAD (pin checkout failed)")
    else:
        line("⚠", Y, f"{name}: unpinned (set commit in engines.yaml for production)")
PY

# ----------------------------------------------------- 4. bring the stack up
step "Start engine stack"
if command -v docker >/dev/null; then
  python3 -m offensia.core.cli engines up --wait 40 | sed 's/^/  /' || warn "some engines did not come up (see above)"
else
  warn "docker not found — skipping Docker engines. The reference engine can stand in:"
  info "python -m offensia.engines.reference_engine"
fi

# ------------------------------------------------------- 5. configuration
step "Configuration"
if [ ! -f "$BASE/scope.allow" ]; then
  cp "$BASE/scope.allow.example" "$BASE/scope.allow" 2>/dev/null \
    || printf '# OffensIA scope — default deny.\n' > "$BASE/scope.allow"
  ok "created scope.allow (default-deny)"
else
  ok "scope.allow present"
fi
python3 -m offensia.core.cli init | sed 's/^/  /'

# --------------------------------------------------- 6. register MCP in agent
step "Register OffensIA MCP into agent config"
if [ -z "$AGENT_CONFIG" ]; then
  case "$AGENT" in
    kimi) AGENT_CONFIG="${HOME}/.config/kimi/mcp.json" ;;
    glm)  AGENT_CONFIG="${HOME}/.config/glm/mcp.json" ;;
    *) err "unknown agent '$AGENT' (use kimi|glm or pass an explicit path)"; exit 1 ;;
  esac
fi
if python3 -m offensia.core.cli agent register --agent-config "$AGENT_CONFIG" | sed 's/^/  /'; then
  ok "registered ($AGENT_CONFIG)"
else
  warn "agent registration did not complete — see message above."
fi

# ------------------------------------------------------------- 7. self-test
step "Health & self-test"
python3 -m offensia.core.cli doctor | sed 's/^/  /' || true

printf "\n${C_BOLD}${C_GREEN}✔ OffensIA ready.${C_RESET} Start your agent (${C_CYAN}%s${C_RESET}) — the offensia_* tools are registered.\n" "$AGENT"
printf "${C_DIM}  Authorize a target before testing:${C_RESET}\n"
printf "    ${C_CYAN}./offensia scope add <target> --auth <authorization_ref>${C_RESET}\n"

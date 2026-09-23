#!/usr/bin/env bash
# Start OffensIA — bring the engine stack up and report health.
#
#   ./start.sh                start engines from deps/engines.yaml (Docker/pip)
#   ./start.sh --reference    force the dependency-free reference engine instead
#
# Idempotent: safe to run repeatedly. Stop everything with ./stop.sh.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
export OFFENSIA_BASE="$BASE"
MODE="${1:-auto}"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_GREEN=$'\033[32m'; C_CYAN=$'\033[36m'; C_DIM=$'\033[2m'
else C_RESET=""; C_BOLD=""; C_GREEN=""; C_CYAN=""; C_DIM=""; fi

if [ -x "$BASE/.venv/bin/python" ]; then PY="$BASE/.venv/bin/python"; else PY="python3"; fi

health() { "$PY" - "$1" <<'PY' 2>/dev/null
import sys, urllib.request
try:
    urllib.request.urlopen(sys.argv[1], timeout=3); print("up")
except Exception:
    print("down")
PY
}

# Launch the reference engine fully detached so its PID is the real process
# (setsid preferred; nohup+setpgid fallback). Records the PID for ./stop.sh.
start_reference() {
  if [ -f "$BASE/.reference-engine.pid" ] && kill -0 "$(cat "$BASE/.reference-engine.pid" 2>/dev/null)" 2>/dev/null; then
    printf "  ${C_GREEN}✓${C_RESET} reference engine already running (pid $(cat "$BASE/.reference-engine.pid"))\n"
    return 0
  fi
  if command -v setsid >/dev/null; then
    setsid "$PY" -m offensia.engines.reference_engine >"$BASE/reference-engine.log" 2>&1 &
  else
    nohup "$PY" -m offensia.engines.reference_engine >"$BASE/reference-engine.log" 2>&1 &
  fi
  echo $! > "$BASE/.reference-engine.pid"
  printf "  ${C_GREEN}✓${C_RESET} reference engine started (pid $(cat "$BASE/.reference-engine.pid"))\n"
}

printf "${C_BOLD}${C_CYAN}▸ Starting OffensIA${C_RESET}\n"

if [ "$MODE" = "--reference" ]; then
  start_reference
else
  "$PY" -m offensia.core.cli engines up --wait 40 | sed 's/^/  /' || true
  # Fallback: if no engine answers on either port, stand up the reference engine.
  if [ "$(health http://127.0.0.1:8888/health)" = "down" ] && \
     [ "$(health http://127.0.0.1:11235/health)" = "down" ]; then
    printf "  ${C_DIM}no manifest engine reachable — starting reference engine as fallback${C_RESET}\n"
    start_reference
  fi
fi

sleep 1
"$PY" -m offensia.core.cli doctor | sed 's/^/  /' || true
printf "\n${C_BOLD}${C_GREEN}✔ OffensIA is up.${C_RESET} Stop it after use with: ${C_CYAN}./stop.sh${C_RESET}\n"

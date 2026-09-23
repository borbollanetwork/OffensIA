#!/usr/bin/env bash
# Stop OffensIA — shut down the engine stack and the reference engine.
#
#   ./stop.sh
#
# Stops Docker engines (docker compose down), pip engines (by pidfile), and the
# reference engine. Safe to run even if nothing is running.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
export OFFENSIA_BASE="$BASE"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_GREEN=$'\033[32m'; C_CYAN=$'\033[36m'
else C_RESET=""; C_BOLD=""; C_GREEN=""; C_CYAN=""; fi

if [ -x "$BASE/.venv/bin/python" ]; then PY="$BASE/.venv/bin/python"; else PY="python3"; fi

printf "${C_BOLD}${C_CYAN}▸ Stopping OffensIA${C_RESET}\n"

# 1. Manifest engines (docker compose down / pip pidfiles).
"$PY" -m offensia.core.cli engines down | sed 's/^/  /' || true

# 2. Reference engine, via its own pidfile (no pkill self-match).
PIDF="$BASE/.reference-engine.pid"
if [ -f "$PIDF" ]; then
  PID="$(cat "$PIDF" 2>/dev/null || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    printf "  ${C_GREEN}✓${C_RESET} reference engine stopped (pid %s)\n" "$PID"
  fi
  rm -f "$PIDF"
else
  printf "  reference engine not running (no pidfile)\n"
fi

# 3. Safety net: if the reference-engine ports are still held, free them.
if command -v fuser >/dev/null; then
  for port in 8888 11235; do
    if fuser "${port}/tcp" >/dev/null 2>&1; then
      fuser -k "${port}/tcp" >/dev/null 2>&1 || true
      printf "  ${C_GREEN}✓${C_RESET} freed port %s\n" "$port"
    fi
  done
fi

printf "\n${C_BOLD}${C_GREEN}✔ OffensIA stopped.${C_RESET} Start again with: ${C_CYAN}./start.sh${C_RESET}\n"

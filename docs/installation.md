# Installation

## Requirements
- Python >= 3.11
- git
- Docker (for the recon engine; optional but recommended)
- Linux (Ubuntu / Debian / Kali tested). Not coupled to Kali.

## One command
```bash
git clone <your-private-repo> OffensIA && cd OffensIA
./install.sh kimi        # or: ./install.sh glm
# optional explicit agent config path:
./install.sh kimi /path/to/agent/mcp.json
```

The installer is idempotent: preflight → venv → `pip install -e .` → provision
engines from `deps/engines.yaml` → copy `scope.allow.example` to `scope.allow` if
missing → register the OffensIA MCP server into your agent config (atomic, backup,
abort-on-malformed) → `offensia doctor`.

## Verify
```bash
offensia doctor      # actionable diagnostics, non-zero exit if something needs attention
python -m pytest -q  # run the test suite
```

## Uninstall / rollback
```bash
offensia agent unregister --agent-config /path/to/agent/mcp.json   # restores backup
```

## Engine stack

The installer starts Docker-based engines automatically when Docker is present.
Manage them anytime:
```bash
offensia engines up      # start engines from deps/engines.yaml (Docker + pip)
offensia engines status  # show pinned commit and provisioned state
offensia engines down    # stop them
```
Without Docker, the dependency-free reference engine can stand in:
```bash
python -m offensia.engines.reference_engine
```

## Docker auto-install

If Docker is not found, `install.sh` installs Docker Engine using Docker's official convenience script (https://get.docker.com), enables the service, and adds your user to the `docker` group (effective after the next login). Requires root or `sudo`. Opt out with `OFFENSIA_SKIP_DOCKER=1 ./install.sh`.

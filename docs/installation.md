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

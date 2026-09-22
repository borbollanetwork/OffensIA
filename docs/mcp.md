# MCP Interface

The OffensIA MCP server (`offensia/core/server.py`) exposes neutral tools. Every
active tool runs the pipeline: scope → capability → adapter → bounded/normalized
result → evidence store → hash-chained ledger. Failures return structured errors;
the server does not crash on tool/network errors.

## Tools
- `offensia_scope_list`, `offensia_scope_add`
- `offensia_recon_crawl` (web.content_extract; returns fenced UNTRUSTED data)
- `offensia_port_scan` (network.port_scan)
- `offensia_exec` (generic.command)
- `offensia_finding_create` (non-confirming states, anchored to evidence)
- `offensia_validate_finding` (code-enforced promotion)
- `offensia_coverage_status`, `offensia_coverage_set`
- `offensia_evidence_get`, `offensia_ledger_verify`, `offensia_report_generate`

Run standalone: `python -m offensia.core.server` (registered automatically by the
installer into your agent config).

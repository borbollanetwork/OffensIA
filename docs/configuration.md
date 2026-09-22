# Configuration

All configuration is environment-driven; see `.env.example`.

| Variable | Meaning | Default |
|---|---|---|
| OFFENSIA_BASE | Repo/base dir | repo root |
| OFFENSIA_EXECUTION_URL | Execution engine base URL | http://127.0.0.1:8888 |
| OFFENSIA_RECON_URL | Recon engine base URL | http://127.0.0.1:11235 |
| OFFENSIA_HTTP_TIMEOUT | Adapter HTTP timeout (s) | 300 |
| OFFENSIA_HTTP_MAX_BYTES | Max bounded output bytes | 524288 |
| OFFENSIA_PROVIDER | Active provider (kimi/glm) | kimi |
| OFFENSIA_MODEL_ID / KIMI_MODEL_ID / GLM_MODEL_ID | Model id (configurable, never invented) | unset |
| MOONSHOT_API_KEY / ZHIPU_API_KEY | Provider keys | unset |

Local services bind to localhost by default. Never commit real keys.

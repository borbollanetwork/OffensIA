# OffensIA Doctrine — Mobile Attack Surface

Applies to Android and iOS apps and the backends they talk to. Mobile testing is
three surfaces at once: the client binary, its runtime behavior on device, and the
server it trusts. Never confirm a client-side "finding" without checking whether
the server actually enforces the control.

## What to look for
- **Storage**: secrets, tokens, PII in shared prefs / plists / SQLite / keychain /
  keystore; world-readable files; cached sensitive responses.
- **Transport**: missing TLS, disabled validation, no certificate pinning, cleartext
  fallback.
- **Auth/session**: token binding, refresh handling, biometric bypass, deep-link and
  URL-scheme auth flows, OAuth redirect handling in WebViews.
- **IPC**: exported Android components (activities/services/receivers/providers),
  intent handling, iOS URL schemes and universal links.
- **WebView**: `addJavascriptInterface`, file access, mixed content, JS bridge abuse.
- **Client-side trust**: authorization or pricing decided on the client; feature
  flags; jailbreak/root and anti-tamper that only gate the UI.
- **Native libs**: memory-unsafe code, exported JNI, bundled keys.

## When it applies / preconditions
- Static findings (secrets, exported components) require the app package (APK/IPA)
  or source. Runtime findings require an instrumented device/emulator with the app
  installed and, where relevant, a proxy in path.
- A backend-correlation test requires the mobile request captured plus the ability
  to replay it with an altered role/object/parameter.

## Evidence required
- Storage: the file path + the extracted secret/value, and proof it is used.
- Client-side control bypass: the modified request AND the server's accepting
  response, plus a negative control showing the intended behavior.
- Exported IPC: the component manifest entry + a crafted intent/scheme call and its
  observed effect.

## Refuting false positives
A hardcoded string that looks like a key is INFORMATIONAL until shown to
authenticate something. A disabled root check is HARDENING unless it gates a real
security boundary. Client-side "vulnerabilities" that the server independently
enforces are FALSE_POSITIVE — always test the server.

## Chaining
Leaked mobile token → API access (see `api.md`) → BOLA across tenants. Record each
hop in the attack graph with evidence.

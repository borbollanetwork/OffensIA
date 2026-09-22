# Scope

Default-deny. Nothing is tested unless authorized in `scope.allow`.

Forms: exact host, `*.domain` glob, CIDR, IP, and `!pattern` exclusions (which win
over any allow). Targets are normalized (scheme, credentials, port, path, case,
bracketed IPv6) before matching.

```bash
offensia scope add app.authorized.example --auth CONTRACT-2026-001 --engagement ENG-42
offensia scope list
offensia scope verify app.authorized.example
offensia scope remove app.authorized.example
```

`--auth` is mandatory: it records the written authorization reference for the
target. Out-of-scope attempts are refused and recorded in the ledger.

# Coverage

Coverage is persisted state, not a checklist. States: TESTED, PARTIALLY_TESTED,
NOT_TESTED, BLOCKED, NOT_APPLICABLE, UNKNOWN.

Discovered technologies activate methodology families automatically (e.g. GraphQL →
`web.graphql`, OAuth → `web.oauth_oidc`, Kubernetes → `cloud.kubernetes`).

```bash
offensia coverage show <assessment>
```

Reports show untested and blocked areas as clearly as tested ones. OffensIA never
claims a target "has no vulnerabilities" — only "no vulnerability identified within
the executed coverage."

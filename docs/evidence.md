# Evidence

Raw artifacts live in the content-addressed evidence store
(`engagements/<assessment>/artifacts/<sha256>.bin`); the ledger and findings hold
references, not the bytes. The LLM is never the authoritative evidence store.

The ledger (`engagements/<assessment>/ledger.jsonl`) is append-only and
hash-chained: each event carries `previous_event_hash` and `event_hash`. Tampering
with any historical record breaks the chain.

```bash
offensia ledger verify <assessment>
```

Every confirmed finding resolves back: finding → validation events → tool events →
raw artifacts.

# Knowledge Engine

Consumes authorized local knowledge (Markdown/JSON/YAML/TXT/HTML) and retrieves
selectively — it never dumps the whole base into model context.

Pipeline: discover → classify → index → selective retrieve. When nothing relevant
matches, retrieval returns `KNOWLEDGE_GAP` rather than fabricating methodology.

```bash
offensia knowledge index ./doctrine    # builds knowledge_index.json
```

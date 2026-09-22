"""Knowledge Engine (Control Plane).

Consumes authorized local knowledge sources and retrieves *selectively* — never
dumping the whole base into model context. Pipeline: discover -> classify ->
index -> retrieve. When nothing relevant exists it returns KNOWLEDGE_GAP rather
than fabricating methodology.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

TEXT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml", ".html"}
DOMAIN_HINTS = ("web", "api", "mobile", "internal", "ad", "cloud", "code",
                "research", "container", "kubernetes")


def _classify(path: Path) -> dict:
    parts = [p.lower() for p in path.parts]
    domain = next((d for d in DOMAIN_HINTS if d in parts), "")
    return {"kind": path.suffix.lstrip(".") or "txt", "domain": domain}


def _title(path: Path) -> str:
    if path.suffix.lower() == ".md":
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#"):
                return line.lstrip("#").strip()
    return path.stem


# Cap how much body text feeds the index, so large docs don't dominate.
_CONTENT_TAG_BYTES = 4000
_STOPWORDS = {"the", "and", "for", "with", "that", "this", "not", "are", "its",
              "into", "when", "what", "from", "only", "each", "over", "than",
              "must", "never", "which", "where", "requires", "evidence"}


def _tags(path: Path, title: str = "", content: str = "") -> list[str]:
    text = " ".join([str(path), title, content]).lower()
    tokens = re.split(r"[^a-z0-9]+", text)
    return sorted({t for t in tokens if len(t) >= 3 and t not in _STOPWORDS})


def index(knowledge_dir: Path, out_file: Path | None = None) -> dict:
    kd = Path(knowledge_dir)
    docs = []
    if kd.exists():
        for path in kd.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_EXTS:
                meta = _classify(path)
                title = _title(path)
                content = path.read_text(encoding="utf-8", errors="replace")[:_CONTENT_TAG_BYTES]
                docs.append({
                    "doc_id": hashlib.sha256(str(path).encode()).hexdigest()[:12],
                    "path": str(path),
                    "title": title,
                    "kind": meta["kind"],
                    "domain": meta["domain"],
                    "tags": _tags(path, title, content),
                })
    idx = {"root": str(kd), "count": len(docs), "docs": docs}
    if out_file:
        Path(out_file).write_text(json.dumps(idx, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
    return idx


def retrieve(idx: dict, query: str, limit: int = 5) -> dict:
    """Selective retrieval. Returns matches or a KNOWLEDGE_GAP marker."""
    terms = {t for t in re.split(r"[^a-z0-9]+", query.lower()) if len(t) >= 3}
    scored = []
    for doc in idx.get("docs", []):
        hay = set(doc.get("tags", [])) | {doc.get("domain", ""), doc.get("title", "").lower()}
        score = len(terms & hay)
        if doc.get("domain") and doc["domain"] in terms:
            score += 2
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits = [d for _, d in scored[:limit]]
    if not hits:
        return {"status": "KNOWLEDGE_GAP", "query": query, "results": []}
    return {"status": "OK", "query": query, "results": hits}

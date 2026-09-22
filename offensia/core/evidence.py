"""Evidence store (Evidence Plane).

Raw artifacts live on disk addressed by content hash; the LLM only ever receives
references (evidence ids / hashes), never becomes the authoritative store. A
finding points to evidence ids that resolve back to real artifacts.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    sha256: str
    path: str
    size: int
    kind: str


def _artifacts_dir(assessment_dir: Path) -> Path:
    d = Path(assessment_dir) / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def store(assessment_dir: Path, data: bytes | str, kind: str = "raw") -> EvidenceRef:
    if isinstance(data, str):
        data = data.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    path = _artifacts_dir(assessment_dir) / f"{digest}.bin"
    if not path.exists():
        path.write_bytes(data)
    return EvidenceRef(evidence_id=digest[:16], sha256=digest,
                       path=str(path), size=len(data), kind=kind)


def load(assessment_dir: Path, sha256: str) -> bytes | None:
    path = _artifacts_dir(assessment_dir) / f"{sha256}.bin"
    return path.read_bytes() if path.exists() else None


def resolves(assessment_dir: Path, sha256: str) -> bool:
    return (_artifacts_dir(assessment_dir) / f"{sha256}.bin").exists()

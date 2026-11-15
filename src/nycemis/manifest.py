"""``data/MANIFEST.json``: SHA-256, size and provenance of every frozen input file (OSM extracts, networks)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from nycemis.paths import data_dir, rel


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_path() -> Path:
    return data_dir() / "MANIFEST.json"


def load_manifest() -> dict:
    path = manifest_path()
    if not path.is_file():
        return {"files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def record(path: Path, **meta: object) -> dict:
    """Add or replace the entry for ``path`` (keyed by its repo-relative path) and save the manifest."""
    manifest = load_manifest()
    entry = {"sha256": sha256_file(path), "bytes": Path(path).stat().st_size, **meta}
    manifest["files"][rel(path)] = entry
    manifest["files"] = dict(sorted(manifest["files"].items()))
    manifest_path().parent.mkdir(parents=True, exist_ok=True)
    manifest_path().write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return entry


def verify(path: Path) -> bool:
    """True if ``path`` exists and matches its manifest hash."""
    entry = load_manifest()["files"].get(rel(path))
    return bool(entry) and Path(path).is_file() and sha256_file(path) == entry["sha256"]

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


CACHE_SCHEMA_VERSION = 1


def archive_cache_path(archive_path: Path) -> Path:
    return Path(f"{archive_path}.cache.json")


def build_fingerprint(
    context: dict[str, str],
    files: Iterable[tuple[str, Path]],
) -> dict:
    entries = []
    for relative, path in files:
        stat = Path(path).stat()
        entries.append(
            {
                "path": str(relative).replace("\\", "/"),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "context": dict(sorted(context.items())),
        "files": sorted(entries, key=lambda entry: entry["path"]),
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode()
    payload["fingerprint"] = hashlib.sha256(encoded).hexdigest()
    return payload


def cache_matches(archive_path: Path, fingerprint: dict) -> bool:
    archive_path = Path(archive_path)
    cache_path = archive_cache_path(archive_path)
    if not archive_path.is_file() or not cache_path.is_file():
        return False
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return cached == fingerprint


def write_cache(archive_path: Path, fingerprint: dict) -> None:
    cache_path = archive_cache_path(archive_path)
    cache_path.write_text(
        json.dumps(fingerprint, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

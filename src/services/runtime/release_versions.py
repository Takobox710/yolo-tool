from __future__ import annotations

import re


_VERSION_PATTERN = re.compile(
    r"^[vV]?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?$"
)
_EMBEDDED_VERSION_PATTERN = re.compile(
    r"(?:^|[-_])v?(\d+(?:\.\d+){0,2})(?=$|[-_.])",
    re.IGNORECASE,
)


def normalize_release_version(value: str) -> str:
    text = str(value or "").strip()
    match = _VERSION_PATTERN.match(text)
    if match is None:
        return ""
    major, minor, patch, _prerelease = match.groups()
    return ".".join((major, minor or "0", patch or "0"))


def normalize_environment_version(value: str) -> str:
    """Normalize package versions from filenames and install metadata."""
    text = str(value or "").strip()
    normalized = normalize_release_version(text)
    if normalized:
        return normalized
    match = _EMBEDDED_VERSION_PATTERN.search(text)
    if match is None:
        return ""
    return normalize_release_version(match.group(1))


def is_newer_version(current_version: str, latest_version: str) -> bool:
    current = _version_key(current_version)
    latest = _version_key(latest_version)
    return current is not None and latest is not None and latest > current


def _version_key(value: str) -> tuple[int, int, int, int, str] | None:
    text = str(value or "").strip()
    match = _VERSION_PATTERN.match(text)
    if match is None:
        return None
    major, minor, patch, prerelease = match.groups()
    return (
        int(major),
        int(minor or 0),
        int(patch or 0),
        1 if not prerelease else 0,
        prerelease or "",
    )


__all__ = [
    "is_newer_version",
    "normalize_environment_version",
    "normalize_release_version",
]

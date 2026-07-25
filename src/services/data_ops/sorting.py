from __future__ import annotations

import re
from pathlib import Path


def natural_sort_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", Path(path).name)
    ]


__all__ = ["natural_sort_key"]

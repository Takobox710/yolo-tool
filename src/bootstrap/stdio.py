from __future__ import annotations

import sys


def configure_utf8_stdio() -> None:
    """Force UTF-8 for hidden CLI and structured runtime protocols."""
    for name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            continue


__all__ = ["configure_utf8_stdio"]

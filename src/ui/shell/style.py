from __future__ import annotations

from src.shared.theme import build_style as _build_style


def build_style(mode: object = "light") -> str:
    return _build_style(mode)

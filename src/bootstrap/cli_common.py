from __future__ import annotations

import json
import os
from typing import Any

from src.services.runtime import STRUCTURED_OUTPUT_PREFIX

def _parse_value(raw: str) -> Any:
    text = str(raw)
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        if "." not in text:
            return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text



def _parse_key_values(parts: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key:
            values[key] = _parse_value(value)
    return values



def _emit_structured(event: str, **payload: Any) -> None:
    print(
        f"{STRUCTURED_OUTPUT_PREFIX}"
        + json.dumps({"event": event, **payload}, ensure_ascii=False),
        flush=True,
    )



def _load_json_payload(argv: list[str], usage: str) -> dict[str, Any]:
    if not argv:
        raise SystemExit(usage)
    payload_path = argv[0]
    try:
        text = open(payload_path, "r", encoding="utf-8").read()
    except OSError as exc:
        raise SystemExit(f"无法读取配置文件：{exc}") from exc
    finally:
        try:
            os.unlink(payload_path)
        except OSError:
            pass
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"配置文件不是合法 JSON：{exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("配置文件内容必须是 JSON 对象。")
    return payload



__all__ = ["_emit_structured", "_load_json_payload", "_parse_key_values", "_parse_value"]

from __future__ import annotations

from typing import Any

from src.bootstrap.cli_common import _emit_structured


def emit_runtime_response(request_id: str, result: dict[str, Any]) -> None:
    _emit_structured("runtime_response", request_id=request_id, result=result)


def emit_runtime_error(request_id: str, message: str) -> None:
    _emit_structured("runtime_error", request_id=request_id, message=message)

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from src.services.runtime.windows_spawn import hidden_subprocess_kwargs


EXPORT_PROTOCOL_VERSION = 1
PROBE_EXTENSION_ROOT_ENV = "YOLO_TOOL_MODEL_EXPORT_CANDIDATE_ROOT"


def _probe_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--yolo-export-probe"]
    return [sys.executable, "-m", "src.main", "--yolo-export-probe"]


def probe_packages(package_dir: Path) -> dict:
    env = os.environ.copy()
    env[PROBE_EXTENSION_ROOT_ENV] = str(Path(package_dir).resolve().parent)
    try:
        result = subprocess.run(
            _probe_command(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env=env,
            **hidden_subprocess_kwargs(),
        )
    except Exception as exc:
        raise ValueError(f"无法启动模型转换环境自检：{exc}") from exc
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        message = result.stderr.strip() or "模型转换环境返回了无效的自检结果。"
        raise ValueError(message) from exc
    if payload.get("protocol_version") != EXPORT_PROTOCOL_VERSION or not payload.get("ok"):
        missing = ", ".join(str(item) for item in payload.get("missing", ()))
        raise ValueError(f"模型转换环境缺少依赖：{missing or '协议不兼容'}")
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "模型转换环境自检失败。")
    return payload

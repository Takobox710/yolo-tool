from __future__ import annotations

import sys
from pathlib import Path

from src.services.model_export.formats import resolve_export_format
from src.services.model_export.types import ModelExportConfig


def app_cli_command(*args: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "src.main", *args]


def build_model_export_command(
    config: ModelExportConfig,
    *,
    runtime_executable: Path | None = None,
) -> list[str]:
    spec = resolve_export_format(config.export_format)
    prefix = (
        [str(runtime_executable), "--yolo-export"]
        if runtime_executable is not None
        else app_cli_command("--yolo-export")
    )
    command = [
        *prefix,
        f"model={config.model_path}",
        f"format={spec.argument}",
        f"imgsz={int(config.imgsz)}",
        f"output_dir={config.output_dir}",
    ]
    if spec.argument in {"onnx", "engine"}:
        command.append(f"simplify={str(bool(config.simplify)).lower()}")
    return command


def build_export_command(
    model_path: str,
    export_format: str,
    imgsz: int | str = 640,
) -> list[str]:
    return build_model_export_command(
        ModelExportConfig(
            model_path=Path(model_path),
            output_dir=Path(model_path).resolve().parent,
            export_format=export_format,
            imgsz=int(imgsz),
        )
    )

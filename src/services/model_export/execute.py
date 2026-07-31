from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Callable

from src.services.model_export.formats import (
    export_artifact_path,
    resolve_export_format,
    validate_model_export_source,
)


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def cleanup_stale_export_workdirs(output_dir: str | Path) -> None:
    root = Path(output_dir)
    if not root.exists():
        return
    for path in root.glob(".yolo-export-*"):
        if not path.name.startswith(".yolo-export-backup-"):
            _remove_path(path)
    backup_prefix = ".yolo-export-backup-"
    for backup in root.glob(f"{backup_prefix}*"):
        remainder = backup.name[len(backup_prefix) :]
        _token, separator, target_name = remainder.partition("-")
        if not separator or not target_name:
            _remove_path(backup)
            continue
        target = root / target_name
        if target.exists():
            _remove_path(backup)
        else:
            backup.replace(target)


def export_model_to_directory(
    options: dict,
    *,
    yolo_factory: Callable[[str], object] | None,
    progress: Callable[[str], None] | None = None,
) -> Path:
    values = dict(options)
    model_path = Path(str(values.pop("model", ""))).resolve()
    output_dir_value = str(values.pop("output_dir", "")).strip()
    if not model_path.is_file() or model_path.suffix.lower() != ".pt":
        raise ValueError("请选择存在的 .pt 模型文件。")
    spec = resolve_export_format(str(values.get("format", "")))
    validate_model_export_source(model_path, spec.argument)
    if spec.argument == "sam2_onnx":
        from src.services.model_export.sam_onnx import export_sam2_model_to_directory

        sam_options = dict(values)
        sam_options["model"] = str(model_path)
        sam_options["output_dir"] = output_dir_value
        return export_sam2_model_to_directory(sam_options, progress=progress)
    if yolo_factory is None:
        raise ValueError("YOLO 导出缺少 Ultralytics 运行时。")
    values["format"] = spec.argument
    values["batch"] = 1
    for unsupported in ("dynamic", "half", "int8", "quantize", "nms"):
        values.pop(unsupported, None)
    if not output_dir_value:
        model = yolo_factory(str(model_path))
        result = model.export(**values)
        return Path(str(result)).resolve()

    output_dir = Path(output_dir_value).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cleanup_stale_export_workdirs(output_dir)
    target = export_artifact_path(model_path, output_dir, spec.argument)
    work = output_dir / f".yolo-export-{uuid.uuid4().hex}"
    backup = output_dir / f".yolo-export-backup-{uuid.uuid4().hex}-{target.name}"
    work.mkdir()
    source_copy = work / model_path.name
    shutil.copy2(model_path, source_copy)
    replaced = False
    try:
        if progress:
            progress(f"正在加载模型：{model_path.name}")
        model = yolo_factory(str(source_copy))
        generated_value = model.export(**values)
        generated = Path(str(generated_value))
        if not generated.is_absolute():
            generated = work / generated
        if not generated.exists():
            generated = export_artifact_path(source_copy, work, spec.argument)
        if not generated.exists():
            raise RuntimeError("转换进程未生成预期的模型文件。")
        if target.exists():
            target.replace(backup)
            replaced = True
        shutil.move(str(generated), str(target))
        _remove_path(backup)
        if progress:
            progress(f"转换结果已保存：{target}")
        return target
    except Exception:
        if replaced and backup.exists():
            _remove_path(target)
            backup.replace(target)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if backup.exists() and target.exists():
            _remove_path(backup)

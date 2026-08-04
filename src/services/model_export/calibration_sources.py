from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.model_export.calibration_images import IMAGE_SUFFIXES


@dataclass(frozen=True, slots=True)
class CalibrationSet:
    source: Path
    images: tuple[Path, ...]

    @property
    def count(self) -> int:
        return len(self.images)


def resolve_calibration_images(value: str | Path, sample_limit: int) -> CalibrationSet:
    source = Path(str(value or "")).expanduser().resolve()
    sample_limit = int(sample_limit)
    if not source.exists():
        raise ValueError(f"校准数据不存在：{source}")
    if sample_limit < 1:
        raise ValueError("校准样本数必须大于 0。")
    if source.is_dir():
        images = _scan_images(source)
    elif source.suffix.lower() in {".yaml", ".yml"}:
        images = _images_from_dataset_yaml(source)
    elif source.suffix.lower() in IMAGE_SUFFIXES:
        images = [source]
    else:
        images = _images_from_list_file(source)
    images = [path for path in images if path.is_file()]
    if not images:
        raise ValueError(f"校准数据中没有可用图片：{source}")
    return CalibrationSet(source=source, images=tuple(images[:sample_limit]))


def _images_from_dataset_yaml(path: Path) -> list[Path]:
    import yaml

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"无法读取校准 dataset.yaml：{path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"校准 dataset.yaml 格式无效：{path}")
    root_value = payload.get("path") or "."
    root = Path(str(root_value)).expanduser()
    if not root.is_absolute():
        root = (path.parent / root).resolve()
    value = payload.get("val") or payload.get("validation") or payload.get("train")
    return _resolve_yaml_value(value, root)


def _resolve_yaml_value(value: Any, root: Path) -> list[Path]:
    if isinstance(value, (list, tuple)):
        result: list[Path] = []
        for item in value:
            result.extend(_resolve_yaml_value(item, root))
        return result
    if not value:
        return []
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    if candidate.is_dir():
        return _scan_images(candidate)
    if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
        return [candidate.resolve()]
    if candidate.is_file():
        return _images_from_list_file(candidate)
    return []


def _images_from_list_file(path: Path) -> list[Path]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"无法读取校准图片列表：{path}") from exc
    result: list[Path] = []
    for line in lines:
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = path.parent / candidate
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
            result.append(candidate.resolve())
    return result


def _scan_images(root: Path) -> list[Path]:
    return sorted(
        path.resolve()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


__all__ = ["CalibrationSet", "resolve_calibration_images"]

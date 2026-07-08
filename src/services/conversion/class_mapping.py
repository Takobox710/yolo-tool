from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.services.conversion.dataset_split import collect_inputs
from src.services.conversion.types import ClassMappingRow, ConversionConfig


def detect_class_names(
    config: ConversionConfig, labeled: list[tuple[Path, Path]] | None = None
) -> list[str]:
    if config.source_format == "labelme":
        mappings = normalize_class_name_mapping(config.class_name_mapping or {})
        if mappings:
            ordered: list[str] = []
            for yolo_name in mappings.values():
                if yolo_name not in ordered:
                    ordered.append(yolo_name)
            return ordered
    existing = [
        str(name).strip() for name in (config.class_names or []) if str(name).strip()
    ]
    if existing:
        return existing
    pairs = labeled if labeled is not None else collect_inputs(config)[0]
    if config.source_format == "labelme":
        names: list[str] = []
        seen: set[str] = set()
        for _image_path, label_path in pairs:
            try:
                payload = json.loads(label_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            for shape in payload.get("shapes", []):
                label = str(shape.get("label") or "").strip()
                if label and label not in seen:
                    seen.add(label)
                    names.append(label)
        if names:
            return names
    max_class_id = -1
    for _image_path, label_path in pairs:
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                max_class_id = max(max_class_id, int(float(parts[0])))
            except ValueError:
                continue
    if max_class_id >= 0:
        return [f"class_{index}" for index in range(max_class_id + 1)]
    raise ValueError("未能自动识别类别，请检查标注文件是否包含有效类别")


def detect_labelme_classes(annotation_dir: Path) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for label_path in sorted(Path(annotation_dir).glob("*.json")):
        try:
            payload = json.loads(label_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for shape in payload.get("shapes", []):
            label = str(shape.get("label") or "").strip()
            if label and label not in seen:
                seen.add(label)
                names.append(label)
    return names


def normalize_class_name_mapping(mapping: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for labelme_name, yolo_name in (mapping or {}).items():
        source = str(labelme_name or "").strip()
        target = str(yolo_name or "").strip()
        if source and target:
            normalized[source] = target
    return normalized


def build_class_mapping_rows(
    labelme_names: list[str], stored_mapping: dict[str, str] | None = None
) -> list[ClassMappingRow]:
    stored_mapping = normalize_class_name_mapping(stored_mapping or {})
    grouped: dict[str, list[str]] = {}
    used: set[str] = set()
    for labelme_name in labelme_names:
        yolo_name = stored_mapping.get(labelme_name, labelme_name)
        grouped.setdefault(yolo_name, []).append(labelme_name)
        used.add(labelme_name)
    for labelme_name, yolo_name in stored_mapping.items():
        if labelme_name not in used:
            grouped.setdefault(yolo_name, []).append(labelme_name)
    rows = [
        ClassMappingRow(yolo_name=yolo_name, labelme_names=", ".join(names))
        for yolo_name, names in grouped.items()
    ]
    rows.sort(
        key=lambda row: (
            labelme_names.index(row.labelme_names.split(",")[0].strip())
            if row.labelme_names.split(",")[0].strip() in labelme_names
            else len(labelme_names)
        )
    )
    return rows


def parse_class_mapping_rows(
    rows: Iterable[ClassMappingRow], detected_labelme_names: Iterable[str]
) -> tuple[dict[str, str], list[str]]:
    detected = {
        str(name).strip() for name in detected_labelme_names if str(name).strip()
    }
    mapping: dict[str, str] = {}
    errors: list[str] = []
    seen_sources: set[str] = set()
    seen_targets: list[str] = []
    for index, row in enumerate(rows, start=1):
        target = str(row.yolo_name or "").strip()
        raw_sources = str(row.labelme_names or "").strip()
        if not target:
            errors.append(f"第 {index} 行的 YOLO 类别名称不能为空。")
            continue
        if not raw_sources:
            errors.append(f"第 {index} 行的 Labelme 类别名称不能为空。")
            continue
        names = [part.strip() for part in raw_sources.split(",") if part.strip()]
        if not names:
            errors.append(f"第 {index} 行的 Labelme 类别名称不能为空。")
            continue
        for name in names:
            if name not in detected:
                errors.append(f"第 {index} 行包含不存在的 Labelme 类别：{name}")
                continue
            if name in seen_sources:
                errors.append(f"Labelme 类别 {name} 被重复配置。")
                continue
            seen_sources.add(name)
            mapping[name] = target
        if target not in seen_targets:
            seen_targets.append(target)
    missing = sorted(detected - seen_sources)
    if missing:
        errors.append(f"仍有未配置的 Labelme 类别：{', '.join(missing)}")
    if errors:
        return {}, errors
    return {
        labelme_name: mapping[labelme_name]
        for target in seen_targets
        for labelme_name in mapping
        if mapping[labelme_name] == target
    }, []

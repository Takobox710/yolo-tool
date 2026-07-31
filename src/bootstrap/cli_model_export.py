from __future__ import annotations

import json
import os

from src.bootstrap.cli_common import _emit_structured, _parse_key_values

def _run_export_cli_impl(argv: list[str]) -> int:
    os.environ["YOLO_AUTOINSTALL"] = "false"
    options = _parse_key_values(argv)
    if not options.get("model"):
        raise SystemExit("Missing model=... for export")
    from src.services.ultralytics_compat import ensure_cv2_highgui_compat
    from src.services.model_export import export_model_to_directory

    ensure_cv2_highgui_compat()
    try:
        yolo_factory = None
        if str(options.get("format") or "").strip().lower() != "sam2_onnx":
            from ultralytics import YOLO

            yolo_factory = YOLO
        result = export_model_to_directory(
            options,
            yolo_factory=yolo_factory,
            progress=lambda message: _emit_structured("progress", message=message),
        )
        _emit_structured("done", ok=True, result_path=str(result))
        return 0
    except Exception as exc:
        _emit_structured("error", message=str(exc))
        return 1



def _run_export_probe_cli_impl(argv: list[str]) -> int:
    from importlib import metadata
    import importlib
    from src.services.model_export.package import EXPORT_PROTOCOL_VERSION

    del argv
    distributions = {
        "openvino": "openvino",
        "ncnn": "ncnn",
        "pnnx": "pnnx",
        "tensorrt": "tensorrt",
    }
    versions: dict[str, str] = {}
    missing: list[str] = []
    for module_name, distribution in distributions.items():
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            missing.append(module_name)
            versions[module_name] = f"不可用：{exc}"
            continue
        try:
            versions[module_name] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[module_name] = "已安装"
    payload = {
        "protocol_version": EXPORT_PROTOCOL_VERSION,
        "ok": not missing,
        "modules": versions,
        "missing": missing,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 0 if not missing else 1



def _run_install_model_export_package_cli_impl(argv: list[str]) -> int:
    from src.services.model_export import install_extension_package

    options = _parse_key_values(argv)
    package_path = str(options.get("package") or "").strip()
    if not package_path:
        raise SystemExit("Usage: --install-model-export-package package=<archive>")
    try:
        installed = install_extension_package(package_path)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {"ok": True, "version": installed.version, "root": str(installed.root)},
            ensure_ascii=False,
        )
    )
    return 0



def _run_migrate_legacy_extension_cli_impl(argv: list[str]) -> int:
    from src.services.runtime import migrate_legacy_extensions

    del argv
    try:
        migrated = migrate_legacy_extensions()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "migrated": migrated}, ensure_ascii=False))
    return 0



def run_export(argv: list[str]) -> int:
    return _run_export_cli_impl(argv)


def run_export_probe(argv: list[str]) -> int:
    return _run_export_probe_cli_impl(argv)


def run_install_model_export_package(argv: list[str]) -> int:
    return _run_install_model_export_package_cli_impl(argv)


def run_migrate_legacy_extension(argv: list[str]) -> int:
    return _run_migrate_legacy_extension_cli_impl(argv)


__all__ = ["run_export", "run_export_probe", "run_install_model_export_package", "run_migrate_legacy_extension"]

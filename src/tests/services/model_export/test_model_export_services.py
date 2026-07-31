from __future__ import annotations

from pathlib import Path

import pytest


def test_format_mapping_targets_and_model_scan(tmp_path):
    from src.services.model_export import (
        export_artifact_path,
        find_export_model_paths,
        resolve_export_format,
    )

    base = tmp_path / "data" / "models" / "base.pt"
    sam = tmp_path / "data" / "models" / "sam2.1_hiera_base_plus.pt"
    best = tmp_path / "result" / "train-2" / "weights" / "best.pt"
    base.parent.mkdir(parents=True)
    best.parent.mkdir(parents=True)
    base.write_bytes(b"base")
    sam.write_bytes(b"sam")
    best.write_bytes(b"best")

    assert resolve_export_format("TensorRT").argument == "engine"
    assert resolve_export_format("SAM2 ONNX").argument == "sam2_onnx"
    assert not resolve_export_format("OpenVINO").built_in
    assert not resolve_export_format("NCNN").built_in
    assert export_artifact_path(base, tmp_path, "OpenVINO").name == "base_openvino_model"
    assert export_artifact_path(base, tmp_path, "SAM2 ONNX").name == "base_sam2_onnx"
    assert find_export_model_paths(tmp_path, tmp_path) == [best.resolve()]
    assert find_export_model_paths(tmp_path, tmp_path, include_sam_models=True) == [
        best.resolve(),
        sam.resolve(),
    ]


def test_build_export_command_selects_builtin_or_extension(tmp_path):
    from src.services.model_export import ModelExportConfig, build_model_export_command

    config = ModelExportConfig(
        model_path=tmp_path / "model.pt",
        output_dir=tmp_path / "output",
        export_format="onnx",
        imgsz=960,
        simplify=True,
    )
    builtin = build_model_export_command(config)
    extension = build_model_export_command(
        ModelExportConfig(
            model_path=config.model_path,
            output_dir=config.output_dir,
            export_format="ncnn",
            imgsz=640,
        ),
        runtime_executable=tmp_path / "ModelExportRuntime.exe",
    )

    assert "--yolo-export" in builtin
    assert "format=onnx" in builtin
    assert "simplify=true" in builtin
    assert extension[:2] == [str(tmp_path / "ModelExportRuntime.exe"), "--yolo-export"]
    assert "format=ncnn" in extension
    assert not any(item.startswith("simplify=") for item in extension)


def test_tensorrt_capability_does_not_import_backend(monkeypatch):
    from src.services.model_export import runtime as runtime_service

    imported = []
    original_import = __import__

    def tracking_import(name, *args, **kwargs):
        if name.split(".", 1)[0] == "tensorrt":
            imported.append(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(runtime_service, "_modules_available", lambda _modules: True)
    monkeypatch.setattr(runtime_service, "cuda_available", lambda: True)
    monkeypatch.setattr("builtins.__import__", tracking_import)

    capability = runtime_service.export_capability("engine", frozen=False)

    assert capability.available is True
    assert imported == []


def test_cpu_capability_uses_builtins_and_rejects_tensorrt(monkeypatch):
    from src.services.model_export import runtime as runtime_service

    monkeypatch.setattr(runtime_service, "installed_variant", lambda: "cpu")
    monkeypatch.setattr(runtime_service, "_modules_available", lambda _modules: True)

    openvino = runtime_service.export_capability("openvino", frozen=True)
    ncnn = runtime_service.export_capability("ncnn", frozen=True)
    tensorrt = runtime_service.export_capability("engine", frozen=True)

    assert openvino.available is True
    assert openvino.runtime == "CPU 内置运行环境"
    assert ncnn.available is True
    assert tensorrt.available is False
    assert "不包含 TensorRT" in tensorrt.reason


def test_export_uses_staging_and_replaces_only_after_success(tmp_path):
    from src.services.model_export import export_model_to_directory

    source = tmp_path / "model.pt"
    source.write_bytes(b"weights")
    output = tmp_path / "exports"
    output.mkdir()
    target = output / "model.onnx"
    target.write_bytes(b"old")

    class FakeYOLO:
        def __init__(self, model):
            self.model = Path(model)

        def export(self, **_options):
            generated = self.model.with_suffix(".onnx")
            generated.write_bytes(b"new")
            return str(generated)

    result = export_model_to_directory(
        {
            "model": str(source),
            "format": "onnx",
            "imgsz": 640,
            "simplify": True,
            "output_dir": str(output),
        },
        yolo_factory=FakeYOLO,
    )

    assert result == target
    assert target.read_bytes() == b"new"
    assert not list(output.glob(".yolo-export-*"))


def test_export_failure_preserves_existing_target(tmp_path):
    from src.services.model_export import export_model_to_directory

    source = tmp_path / "model.pt"
    source.write_bytes(b"weights")
    output = tmp_path / "exports"
    output.mkdir()
    target = output / "model.torchscript"
    target.write_bytes(b"old")

    class BrokenYOLO:
        def __init__(self, _model):
            pass

        def export(self, **_options):
            raise RuntimeError("export failed")

    with pytest.raises(RuntimeError, match="export failed"):
        export_model_to_directory(
            {
                "model": str(source),
                "format": "torchscript",
                "imgsz": 640,
                "output_dir": str(output),
            },
            yolo_factory=BrokenYOLO,
        )

    assert target.read_bytes() == b"old"
    assert not list(output.glob(".yolo-export-*"))


def test_sam_checkpoint_is_rejected_before_yolo_loading(tmp_path):
    from src.services.model_export import export_model_to_directory

    source = tmp_path / "sam2.1_hiera_base_plus.pt"
    source.write_bytes(b"sam checkpoint")
    called = False

    def yolo_factory(_model):
        nonlocal called
        called = True
        raise AssertionError("SAM checkpoint must not be passed to YOLO")

    with pytest.raises(ValueError, match="不是 Ultralytics YOLO 权重"):
        export_model_to_directory(
            {
                "model": str(source),
                "format": "onnx",
                "imgsz": 640,
                "output_dir": str(tmp_path / "exports"),
            },
            yolo_factory=yolo_factory,
        )

    assert called is False


def test_sam2_format_routes_to_sam_exporter(monkeypatch, tmp_path):
    from src.services.model_export import export_model_to_directory
    from src.services.model_export import sam_onnx

    source = tmp_path / "sam2.1_hiera_base_plus.pt"
    source.write_bytes(b"sam checkpoint")
    expected = tmp_path / "exports" / "sam2"
    received = {}

    def fake_export(options, progress=None):
        received.update(options)
        return expected

    monkeypatch.setattr(
        sam_onnx,
        "export_sam2_model_to_directory",
        fake_export,
    )

    result = export_model_to_directory(
        {
            "model": str(source),
            "format": "sam2_onnx",
            "output_dir": str(tmp_path / "exports"),
        },
        yolo_factory=None,
    )

    assert result == expected
    assert received["model"] == str(source.resolve())
    assert received["output_dir"] == str(tmp_path / "exports")


def test_partial_move_failure_restores_existing_target(monkeypatch, tmp_path):
    from src.services.model_export import export_model_to_directory
    from src.services.model_export import execute

    source = tmp_path / "model.pt"
    source.write_bytes(b"weights")
    output = tmp_path / "exports"
    output.mkdir()
    target = output / "model.onnx"
    target.write_bytes(b"old")

    class FakeYOLO:
        def __init__(self, model):
            self.model = Path(model)

        def export(self, **_options):
            generated = self.model.with_suffix(".onnx")
            generated.write_bytes(b"new")
            return str(generated)

    def broken_move(_source, destination):
        Path(destination).write_bytes(b"partial")
        raise OSError("move failed")

    monkeypatch.setattr(execute.shutil, "move", broken_move)
    with pytest.raises(OSError, match="move failed"):
        export_model_to_directory(
            {
                "model": str(source),
                "format": "onnx",
                "output_dir": str(output),
            },
            yolo_factory=FakeYOLO,
        )

    assert target.read_bytes() == b"old"
    assert not list(output.glob(".yolo-export-*"))


def test_stale_backup_is_restored_when_target_is_missing(tmp_path):
    from src.services.model_export import cleanup_stale_export_workdirs

    output = tmp_path / "exports"
    output.mkdir()
    backup = output / f".yolo-export-backup-{'a' * 32}-model.engine"
    backup.write_bytes(b"old")

    cleanup_stale_export_workdirs(output)

    assert (output / "model.engine").read_bytes() == b"old"
    assert not backup.exists()

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("export_format", "generated_suffix", "artifact_name"),
    [
        ("onnx", ".onnx", "model_fp32.onnx"),
        ("torchscript", ".torchscript", "model_fp32.torchscript"),
        ("openvino", "_openvino_model", "model_fp32_openvino_model"),
        ("engine", ".engine", "model_fp32.engine"),
        ("ncnn", "_ncnn_model", "model_fp32_ncnn_model"),
    ],
)
def test_export_cli_emits_structured_result(
    monkeypatch, tmp_path, capsys, export_format, generated_suffix, artifact_name
):
    from src.train_cli import run_export_cli

    source = tmp_path / "model.pt"
    source.write_bytes(b"weights")
    output = tmp_path / "output"

    class FakeYOLO:
        def __init__(self, model):
            self.model = Path(model)

        def export(self, **options):
            assert options["format"] == export_format
            if generated_suffix.startswith("_"):
                generated = self.model.parent / f"{self.model.stem}{generated_suffix}"
                generated.mkdir()
                (generated / "model.bin").write_bytes(b"model")
            else:
                generated = self.model.with_suffix(generated_suffix)
                generated.write_bytes(b"model")
            return str(generated)

    monkeypatch.setitem(
        sys.modules,
        "src.services.ultralytics_compat",
        SimpleNamespace(ensure_cv2_highgui_compat=lambda: None),
    )
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=FakeYOLO))

    arguments = [
        f"model={source}",
        f"format={export_format}",
        "imgsz=640",
        f"output_dir={output}",
    ]
    if export_format in {"onnx", "engine"}:
        arguments.append("simplify=true")
    code = run_export_cli(arguments)

    captured = capsys.readouterr().out
    assert code == 0
    assert '"event": "done"' in captured
    assert (output / artifact_name).exists()


def test_extension_installer_cli_reports_installed_instance(monkeypatch, tmp_path, capsys):
    from src import train_cli
    from src.services import model_export

    package = tmp_path / "runtime.7z"
    package.touch()
    monkeypatch.setattr(
        model_export,
        "install_extension_package",
        lambda _path: SimpleNamespace(version="runtime-2", root=tmp_path / "installed"),
    )

    code = train_cli.run_install_model_export_package_cli([f"package={package}"])

    payload = capsys.readouterr().out
    assert code == 0
    assert '"version": "runtime-2"' in payload


def test_legacy_extension_migration_cli_reports_result(monkeypatch, capsys):
    from src import train_cli
    from src.services import runtime

    monkeypatch.setattr(runtime, "migrate_legacy_extensions", lambda: True)

    code = train_cli.run_migrate_legacy_extension_cli([])

    assert code == 0
    assert '"migrated": true' in capsys.readouterr().out

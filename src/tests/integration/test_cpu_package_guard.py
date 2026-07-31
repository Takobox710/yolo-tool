from __future__ import annotations

import json


def _write_lock(path, entries):
    path.write_text(
        json.dumps(
            {"environments": {"release-cpu": {"packages": {"p1": entries}}}}
        ),
        encoding="utf-8",
    )


def test_cpu_lock_guard_requires_cpu_runtime_and_rejects_gpu_packages(tmp_path):
    from src.devtools.cpu_package_guard import validate_cpu_lock

    lock_path = tmp_path / "pixi.lock"
    _write_lock(
        lock_path,
        [
            {"pypi": "https://download.pytorch.org/whl/cpu/torch-2.13.0+cpu.whl"},
            {"pypi": "https://download.pytorch.org/whl/cpu/torchvision-0.28.0+cpu.whl"},
            {"pypi": "https://download.pytorch.org/whl/cpu/torchaudio-2.11.0+cpu.whl"},
            {"pypi": "https://files.pythonhosted.org/onnxruntime-1.28.0.whl"},
        ],
    )
    assert validate_cpu_lock(lock_path) == []

    _write_lock(
        lock_path,
        [
            {"pypi": "https://download.pytorch.org/whl/cpu/torch-2.13.0+cpu.whl"},
            {"pypi": "https://download.pytorch.org/whl/cpu/torchvision-0.28.0+cpu.whl"},
            {"pypi": "https://download.pytorch.org/whl/cpu/torchaudio-2.11.0+cpu.whl"},
            {"pypi": "https://files.pythonhosted.org/onnxruntime-gpu-1.28.0.whl"},
            {"pypi": "https://files.pythonhosted.org/tensorrt-11.1.whl"},
        ],
    )
    errors = validate_cpu_lock(lock_path)
    assert any("onnxruntime-gpu" in error for error in errors)
    assert any("tensorrt" in error for error in errors)


def test_cpu_frozen_runtime_guard_rejects_gpu_dll_names(tmp_path):
    from src.devtools.cpu_package_guard import validate_frozen_runtime

    runtime_root = tmp_path / "_internal"
    runtime_root.mkdir()
    (runtime_root / "onnxruntime_providers_cuda.dll").write_bytes(b"bad")

    errors = validate_frozen_runtime(runtime_root)
    assert errors
    assert "onnxruntime_providers_cuda.dll" in errors[0]

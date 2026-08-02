"""Connect a program-only executable to the installed base runtime."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _activate_external_runtime() -> None:
    if not getattr(sys, "frozen", False):
        return

    runtime_root = Path(sys.executable).resolve().parent / "_internal"
    if not runtime_root.is_dir():
        return

    # The executable owns Python and pure modules; the base package owns
    # native libraries. Make both the import and Windows DLL search paths
    # deterministic before application imports begin.
    sys.path.insert(0, str(runtime_root))
    stdlib_archive = runtime_root / "python_stdlib.zip"
    if stdlib_archive.is_file():
        sys.path.insert(0, str(stdlib_archive))
    dll_paths = [
        runtime_root,
        runtime_root / "torch",
        runtime_root / "torch" / "lib",
        runtime_root / "torchvision",
        runtime_root / "cv2",
        runtime_root / "numpy",
        runtime_root / "numpy.libs",
        runtime_root / "onnxruntime" / "capi",
        runtime_root / "openvino",
        runtime_root / "openvino" / "libs",
        runtime_root / "ncnn.libs",
        runtime_root / "pnnx",
        runtime_root / "nncf",
    ]
    dll_paths = [path for path in dll_paths if path.is_dir()]
    for path in dll_paths:
        try:
            os.add_dll_directory(str(path))
        except (AttributeError, OSError):
            pass
    os.environ["PATH"] = os.pathsep.join(
        [str(path) for path in dll_paths] + [os.environ.get("PATH", "")]
    )


_activate_external_runtime()

# -*- mode: python ; coding: utf-8 -*-

import os
import shutil
import sys
from pathlib import Path
import PyInstaller

SPEC_ROOT = Path(SPECPATH).resolve()
ROOT = SPEC_ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HOOKS_DIR = ROOT / "installer" / "hooks"
ASSETS_DIR = ROOT / "src" / "assets"

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)
from src.devtools.runtime_package_boundaries import PROGRAM_EXTERNAL_RUNTIME_EXCLUDES

BASE_EXCLUDES = [
    "pytest",
    "_pytest",
    "iniconfig",
    "pluggy",
    "PyInstaller",
    "_pyinstaller_hooks_contrib",
    "altgraph",
    "setuptools",
    "src.tests",
    "PySide6.scripts.deploy_lib",
    "torch.utils.tensorboard",
    "tensorboard",
    "dask",
    "matplotlib.tests",
    # Optional data/audio and test-only packages are not used by YOLOTool.
    "polars",
    "_polars_runtime_32",
    "torchaudio",
    "adodbapi",
    "isapi",
    "pythonwin",
    "win32",
    "win32com",
    "win32comext",
    "torch.fx.passes.tests",
    "torch._export.db.examples",
    "torch.utils.benchmark",
    "torch.distributed.rpc._testing",
    "torch.distributed.rpc.examples",
    "torch._numpy.testing",
    # TensorRT and NNCF stay out of the GPU base graph; CPU enables NNCF below
    # because OpenVINO INT8 is part of the built-in CPU capability set.
    "tensorrt",
    "nncf",
]

mode = os.environ.get("YOLO_TOOL_BUILD_MODE", "release").strip().lower()
is_dev = mode == "dev"
is_program_only = os.environ.get("YOLO_TOOL_PROGRAM_ONLY", "0") == "1"
build_variant = os.environ.get("YOLO_TOOL_BUILD_VARIANT", "gpu").strip().lower()
is_cpu_variant = build_variant == "cpu"
runtime_distribution = "onnxruntime" if is_cpu_variant else "onnxruntime-gpu"
name = "YOLOTool-dev" if is_dev else "YOLOTool"

PY7ZR_PACKAGES = (
    "py7zr",
    "bcj",
    "pyppmd",
    "backports.zstd",
    "inflate64",
    "brotli",
    "Cryptodome",
)
SAM2_PACKAGES = ("sam2",)
SAM3_PACKAGES = ("sam3",)
CPU_OPENVINO_EXCLUDED_FILES = frozenset(
    {
        "openvino_auto_batch_plugin.dll",
        "openvino_auto_plugin.dll",
        "openvino_hetero_plugin.dll",
        "openvino_intel_gpu_plugin.dll",
        "openvino_intel_npu_compiler.dll",
        "openvino_intel_npu_compiler_loader.dll",
        "openvino_intel_npu_plugin.dll",
        "cache.json",
    }
)


def _is_cpu_openvino_file(path: str | Path) -> bool:
    name = Path(path).name.casefold()
    if name in CPU_OPENVINO_EXCLUDED_FILES:
        return False
    return not name.endswith((".lib", "_debug.lib"))


def _collect_cpu_openvino_files(collector):
    return [
        item
        for item in collector("openvino")
        if _is_cpu_openvino_file(item[0])
    ]


excludes = list(BASE_EXCLUDES)

if is_program_only:
    # The base archive owns Python, pure third-party modules, and native
    # libraries. The program update only carries the application graph.
    datas = []
    binaries = []
    hiddenimports = ["src.assets_rc", "ctypes.util", "ctypes.wintypes"]
    hook_paths = []
    runtime_hooks = [
        str(
            Path(PyInstaller.__file__).resolve().parent
            / "hooks"
            / "rthooks"
            / "pyi_rth_pyside6.py"
        ),
        str(HOOKS_DIR / "program_external_runtime.py"),
    ]
    excludes += [
        *PROGRAM_EXTERNAL_RUNTIME_EXCLUDES,
        "PIL",
        "cv2",
        "torch",
        "ultralytics",
        "onnx",
        "onnxslim",
        "onnxscript",
        "onnx_ir",
        "onnxruntime",
        "openvino",
        "ncnn",
        "pnnx",
        "nncf",
        "matplotlib",
        "psutil",
        "py7zr",
    ]
else:
    if is_cpu_variant:
        excludes = [item for item in excludes if item != "nncf"]
    RUNTIME_DATA_EXCLUDES = [
        "**/test/**",
        "**/tests/**",
        "**/testdata/**",
        "**/testing/**",
        "**/example/**",
        "**/examples/**",
        "**/_examples/**",
    ]
    datas = [
        *collect_data_files("ultralytics", excludes=RUNTIME_DATA_EXCLUDES),
    ]
    native_7z = shutil.which("7z.exe") or shutil.which("7z")
    if native_7z:
        datas += [(native_7z, ".")]
        native_7z_dll = str(Path(native_7z).with_name("7z.dll"))
        if Path(native_7z_dll).is_file():
            datas += [(native_7z_dll, ".")]
    runtime_packages = [
        "torch",
        "cv2",
        "onnx",
        "onnxruntime",
        *SAM2_PACKAGES,
        *SAM3_PACKAGES,
        *PY7ZR_PACKAGES,
    ]
    if is_cpu_variant:
        runtime_packages += ["openvino", "ncnn", "pnnx", "nncf"]

    binaries = []
    for package in runtime_packages:
        if is_cpu_variant and package in SAM2_PACKAGES:
            # The vendored SAM2 wheel only ships a CUDA `_C.pyd`; SAM2's
            # Python inference path remains usable with CPU Torch without it.
            continue
        if is_cpu_variant and package == "openvino":
            binaries += _collect_cpu_openvino_files(collect_dynamic_libs)
        else:
            binaries += collect_dynamic_libs(package)

    hiddenimports = collect_submodules("ultralytics", on_error="ignore")
    hiddenimports += ["src.assets_rc"]
    import_packages = [
        "onnx",
        "onnxslim",
        "onnxscript",
        "onnx_ir",
        "onnxruntime",
        *SAM2_PACKAGES,
        *SAM3_PACKAGES,
        *PY7ZR_PACKAGES,
    ]
    if is_cpu_variant:
        import_packages += ["openvino", "ncnn", "pnnx", "nncf"]
    for package in import_packages:
        hiddenimports += collect_submodules(package, on_error="ignore")
        if is_cpu_variant and package == "openvino":
            datas += [
                item
                for item in collect_data_files(
                    package, excludes=RUNTIME_DATA_EXCLUDES
                )
                if _is_cpu_openvino_file(item[0])
            ]
        else:
            datas += collect_data_files(package, excludes=RUNTIME_DATA_EXCLUDES)
    if is_cpu_variant:
        # The vendored SAM2 wheel exposes a CUDA-only extension as a hidden
        # module even though the CPU inference path does not need it.
        hiddenimports = [item for item in hiddenimports if item != "sam2._C"]
        excludes.append("sam2._C")

    # Keep the small dist-info directories used by importlib.metadata in frozen builds.
    distributions = [
        "onnx",
        runtime_distribution,
        "opencv-python",
        "Pillow",
        "psutil",
        "ultralytics",
    ]
    if is_cpu_variant:
        distributions += ["openvino", "openvino-telemetry", "ncnn", "pnnx", "nncf"]
    for distribution in distributions:
        datas += copy_metadata(distribution)
    if not is_dev:
        datas += collect_data_files(
            "matplotlib",
            subdir="mpl-data",
            excludes=["**/sample_data/**"],
        )
        hiddenimports += [
            "matplotlib",
            "matplotlib.backends.backend_agg",
            "matplotlib.backends.backend_qtagg",
        ]
    hook_paths = [str(HOOKS_DIR)]
    runtime_hooks = []

a = Analysis(
    [str(ROOT / "src/main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=hook_paths,
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

if is_program_only:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ASSETS_DIR / "app_icon.ico"),
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(ASSETS_DIR / "app_icon.ico"),
    )

if not is_program_only:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=name,
    )


from __future__ import annotations

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


# Torch 2.12 on PyInstaller 6 needs .py sources alongside the PYZ archive.
# Without this, torch.distributed may call inspect.getsource() at import time
# and fail in packaged builds with "OSError: could not get source code".
module_collection_mode = "pyz+py"
warn_on_missing_hiddenimports = False

datas = collect_data_files(
    "torch",
    excludes=[
        "**/*.h",
        "**/*.hpp",
        "**/*.cuh",
        "**/*.lib",
        "**/*.cpp",
        "**/*.pyi",
        "**/*.cmake",
    ],
)
binaries = collect_dynamic_libs("torch")
hiddenimports = collect_submodules("torch")
excludedimports = ["torch.utils.tensorboard"]

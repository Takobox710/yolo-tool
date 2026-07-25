from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from src.services.model_export.types import InstalledExtension
from src.services.runtime.release_manifest import sha256_file


def verify_installed_extension(
    installed: InstalledExtension,
    progress: Callable[[str, int], None] | None = None,
    error_factory: Callable[[str], Exception] = ValueError,
) -> None:
    files = list(installed.manifest["files"].items())
    total = max(1, len(files))
    for index, (relative, digest) in enumerate(files, start=1):
        path = installed.root / Path(relative)
        if not path.is_file() or sha256_file(path) != str(digest).lower():
            raise error_factory(f"环境包文件校验失败：{relative}")
        if progress is not None:
            progress("校验安装文件", 65 + int(index * 20 / total))

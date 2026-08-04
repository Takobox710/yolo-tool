from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Type

from src.devtools.package_files import print_elapsed


def build_7z_archive(
    staging_root: Path,
    archive_path: Path,
    *,
    split: bool,
    volume_bytes: int,
    volume_count: int,
    error_type: Type[Exception],
    missing_message: str,
    failed_message: str,
    prefix: str,
) -> Path:
    seven_zip = shutil.which("7z") or shutil.which("7z.exe")
    if not seven_zip:
        raise error_type(missing_message)
    if split:
        for path in archive_path.parent.glob(f"{archive_path.name}.[0-9][0-9][0-9]"):
            path.unlink(missing_ok=True)
    else:
        archive_path.unlink(missing_ok=True)
    split_temp_dir = tempfile.TemporaryDirectory(dir=archive_path.parent, prefix=f".{archive_path.stem}.split-") if split else None
    command_path = Path(split_temp_dir.name) / archive_path.name if split_temp_dir is not None else archive_path
    started = time.perf_counter()
    print(f"{prefix}正在使用 7-Zip 压缩，下面显示实时进度：", flush=True)
    command = [seven_zip, "a", "-t7z", str(command_path), "*"]
    if split:
        command.append(f"-v{volume_bytes}b")
    command.extend(["-m0=lzma2", "-mx=5", "-ms=off", "-mmt=on", "-bsp1", "-bb0"])
    try:
        completed = subprocess.run(command, cwd=Path(staging_root).resolve(), check=False)
        if completed.returncode != 0:
            raise error_type(failed_message.format(code=completed.returncode))
        if split:
            volumes = sorted(command_path.parent.glob(f"{command_path.name}.[0-9][0-9][0-9]"))
            if not volumes or len(volumes) > volume_count:
                raise error_type(f"{prefix}归档最多允许生成 {volume_count} 个分卷，实际生成 {len(volumes)} 个。")
            if any(path.stat().st_size >= 1_073_741_824 for path in volumes):
                raise error_type(f"{prefix}归档分卷必须严格小于 1 GiB。")
            for path in volumes:
                path.replace(archive_path.parent / path.name)
            result = Path(f"{archive_path}.001")
        else:
            if not archive_path.is_file():
                raise error_type(f"{prefix}归档单卷未生成。")
            result = archive_path
        print_elapsed(f"{prefix}7-Zip 压缩完成", started, perf_counter=time.perf_counter)
        return result
    finally:
        if split_temp_dir is not None:
            split_temp_dir.cleanup()


__all__ = ["build_7z_archive"]

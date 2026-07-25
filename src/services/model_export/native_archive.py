from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from re import finditer
from typing import Callable

from src.services.runtime.windows_spawn import hidden_subprocess_kwargs


class NativeArchiveError(RuntimeError):
    """Raised when the bundled native 7-Zip helper cannot process an archive."""


def _candidate_executables() -> tuple[Path, ...]:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        candidates.extend(
            (
                executable_root / "_internal" / "7z.exe",
                executable_root / "7zz.exe",
                executable_root / "7z.exe",
            )
        )
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "7z.exe")
    for name in ("7z.exe", "7z", "7zz.exe", "7zz"):
        resolved = shutil.which(name)
        if resolved:
            candidates.append(Path(resolved))
    return tuple(candidates)


def find_native_7z() -> Path | None:
    for candidate in _candidate_executables():
        if candidate.is_file():
            return candidate
    return None


def _environment(executable: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join(
        [str(executable.parent), environment.get("PATH", "")]
    )
    return environment


def read_archive_member(archive_path: Path, member_name: str) -> bytes | None:
    executable = find_native_7z()
    if executable is None:
        return None
    completed = subprocess.run(
        [
            str(executable),
            "e",
            "-so",
            "-bd",
            "-bsp0",
            str(Path(archive_path).resolve()),
            member_name,
        ],
        capture_output=True,
        check=False,
        cwd=str(executable.parent),
        env=_environment(executable),
        timeout=120,
        **hidden_subprocess_kwargs(),
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def extract_archive(
    archive_path: Path,
    destination: Path,
    *,
    progress: Callable[[int], None] | None = None,
) -> None:
    executable = find_native_7z()
    if executable is None:
        raise NativeArchiveError("未找到原生 7-Zip 解压器。")
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    command = [
        str(executable),
        "x",
        "-y",
        "-aoa",
        "-bso0",
        "-bsp1",
        str(Path(archive_path).resolve()),
        f"-o{destination}",
    ]
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            cwd=str(executable.parent),
            env=_environment(executable),
            **hidden_subprocess_kwargs(),
        )
    except OSError as exc:
        raise NativeArchiveError("无法启动原生 7-Zip 解压器。") from exc

    output = bytearray()
    last_progress = -1
    pending = b""
    started_at = time.monotonic()
    stream = process.stdout
    try:
        while stream is not None:
            chunk = stream.read(4096)
            if not chunk:
                break
            output.extend(chunk)
            if progress is not None:
                combined = pending + chunk
                for match in finditer(rb"(?<!\d)(\d{1,3})%", combined):
                    value = min(int(match.group(1)), 100)
                    if value > last_progress:
                        last_progress = value
                        progress(value)
                pending = combined[-4:]
            if time.monotonic() - started_at > 1800:
                process.kill()
                raise NativeArchiveError("原生 7-Zip 解压超时。")
        return_code = process.wait(timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        process.kill()
        process.wait()
        raise NativeArchiveError("原生 7-Zip 解压失败。") from exc
    finally:
        if stream is not None:
            stream.close()

    if return_code != 0:
        detail = bytes(output).decode("utf-8", errors="replace").strip()
        raise NativeArchiveError(detail or "原生 7-Zip 解压失败。")
    if progress is not None and last_progress < 100:
        progress(100)

"""Compatibility facade for Release checks, downloads, and installer control."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
from threading import Event
from typing import Callable, Iterable
from urllib.request import urlopen

from src import APP_VERSION
from src.services.runtime.release_catalog import (
    GITHUB_LATEST_RELEASE_URL,
    GITHUB_REPOSITORY,
    ReleaseCheckResult,
    check_latest_release as _check_latest_release,
)
from src.services.runtime.install_instance import load_install_instance
from src.services.runtime.release_download import download_release_asset as _download_release_asset
from src.services.runtime.release_installer import (
    launch_installer,
    pause_installer,
    resume_installer,
    wait_if_paused as _wait_if_paused,
)
from src.services.runtime.release_versions import (
    is_newer_version,
    normalize_environment_version,
    normalize_release_version,
)


_DOWNLOADS_FOLDER_ID = (
    0x374DE290,
    0x123F,
    0x4565,
    (0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
)


def check_latest_release(current_version: str = APP_VERSION, *, timeout: float = 8.0) -> ReleaseCheckResult:
    return _check_latest_release(
        current_version,
        timeout=timeout,
        urlopen_fn=urlopen,
        load_install_instance_fn=load_install_instance,
    )


def _windows_downloads_directory() -> Path | None:
    if os.name != "nt":
        return None
    try:
        from ctypes import wintypes

        class _Guid(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        folder_id = _Guid(
            _DOWNLOADS_FOLDER_ID[0],
            _DOWNLOADS_FOLDER_ID[1],
            _DOWNLOADS_FOLDER_ID[2],
            (ctypes.c_ubyte * 8)(*_DOWNLOADS_FOLDER_ID[3]),
        )
        path = wintypes.LPWSTR()
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(_Guid), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(wintypes.LPWSTR)
        ]
        shell32.SHGetKnownFolderPath.restype = ctypes.c_long
        result = shell32.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path))
        if result != 0 or not path.value:
            return None
        resolved = Path(path.value)
        ctypes.WinDLL("ole32").CoTaskMemFree(ctypes.cast(path, ctypes.c_void_p))
        return resolved
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def downloads_directory() -> Path:
    resolved = _windows_downloads_directory()
    return resolved if resolved is not None else Path.home() / "Downloads"


def download_release_asset(
    asset_url: str,
    asset_name: str,
    *,
    download_dir: str | Path | None = None,
    timeout: float = 60.0,
    progress: Callable[[int, int], None] | None = None,
    pause_event: Event | None = None,
    stop_event: Event | None = None,
) -> Path:
    return _download_release_asset(
        asset_url,
        asset_name,
        download_dir=download_dir,
        timeout=timeout,
        progress=progress,
        pause_event=pause_event,
        stop_event=stop_event,
        urlopen_fn=urlopen,
        downloads_directory_fn=downloads_directory,
        wait_if_paused_fn=_wait_if_paused,
    )


def download_and_launch_installer(
    asset_url: str,
    asset_name: str,
    *,
    download_dir: str | Path | None = None,
    timeout: float = 60.0,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    path = download_release_asset(
        asset_url, asset_name, download_dir=download_dir, timeout=timeout, progress=progress
    )
    launch_installer(path)
    return path


def download_release_assets(
    assets: Iterable[tuple[str, str]],
    *,
    download_dir: str | Path | None = None,
    timeout: float = 60.0,
    progress: Callable[[str, int, int, int, int], None] | None = None,
    pause_event: Event | None = None,
    stop_event: Event | None = None,
) -> tuple[Path, ...]:
    selected = tuple((str(name), str(url)) for name, url in assets)
    if not selected:
        raise ValueError("未选择要下载的 Release 资源。")
    paths: list[Path] = []
    for index, (name, url) in enumerate(selected):
        paths.append(
            download_release_asset(
                url,
                name,
                download_dir=download_dir,
                timeout=timeout,
                pause_event=pause_event,
                stop_event=stop_event,
                progress=(
                    lambda downloaded, total, asset_name=name, asset_index=index: progress(
                        asset_name, asset_index, len(selected), downloaded, total
                    )
                    if progress
                    else None
                ),
            )
        )
    return tuple(paths)


__all__ = [
    "GITHUB_LATEST_RELEASE_URL",
    "GITHUB_REPOSITORY",
    "ReleaseCheckResult",
    "check_latest_release",
    "download_and_launch_installer",
    "download_release_asset",
    "download_release_assets",
    "downloads_directory",
    "is_newer_version",
    "launch_installer",
    "normalize_environment_version",
    "normalize_release_version",
    "pause_installer",
    "resume_installer",
]

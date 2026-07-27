from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src import APP_VERSION


GITHUB_REPOSITORY = "Takobox710/yolo-tool"
GITHUB_LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
_VERSION_PATTERN = re.compile(
    r"^[vV]?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?$"
)
_INSTALLER_NAME_PATTERN = re.compile(r"^YOLOTool_Setup_[0-9A-Za-z.-]+\.exe$", re.IGNORECASE)
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_DOWNLOADS_FOLDER_ID = (
    0x374DE290,
    0x123F,
    0x4565,
    (0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
)


@dataclass(frozen=True, slots=True)
class ReleaseCheckResult:
    current_version: str
    latest_version: str = ""
    release_url: str = ""
    release_notes: str = ""
    installer_asset_name: str = ""
    installer_asset_url: str = ""
    environment_asset_names: tuple[str, ...] = ()
    environment_asset_urls: tuple[str, ...] = ()
    update_available: bool = False
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.error and bool(self.latest_version)


def check_latest_release(
    current_version: str = APP_VERSION,
    *,
    timeout: float = 8.0,
) -> ReleaseCheckResult:
    """Read the latest stable GitHub Release without blocking the Qt thread."""
    request = Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "YOLOTool-version-check",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        return ReleaseCheckResult(current_version=str(current_version), error=str(exc))

    if not isinstance(payload, dict):
        return ReleaseCheckResult(
            current_version=str(current_version),
            error="GitHub Release 返回格式无效",
        )
    tag_name = str(payload.get("tag_name") or "").strip()
    latest_version = normalize_release_version(tag_name)
    if not latest_version:
        return ReleaseCheckResult(
            current_version=str(current_version),
            error="GitHub Release 缺少有效版本号",
        )
    (
        installer_asset_name,
        installer_asset_url,
        environment_asset_names,
        environment_asset_urls,
    ) = _parse_assets(
        payload.get("assets")
    )
    return ReleaseCheckResult(
        current_version=str(current_version),
        latest_version=latest_version,
        release_url=str(payload.get("html_url") or ""),
        release_notes=str(payload.get("body") or ""),
        installer_asset_name=installer_asset_name,
        installer_asset_url=installer_asset_url,
        environment_asset_names=environment_asset_names,
        environment_asset_urls=environment_asset_urls,
        update_available=is_newer_version(current_version, latest_version),
    )


def _parse_assets(payload) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    installer_name = ""
    installer_url = ""
    environment_names: list[str] = []
    environment_urls: list[str] = []
    if not isinstance(payload, list):
        return installer_name, installer_url, (), ()
    for asset in payload:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip()
        url = str(asset.get("browser_download_url") or "").strip()
        if not name:
            continue
        if not installer_name and _INSTALLER_NAME_PATTERN.fullmatch(name):
            installer_name = name
            installer_url = url
            continue
        if _is_environment_asset(name):
            environment_names.append(name)
            environment_urls.append(url)
    return (
        installer_name,
        installer_url,
        tuple(environment_names),
        tuple(environment_urls),
    )


def _is_environment_asset(name: str) -> bool:
    lowered = name.casefold()
    return lowered.endswith((".7z", ".zip")) and (
        lowered.startswith("yolotool_baseenv_")
        or lowered.startswith("yolotool_extraenv_")
    )


def downloads_directory() -> Path:
    """Return the Windows-known Downloads folder, including redirected locations."""
    resolved = _windows_downloads_directory()
    return resolved if resolved is not None else Path.home() / "Downloads"


def _windows_downloads_directory() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import ctypes
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
            ctypes.POINTER(_Guid),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.LPWSTR),
        ]
        shell32.SHGetKnownFolderPath.restype = ctypes.c_long
        result = shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, None, ctypes.byref(path)
        )
        if result != 0 or not path.value:
            return None
        resolved = Path(path.value)
        ctypes.WinDLL("ole32").CoTaskMemFree(ctypes.cast(path, ctypes.c_void_p))
        return resolved
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def download_and_launch_installer(
    asset_url: str,
    asset_name: str,
    *,
    download_dir: str | Path | None = None,
    timeout: float = 60.0,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Download a YOLOTool installer to Downloads and launch it."""
    path = download_release_asset(
        asset_url,
        asset_name,
        download_dir=download_dir,
        timeout=timeout,
        progress=progress,
    )
    launch_installer(path)
    return path


def download_release_asset(
    asset_url: str,
    asset_name: str,
    *,
    download_dir: str | Path | None = None,
    timeout: float = 60.0,
    progress: Callable[[int, int], None] | None = None,
    pause_event: Event | None = None,
) -> Path:
    parsed = urlparse(str(asset_url or ""))
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Release 资源下载地址无效。")
    safe_name = Path(str(asset_name or "")).name
    if safe_name != str(asset_name) or not (
        _INSTALLER_NAME_PATTERN.fullmatch(safe_name)
        or _is_environment_asset(safe_name)
    ):
        raise ValueError("Release 资源名称无效。")
    target_dir = Path(download_dir) if download_dir is not None else downloads_directory()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    partial = target.with_name(f"{target.name}.part")
    request = Request(
        str(asset_url),
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "YOLOTool-installer-download",
        },
    )
    downloaded = 0
    try:
        with urlopen(request, timeout=timeout) as response, partial.open("wb") as stream:
            headers = getattr(response, "headers", None)
            total = int((headers.get("Content-Length") if headers else 0) or 0)
            if progress:
                progress(0, total)
            while True:
                _wait_if_paused(pause_event)
                chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                stream.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
        os.replace(partial, target)
    except Exception:
        try:
            partial.unlink()
        except OSError:
            pass
        raise
    return target


def download_release_assets(
    assets: Iterable[tuple[str, str]],
    *,
    download_dir: str | Path | None = None,
    timeout: float = 60.0,
    progress: Callable[[str, int, int, int, int], None] | None = None,
    pause_event: Event | None = None,
) -> tuple[Path, ...]:
    """Download selected Release assets sequentially and report aggregate progress."""
    selected = tuple((str(name), str(url)) for name, url in assets)
    if not selected:
        raise ValueError("未选择要下载的 Release 资源。")
    paths: list[Path] = []
    total_assets = len(selected)
    for index, (name, url) in enumerate(selected):
        path = download_release_asset(
            url,
            name,
            download_dir=download_dir,
            timeout=timeout,
            pause_event=pause_event,
            progress=(
                lambda downloaded, total, asset_name=name, asset_index=index: progress(
                    asset_name,
                    asset_index,
                    total_assets,
                    downloaded,
                    total,
                )
                if progress
                else None
            ),
        )
        paths.append(path)
    return tuple(paths)


def launch_installer(path: str | Path):
    installer = str(Path(path).resolve())
    if os.name == "nt":
        return subprocess.Popen(
            [installer],
            cwd=str(Path(installer).parent),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    startfile = getattr(os, "startfile", None)
    if callable(startfile):
        startfile(installer)
        return None
    return subprocess.Popen([installer], cwd=str(Path(installer).parent))


def pause_installer(process) -> None:
    _installer_process(process).suspend()


def resume_installer(process) -> None:
    _installer_process(process).resume()


def _installer_process(process):
    if hasattr(process, "suspend") and hasattr(process, "resume"):
        return process
    if process is None or not getattr(process, "pid", None):
        raise ValueError("安装器进程不可暂停。")
    import psutil

    return psutil.Process(process.pid)


def _wait_if_paused(pause_event: Event | None) -> None:
    while pause_event is not None and pause_event.is_set():
        time.sleep(0.1)


def normalize_release_version(value: str) -> str:
    text = str(value or "").strip()
    match = _VERSION_PATTERN.match(text)
    if match is None:
        return ""
    major, minor, patch, _prerelease = match.groups()
    return ".".join((major, minor or "0", patch or "0"))


def is_newer_version(current_version: str, latest_version: str) -> bool:
    current = _version_key(current_version)
    latest = _version_key(latest_version)
    return current is not None and latest is not None and latest > current


def _version_key(value: str) -> tuple[int, int, int, int, str] | None:
    text = str(value or "").strip()
    match = _VERSION_PATTERN.match(text)
    if match is None:
        return None
    major, minor, patch, prerelease = match.groups()
    return (
        int(major),
        int(minor or 0),
        int(patch or 0),
        1 if not prerelease else 0,
        prerelease or "",
    )


__all__ = [
    "GITHUB_LATEST_RELEASE_URL",
    "GITHUB_REPOSITORY",
    "ReleaseCheckResult",
    "check_latest_release",
    "download_and_launch_installer",
    "download_release_assets",
    "download_release_asset",
    "downloads_directory",
    "is_newer_version",
    "launch_installer",
    "normalize_release_version",
    "pause_installer",
    "resume_installer",
]

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request


_INSTALLER_NAME_PATTERN = re.compile(
    r"^YOLOTool_Setup_[0-9A-Za-z.-]+\.exe$", re.IGNORECASE
)
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def _is_environment_asset(name: str) -> bool:
    lowered = name.casefold()
    return lowered.endswith((".7z", ".zip")) and (
        lowered.startswith("yolotool_baseenv_")
        or lowered.startswith("yolotool_extraenv_")
    )


def download_release_asset(
    asset_url: str,
    asset_name: str,
    *,
    download_dir: str | Path | None = None,
    timeout: float = 60.0,
    progress: Callable[[int, int], None] | None = None,
    pause_event=None,
    urlopen_fn,
    downloads_directory_fn,
    wait_if_paused_fn,
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
    target_dir = (
        Path(download_dir)
        if download_dir is not None
        else downloads_directory_fn()
    )
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
        with urlopen_fn(request, timeout=timeout) as response, partial.open("wb") as stream:
            headers = getattr(response, "headers", None)
            total = int((headers.get("Content-Length") if headers else 0) or 0)
            if progress:
                progress(0, total)
            while True:
                wait_if_paused_fn(pause_event)
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

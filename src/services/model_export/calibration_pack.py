from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from src.shared.paths import DATA_ROOT


GENERIC_CALIBRATION_PACK = "coco128"
GENERIC_CALIBRATION_URL = (
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip"
)
_IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
_CHUNK_SIZE = 1024 * 1024


def generic_calibration_cache_root(cache_root: str | Path | None = None) -> Path:
    if cache_root is not None:
        return Path(cache_root).expanduser().resolve()
    return (DATA_ROOT / "runtime" / "calibration_sets").resolve()


def generic_calibration_pack_path(
    cache_root: str | Path | None = None,
) -> Path | None:
    root = generic_calibration_cache_root(cache_root) / GENERIC_CALIBRATION_PACK
    if any(path.is_file() for path in root.rglob("*")) if root.is_dir() else False:
        return root
    return None


def download_generic_calibration_pack(
    *,
    cache_root: str | Path | None = None,
    progress: Callable[[int, int], None] | None = None,
    timeout: float = 60.0,
    urlopen_fn=urlopen,
) -> Path:
    existing = generic_calibration_pack_path(cache_root)
    if existing is not None:
        return existing

    root = generic_calibration_cache_root(cache_root)
    root.mkdir(parents=True, exist_ok=True)
    stage = root / f".{GENERIC_CALIBRATION_PACK}.download"
    archive = root / f".{GENERIC_CALIBRATION_PACK}.zip"
    shutil.rmtree(stage, ignore_errors=True)
    archive.unlink(missing_ok=True)
    request = Request(
        GENERIC_CALIBRATION_URL,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "YOLOTool-calibration-pack",
        },
    )
    downloaded = 0
    try:
        response_context = _open_download(request, timeout, urlopen_fn)
        with response_context as response, archive.open("wb") as stream:
            headers = getattr(response, "headers", None)
            total = int((headers.get("Content-Length") if headers else 0) or 0)
            if progress:
                progress(0, total)
            while True:
                chunk = response.read(_CHUNK_SIZE)
                if not chunk:
                    break
                stream.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)

        stage.mkdir(parents=True, exist_ok=True)
        _extract_archive_safely(archive, stage)
        if not any(path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES for path in stage.rglob("*")):
            raise ValueError("通用校准集压缩包中没有可用图片。")
        (stage / "SOURCE.txt").write_text(
            "YOLOTool 通用 INT8 校准集\n"
            f"来源：{GENERIC_CALIBRATION_URL}\n"
            "数据集：COCO128（图片来自 Microsoft COCO）\n"
            "用途：仅用于模型量化校准，不包含在 YOLOTool 安装包中。\n",
            encoding="utf-8",
        )
        target = root / GENERIC_CALIBRATION_PACK
        shutil.rmtree(target, ignore_errors=True)
        os.replace(stage, target)
        return target
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        archive.unlink(missing_ok=True)
        raise
    finally:
        archive.unlink(missing_ok=True)


def _extract_archive_safely(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            target = (destination / member.filename).resolve()
            if destination != target and destination not in target.parents:
                raise ValueError("通用校准集压缩包包含非法路径。")
        package.extractall(destination)


def _open_download(request: Request, timeout: float, urlopen_fn):
    if urlopen_fn is not urlopen:
        return urlopen_fn(request, timeout=timeout)
    try:
        import requests
    except ImportError:
        return urlopen_fn(request, timeout=timeout)
    response = requests.get(
        request.full_url,
        headers=dict(request.header_items()),
        stream=True,
        timeout=timeout,
    )
    response.raise_for_status()
    return _RequestsResponse(response)


class _RequestsResponse:
    def __init__(self, response) -> None:
        self._response = response
        self.headers = response.headers

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self._response.close()
        return False

    def read(self, size: int):
        return self._response.raw.read(size)


__all__ = [
    "GENERIC_CALIBRATION_PACK",
    "GENERIC_CALIBRATION_URL",
    "download_generic_calibration_pack",
    "generic_calibration_cache_root",
    "generic_calibration_pack_path",
]

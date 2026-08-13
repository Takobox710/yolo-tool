from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import tempfile
from pathlib import Path


class SamAsciiPathStager:
    """Expose SAM inputs through an ASCII-only temporary location on Windows."""

    def __init__(self) -> None:
        self._root: Path | None = None
        self._staged_paths: set[Path] = set()

    def stage_file(self, source: str | Path) -> Path:
        path = Path(source).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"SAM 输入文件不存在：{path}")
        compatible = _ascii_windows_path(path)
        if compatible is not None:
            return compatible

        target = self._stage_root() / f"{_path_token(path)}{path.suffix}"
        if not target.exists():
            _link_or_copy_file(path, target)
        self._staged_paths.add(target)
        return target

    def stage_directory(self, source: str | Path) -> Path:
        path = Path(source).resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"SAM 输入目录不存在：{path}")
        compatible = _ascii_windows_path(path)
        if compatible is not None:
            return compatible

        target = self._stage_root() / _path_token(path)
        if not target.exists():
            for item in path.rglob("*"):
                relative = item.relative_to(path)
                destination = target / relative
                if item.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif item.is_file():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    _link_or_copy_file(item, destination)
        self._staged_paths.add(target)
        return target

    def discard_file(self, path: str | Path) -> None:
        target = Path(path)
        if target not in self._staged_paths or not target.is_file():
            return
        target.unlink(missing_ok=True)
        self._staged_paths.discard(target)

    def close(self) -> None:
        if self._root is not None:
            shutil.rmtree(self._root, ignore_errors=True)
        self._root = None
        self._staged_paths.clear()

    def _stage_root(self) -> Path:
        if self._root is None:
            base = _ascii_temp_base()
            self._root = Path(tempfile.mkdtemp(prefix="yolo-tool-sam-", dir=base))
        return self._root


def _ascii_windows_path(path: Path) -> Path | None:
    value = str(path)
    if value.isascii():
        return path
    if os.name != "nt":
        return None
    buffer_length = ctypes.windll.kernel32.GetShortPathNameW(value, None, 0)
    if buffer_length <= 0:
        return None
    buffer = ctypes.create_unicode_buffer(buffer_length)
    if ctypes.windll.kernel32.GetShortPathNameW(value, buffer, buffer_length) <= 0:
        return None
    short_path = Path(buffer.value)
    return short_path if str(short_path).isascii() else None


def _ascii_temp_base() -> Path:
    candidates = [Path(tempfile.gettempdir())]
    if os.name == "nt":
        public_root = Path(os.environ.get("PUBLIC", r"C:\\Users\\Public"))
        candidates.extend((public_root / "Documents", public_root, Path(r"C:\\Temp")))
    for candidate in candidates:
        compatible = _ascii_windows_path(candidate.resolve())
        if compatible is None:
            continue
        base = compatible / "YOLOToolRuntime"
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        if str(base).isascii():
            return base
    raise RuntimeError("无法创建 ASCII 临时目录，SAM 无法兼容当前包含中文字符的路径。")


def _path_token(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:24]


def _link_or_copy_file(source: Path, target: Path) -> None:
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


__all__ = ["SamAsciiPathStager"]

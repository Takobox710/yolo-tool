from __future__ import annotations

import ctypes
import shutil
import subprocess
from pathlib import Path


def show_message(message: str, title: str = "YOLOTool") -> None:
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)


def main() -> None:
    project_root = Path(__file__).resolve().parent
    pixi_path = shutil.which("pixi")
    if not pixi_path:
        show_message("未找到 pixi，请先安装 pixi 并确保它已加入 PATH。")
        return

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [pixi_path, "run", "app"],
            cwd=project_root,
            creationflags=creation_flags,
        )
    except Exception as exc:
        show_message(f"程序启动失败：{exc}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import subprocess
import sys

from PySide6.QtCore import QThread, Signal

from src.shared.paths import ROOT
from src.services.runtime import hidden_subprocess_kwargs


class ModelLabelsWorker(QThread):
    finished_with_labels = Signal(object)
    failed = Signal(str)

    def __init__(self, model_path: str):
        super().__init__()
        self.model_path = model_path

    def _cli_command(self, flag: str, *args: str) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, flag, *args]
        return [sys.executable, "-m", "src.main", flag, *args]

    def run(self):
        try:
            result = subprocess.run(
                self._cli_command("--yolo-model-labels", self.model_path),
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                **hidden_subprocess_kwargs(),
            )
            if result.returncode != 0:
                raise RuntimeError(
                    result.stderr.strip() or f"模型类别进程退出码：{result.returncode}"
                )
            labels = json.loads(result.stdout or "[]")
            self.finished_with_labels.emit(labels)
        except Exception as exc:  # pragma: no cover - background safety
            self.failed.emit(str(exc))


__all__ = ["ModelLabelsWorker"]

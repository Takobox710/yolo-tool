from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPlainTextEdit, QVBoxLayout


class CommandDialog(QDialog):
    def __init__(self, command: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑训练命令")
        layout = QVBoxLayout(self)
        self.command_edit = QPlainTextEdit(" ".join(command))
        layout.addWidget(self.command_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_command(self) -> list[str]:
        return self.command_edit.toPlainText().strip().split()

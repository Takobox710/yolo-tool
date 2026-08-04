from __future__ import annotations

from src.shared.qt import QFileDialog, QComboBox, QLineEdit


def choose_dir(page, edit: QLineEdit) -> None:
    current = page.resolve_path_text(edit) if edit.text() else str(page.project_root())
    path = QFileDialog.getExistingDirectory(page, "选择文件夹", current)
    if path:
        edit.setText(page.display_path(path))


def choose_file(page, edit: QLineEdit, caption: str = "选择文件") -> None:
    current = page.resolve_path_text(edit) if edit.text() else str(page.project_root())
    path, _ = QFileDialog.getOpenFileName(page, caption, current, "All Files (*)")
    if path:
        edit.setText(page.display_path(path))


def choose_pt_for_combo(page, combo: QComboBox) -> None:
    models_dir = page.project_root() / "data" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    path, _ = QFileDialog.getOpenFileName(
        page, "选择模型文件", str(models_dir), "PyTorch 模型 (*.pt);;所有文件 (*)"
    )
    if path:
        combo.setCurrentText(page.display_path(path))

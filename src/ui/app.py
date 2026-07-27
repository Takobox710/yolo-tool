from __future__ import annotations

from src.shared.qt import QApplication, QFont, Qt
from src.ui.shell.window import WorkbenchWindow, build_style
from src.ui.shared.assets import load_app_icon


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    app.setStyleSheet(build_style())
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())



from __future__ import annotations

from src.shared.paths import ICON_PNG
from src.shared.qt import QApplication, QFont, QIcon, Qt
from src.ui.shell.window import WorkbenchWindow, build_style


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    if ICON_PNG.exists():
        app.setWindowIcon(QIcon(str(ICON_PNG)))
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    app.setStyleSheet(build_style())
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())



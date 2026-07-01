from __future__ import annotations

from scr.ui.qt import QApplication, QFont, Qt
from scr.ui.window import WorkbenchWindow, build_style


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    app.setStyleSheet(build_style())
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())

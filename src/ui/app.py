from __future__ import annotations

from src.shared.qt import QApplication, QFont, Qt
from src.services.settings import load_app_state
from src.ui.shell.window import WorkbenchWindow
from src.ui.shared.assets import load_app_icon
from src.ui.shared.theme import apply_theme


def run_app() -> None:
    app = QApplication.instance() or QApplication([])
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    app_state = load_app_state()
    theme_mode = apply_theme(app, app_state.theme_mode)
    window = WorkbenchWindow(theme_mode=theme_mode)
    window.show()
    raise SystemExit(app.exec())



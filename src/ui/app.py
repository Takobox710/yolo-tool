from __future__ import annotations

from src.services.runtime import check_runtime_compatibility
from src.shared.paths import ICON_PNG
from src.shared.qt import QApplication, QFont, QIcon, QMessageBox, Qt
from src.ui.shell.window import WorkbenchWindow, build_style


def run_app() -> None:
    compatibility = check_runtime_compatibility()
    if not compatibility.compatible:
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None,
            "运行环境不兼容",
            f"当前运行环境无法启动程序。\n{compatibility.reason}\n请安装匹配的环境更新包。",
        )
        raise SystemExit(78)

    app = QApplication.instance() or QApplication([])
    if ICON_PNG.exists():
        app.setWindowIcon(QIcon(str(ICON_PNG)))
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    app.setStyleSheet(build_style())
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())



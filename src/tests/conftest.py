import gc
import pytest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shared.qt import QApplication, QEvent


_QT_APP = None


def _cleanup_qt_widgets(app):
    for widget in app.topLevelWidgets():
        widget.hide()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


@pytest.fixture(autouse=True)
def cleanup_qt_top_level_widgets():
    yield
    global _QT_APP
    app = QApplication.instance()
    if app is None:
        return
    _QT_APP = app
    _cleanup_qt_widgets(app)


@pytest.fixture(scope="session", autouse=True)
def shutdown_qt_application():
    yield
    global _QT_APP
    app = _QT_APP or QApplication.instance()
    if app is None:
        return
    _cleanup_qt_widgets(app)
    app.exit(0)
    _QT_APP = None
    del app
    gc.collect()

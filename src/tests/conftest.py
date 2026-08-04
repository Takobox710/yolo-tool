import gc
import os
import pytest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.shared.qt import QApplication, QEvent


_QT_APP = None


@pytest.fixture(scope="session")
def qt_app():
    """Provide the single offscreen Qt application used by UI tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    return app


def _cleanup_qt_widgets(app):
    for widget in app.topLevelWidgets():
        widget.hide()
        widget.deleteLater()
    # A second pass releases page-owned workers queued by the first deletion pass.
    for _ in range(2):
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


def pytest_configure(config):
    for name, description in {
        "workflow_annotation": "annotation UI and service workflows",
        "workflow_model_export": "model export UI and service workflows",
        "workflow_release": "release update and runtime workflows",
        "workflow_installer": "Windows installer and packaging workflows",
    }.items():
        config.addinivalue_line("markers", f"{name}: {description}")


def pytest_collection_modifyitems(config, items):
    del config
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        if "/annotation/" in path:
            item.add_marker("workflow_annotation")
        elif "/model_export/" in path or "/data_processing/" in path:
            item.add_marker("workflow_model_export")
        elif "/settings/" in path or "/runtime/" in path:
            item.add_marker("workflow_release")
        elif "/integration/" in path and ("installer" in path or "packaging" in path):
            item.add_marker("workflow_installer")

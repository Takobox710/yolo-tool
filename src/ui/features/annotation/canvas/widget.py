from __future__ import annotations

from PySide6.QtCore import QTimer

from src.shared.qt import QSizePolicy, Qt, QWidget
from src.ui.features.annotation.canvas.commands import AnnotationCanvasCommandMixin
from src.ui.features.annotation.canvas.context_menu import AnnotationCanvasContextMenuMixin
from src.ui.features.annotation.canvas.drawing import AnnotationCanvasDrawingMixin
from src.ui.features.annotation.canvas.history import AnnotationCanvasHistoryMixin
from src.ui.features.annotation.canvas.hit_test import AnnotationCanvasHitTestMixin
from src.ui.features.annotation.canvas.interaction import AnnotationCanvasInteractionMixin
from src.ui.features.annotation.canvas.lifecycle import (
    SAM_SUPPORTED_SHAPES,
    AnnotationCanvasLifecycleMixin,
)
from src.ui.features.annotation.canvas.render import AnnotationCanvasRenderMixin
from src.ui.features.annotation.canvas.state import initialize_canvas_state
from src.ui.features.annotation.canvas.status import AnnotationCanvasStatusMixin


class AnnotationCanvas(
    AnnotationCanvasLifecycleMixin,
    AnnotationCanvasCommandMixin,
    AnnotationCanvasHistoryMixin,
    AnnotationCanvasContextMenuMixin,
    AnnotationCanvasDrawingMixin,
    AnnotationCanvasHitTestMixin,
    AnnotationCanvasInteractionMixin,
    AnnotationCanvasRenderMixin,
    AnnotationCanvasStatusMixin,
    QWidget,
):
    def __init__(self):
        super().__init__()
        self.setObjectName("annotationCanvas")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(420, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        initialize_canvas_state(self)
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_flash)


__all__ = ["AnnotationCanvas", "SAM_SUPPORTED_SHAPES"]

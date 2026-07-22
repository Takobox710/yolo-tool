from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QScrollArea, QVBoxLayout, QWidget

from PIL import Image

from src.shared.paths import ICON_PNG


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
    qimage = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


def load_nav_icon(device_pixel_ratio: float = 1.0) -> QPixmap | None:
    if ICON_PNG.exists():
        pix = QPixmap(str(ICON_PNG))
        if not pix.isNull():
            dpr = max(float(device_pixel_ratio), 1.0)
            physical_size = max(1, round(28 * dpr))
            pix = pix.scaled(
                physical_size,
                physical_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pix.setDevicePixelRatio(dpr)
            return pix
    return None


class Card(QFrame):
    def __init__(self, title: str = ""):
        super().__init__()
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("sectionTitle")
            self.layout.addWidget(label)


class CardNoPad(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)


class ImageView(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("imageView")
        self.setMinimumHeight(180)
        self._pixmap = None

    def set_pil_image(self, image: Image.Image):
        self._pixmap = pil_to_pixmap(image)
        self._rescale()

    def clear_image(self, text: str = ""):
        self._pixmap = None
        self.clear()
        if text:
            self.setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._pixmap is None:
            return
        self.setPixmap(self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))


class PageScrollArea(QScrollArea):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "inner_page", None):
            self.inner_page.setMaximumWidth(self.viewport().width())


def scroll_page(widget: QWidget):
    scroll = PageScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(widget)
    scroll.inner_page = widget
    return scroll



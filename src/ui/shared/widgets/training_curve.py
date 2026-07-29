from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel

from src.ui.shared.widgets.chart_primitives import _begin_chart_paint, _finish_chart_paint

class TrainingCurveWidget(QLabel):
    """Responsive training curve renderer with a compact summary header."""

    def __init__(self):
        super().__init__()
        self.setObjectName("chartView")
        self.setMinimumHeight(180)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._data: dict[str, list[float]] = {}

    def set_curve_data(self, data: Mapping[str, Sequence[float]]) -> None:
        self._data = {key: [float(value) for value in values] for key, values in data.items()}
        self._redraw()

    def resizeEvent(self, event):  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._redraw()

    def refresh_for_device_pixel_ratio(self) -> None:
        self._redraw()

    def _redraw(self) -> None:
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        pixmap, painter, dpr = _begin_chart_paint(self, width, height)

        map50 = self._find_column("metrics/mAP50(", exclude="95")
        box_loss = "val/box_loss" if self._data.get("val/box_loss") else "train/box_loss"
        epoch_count = max((len(values) for values in self._data.values()), default=0)
        epoch_values = self._epoch_values(epoch_count)
        summary = [("Epoch", str(epoch_count or "-"))]
        left = 34
        self._draw_summary(painter, summary, width, left)

        top = 42
        right = max(width - 18, left + 1)
        bottom = max(height - 28, top + 1)
        chart_w = right - left
        chart_h = bottom - top
        self._draw_axes(painter, left, top, chart_w, chart_h, epoch_values)

        if not self._data:
            painter.setPen(QColor("#94A2AD"))
            painter.setFont(QFont("Microsoft YaHei UI", 11))
            painter.drawText(left, top, chart_w, chart_h, Qt.AlignmentFlag.AlignCenter, "暂无训练记录\n请先进行模型训练")
            _finish_chart_paint(self, pixmap, painter, dpr)
            return

        series = []
        if map50:
            series.append((map50, QColor("#246BFE"), "mAP50", False))
        if self._data.get(box_loss):
            series.append((box_loss, QColor("#D94A38"), "Box Loss", True))
        self._draw_curve_lines(painter, (left, top, chart_w, chart_h), series, epoch_values)
        self._draw_legend(painter, width, height, series)

        _finish_chart_paint(self, pixmap, painter, dpr)

    def _find_column(self, prefix: str, exclude: str = "") -> str | None:
        for key in self._data:
            if key.startswith(prefix) and (not exclude or exclude not in key):
                return key
        return None

    def _epoch_values(self, epoch_count: int) -> list[float]:
        epochs = self._data.get("epoch", [])
        if len(epochs) >= epoch_count:
            return epochs[:epoch_count]
        return [float(index) for index in range(epoch_count)]

    def _epoch_ticks(self, epoch_values: list[float]) -> list[tuple[float, float]]:
        if not epoch_values:
            return []
        if len(epoch_values) == 1:
            return [(epoch_values[0], 0.0)]
        tick_count = min(6, len(epoch_values))
        indices = [round(index * (len(epoch_values) - 1) / (tick_count - 1)) for index in range(tick_count)]
        return [
            (epoch_values[index], index / (len(epoch_values) - 1))
            for index in dict.fromkeys(indices)
        ]

    def _draw_summary(
        self,
        painter: QPainter,
        summary: list[tuple[str, str]],
        width: int,
        axis_left: int,
    ) -> None:
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        axis_font = QFont("Microsoft YaHei UI", 8)
        x = max(0, axis_left - 8 - QFontMetrics(axis_font).horizontalAdvance("1.0"))
        for label, value in summary:
            text = f"{label}: {value}"
            text_w = painter.fontMetrics().horizontalAdvance(text) + 18
            if x + text_w > width - 8:
                break
            painter.setPen(QColor("#5B6773"))
            painter.drawText(x, 12, text_w, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            x += text_w + 10

    def _draw_axes(
        self,
        painter: QPainter,
        x: int,
        y: int,
        width: int,
        height: int,
        epoch_values: list[float],
    ) -> None:
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawLine(x, y + height, x + width, y + height)
        painter.drawLine(x, y, x, y + height)
        painter.setPen(QPen(QColor("#E9EEF3"), 1))
        for tick in range(1, 5):
            ty = y + round(height * tick / 5)
            painter.drawLine(x, ty, x + width, ty)
        painter.setPen(QColor("#000000"))
        for tick in range(6):
            value = tick / 5
            ty = y + height - round(value * height)
            painter.drawText(0, ty - 8, x - 8, 16, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value:.1f}")
        axis_font_metrics = painter.fontMetrics()
        for epoch, position in self._epoch_ticks(epoch_values):
            label = f"{epoch:g}"
            label_width = max(28, axis_font_metrics.horizontalAdvance(label) + 8)
            tx = x + round(position * width)
            painter.drawText(
                tx - label_width // 2,
                y + height + 6,
                label_width,
                16,
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

    def _draw_curve_lines(
        self,
        painter: QPainter,
        rect: tuple[int, int, int, int],
        series,
        epoch_values: list[float],
    ) -> None:
        x, y, width, height = rect
        for key, color, _label, is_loss in series:
            vals = self._data.get(key, [])
            if not vals:
                continue
            max_value = max(vals) if is_loss else 1.0
            min_value = min(vals) if is_loss else 0.0
            if max_value == min_value:
                max_value = min_value + 1.0
            curve_epochs = epoch_values[: len(vals)]
            epoch_start = curve_epochs[0] if curve_epochs else 0.0
            epoch_end = curve_epochs[-1] if curve_epochs else max(len(vals) - 1, 1)
            epoch_span = epoch_end - epoch_start or 1.0
            path = QPainterPath()
            for index, value in enumerate(vals):
                epoch = curve_epochs[index] if index < len(curve_epochs) else float(index)
                px = x + ((epoch - epoch_start) / epoch_span) * width
                py = y + height - ((value - min_value) / (max_value - min_value)) * height
                if index == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, 2))
            painter.drawPath(path)

            last_x = x + width
            last_y = y + height - ((vals[-1] - min_value) / (max_value - min_value)) * height
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(last_x - 3), int(last_y - 3), 6, 6)

    def _draw_legend(self, painter: QPainter, width: int, height: int, series) -> None:
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        fm = painter.fontMetrics()
        active = [(color, label) for key, color, label, _ in series if self._data.get(key)]
        legend_w = sum(fm.horizontalAdvance(label) + 30 for color, label in active)
        x = max(46, width - legend_w - 14)
        y = 14
        for color, label in active:
            painter.setPen(QPen(color, 3))
            painter.drawLine(x, y + 8, x + 16, y + 8)
            painter.setPen(QColor("#14233A"))
            item_w = fm.horizontalAdvance(label) + 30
            painter.drawText(x + 20, y, item_w - 20, 16, Qt.AlignmentFlag.AlignVCenter, label)
            x += item_w

    def _format_axis(self, value: float) -> str:
        if value < 0:
            return "-"
        return f"{value:.3f}" if abs(value) < 1 else f"{value:.2f}"

    def _format_percent(self, value: float) -> str:
        return "-" if value < 0 else f"{value * 100:.1f}%"

    def _last_value(self, key: str | None) -> float:
        if not key or not self._data.get(key):
            return -1.0
        return self._data[key][-1]
__all__ = ["TrainingCurveWidget"]

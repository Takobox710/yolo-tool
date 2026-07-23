from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import ceil

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel


_BAR_TOP_PADDING = 27


def _begin_chart_paint(widget: QLabel, width: int, height: int):
    dpr = max(float(widget.devicePixelRatioF()), 1.0)
    pixmap = QPixmap(
        max(round(width * dpr), 1),
        max(round(height * dpr), 1),
    )
    pixmap.fill(Qt.GlobalColor.white)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(dpr, dpr)
    return pixmap, painter, dpr


def _finish_chart_paint(widget: QLabel, pixmap: QPixmap, painter: QPainter, dpr: float) -> None:
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    widget.setPixmap(pixmap)


class DatasetDistributionWidget(QLabel):
    """Responsive dataset split bar chart for the home page."""

    def __init__(self):
        super().__init__()
        self.setObjectName("chartView")
        self.setMinimumHeight(200)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._single_class_name = ""
        self._summary_title = ""
        self._show_total_summary = True
        self._folder_mode = False
        self._chart_mode = "standard"
        self._bars: list[tuple[str, int]] = []

    def set_single_class_counts(
        self, split_counts: Mapping[str, int], class_name: str
    ) -> None:
        counts = {
            split: max(int(split_counts.get(split, 0)), 0)
            for split in ("train", "val", "test")
        }
        self.set_standard_counts(sum(counts.values()), counts, 0, class_name)

    def set_standard_counts(
        self,
        total_images: int,
        split_counts: Mapping[str, int],
        unannotated_images: int,
        class_name: str = "",
    ) -> None:
        total = max(int(total_images), 0)
        counts = {
            split: max(int(split_counts.get(split, 0)), 0)
            for split in ("train", "val", "test")
        }
        unannotated = max(int(unannotated_images), 0)
        self._single_class_name = str(class_name or "").strip()
        self._summary_title = ""
        self._show_total_summary = False
        self._folder_mode = False
        self._chart_mode = "standard"
        split_bars = [
            ("训练", counts["train"]),
            ("验证", counts["val"]),
            ("测试", counts["test"]),
        ]
        if unannotated:
            split_bars.append(("未标注", unannotated))
        sorted_bars = sorted(
            split_bars,
            key=lambda item: item[1],
            reverse=True,
        )
        self._bars = [("总图片", total), *sorted_bars]
        self._redraw()

    def set_folder_counts(
        self, total_images: int, annotated_images: int, class_name: str = "文件夹统计"
    ) -> None:
        total = max(int(total_images), 0)
        annotated = min(max(int(annotated_images), 0), total)
        self.set_standard_counts(
            total,
            {"train": 0, "val": 0, "test": 0},
            total - annotated,
            class_name or "文件夹统计",
        )

    def set_multi_class_counts(self, class_counts: Mapping[str, int]) -> None:
        self._single_class_name = ""
        self._summary_title = "总计"
        self._show_total_summary = True
        self._folder_mode = False
        self._chart_mode = "multi"
        sorted_counts = sorted(
            (
                (str(name), max(int(count), 0))
                for name, count in class_counts.items()
                if str(name).strip()
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        total = sum(count for _name, count in sorted_counts)
        self._bars = [
            ("总标注", total),
            *sorted_counts,
        ]
        self._redraw()

    def set_counts(self, split_counts: Mapping[str, int], class_names: Sequence[str]) -> None:
        class_name = next((str(name) for name in class_names if str(name).strip()), "")
        self.set_single_class_counts(split_counts, class_name)

    def resizeEvent(self, event):  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._redraw()

    def refresh_for_device_pixel_ratio(self) -> None:
        self._redraw()

    def _redraw(self) -> None:
        width = max(self.width(), 1)
        height = max(self.height(), 1)
        pixmap, painter, dpr = _begin_chart_paint(self, width, height)

        if self._chart_mode == "multi" and self._bars:
            total = self._bars[0][1]
        else:
            total = self._bars[0][1] if self._bars else 0
        colors = [
            QColor("#64748B"),
            QColor("#3B82F6"),
            QColor("#22A06B"),
            QColor("#F2A900"),
            QColor("#EF4444"),
            QColor("#8B5CF6"),
            QColor("#06B6D4"),
            QColor("#F97316"),
        ]

        painter.setPen(QColor("#14233A"))
        painter.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        if self._show_total_summary:
            painter.drawText(
                18,
                7,
                max(width - 36, 1),
                22,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"总标注 {total} 个",
            )
        elif self._single_class_name:
            painter.drawText(
                18,
                7,
                max(width - 36, 1),
                22,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self._single_class_name,
            )

        left = 20
        right = max(width - 22, left + 1)
        has_header = self._show_total_summary or bool(self._single_class_name)
        plot_top = 25 if has_header else 7
        axis_top = 38 if has_header else 15
        bottom = max(height - 33, axis_top + 1)
        chart_w = right - left
        chart_h = bottom - plot_top
        axis_h = bottom - axis_top
        painter.setPen(QPen(QColor("#D7E0EA"), 1))
        painter.drawLine(left, bottom, right, bottom)
        painter.drawLine(left, axis_top, left, bottom)
        painter.setPen(QPen(QColor("#EDF2F7"), 1))
        for tick in range(1, 5):
            y = bottom - round(axis_h * tick / 5)
            painter.drawLine(left, y, right, y)

        max_count = max((count for _label, count in self._bars), default=0)
        max_count = max(max_count, 1)
        percent_total = self._percent_total()
        bar_count = max(len(self._bars), 1)
        slot_w = chart_w / bar_count
        bar_width = max(18, min(72, int(slot_w * 0.42)))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        for index, (label_text, count) in enumerate(self._bars):
            if label_text in {"总照片", "总图片", "总标注"}:
                percent = 100.0 if count else 0.0
            elif percent_total:
                percent = count / percent_total * 100
            else:
                percent = 0.0
            bar_h = (
                round((count / max_count) * (chart_h - _BAR_TOP_PADDING))
                if count
                else 0
            )
            x = round(left + slot_w * index + (slot_w - bar_width) / 2)
            y = bottom - bar_h
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colors[index % len(colors)])
            painter.drawRect(x, y, bar_width, bar_h)
            painter.setPen(QColor("#14233A"))
            painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
            painter.drawText(
                x - 18,
                max(plot_top, y - _BAR_TOP_PADDING),
                bar_width + 36,
                _BAR_TOP_PADDING,
                Qt.AlignmentFlag.AlignCenter,
                str(count),
            )
            painter.setFont(QFont("Microsoft YaHei UI", 9))
            painter.setPen(QColor("#5B6773"))
            label = f"{label_text} {percent:.0f}%"
            painter.drawText(
                round(left + slot_w * index),
                bottom + 8,
                round(slot_w),
                30,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                self._wrap_text(label, ceil(slot_w)),
            )

        if not total or not self._bars:
            painter.setPen(QColor("#94A2AD"))
            painter.setFont(QFont("Microsoft YaHei UI", 10))
            painter.drawText(
                left,
                axis_top,
                chart_w,
                axis_h,
                Qt.AlignmentFlag.AlignCenter,
                "暂无已划分的数据集",
            )

        painter.end()
        pixmap.setDevicePixelRatio(dpr)
        self.setPixmap(pixmap)

    def _percent_total(self) -> int:
        if self._show_total_summary:
            return sum(count for _label, count in self._bars[1:])
        return self._bars[0][1] if self._bars else 0

    def _wrap_text(self, text: str, max_width: int) -> str:
        if not text:
            return text
        fm = self.fontMetrics()
        if fm.horizontalAdvance(text) <= max_width:
            return text
        parts = text.split(" ")
        lines: list[str] = []
        current = ""
        for part in parts:
            candidate = part if not current else f"{current} {part}"
            if fm.horizontalAdvance(candidate) <= max_width or not current:
                current = candidate
                continue
            lines.append(current)
            current = part
        if current:
            lines.append(current)
        return "\n".join(lines[:2])


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
        summary = [("Epoch", str(epoch_count or "-"))]
        left = 34
        self._draw_summary(painter, summary, width, left)

        top = 42
        right = max(width - 18, left + 1)
        bottom = max(height - 28, top + 1)
        chart_w = right - left
        chart_h = bottom - top
        self._draw_axes(painter, left, top, chart_w, chart_h)

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
        self._draw_curve_lines(painter, (left, top, chart_w, chart_h), series)
        self._draw_legend(painter, width, height, series)

        _finish_chart_paint(self, pixmap, painter, dpr)

    def _find_column(self, prefix: str, exclude: str = "") -> str | None:
        for key in self._data:
            if key.startswith(prefix) and (not exclude or exclude not in key):
                return key
        return None

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

    def _draw_axes(self, painter: QPainter, x: int, y: int, width: int, height: int) -> None:
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
            tx = x + round(value * width)
            painter.drawText(0, ty - 8, x - 8, 16, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value:.1f}")
            painter.drawText(tx - 14, y + height + 6, 28, 16, Qt.AlignmentFlag.AlignCenter, f"{value:.1f}")

    def _draw_curve_lines(self, painter: QPainter, rect: tuple[int, int, int, int], series) -> None:
        x, y, width, height = rect
        for key, color, _label, is_loss in series:
            vals = self._data.get(key, [])
            if not vals:
                continue
            max_value = max(vals) if is_loss else 1.0
            min_value = min(vals) if is_loss else 0.0
            if max_value == min_value:
                max_value = min_value + 1.0
            path = QPainterPath()
            for index, value in enumerate(vals):
                px = x + (index / max(len(vals) - 1, 1)) * width
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

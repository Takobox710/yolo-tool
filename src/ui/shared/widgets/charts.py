from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import ceil

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel


from src.ui.shared.widgets.chart_primitives import (
    _BAR_TOP_PADDING,
    _CHART_FRAME_COLOR,
    _CHART_FRAME_RADIUS,
    _begin_chart_paint,
    _finish_chart_paint,
)

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

from src.ui.shared.widgets.training_curve import TrainingCurveWidget

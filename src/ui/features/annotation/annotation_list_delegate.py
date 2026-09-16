from __future__ import annotations

from src.shared.qt import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem, Qt
from src.ui.shared.theme import current_colors


KEYPOINT_WARNING = "（未被标注框框住）"


class AnnotationListDelegate(QStyledItemDelegate):
    """Keep the keypoint warning distinct without replacing list item behavior."""

    def paint(self, painter, option, index):  # noqa: N802 - Qt API name
        if not bool(index.data(Qt.ItemDataRole.UserRole)):
            super().paint(painter, option, index)
            return

        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        text = styled.text
        styled.text = ""
        style = styled.widget.style() if styled.widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, styled.widget)

        warning = KEYPOINT_WARNING
        label = text[: -len(warning)] if text.endswith(warning) else text
        text_rect = styled.rect.adjusted(4, 0, -4, 0)
        metrics = styled.fontMetrics
        warning_width = metrics.horizontalAdvance(warning)
        label_width = max(0, text_rect.width() - warning_width)
        visible_label = metrics.elidedText(label, Qt.TextElideMode.ElideRight, label_width)
        label_color = (
            styled.palette.highlightedText().color()
            if styled.state & QStyle.StateFlag.State_Selected
            else styled.palette.text().color()
        )

        painter.save()
        painter.setFont(styled.font)
        painter.setPen(label_color)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, visible_label)
        painter.setPen(current_colors().warning)
        warning_rect = text_rect.adjusted(metrics.horizontalAdvance(visible_label), 0, 0, 0)
        painter.drawText(warning_rect, Qt.AlignmentFlag.AlignVCenter, warning)
        painter.restore()


__all__ = ["AnnotationListDelegate", "KEYPOINT_WARNING"]

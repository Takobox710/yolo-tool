from __future__ import annotations

from PySide6.QtGui import QAction

from src.shared.qt import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    Qt,
    QWidget,
    QWidgetAction,
)


class AnnotationMenuMixin:
    def _confirm_file_action(self, title: str, message: str) -> bool:
        return (
            QMessageBox.question(self, title, message)
            == QMessageBox.StandardButton.Yes
        )

    def _add_menu_button_action(
        self,
        menu: QMenu,
        text: str,
        *,
        color: str = "#14233A",
        hover_background: str = "#F5F8FB",
        trailing_text: str = "",
        show_submenu_arrow: bool = False,
    ) -> QWidgetAction:
        action = QWidgetAction(menu)
        container = QWidget(menu)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(26, 6, 26, 6)
        layout.setSpacing(12)
        label = QLabel(text, container)
        label.setStyleSheet(f"color: {color};")
        layout.addWidget(label)
        layout.addStretch(1)
        if trailing_text:
            trailing_label = QLabel(trailing_text, container)
            trailing_label.setStyleSheet("color: #6B7280;")
            trailing_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(trailing_label)
        if show_submenu_arrow:
            arrow_label = QLabel("›", container)
            arrow_label.setStyleSheet("color: #6B7280;")
            arrow_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(arrow_label)
        container.setStyleSheet(
            f"QWidget {{ background: transparent; }}"
            f"QWidget:hover {{ background: {hover_background}; }}"
        )
        container.mousePressEvent = lambda _event: action.trigger()
        action.setDefaultWidget(container)
        menu.addAction(action)
        return action

    def _add_danger_menu_action(
        self,
        menu: QMenu,
        text: str,
        *,
        trailing_text: str = "",
    ) -> QWidgetAction:
        return self._add_menu_button_action(
            menu,
            text,
            color="#C62828",
            hover_background="#FCE8E6",
            trailing_text=trailing_text,
        )

    def open_file_list_context_menu(self, pos) -> None:
        row = self.file_list.indexAt(pos).row()
        if not (0 <= row < len(self.image_items)):
            return
        image_path = self.image_items[row]
        menu = QMenu(self)
        save_default_action = None
        save_labelme_action = None
        save_yolo_action = None
        if self.show_yolo_save_in_context_menu():
            if not self.labelme_auto_save_enabled():
                save_labelme_action = self._add_menu_button_action(menu, "保存Labelme标注")
            if not self.yolo_auto_save_enabled():
                save_yolo_action = self._add_menu_button_action(menu, "保存YOLO标注")
        elif not self.labelme_auto_save_enabled():
            save_default_action = self._add_menu_button_action(menu, "保存")
        if (
            save_default_action is not None
            or save_labelme_action is not None
            or save_yolo_action is not None
        ):
            menu.addSeparator()
        delete_annotations_action = self._add_danger_menu_action(menu, "删除所有标注")
        delete_image_action = self._add_danger_menu_action(menu, "删除图片及标注")
        selected = menu.exec(self.file_list.viewport().mapToGlobal(pos))
        if save_default_action is not None and selected == save_default_action:
            self.save_current_default()
            return
        if save_labelme_action is not None and selected == save_labelme_action:
            self.save_current_labelme()
            return
        if save_yolo_action is not None and selected == save_yolo_action:
            self.save_current_yolo()
            return
        if selected == delete_annotations_action:
            if self._confirm_file_action(
                "删除所有标注",
                f"确定删除 {image_path.name} 的全部标注吗？",
            ):
                self.clear_annotations_for_image(image_path)
            return
        if selected == delete_image_action:
            if self._confirm_file_action(
                "删除图片及标注",
                f"确定删除图片 {image_path.name} 及其标注吗？",
            ):
                self.delete_image_and_annotations(image_path)

    def set_selected_annotation_class(self, class_id: int) -> None:
        if not (0 <= self.canvas.selected_index < len(self.canvas.annotations)):
            return
        self.canvas.annotations[self.canvas.selected_index].class_id = class_id
        self.refresh_annotation_list()
        self._sync_target_type_to_selection()
        self.mark_dirty_and_save()

    def open_annotation_list_context_menu(self, pos) -> None:
        row = self.annotation_list.indexAt(pos).row()
        if not (0 <= row < len(self.canvas.annotations)):
            return
        self.canvas.selected_index = row
        self.sync_selection(row)
        self.canvas.update()
        menu = QMenu(self)
        class_menu = QMenu("目标类型", menu)
        class_actions: dict[object, int] = {}
        names = self.class_names()
        current_class_id = self.canvas.annotations[row].class_id
        for index, class_name in enumerate(names):
            action = class_menu.addAction(f"{index} : {class_name}")
            action.setCheckable(True)
            action.setChecked(index == current_class_id)
            class_actions[action] = index
        class_entry_action = self._add_menu_button_action(
            menu,
            "目标类型",
            show_submenu_arrow=True,
        )
        menu.addSeparator()
        delete_action = self._add_danger_menu_action(menu, "删除标注")
        selected = menu.exec(self.annotation_list.viewport().mapToGlobal(pos))
        if selected == class_entry_action:
            class_selected = class_menu.exec(menu.pos() + menu.actionGeometry(class_entry_action).topRight())
            if class_selected in class_actions:
                self.set_selected_annotation_class(class_actions[class_selected])
            return
        if selected in class_actions:
            self.set_selected_annotation_class(class_actions[selected])
            return
        if selected == delete_action:
            self.delete_selected()

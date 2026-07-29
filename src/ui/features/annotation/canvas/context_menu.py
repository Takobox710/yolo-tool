from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from src.shared.qt import QHBoxLayout, QLabel, QMenu, Qt, QWidget, QWidgetAction
from src.ui.shared.widgets.toggle_switch import AnimatedToggleSwitch


class AnnotationCanvasContextMenuMixin:
    def _show_context_menu(self, global_pos) -> None:
        menu = QMenu(self)
        menu.setSeparatorsCollapsible(False)
        sam_widget_action = QWidgetAction(menu)
        sam_widget = QWidget(menu)
        sam_layout = QHBoxLayout(sam_widget)
        sam_layout.setContentsMargins(14, 5, 14, 5)
        sam_layout.setSpacing(0)
        sam_label = QLabel("SAM 智能标注", sam_widget)
        # QWidgetAction 内容不会自动采用 QMenu 的 QAction 字体。
        # 显式复用菜单字体，避免 SAM 行与普通菜单项出现字号差异。
        sam_label.setFont(menu.font())
        sam_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # 让文字占据开关左侧的剩余区域并与普通菜单项左对齐。
        sam_layout.addWidget(sam_label, 1)
        sam_switch = AnimatedToggleSwitch(sam_widget, width=36, height=18)
        # 菜单每次打开都会新建控件，初始化状态时不应播放切换动画。
        sam_switch.blockSignals(True)
        sam_switch.setChecked(self.sam_assist_enabled)
        sam_switch.blockSignals(False)
        has_sam_model = bool(self.sam_model_name)
        sam_switch.setEnabled(has_sam_model)
        sam_widget.setToolTip(
            f"当前模型：{self.sam_model_name}"
            if has_sam_model
            else "当前 SAM 模型不可用于画布辅助标注"
        )
        sam_layout.addWidget(sam_switch)
        sam_widget_action.setDefaultWidget(sam_widget)

        select_action = QAction("编辑", menu)
        select_action.setCheckable(True)
        select_action.setChecked(self.draw_shape == "select")
        select_action.setShortcut(QKeySequence("V"))
        select_action.setShortcutVisibleInContextMenu(True)
        menu.addAction(select_action)
        separator_top = QAction(menu)
        separator_top.setSeparator(True)
        menu.addAction(separator_top)
        shape_actions: dict[QAction, str] = {}
        for title, shape, shortcut in [
            ("矩形框", "rect", "R"),
            ("有向矩形", "obb_single", "O"),
            ("镜像有向矩形", "obb_mirror", "M"),
            ("多边形", "polygon", "P"),
            ("圆形", "circle", "C"),
        ]:
            action = QAction(title, menu)
            action.setCheckable(True)
            action.setChecked(self.draw_shape == shape)
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutVisibleInContextMenu(True)
            menu.addAction(action)
            shape_actions[action] = shape
        if self.line_expand_enabled:
            line_expand_action = QAction("直线拓展", menu)
            line_expand_action.setCheckable(True)
            line_expand_action.setChecked(self.draw_shape == "line_expand")
            line_expand_action.setShortcut(QKeySequence("L"))
            line_expand_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(line_expand_action)
            shape_actions[line_expand_action] = "line_expand"
        def apply_sam_enabled(enabled: bool) -> None:
            actual = False
            if self.sam_toggle_callback is not None:
                actual = bool(self.sam_toggle_callback(bool(enabled)))
            if sam_switch.isChecked() != actual:
                sam_switch.blockSignals(True)
                sam_switch.setChecked(actual)
                sam_switch.blockSignals(False)
            supported = {"rect", "obb_single", "obb_mirror", "polygon"}
            for action, shape in shape_actions.items():
                action.setEnabled(not actual or shape in supported)

        sam_switch.toggled.connect(apply_sam_enabled)
        apply_sam_enabled(self.sam_assist_enabled)
        class_actions: dict[QAction, int] = {}
        if 0 <= self.selected_index < len(self.annotations):
            class_menu = menu.addMenu("目标类型")
            for index, class_name in enumerate(self.class_names):
                action = QAction(f"{index} : {class_name}", class_menu)
                action.setCheckable(True)
                action.setChecked(self.annotations[self.selected_index].class_id == index)
                class_menu.addAction(action)
                class_actions[action] = index
        save_default_action = None
        save_labelme_action = None
        save_yolo_action = None
        undo_action = None
        redo_action = None
        if self.can_save_default:
            save_default_action = QAction("保存", menu)
            save_default_action.setShortcut(QKeySequence.StandardKey.Save)
            save_default_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(save_default_action)
        elif self.can_save_labelme:
            save_labelme_action = QAction("保存Labelme标注", menu)
            save_labelme_action.setShortcut(QKeySequence.StandardKey.Save)
            save_labelme_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(save_labelme_action)
        if self.show_separate_yolo_save and self.can_save_yolo:
            save_yolo_action = QAction("保存YOLO标注", menu)
            menu.addAction(save_yolo_action)
        has_selected_annotation = self._has_selected_annotation()
        if (
            save_default_action is not None
            or save_labelme_action is not None
            or save_yolo_action is not None
            or has_selected_annotation
            or self.can_undo
            or self.can_redo
            or self._can_show_cancel_drawing_action()
        ):
            separator_bottom = QAction(menu)
            separator_bottom.setSeparator(True)
            menu.addAction(separator_bottom)
        delete_action = None
        if has_selected_annotation:
            delete_action = QAction("删除", menu)
            delete_action.setShortcut(QKeySequence(Qt.Key.Key_Delete))
            delete_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(delete_action)
        if self.can_undo:
            undo_action = QAction("撤销", menu)
            undo_action.setShortcut(QKeySequence.StandardKey.Undo)
            undo_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(undo_action)
        if self.can_redo:
            redo_action = QAction("恢复", menu)
            redo_action.setShortcut(QKeySequence("Ctrl+Y"))
            redo_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(redo_action)
        cancel_action = None
        if self._can_show_cancel_drawing_action():
            cancel_action = QAction("取消当前绘制", menu)
            cancel_action.setShortcut(QKeySequence(Qt.Key.Key_Escape))
            cancel_action.setShortcutVisibleInContextMenu(True)
            menu.addAction(cancel_action)
        sam_separator = QAction(menu)
        sam_separator.setSeparator(True)
        menu.addAction(sam_separator)
        menu.addAction(sam_widget_action)
        selected = menu.exec(global_pos)
        if selected is None:
            return
        if selected == select_action:
            self.set_draw_shape("select")
        elif delete_action is not None and selected == delete_action:
            self.delete_selected()
        elif save_default_action is not None and selected == save_default_action:
            if self.save_default_callback is not None:
                self.save_default_callback()
        elif save_labelme_action is not None and selected == save_labelme_action:
            if self.save_labelme_callback is not None:
                self.save_labelme_callback()
        elif save_yolo_action is not None and selected == save_yolo_action:
            if self.save_yolo_callback is not None:
                self.save_yolo_callback()
        elif undo_action is not None and selected == undo_action:
            if self.undo_callback is not None:
                self.undo_callback()
        elif redo_action is not None and selected == redo_action:
            if self.redo_callback is not None:
                self.redo_callback()
        elif cancel_action is not None and selected == cancel_action:
            self._reset_transient_draw_state()
            self.update()
        elif selected in class_actions and 0 <= self.selected_index < len(self.annotations):
            if self.class_change_callback is not None:
                self.class_change_callback(class_actions[selected])
            else:
                self.annotations[self.selected_index].class_id = class_actions[selected]
                self._emit_changed()
                self.update()
        elif selected in shape_actions:
            self.set_draw_shape(shape_actions[selected])

    def _add_menu_button_action(
        self,
        menu: QMenu,
        text: str,
        *,
        color: str = "#14233A",
        hover_background: str = "#F5F8FB",
        trailing_text: str = "",
    ) -> QWidgetAction:
        action = QWidgetAction(menu)
        container = QWidget(menu)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(36, 6, 14, 6)
        layout.setSpacing(0)
        label = QLabel(text, container)
        label.setStyleSheet(f"color: {color};")
        layout.addWidget(label)
        layout.addStretch(1)
        if trailing_text:
            trailing_label = QLabel(trailing_text, container)
            trailing_label.setStyleSheet("color: #14233A;")
            trailing_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            trailing_label.setFixedWidth(34)
            layout.addWidget(trailing_label)
        container.setStyleSheet(
            f"QWidget {{ background: transparent; }}"
            f"QWidget:hover {{ background: {hover_background}; }}"
        )
        container.mousePressEvent = lambda _event: action.trigger()
        action.setDefaultWidget(container)
        menu.addAction(action)
        return action

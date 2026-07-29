from __future__ import annotations

from src.services.data_ops import relative_path_from_project
from src.services.validation import is_live_source_mode
from src.shared.qt import Qt
from src.ui.features.validation.sources import IMAGE_SOURCE_OPTIONS, VIDEO_SOURCE_OPTIONS


def update_source_mode(page, value):
    page.detection_started_for_source = False
    page.clear_validation_previews()
    layouts = [
        getattr(page, name, None)
        for name in (
            "validation_layout",
            "validation_split_layout",
            "left_column_layout",
            "validation_right_layout",
            "validation_views_layout",
            "source_panel_layout",
            "result_panel_layout",
        )
    ]
    layouts = [layout for layout in layouts if layout is not None]
    page.setUpdatesEnabled(False)
    for layout in layouts:
        layout.setEnabled(False)
    try:
        camera = is_live_source_mode(value)
        image_folder_mode = value == "图片检测"
        video_folder_mode = value == "视频检测"
        folder_source_mode = image_folder_mode or video_folder_mode
        val_mode = page.is_val_mode(value)
        page.source_box.setVisible(folder_source_mode)
        page.data_box.setVisible(val_mode)
        page.source_scope_box.setVisible(val_mode)
        page.camera_box.setVisible(camera)
        page.save_box.setVisible(True)
        page.open_val_save_btn.setVisible(val_mode)
        page.set_result_navigation_enabled((not camera) and (not val_mode))
        page.detect_log.setVisible(not val_mode)
        log_index = page.left_column_layout.indexOf(page.detect_log)
        if log_index >= 0:
            page.left_column_layout.setStretch(log_index, 0 if val_mode else 1)
        page.left_column_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop if val_mode else Qt.AlignmentFlag(0)
        )
        page.toolbar_widget.setVisible(not val_mode and not camera)
        page.views_widget.setVisible(not val_mode)
        page.table_panel.setVisible(not val_mode)
        page.val_log_panel.setVisible(val_mode)
        if camera:
            page.counter.setText("实时预览")
        elif val_mode:
            page.counter.setText("验证模式")
        elif not page.detect_results:
            page.counter.setText("0/0")
        validation = page.context.settings.validation
        source_path = validation.source_path
        source_selection = validation.source_selection
        if image_folder_mode:
            current_source = source_selection
            if current_source not in IMAGE_SOURCE_OPTIONS:
                current_source = (
                    relative_path_from_project(source_path, page.project_root())
                    if source_path
                    else validation.source_scope
                )
            page._configure_source_combo(
                IMAGE_SOURCE_OPTIONS,
                relative_path_from_project(source_path, page.project_root())
                if source_path
                else current_source,
                "选择图片文件夹或图片文件",
            )
        elif video_folder_mode:
            page._configure_source_combo(
                VIDEO_SOURCE_OPTIONS,
                relative_path_from_project(source_path, page.project_root())
                if source_path
                else (
                    source_selection
                    if source_selection in VIDEO_SOURCE_OPTIONS
                    else "批量视频"
                ),
                "选择视频文件夹或视频文件",
            )
        page.update_detection_button_text()
        page.refresh_source_items()
        update_video_mode_controls(page)
    finally:
        for layout in reversed(layouts):
            layout.setEnabled(True)
        for layout in layouts:
            layout.activate()
        page.setUpdatesEnabled(True)
        page.updateGeometry()
        page.update()


def is_video_detection_mode(page) -> bool:
    return page.mode_combo.currentText() == "视频检测"


def update_video_mode_controls(page) -> None:
    video_mode = is_video_detection_mode(page)
    detection_mode = not page.is_val_mode()
    live_mode = is_live_source_mode(page.mode_combo.currentText())
    page.result_nav_widget.setVisible(detection_mode and not video_mode and not live_mode)
    page.video_progress_widget.setVisible(detection_mode and video_mode)
    page.start_det_btn.setVisible(True)
    page.stop_det_btn.setVisible(True)
    page.video_play_btn.setVisible(video_mode)
    page.video_prev_btn.setVisible(video_mode)
    page.video_next_btn.setVisible(video_mode)
    page.source_view.setVisible(not video_mode)
    page.result_view.setVisible(not video_mode)
    page.source_video_player.setVisible(video_mode)
    page.result_video_player.setVisible(video_mode)
    if not video_mode:
        page.video_play_btn.blockSignals(True)
        page.video_play_btn.setChecked(False)
        page.video_play_btn.blockSignals(False)
        page.stop_video_playback()
    elif page.source_items:
        page.load_video_source(page.source_items[page.source_index])


__all__ = ["is_video_detection_mode", "update_source_mode", "update_video_mode_controls"]

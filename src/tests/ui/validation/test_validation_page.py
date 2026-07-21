from pathlib import Path

import os

from PIL import Image

import subprocess

import sys

from types import SimpleNamespace

from src.tests.helpers.ui_paths import (
    APP,
    DATA_VIEW,
    HOME_VIEW,
    ICON_ICO,
    ICON_PNG,
    INSTALLER_ISS,
    PACKAGING_DOC,
    PACKAGING_ONE_CLICK_SCRIPT,
    PACKAGING_SCRIPT,
    PACKAGING_SPEC,
    PAGE_BASE,
    SETTINGS_VIEW,
    TRAIN_VIEW,
    UI_BUNDLE_PATHS,
    VALIDATE_VIEW,
    WINDOW,
)


def _read_app():
    return APP.read_text(encoding="utf-8")

def _read_ui_bundle():
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_BUNDLE_PATHS)


def _sample_detection_item():
    return SimpleNamespace(
        label="weld",
        confidence=0.9,
        center_x=10.0,
        center_y=20.0,
        width=30.0,
        height=40.0,
        angle=0.0,
    )


def test_validation_page_lists_training_best_and_last_models_by_feature_flag(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    run_dir = tmp_path / "result" / "train-2" / "weights"
    run_dir.mkdir(parents=True)
    (run_dir / "best.pt").write_text("best", encoding="utf-8")
    (run_dir / "last.pt").write_text("last", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["show_last_training_models"] = True
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = ValidatePage(fake_app)
    page.on_show()
    items = [page.model_combo.itemText(i) for i in range(page.model_combo.count())]

    assert "train-2\\best.pt" in items
    assert "train-2\\last.pt" in items

    fake_app.settings["features"]["show_last_training_models"] = False
    page.refresh_model_choices()
    items = [page.model_combo.itemText(i) for i in range(page.model_combo.count())]

    assert "train-2\\best.pt" in items
    assert "train-2\\last.pt" not in items


def test_validation_page_only_lists_training_output_models(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    (tmp_path / "result" / "train" / "weights").mkdir(parents=True)
    (tmp_path / "result" / "train" / "weights" / "best.pt").write_text(
        "b", encoding="utf-8"
    )
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = ValidatePage(fake_app)
    page.on_show()

    items = [page.model_combo.itemText(i) for i in range(page.model_combo.count())]

    assert items == ["train\\best.pt"]
    assert page._get_model_path() == str((tmp_path / "result" / "train" / "weights" / "best.pt").resolve())


def test_validation_page_lists_newer_training_numbers_first(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["show_last_training_models"] = True
    for run_name in ("train-2", "train-10"):
        run_dir = tmp_path / "result" / run_name / "weights"
        run_dir.mkdir(parents=True)
        (run_dir / "best.pt").write_text("best", encoding="utf-8")
        (run_dir / "last.pt").write_text("last", encoding="utf-8")
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = ValidatePage(fake_app)
    page.on_show()

    items = [page.model_combo.itemText(i) for i in range(page.model_combo.count())]

    assert items == [
        "train-10\\best.pt",
        "train-10\\last.pt",
        "train-2\\best.pt",
        "train-2\\last.pt",
    ]


def test_validation_page_ignores_base_models_in_data_models(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    models_dir = tmp_path / "data" / "models"
    models_dir.mkdir(parents=True)
    model_path = models_dir / "alpha.pt"
    model_path.write_text("a", encoding="utf-8")
    run_model_path = tmp_path / "result" / "train-1" / "weights" / "best.pt"
    run_model_path.parent.mkdir(parents=True)
    run_model_path.write_text("best", encoding="utf-8")
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = ValidatePage(fake_app)
    page.on_show()
    items = [page.model_combo.itemText(i) for i in range(page.model_combo.count())]

    assert items == ["train-1\\best.pt"]
    assert "alpha.pt" not in items
    assert page._get_model_path() == str(run_model_path.resolve())


def test_validation_page_uses_best_when_last_is_selected_and_flag_turns_off(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["features"]["show_last_training_models"] = True
    run_dir = tmp_path / "result" / "train-8" / "weights"
    run_dir.mkdir(parents=True)
    best_path = run_dir / "best.pt"
    last_path = run_dir / "last.pt"
    best_path.write_text("best", encoding="utf-8")
    last_path.write_text("last", encoding="utf-8")
    settings["validation"]["model_path"] = str(last_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
    )

    page = ValidatePage(fake_app)
    page.on_show()
    assert page.model_combo.currentText() == "train-8\\last.pt"

    fake_app.settings["features"]["show_last_training_models"] = False
    page.refresh_model_choices()

    assert page.model_combo.currentText() == "train-8\\best.pt"


def test_validation_page_supports_dataset_val_mode(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    page = ValidatePage(fake_app)
    page.mode_combo.setCurrentText("数据集验证")

    assert page.start_det_btn.text() == "开始验证"
    assert not page.data_box.isHidden()
    assert not page.source_scope_box.isHidden()
    assert not page.save_box.isHidden()
    assert not page.open_val_save_btn.isHidden()
    assert page.source_box.isHidden()
    assert not page.val_log_panel.isHidden()
    assert page.toolbar_widget.isHidden()
    assert page.views_widget.isHidden()
    assert page.table_panel.isHidden()
    assert page.counter.text() == "验证模式"
    assert page.save_edit.text() == str(Path("result") / "gui_val")


def test_validation_page_compacts_left_panel_for_dataset_val_mode(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, Qt
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    page = ValidatePage(fake_app)
    page.resize(1200, 900)
    page.mode_combo.setCurrentText("数据集验证")
    page.show()
    app.processEvents()

    assert page.left_column_layout.alignment() == Qt.AlignmentFlag.AlignTop
    assert page.model_combo.parentWidget().height() <= 50
    assert page.data_edit.parentWidget().height() <= 50
    page.close()


def test_validation_page_expands_detection_log_to_left_panel_bottom(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    page = ValidatePage(fake_app)
    page.resize(1200, 900)
    page.show()
    app.processEvents()

    assert page.detect_log.height() > page.detect_log.minimumHeight()
    assert page.detect_log.geometry().bottom() >= (
        page.detect_log.parentWidget().rect().bottom() - 20
    )
    page.close()


def test_validation_page_uses_dataset_scope_combo_for_folder_mode(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["validation"]["source_mode"] = "图片/视频文件夹"
    model_path = tmp_path / "data" / "models" / "alpha.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("model", encoding="utf-8")
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    page = ValidatePage(fake_app)
    assert page.mode_combo.currentText() == "图片检测"
    page.mode_combo.setCurrentText("图片检测")

    assert not page.source_box.isHidden()
    assert page.data_box.isHidden()
    assert page.source_scope_box.isHidden()
    assert page.source_combo.currentText() == "全部图片"
    assert page.open_val_save_btn.isHidden()
    assert (
        page.source_combo.lineEdit().placeholderText()
        == "选择图片文件夹或图片文件"
    )


def test_validation_page_source_options_choose_single_media_files(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    image = tmp_path / "single.jpg"
    video = tmp_path / "single.mp4"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )
    page = ValidatePage(fake_app)

    assert [
        page.source_combo.itemText(index)
        for index in range(page.source_combo.count())
    ][-1:] == ["单张图片"]

    monkeypatch.setattr(
        "src.ui.features.validation.page_actions.QFileDialog.getOpenFileName",
        lambda *_args: (str(image), ""),
    )
    page.source_combo.setCurrentText("单张图片")
    page.choose_detection_source(page.source_combo)

    assert settings["validation"]["source_selection"] == "单张图片"
    assert Path(settings["validation"]["source_path"]) == image.resolve()
    assert page.source_items == [image.resolve()]

    page.mode_combo.setCurrentText("视频检测")
    assert [
        page.source_combo.itemText(index)
        for index in range(page.source_combo.count())
    ] == ["批量视频", "单个视频"]
    monkeypatch.setattr(
        "src.ui.features.validation.page_actions.QFileDialog.getOpenFileName",
        lambda *_args: (str(video), ""),
    )
    page.source_combo.setCurrentText("单个视频")
    page.choose_detection_source(page.source_combo)

    assert settings["validation"]["source_selection"] == "单个视频"
    assert Path(settings["validation"]["source_path"]) == video.resolve()
    assert page.source_items == [video.resolve()]
    page.close()


def test_validation_page_displays_custom_source_as_relative_path(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    custom_source = tmp_path.parent / "custom-source"
    custom_source.mkdir()
    settings["validation"]["source_path"] = str(custom_source)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )
    page = ValidatePage(fake_app)
    monkeypatch.setattr(
        "src.ui.features.validation.page_actions.QFileDialog.getExistingDirectory",
        lambda *_args: str(custom_source),
    )
    expected_display = os.path.relpath(
        str(custom_source.resolve()), str(tmp_path.resolve())
    )
    assert page.source_combo.currentText() == expected_display

    page.mode_combo.setCurrentText("图片检测")
    page.choose_detection_source(page.source_combo)

    assert page.source_combo.currentText() == expected_display
    assert Path(page._folder_source_path_for_selection()) == custom_source.resolve()
    page.close()


def test_validation_page_uses_video_controls_for_video_input(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QMediaPlayer
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    video_folder = tmp_path / "videos"
    video_folder.mkdir()
    video_path = video_folder / "demo.mp4"
    video_path.write_bytes(b"video")
    second_video_path = video_folder / "demo-2.mp4"
    second_video_path.write_bytes(b"video")
    settings["validation"]["source_mode"] = "视频检测"
    settings["validation"]["source_path"] = str(video_folder)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    page = ValidatePage(fake_app)
    page.resize(1200, 900)
    page.show()
    app.processEvents()

    assert page.mode_combo.currentText() == "视频检测"
    assert page.result_nav_widget.isHidden()
    assert not page.video_progress_widget.isHidden()
    assert not page.video_play_btn.isHidden()
    assert not page.video_play_btn.isChecked()
    assert not page.video_list_btn.isHidden()
    assert not page.video_open_dir_btn.isHidden()
    assert not page.video_prev_btn.isHidden()
    assert not page.video_next_btn.isHidden()
    assert page.video_progress.maximum() == 1000
    assert not page.source_video_player.isHidden()
    assert not page.result_video_player.isHidden()
    assert abs(page.source_panel.width() - page.result_panel.width()) <= 1
    assert not page.start_det_btn.isHidden()
    assert not page.stop_det_btn.isHidden()
    assert page.start_det_btn.text() == "开启检测"
    first_video_path = page.source_items[0]
    second_video_path = page.source_items[1]
    assert page.current_video_source_path == first_video_path.resolve()
    page.video_play_btn.blockSignals(True)
    page.video_play_btn.setChecked(True)
    page.video_play_btn.blockSignals(False)
    page.handle_video_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
    assert not page.video_play_btn.isChecked()
    assert page.video_play_btn.toolTip() == "播放视频"
    assert page.video_progress.value() == page.video_progress.maximum()
    page.mode_combo.setCurrentText("图片检测")
    assert page.updatesEnabled()
    assert page.validation_layout.isEnabled()
    assert page.validation_split_layout.isEnabled()
    assert not page.source_view.isHidden()
    assert page.source_video_player.isHidden()
    assert page.result_video_player.isHidden()
    assert page.video_progress_widget.isHidden()

    page.mode_combo.setCurrentText("视频检测")
    assert page.updatesEnabled()
    assert page.validation_layout.isEnabled()
    assert page.validation_split_layout.isEnabled()
    assert page.source_view.isHidden()
    assert not page.source_video_player.isHidden()
    assert not page.result_video_player.isHidden()
    assert not page.video_progress_widget.isHidden()
    page.next_video()
    assert page.source_index == 1
    assert page.current_video_source_path == second_video_path.resolve()
    page.previous_video()
    assert page.source_index == 0
    assert page.current_video_source_path == first_video_path.resolve()
    page.handle_video_progress(
        {
            "percent": 42,
            "frame": 420,
            "total_frames": 1000,
            "frames_last_second": 36,
            "source_path": str(second_video_path),
        }
    )
    assert page.video_progress.value() == 0
    assert page.current_video_source_path == first_video_path.resolve()
    second_result_path = tmp_path / "second-result.mp4"
    page.handle_video_completed(
        {
            "source_path": str(second_video_path),
            "result_path": str(second_result_path),
        }
    )
    assert page.current_video_source_path == first_video_path.resolve()
    assert (
        page.video_result_by_source[str(second_video_path.resolve())]
        == second_result_path.resolve()
    )
    assert "视频检测进度：42%（420/1000帧） | 上一秒：36帧" in page.detect_log.toPlainText()
    page.close()


def test_validation_page_image_previews_ignore_pixmap_width_for_layout(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QSizePolicy
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )
    page = ValidatePage(fake_app)
    page.resize(1200, 900)
    page.show()
    app.processEvents()

    assert page.source_view.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored
    assert page.result_view.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored
    assert page.source_panel.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored
    assert page.result_panel.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored

    source_width = page.source_panel.width()
    result_width = page.result_panel.width()
    assert abs(source_width - result_width) <= 1
    page.close()


def test_validation_page_previews_sources_before_detection(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    source_folder = tmp_path / "inputs"
    source_folder.mkdir()
    first = source_folder / "1.jpg"
    second = source_folder / "2.jpg"
    Image.new("RGB", (320, 180), "red").save(first)
    Image.new("RGB", (180, 320), "blue").save(second)
    settings["validation"]["source_path"] = str(source_folder)
    settings["validation"]["source_selection"] = ""
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    page = ValidatePage(fake_app)

    assert not page.detection_started_for_source
    assert page.source_items == [first.resolve(), second.resolve()]
    assert page.source_view._pixmap.size().width() == 320
    assert page.source_view._pixmap.size().height() == 180

    page.first_result()
    assert page.source_index == 0
    page.next_result()
    assert page.source_index == 1
    page.last_result()
    assert page.source_index == 1
    page.prev_result()
    assert page.source_index == 0

    page.source_index = 1
    assert page.show_cached_source_result(second)
    assert page.source_view._pixmap.size().width() == 180
    assert page.source_view._pixmap.size().height() == 320

    page.detection_started_for_source = True
    page.source_index = 0
    assert not page.show_cached_source_result(second)
    assert page.source_view._pixmap.size().width() == 180

    page.detection_started_for_source = False
    page.mode_combo.setCurrentText("视频检测")
    assert page.source_view._pixmap is None
    assert page.result_view._pixmap is None
    assert page.source_video_player.path is None
    assert page.result_video_player.path is None
    page.close()


def test_validation_page_accepts_dropped_media_and_selects_single_source(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    image = tmp_path / "drop-image.jpg"
    image.write_bytes(b"image")
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    class _MimeData:
        def hasUrls(self):
            return True

        def urls(self):
            return [SimpleNamespace(toLocalFile=lambda: str(image))]

    class _DropEvent:
        def __init__(self):
            self.accepted = False

        def mimeData(self):
            return _MimeData()

        def acceptProposedAction(self):
            self.accepted = True

        def ignore(self):
            self.accepted = False

    page = ValidatePage(fake_app)
    event = _DropEvent()
    page.dropEvent(event)

    assert event.accepted
    assert page.mode_combo.currentText() == "图片检测"
    assert page.source_combo.currentText() == os.path.relpath(str(image), str(tmp_path))
    assert page.source_items == [image.resolve()]
    assert settings["validation"]["source_mode"] == "图片检测"
    assert Path(settings["validation"]["source_path"]) == image.resolve()
    page.close()


def test_validation_page_uses_project_root_cwd_for_dataset_val(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.shared.paths import ROOT
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    model_path = tmp_path / "result" / "train-1" / "weights" / "best.pt"
    data_path = tmp_path / "data" / "data.yaml"
    model_path.parent.mkdir(parents=True)
    data_path.parent.mkdir(parents=True)
    model_path.write_text("weights", encoding="utf-8")
    data_path.write_text("path: data\nval: val/images\nnames: ['weld']\n", encoding="utf-8")
    settings["validation"]["model_path"] = str(model_path)
    settings["validation"]["data"] = str(data_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )
    captured = {}

    class _FakeProcess:
        def poll(self):
            return None

    fake_handle = SimpleNamespace(process=_FakeProcess())

    def fake_spawn(command, cwd, queue):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["queue"] = queue
        return fake_handle

    monkeypatch.setattr("src.ui.features.validation.runtime.spawn_logged_process", fake_spawn)

    page = ValidatePage(fake_app)
    page.on_show()
    page.model_combo.setCurrentText(str(model_path))
    page.mode_combo.setCurrentText("数据集验证")
    page.start_detection()

    assert captured["cwd"] == str(ROOT)
    page._finish_dataset_validation(0)


def test_validation_page_temporarily_rewrites_val_split_for_dataset_val(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    model_path = tmp_path / "result" / "train-1" / "weights" / "best.pt"
    data_dir = tmp_path / "data"
    data_path = data_dir / "data.yaml"
    model_path.parent.mkdir(parents=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    model_path.write_text("weights", encoding="utf-8")
    original_yaml = "\n".join(
        [
            "path: .",
            "train: train/images",
            "val: val/images",
            "test: test/images",
            "names: ['weld']",
        ]
    ) + "\n"
    data_path.write_text(original_yaml, encoding="utf-8")
    settings["validation"]["model_path"] = str(model_path)
    settings["validation"]["data"] = str(data_path)
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    class _FakeProcess:
        def poll(self):
            return None

    fake_handle = SimpleNamespace(process=_FakeProcess())

    def fake_spawn(command, cwd, queue):
        return fake_handle

    monkeypatch.setattr("src.ui.features.validation.runtime.spawn_logged_process", fake_spawn)

    page = ValidatePage(fake_app)
    page.on_show()
    page.mode_combo.setCurrentText("数据集验证")
    page.model_combo.setCurrentText(str(model_path))
    page.source_scope_combo.setCurrentText("全部图片")
    page.start_detection()

    rewritten = data_path.read_text(encoding="utf-8")
    assert "val: images" in rewritten
    assert "val: val/images" not in rewritten

    page._restore_temporary_validation_yaml_if_needed()

    assert data_path.read_text(encoding="utf-8") == original_yaml


def test_validation_page_folder_mode_uses_batch_worker_not_single_start(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.validation.page import ValidatePage

    app = QApplication.instance() or QApplication([])
    settings = build_default_settings(tmp_path)
    settings["validation"]["source_mode"] = "图片检测"
    model_path = tmp_path / "data" / "models" / "alpha.pt"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("model", encoding="utf-8")
    fake_app = SimpleNamespace(
        settings=settings,
        settings_service=SimpleNamespace(save=lambda _data: None),
        run_background=lambda _kind, _fn: None,
        status=SimpleNamespace(setText=lambda _text: None),
        training_handle=None,
        validation_handle=None,
    )

    page = ValidatePage(fake_app)
    page.model_combo.setCurrentText(str(model_path))
    page.source_items = [tmp_path / "a.jpg", tmp_path / "b.jpg"]
    called = {"single": False, "worker": False}

    monkeypatch.setattr(page, "refresh_source_items", lambda: None)
    monkeypatch.setattr(
        page,
        "start_current_source_detection",
        lambda: called.__setitem__("single", True),
    )

    class _FakeWorker:
        def __init__(self, config, stop_event):
            called["worker"] = True
            self.progress = SimpleNamespace(connect=lambda _fn: None)
            self.result_payload = SimpleNamespace(connect=lambda _fn: None)
            self.finished_with_results = SimpleNamespace(connect=lambda _fn: None)
            self.failed = SimpleNamespace(connect=lambda _fn: None)
            self.finished = SimpleNamespace(connect=lambda _fn: None)

        def start(self):
            return None

    monkeypatch.setattr("src.ui.features.validation.page.DetectionWorker", _FakeWorker)

    page.mode_combo.setCurrentText("图片检测")
    page.start_detection()

    assert called["single"] is False
    assert called["worker"] is True


def test_validation_page_keeps_detection_worker_until_thread_finished():
    from src.ui.features.validation.runtime import apply_detect_done, apply_detect_error

    worker = object()
    page = SimpleNamespace(
        detect_stop=SimpleNamespace(is_set=lambda: False, clear=lambda: None),
        append_active_log=lambda _text: None,
        set_status_text=lambda _text: None,
        detect_worker=worker,
        is_detecting=True,
        start_det_btn=SimpleNamespace(setEnabled=lambda _value: None),
        stop_det_btn=SimpleNamespace(setEnabled=lambda _value: None),
    )

    apply_detect_done(page, True)
    assert page.detect_worker is worker
    assert page.is_detecting is False

    page.detect_worker = worker
    page.is_detecting = True
    apply_detect_error(page, "boom")
    assert page.detect_worker is worker
    assert page.is_detecting is False


def test_validation_result_cache_drops_in_memory_images_for_saved_image_results(tmp_path):
    from src.ui.features.validation.results import handle_detection_result

    source_path = tmp_path / "source.jpg"
    result_path = tmp_path / "result.jpg"
    Image.new("RGB", (10, 10), "white").save(source_path)
    Image.new("RGB", (10, 10), "black").save(result_path)
    shown = {"count": 0}
    page = SimpleNamespace(
        mode_combo=SimpleNamespace(currentText=lambda: "图片检测"),
        detect_results=[],
        result_by_source={},
        is_batch_detection=True,
        user_selected_result=False,
        detect_index=-1,
        counter=SimpleNamespace(setText=lambda _text: None),
        append_active_log=lambda _text: None,
        show_detection_payload=lambda payload: shown.update({"count": shown["count"] + 1, "payload": payload}),
    )
    payload = {
        "source_image": Image.open(source_path).convert("RGB"),
        "result_image": Image.open(result_path).convert("RGB"),
        "items": [_sample_detection_item()],
        "status": "1/1 source.jpg",
        "source_name": "source.jpg",
        "source_path": str(source_path),
        "result_path": str(result_path),
        "elapsed": 0.1,
    }

    handle_detection_result(page, payload)

    assert shown["count"] == 1
    assert len(page.detect_results) == 1
    assert "source_image" not in page.detect_results[0]
    assert "result_image" not in page.detect_results[0]


def test_validation_result_without_saved_result_path_is_not_cached(tmp_path):
    from src.ui.features.validation.results import handle_detection_result

    source_path = tmp_path / "clip.mp4"
    source_path.write_bytes(b"video")
    shown = {"count": 0}
    page = SimpleNamespace(
        mode_combo=SimpleNamespace(currentText=lambda: "视频检测"),
        detect_results=[],
        result_by_source={},
        is_batch_detection=False,
        user_selected_result=False,
        detect_index=-1,
        counter=SimpleNamespace(setText=lambda _text: None),
        append_active_log=lambda _text: None,
        show_detection_payload=lambda payload: shown.update({"count": shown["count"] + 1, "payload": payload}),
    )
    payload = {
        "source_image": Image.new("RGB", (10, 10), "white"),
        "result_image": Image.new("RGB", (10, 10), "black"),
        "items": [_sample_detection_item()],
        "status": "clip.mp4 #1",
        "source_name": "clip.mp4 #1",
        "source_path": str(source_path),
        "elapsed": 0.1,
    }

    handle_detection_result(page, payload)

    assert shown["count"] == 1
    assert page.detect_results == []
    assert page.result_by_source == {}



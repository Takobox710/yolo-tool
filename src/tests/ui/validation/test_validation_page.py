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


def test_validation_page_supports_dataset_val_mode(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication, QPushButton
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

    assert page.start_det_btn.text() == "开始检测"
    assert not page.data_box.isHidden()
    assert not page.source_scope_box.isHidden()
    assert not page.save_box.isHidden()
    assert not page.open_val_save_btn.isHidden()
    assert page.source_box.isHidden()
    assert not page.start_det_btn.isHidden()
    assert not page.stop_det_btn.isHidden()
    assert any(button.text() == "选择" for button in page.source_scope_box.findChildren(QPushButton))
    assert not page.val_log_panel.isHidden()
    assert page.toolbar_widget.isHidden()
    assert page.views_widget.isHidden()
    assert page.table_panel.isHidden()
    assert page.counter.text() == "验证模式"
    assert page.save_edit.text() == str(Path("result") / "gui_val")


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


def test_validation_page_keeps_detection_worker_until_thread_finished():
    from src.ui.features.validation.runtime import apply_detect_done, apply_detect_error

    worker = object()
    page = SimpleNamespace(
        detect_stop=SimpleNamespace(is_set=lambda: False, clear=lambda: None),
        append_active_log=lambda _text: None,
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

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]
    linear = [
        value / 12.92
        if value <= 0.04045
        else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    bright, dark = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (bright + 0.05) / (dark + 0.05)


@pytest.fixture(autouse=True)
def restore_application_theme():
    from src.shared.qt import QApplication
    from src.ui.shared.theme import DEFAULT_STYLE_PROPERTY, THEME_MODE_PROPERTY

    app = QApplication.instance() or QApplication([])
    original = {
        "style": app.style().objectName(),
        "stylesheet": app.styleSheet(),
        "palette": app.palette(),
        "theme_mode": app.property(THEME_MODE_PROPERTY),
        "default_style": app.property(DEFAULT_STYLE_PROPERTY),
    }
    yield
    app.setStyle(original["style"])
    app.setStyleSheet(original["stylesheet"])
    app.setPalette(original["palette"])
    app.setProperty(THEME_MODE_PROPERTY, original["theme_mode"])
    app.setProperty(DEFAULT_STYLE_PROPERTY, original["default_style"])


def test_theme_palettes_keep_primary_text_readable():
    from src.shared.theme import DARK_COLORS, LIGHT_COLORS

    for colors in (LIGHT_COLORS, DARK_COLORS):
        assert _contrast_ratio(colors.text, colors.window) >= 4.5
        assert _contrast_ratio(colors.text, colors.surface) >= 4.5
        assert _contrast_ratio(colors.text, colors.input_bg) >= 4.5
        assert _contrast_ratio(colors.selection_text, colors.selection) >= 4.5
        assert _contrast_ratio(colors.primary_text, colors.primary_bg) >= 4.5
        assert _contrast_ratio("#FFFFFF", colors.success) >= 4.5


def test_light_theme_keeps_native_list_and_combo_popup_metrics():
    from src.shared.theme import build_style

    style = build_style("light")

    assert "QListWidget" not in style
    assert "QComboBox QAbstractItemView" not in style
    assert "QScrollBar" not in style
    assert "QCheckBox::indicator" not in style


def test_dark_theme_keeps_list_items_and_combo_popup_readable():
    from src.shared.theme import build_style

    style = build_style("dark")

    assert "QListWidget::item { padding: 0; border-bottom: 1px solid" in style
    assert "QComboBox QAbstractItemView::item { min-height: 28px; padding: 4px 8px; }" in style


def test_annotation_file_rows_use_theme_specific_height():
    from src.shared.qt import QApplication, QListWidgetItem
    from src.ui.features.annotation.file_item import AnnotationFileListItemWidget
    from src.ui.shared.theme import apply_theme

    app = QApplication.instance() or QApplication([])
    item = QListWidgetItem()
    widget = AnnotationFileListItemWidget(item)

    apply_theme(app, "light")
    assert widget.sizeHint().height() == 28

    apply_theme(app, "dark")
    assert widget.sizeHint().height() == 36


def test_existing_annotation_rows_refresh_after_dark_toggle(tmp_path):
    from PIL import Image
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.annotation.page import AnnotationPage
    from src.ui.shared.theme import apply_theme

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    Image.new("RGB", (32, 32), "white").save(images_dir / "1.jpg")
    app = QApplication.instance() or QApplication([])
    apply_theme(app, "light")
    settings = build_default_settings(tmp_path)
    page = AnnotationPage(
        type(
            "Host",
            (),
            {
                "settings": settings,
                "settings_service": type(
                    "Service", (), {"save": lambda _self, _value: None}
                )(),
            },
        )()
    )
    page.prepare_for_first_show()
    item = page.file_list.item(0)
    widget = page.file_list.itemWidget(item)
    assert item.sizeHint().height() == 28

    apply_theme(app, "dark")
    page.refresh_for_theme()
    app.processEvents()

    assert item.sizeHint().height() == 36
    label_rect = widget.name_label.geometry()
    top_gap = label_rect.top()
    bottom_gap = widget.height() - label_rect.bottom() - 1
    assert top_gap >= 6
    assert bottom_gap >= 6


def test_window_theme_toggle_refreshes_loaded_pages(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import src.ui.shell.window as window_module
    from src.shared.qt import QApplication
    from src.ui.shared.theme import apply_theme

    app = QApplication.instance() or QApplication([])
    refreshed = []
    host = SimpleNamespace(
        pages={
            "fake": SimpleNamespace(
                refresh_for_theme=lambda: refreshed.append(True)
            )
        },
        settings=SimpleNamespace(project=SimpleNamespace(root=str(tmp_path))),
        _theme_mode="light",
        refresh_theme_styles=lambda: window_module.WorkbenchWindow.refresh_theme_styles(host),
    )
    monkeypatch.setattr(
        window_module,
        "save_theme_mode",
        lambda _mode, fallback: SimpleNamespace(
            last_project_root=str(fallback),
            theme_mode="dark",
        ),
    )

    window_module.WorkbenchWindow.set_theme_mode(host, "dark")

    assert refreshed == [True]
    assert host._theme_mode == "dark"
    apply_theme(app, "light")


def test_apply_theme_overrides_existing_dark_system_palette():
    from src.shared.qt import QApplication
    from src.shared.theme import LIGHT_COLORS, build_style
    from src.ui.shared.theme import apply_theme, build_palette, current_theme_mode

    app = QApplication.instance() or QApplication([])
    app.setPalette(build_palette("dark"))
    assert app.palette().window().color().name().upper() != LIGHT_COLORS.window

    apply_theme(app, "light")

    assert current_theme_mode(app) == "light"
    assert app.palette().window().color().name().upper() == LIGHT_COLORS.window
    assert app.styleSheet() == build_style("light")


def test_settings_dark_checkbox_updates_application_theme(tmp_path):
    from src.services.settings import build_default_settings
    from src.shared.qt import QApplication
    from src.ui.features.settings.page import SettingsPage
    from src.ui.shared.context import WorkbenchContext
    from src.ui.shared.theme import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "light")
    applied = []
    context = WorkbenchContext(
        settings_service=type("Service", (), {"save": lambda _self, _value: None})(),
        load_result=type(
            "LoadResult",
            (),
            {
                "settings": build_default_settings(tmp_path),
                "migrated": False,
                "issues": (),
            },
        )(),
        get_theme_mode=lambda: applied[-1] if applied else "light",
        set_theme_mode=applied.append,
    )

    page = SettingsPage(context)
    assert page.dark_mode_check.isChecked() is False

    page.dark_mode_check.setChecked(True)

    assert applied == ["dark"]


def test_reused_release_dialog_reapplies_current_dark_style():
    from src.shared.qt import QApplication, QDialog
    from src.shared.theme import DARK_COLORS
    from src.ui.features.settings.update_dialog_install import (
        apply_release_dialog_style,
    )
    from src.ui.shared.theme import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "dark")
    dialog = QDialog()

    apply_release_dialog_style(dialog)

    assert DARK_COLORS.input_bg in dialog.styleSheet()
    apply_theme(app, "light")

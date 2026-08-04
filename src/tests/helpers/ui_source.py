"""Shared source-text readers used by architecture and UI contract tests."""

from src.tests.helpers.ui_paths import APP, UI_BUNDLE_PATHS


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def read_ui_bundle() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_BUNDLE_PATHS)


def show_page(page, app):
    page.on_show()
    app.processEvents()
    app.processEvents()
    return page

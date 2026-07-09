from __future__ import annotations

from src.shared.qt import QTimer
from src.ui.shell.page_registry import PAGE_TITLES, create_page


def ensure_page(window, key: str):
    if key in window.pages:
        return window.pages[key]
    page = create_page(window, key)
    window.pages[key] = page
    window.stack.addWidget(page)
    return page


def preload_pages(window, keys=None) -> None:
    for key in keys or window.page_order:
        ensure_page(window, key)


def clear_pages(window) -> None:
    while window.stack.count():
        widget = window.stack.widget(0)
        window.stack.removeWidget(widget)
        widget.setParent(None)
    window.pages.clear()


def reload_pages(window, current_page: str = "home") -> None:
    clear_pages(window)
    show_page(window, current_page)


def show_page(window, key: str) -> None:
    if key not in PAGE_TITLES:
        key = "home"
    previous_page = window.pages.get(window.current_page_key)
    if previous_page is not None and window.current_page_key != key:
        window._invoke_page_hook(previous_page, "on_hide")
    window.current_page_key = key
    window.dismiss_help_bubbles()
    page = ensure_page(window, key)
    window.stack.setCurrentWidget(page)
    for name, button in window.nav_buttons.items():
        button.setChecked(name == key)
    window.settings["ui"]["last_page"] = key
    QTimer.singleShot(0, lambda page=page: window._invoke_page_hook(page, "on_show"))


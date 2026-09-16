from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

from src.shared.qt import QApplication
from src.shared.theme import (
    ThemeColors,
    ThemeMode,
    build_style,
    normalize_theme_mode,
    theme_colors,
)


THEME_MODE_PROPERTY = "_yolotool_theme_mode"
DEFAULT_STYLE_PROPERTY = "_yolotool_default_style"


def build_palette(mode: object = "light") -> QPalette:
    c = theme_colors(mode)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(c.window))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(c.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(c.input_bg))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(c.table_alt))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(c.tooltip_bg))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(c.tooltip_text))
    palette.setColor(QPalette.ColorRole.Text, QColor(c.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(c.surface_alt))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(c.text))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Link, QColor(c.accent))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(c.selection))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(c.selection_text))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(c.text_muted))
    palette.setColor(QPalette.ColorRole.Light, QColor(c.surface))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(c.border))
    palette.setColor(QPalette.ColorRole.Mid, QColor(c.border_strong))
    palette.setColor(QPalette.ColorRole.Dark, QColor(c.border_strong))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(c.window))

    disabled = QPalette.ColorGroup.Disabled
    palette.setColor(disabled, QPalette.ColorRole.WindowText, QColor(c.disabled_text))
    palette.setColor(disabled, QPalette.ColorRole.Text, QColor(c.disabled_text))
    palette.setColor(disabled, QPalette.ColorRole.ButtonText, QColor(c.disabled_text))
    palette.setColor(disabled, QPalette.ColorRole.Button, QColor(c.disabled_bg))
    palette.setColor(disabled, QPalette.ColorRole.Base, QColor(c.disabled_bg))
    return palette


def apply_theme(app: QApplication, mode: object = "light") -> ThemeMode:
    normalized = normalize_theme_mode(mode)
    default_style = app.property(DEFAULT_STYLE_PROPERTY)
    if not default_style:
        default_style = app.style().objectName()
        app.setProperty(DEFAULT_STYLE_PROPERTY, default_style)
    if normalized == "dark":
        app.setStyle("Fusion")
    elif default_style:
        app.setStyle(str(default_style))
    app.setPalette(build_palette(normalized))
    app.setStyleSheet(build_style(normalized))
    app.setProperty(THEME_MODE_PROPERTY, normalized)
    return normalized


def current_theme_mode(app: QApplication | None = None) -> ThemeMode:
    resolved = app or QApplication.instance()
    if resolved is None:
        return "light"
    return normalize_theme_mode(resolved.property(THEME_MODE_PROPERTY))


def current_colors(app: QApplication | None = None) -> ThemeColors:
    return theme_colors(current_theme_mode(app))


__all__ = [
    "THEME_MODE_PROPERTY",
    "apply_theme",
    "build_palette",
    "current_colors",
    "current_theme_mode",
]

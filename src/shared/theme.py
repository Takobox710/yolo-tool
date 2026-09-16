from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ThemeMode = Literal["light", "dark"]


@dataclass(frozen=True, slots=True)
class ThemeColors:
    window: str
    surface: str
    surface_alt: str
    elevated: str
    nav: str
    nav_hover: str
    nav_text: str
    text: str
    page_title: str
    text_muted: str
    border: str
    border_strong: str
    input_bg: str
    input_border: str
    table_alt: str
    table_hover: str
    selection: str
    selection_text: str
    accent: str
    accent_hover: str
    primary_bg: str
    primary_hover: str
    primary_text: str
    disabled_bg: str
    disabled_text: str
    warning: str
    warning_bg: str
    tooltip_bg: str
    tooltip_text: str
    menu_bg: str
    menu_hover: str
    scroll_track: str
    scroll_handle: str
    scroll_handle_hover: str
    chart_bg: str
    chart_frame: str
    chart_grid_major: str
    chart_grid_minor: str
    chart_axis: str
    chart_label: str
    chart_muted: str
    canvas_bg: str
    canvas_border: str
    success: str
    success_hover: str
    success_soft: str
    success_text: str
    progress_track: str


LIGHT_COLORS = ThemeColors(
    window="#EEF2F6",
    surface="#FFFFFF",
    surface_alt="#F5F8FB",
    elevated="#F0F2F5",
    nav="#26394D",
    nav_hover="#344D66",
    nav_text="#FFFFFF",
    text="#14233A",
    page_title="#1A3857",
    text_muted="#627286",
    border="#D9E3EC",
    border_strong="#B8C4D0",
    input_bg="#FFFFFF",
    input_border="#CFD9E3",
    table_alt="#F7FAFC",
    table_hover="#EEF6FF",
    selection="#DCEEFF",
    selection_text="#0D2B49",
    accent="#208FD4",
    accent_hover="#1A7ABF",
    primary_bg="#1A7ABF",
    primary_hover="#16699F",
    primary_text="#FFFFFF",
    disabled_bg="#C0CCD8",
    disabled_text="#8899AA",
    warning="#C62828",
    warning_bg="#FCE8E6",
    tooltip_bg="#14233A",
    tooltip_text="#FFFFFF",
    menu_bg="#FFFFFF",
    menu_hover="#F0F4F8",
    scroll_track="#EDF1F5",
    scroll_handle="#B8C5D2",
    scroll_handle_hover="#93A5B6",
    chart_bg="#FFFFFF",
    chart_frame="#CFD9E3",
    chart_grid_major="#D7E0EA",
    chart_grid_minor="#EDF2F7",
    chart_axis="#000000",
    chart_label="#14233A",
    chart_muted="#94A2AD",
    canvas_bg="#F2F5F9",
    canvas_border="#D9E3EC",
    success="#117E4D",
    success_hover="#0F6E43",
    success_soft="#E8F7F0",
    success_text="#147548",
    progress_track="#E5E5E5",
)


DARK_COLORS = ThemeColors(
    window="#111820",
    surface="#1B242E",
    surface_alt="#242F3B",
    elevated="#202A35",
    nav="#152230",
    nav_hover="#273C50",
    nav_text="#F3F7FB",
    text="#E8EEF5",
    page_title="#4EA7E8",
    text_muted="#A8B5C3",
    border="#394756",
    border_strong="#516275",
    input_bg="#141C25",
    input_border="#465567",
    table_alt="#202A35",
    table_hover="#2A3948",
    selection="#245B84",
    selection_text="#FFFFFF",
    accent="#4EA7E8",
    accent_hover="#72BCEF",
    primary_bg="#2A75A8",
    primary_hover="#245F89",
    primary_text="#FFFFFF",
    disabled_bg="#2B3540",
    disabled_text="#758291",
    warning="#FF7B72",
    warning_bg="#3A2427",
    tooltip_bg="#2E3A47",
    tooltip_text="#F3F6FA",
    menu_bg="#1E2833",
    menu_hover="#2C4358",
    scroll_track="#151D25",
    scroll_handle="#4A5B6D",
    scroll_handle_hover="#667A8E",
    chart_bg="#1B242E",
    chart_frame="#3B4A5B",
    chart_grid_major="#344252",
    chart_grid_minor="#252F3A",
    chart_axis="#A8B5C3",
    chart_label="#E8EEF5",
    chart_muted="#8493A3",
    canvas_bg="#202833",
    canvas_border="#394756",
    success="#2B7A5A",
    success_hover="#1F7A52",
    success_soft="#173A2D",
    success_text="#8BE0B7",
    progress_track="#374452",
)


_THEMES = {"light": LIGHT_COLORS, "dark": DARK_COLORS}


LIGHT_STYLE = """
QWidget { font-family: "Microsoft YaHei UI"; font-size: 14px; color: #14233A; }
QMainWindow, QDialog, QMessageBox, QScrollArea, QScrollArea > QWidget > QWidget, QStackedWidget { background: #EEF2F6; }
#nav { background: #26394D; }
#brand { color: white; font-size: 24px; font-weight: 700; }
#navButton { color: white; background: transparent; border: 0; padding: 10px 14px; font-weight: 700; font-size: 17px; }
#navButton:checked, #navButton:hover { background: #344D66; border-radius: 6px; }
#dataSidebar { background: #26394D; border-radius: 8px; }
#dataSidebarTitle { color: white; font-size: 24px; font-weight: 700; padding: 4px 0 10px 0; }
#dataSidebarDivider { color: #536779; background: #536779; max-height: 1px; }
#dataNavButton { color: white; background: transparent; border: 0; padding: 10px 8px; text-align: left; font-size: 16px; }
#dataNavButton:checked, #dataNavButton:hover { background: #344D66; border-radius: 5px; }
#annotationSidebar { background: #26394D; border-radius: 8px; }
#annotationIcon { color: white; font-size: 30px; font-weight: 700; }
#annotationTitle { color: white; font-size: 24px; font-weight: 700; padding: 4px 0 10px 0; }
#annotationDivider { color: #536779; background: #536779; max-height: 1px; }
#annotationToolButton { color: white; background: transparent; border: 0; padding: 10px 8px; text-align: left; font-size: 16px; }
#annotationToolButton[compactArrowButton="true"] { padding-left: 6px; }
#annotationToolButton:hover { background: #344D66; border-radius: 5px; }
#annotationToolButton:disabled { color: #92A0AF; background: transparent; }
#annotationCanvas { background: #F3F6FA; border: 1px solid #D9E3EC; border-radius: 3px; }
#annotationRightPanel { background: transparent; }
#annotationPathLabel { color: #14233A; font-size: 16px; }
#annotationPrimaryButton { background: #26394D; color: white; border: 0; border-radius: 4px; padding: 9px 10px; }
#annotationPrimaryButton:hover { background: #344D66; }
#stack { background: #EEF2F6; }
#card { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
#pageTitle { color: #1A3857; font-size: 28px; font-weight: 700; }
#sectionTitle { color: #18344F; font-size: 18px; font-weight: 700; }
#metricValue { color: #0D2B49; font-size: 16px; font-weight: 700; }
#statValue { color: #0D2B49; font-size: 14px; font-weight: 700; }
#fieldLabel { color: #627286; font-size: 12px; }
#helpText { color: #627286; font-size: 12px; line-height: 18px; }
#inlineFieldLabel { color: #14233A; font-size: 14px; font-weight: 400; }
#annotationUnsaved, QComboBox[warning="true"] { color: #C62828; }
#modelExportSectionTitle { color: #18344F; font-size: 14px; font-weight: 700; }
#modelExportSectionDivider { background: #D9E3EC; color: #D9E3EC; }
#imageView { background: #F8FBFD; border: 1px solid #D9E3EC; border-radius: 6px; color: #627286; }
#statCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
#metricCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
#chartView { background: white; border: 0; }
#systemInfoOuter { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
#systemInfoInner { background: #F0F2F5; border: 1px solid #E0E3E8; border-radius: 6px; }
#upgradeIndicator { color: #208FD4; width: 26px; height: 26px; border: 0; border-radius: 0; background: transparent; padding: 0px; }
#upgradeIndicator:hover { background: transparent; }
#releaseCheckToast { background: white; border: 1px solid #D9E3EC; border-radius: 10px; }
#releaseCheckToast[failed="true"] { border-color: #E5A5A5; }
#releaseCheckProgress { background: #208FD4; border: 0; }
#releaseCheckToast[failed="true"] #releaseCheckProgress { background: #D95C5C; }
#releaseCheckIconBox { background: #F0F2F5; border: 0; border-radius: 8px; }
#releaseCheckIcon { color: #208FD4; font-size: 22px; font-weight: 700; }
#releaseCheckToast[failed="true"] #releaseCheckIcon { color: #D95C5C; }
#releaseCheckTitle { color: #14233A; font-size: 15px; font-weight: 400; }
#releaseCheckMessage { color: #627286; font-size: 13px; line-height: 20px; }
#releaseCheckClose { background: transparent; border: 0; color: #627286; font-size: 20px; padding: 0px 2px; }
#releaseCheckClose:hover { color: #14233A; }
QLineEdit, QTextEdit, QComboBox, QTableWidget { background: white; border: 1px solid #CFD9E3; border-radius: 5px; padding: 7px; }
QLineEdit#modelExportFlatEdit { padding: 0px 7px; }
QTableWidget { background: #FFFFFF; alternate-background-color: #F7FAFC; gridline-color: #E1E8F0; selection-background-color: #DCEEFF; selection-color: #0D2B49; }
QTableWidget::item { padding: 6px; border-bottom: 1px solid #E8EDF2; }
QTableWidget::item:hover { background: #EEF6FF; }
QHeaderView::section { background: #EAF1F8; color: #0D2B49; border: 0; border-right: 1px solid #D8E2EC; border-bottom: 1px solid #CBD8E4; padding: 7px 6px; font-weight: 700; }
QHeaderView::up-arrow { image: none; width: 0px; height: 0px; }
QHeaderView::down-arrow { image: none; width: 0px; height: 0px; }
QPushButton { background: #208FD4; color: white; border: 0; border-radius: 5px; padding: 9px 14px; }
QPushButton:hover { background: #1A7ABF; }
QPushButton#softButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; }
QPushButton#softButton:hover { background: #E8EDF2; border-color: #B8C4D0; }
QPushButton#compactSoftButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; border-radius: 5px; padding: 4px 10px; font-size: 14px; }
QPushButton#compactSoftButton:hover { background: #E8EDF2; border-color: #B8C4D0; }
QPushButton:disabled { background: #C0CCD8; color: #8899AA; }
QTabWidget::pane { border: 1px solid #D9E3EC; background: white; border-radius: 6px; }
QTabBar::tab { padding: 9px 16px; background: #F5F8FB; border: 1px solid #D9E3EC; }
QTabBar::tab:selected { background: white; color: #208FD4; }
QToolTip { background: #14233A; color: white; border: 0; border-radius: 4px; padding: 6px 8px; }
"""


def normalize_theme_mode(value: object) -> ThemeMode:
    return "dark" if str(value or "").strip().lower() == "dark" else "light"


def theme_colors(mode: object = "light") -> ThemeColors:
    return _THEMES[normalize_theme_mode(mode)]


def _build_dark_style() -> str:
    c = DARK_COLORS
    return f"""
QWidget {{ font-family: "Microsoft YaHei UI"; font-size: 14px; color: {c.text}; }}
QMainWindow, QDialog, QMessageBox, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {c.window}; }}
QScrollArea > QWidget > QWidget, QStackedWidget {{ color: {c.text}; }}
#nav {{ background: {c.nav}; }}
#brand {{ color: {c.nav_text}; font-size: 24px; font-weight: 700; }}
#navButton {{ color: {c.nav_text}; background: transparent; border: 0; padding: 10px 14px; font-weight: 700; font-size: 17px; }}
#navButton:checked, #navButton:hover {{ background: {c.nav_hover}; border-radius: 6px; }}
#dataSidebar, #annotationSidebar {{ background: {c.nav}; border-radius: 8px; }}
#dataSidebarTitle, #annotationTitle {{ color: {c.nav_text}; font-size: 24px; font-weight: 700; padding: 4px 0 10px 0; }}
#dataSidebarDivider, #annotationDivider {{ color: {c.nav_hover}; background: {c.nav_hover}; max-height: 1px; }}
#dataNavButton, #annotationToolButton {{ color: {c.nav_text}; background: transparent; border: 0; padding: 10px 8px; text-align: left; font-size: 16px; }}
#dataNavButton:checked, #dataNavButton:hover, #annotationToolButton:hover {{ background: {c.nav_hover}; border-radius: 5px; }}
#annotationToolButton[compactArrowButton="true"] {{ padding-left: 6px; }}
#annotationToolButton:disabled {{ color: {c.disabled_text}; background: transparent; }}
#annotationIcon {{ color: {c.nav_text}; font-size: 30px; font-weight: 700; }}
#annotationCanvas {{ background: {c.canvas_bg}; border: 1px solid {c.canvas_border}; border-radius: 3px; }}
#annotationRightPanel {{ background: transparent; }}
#annotationPathLabel {{ color: {c.text}; font-size: 16px; }}
#annotationPrimaryButton {{ background: {c.nav}; color: {c.nav_text}; border: 0; border-radius: 4px; padding: 9px 10px; }}
#annotationPrimaryButton:hover {{ background: {c.nav_hover}; }}
#stack {{ background: {c.window}; }}
#card {{ background: {c.surface}; border: 1px solid {c.border}; border-radius: 8px; }}
#pageTitle {{ color: {c.page_title}; font-size: 28px; font-weight: 700; }}
#sectionTitle {{ color: {c.text}; font-size: 18px; font-weight: 700; }}
#metricValue {{ color: {c.text}; font-size: 16px; font-weight: 700; }}
#statValue {{ color: {c.text}; font-size: 14px; font-weight: 700; }}
#fieldLabel, #helpText {{ color: {c.text_muted}; font-size: 12px; }}
#inlineFieldLabel {{ color: {c.text}; font-size: 14px; font-weight: 400; }}
#annotationUnsaved, QComboBox[warning="true"] {{ color: {c.warning}; }}
#modelExportSectionTitle {{ color: {c.text}; font-size: 14px; font-weight: 700; }}
#modelExportSectionDivider {{ background: {c.border}; color: {c.border}; }}
#imageView {{ background: {c.surface_alt}; border: 1px solid {c.border}; border-radius: 6px; color: {c.text_muted}; }}
#statCard, #metricCard {{ background: {c.surface_alt}; border: 1px solid {c.border}; border-radius: 6px; }}
#chartView {{ background: {c.chart_bg}; border: 0; }}
#systemInfoOuter {{ background: {c.surface}; border: 1px solid {c.border}; border-radius: 8px; }}
#systemInfoInner {{ background: {c.elevated}; border: 1px solid {c.border}; border-radius: 6px; }}
#upgradeIndicator {{ color: {c.accent}; width: 26px; height: 26px; border: 0; border-radius: 0; background: transparent; padding: 0px; }}
#upgradeIndicator:hover {{ background: transparent; }}
#releaseCheckToast {{ background: {c.surface}; border: 1px solid {c.border}; border-radius: 10px; }}
#releaseCheckToast[failed="true"] {{ border-color: {c.warning}; }}
#releaseCheckProgress {{ background: {c.accent}; border: 0; }}
#releaseCheckToast[failed="true"] #releaseCheckProgress {{ background: {c.warning}; }}
#releaseCheckIconBox {{ background: {c.elevated}; border: 0; border-radius: 8px; }}
#releaseCheckIcon {{ color: {c.accent}; font-size: 22px; font-weight: 700; }}
#releaseCheckToast[failed="true"] #releaseCheckIcon {{ color: {c.warning}; }}
#releaseCheckTitle {{ color: {c.text}; font-size: 15px; font-weight: 400; }}
#releaseCheckMessage {{ color: {c.text_muted}; font-size: 13px; line-height: 20px; }}
#releaseCheckClose {{ background: transparent; border: 0; color: {c.text_muted}; font-size: 20px; padding: 0px 2px; }}
#releaseCheckClose:hover {{ color: {c.text}; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {c.input_bg}; color: {c.text}; border: 1px solid {c.input_border}; border-radius: 5px; padding: 7px; selection-background-color: {c.selection}; selection-color: {c.selection_text}; }}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: {c.disabled_bg}; color: {c.disabled_text}; border-color: {c.border}; }}
QLineEdit#modelExportFlatEdit {{ padding: 0px 7px; }}
QComboBox QAbstractItemView {{ background: {c.input_bg}; color: {c.text}; border: 1px solid {c.border_strong}; padding: 4px; selection-background-color: {c.selection}; selection-color: {c.selection_text}; outline: 0; }}
QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 4px 8px; }}
QTableWidget, QTableView, QListWidget {{ background: {c.input_bg}; alternate-background-color: {c.table_alt}; color: {c.text}; border: 1px solid {c.input_border}; border-radius: 5px; gridline-color: {c.border}; selection-background-color: {c.selection}; selection-color: {c.selection_text}; outline: 0; }}
QTableWidget::item, QTableView::item {{ padding: 6px; border-bottom: 1px solid {c.border}; }}
QListWidget::item {{ padding: 0; border-bottom: 1px solid {c.border}; }}
QTableWidget::item:hover, QTableView::item:hover, QListWidget::item:hover {{ background: {c.table_hover}; }}
QHeaderView::section {{ background: {c.surface_alt}; color: {c.text}; border: 0; border-right: 1px solid {c.border}; border-bottom: 1px solid {c.border_strong}; padding: 7px 6px; font-weight: 700; }}
QHeaderView::up-arrow, QHeaderView::down-arrow {{ image: none; width: 0px; height: 0px; }}
QPushButton {{ background: {c.primary_bg}; color: {c.primary_text}; border: 0; border-radius: 5px; padding: 9px 14px; }}
QPushButton:hover {{ background: {c.primary_hover}; }}
QPushButton#softButton {{ background: {c.surface_alt}; color: {c.text}; border: 1px solid {c.border}; }}
QPushButton#softButton:hover {{ background: {c.elevated}; border-color: {c.border_strong}; }}
QPushButton#compactSoftButton {{ background: {c.surface_alt}; color: {c.text}; border: 1px solid {c.border}; border-radius: 5px; padding: 4px 10px; font-size: 14px; }}
QPushButton#compactSoftButton:hover {{ background: {c.elevated}; border-color: {c.border_strong}; }}
QPushButton:disabled {{ background: {c.disabled_bg}; color: {c.disabled_text}; }}
QToolButton {{ color: {c.text}; background: {c.surface_alt}; border: 1px solid {c.border}; border-radius: 5px; padding: 5px 8px; }}
QToolButton:hover {{ background: {c.elevated}; border-color: {c.border_strong}; }}
QTabWidget::pane {{ border: 1px solid {c.border}; background: {c.surface}; border-radius: 6px; }}
QTabBar::tab {{ padding: 9px 16px; background: {c.surface_alt}; color: {c.text}; border: 1px solid {c.border}; }}
QTabBar::tab:selected {{ background: {c.surface}; color: {c.accent}; }}
QTabBar::tab:hover:!selected {{ background: {c.elevated}; }}
QToolTip {{ background: {c.tooltip_bg}; color: {c.tooltip_text}; border: 1px solid {c.border_strong}; border-radius: 4px; padding: 6px 8px; }}
QMenu {{ background: {c.menu_bg}; color: {c.text}; border: 1px solid {c.border}; padding: 4px; }}
QMenu::item {{ padding: 7px 28px 7px 22px; background: transparent; }}
QMenu::item:selected {{ background: {c.menu_hover}; color: {c.text}; }}
QMenu::separator {{ height: 1px; background: {c.border}; margin: 5px 8px; }}
QProgressBar {{ background: {c.progress_track}; color: {c.text}; border: 0; border-radius: 4px; text-align: center; }}
QProgressBar::chunk {{ background: {c.accent}; border-radius: 4px; }}
QSlider::groove:horizontal {{ height: 4px; border-radius: 2px; background: {c.border}; }}
QSlider::sub-page:horizontal {{ background: {c.accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 16px; margin: -6px 0; border-radius: 8px; background: {c.surface}; border: 2px solid {c.accent}; }}
QScrollBar:vertical {{ background: {c.scroll_track}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c.scroll_handle}; min-height: 28px; border-radius: 6px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {c.scroll_handle_hover}; }}
QScrollBar:horizontal {{ background: {c.scroll_track}; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {c.scroll_handle}; min-width: 28px; border-radius: 6px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {c.scroll_handle_hover}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; border: 0; width: 0; height: 0; }}
QStatusBar {{ background: {c.window}; color: {c.text_muted}; }}
"""


def build_style(mode: object = "light") -> str:
    if normalize_theme_mode(mode) == "light":
        return LIGHT_STYLE
    return _build_dark_style()


STYLE = LIGHT_STYLE


def build_draw_shape_style(mode: object = "light") -> str:
    c = theme_colors(mode)
    return f"""
QFrame#drawShapeList {{ background: {c.surface}; border: 1px solid {c.border}; border-radius: 10px; }}
QFrame#drawShapeDivider {{ background: {c.border}; }}
QPushButton#drawShapeEditOption, QPushButton#drawShapeOptionSingle, QPushButton#drawShapeOptionFirst,
QPushButton#drawShapeOption, QPushButton#drawShapeOptionLast {{
    background: {c.surface}; color: {c.text}; border: 0; border-radius: 0;
    padding: 10px 14px; text-align: center; font-size: 15px;
}}
QPushButton#drawShapeEditOption {{ border-top-left-radius: 10px; border-top-right-radius: 10px; }}
QPushButton#drawShapeOptionSingle {{ border-radius: 10px; }}
QPushButton#drawShapeOptionFirst {{ border-top-left-radius: 0; border-top-right-radius: 0; border-bottom: 1px solid {c.border}; }}
QPushButton#drawShapeOption {{ border-bottom: 1px solid {c.border}; }}
QPushButton#drawShapeOptionLast {{ border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }}
QPushButton#drawShapeEditOption:hover, QPushButton#drawShapeOptionSingle:hover,
QPushButton#drawShapeOptionFirst:hover, QPushButton#drawShapeOption:hover,
QPushButton#drawShapeOptionLast:hover {{ background: {c.surface_alt}; }}
QPushButton#drawShapeOptionSingle:disabled, QPushButton#drawShapeOptionFirst:disabled,
QPushButton#drawShapeOption:disabled, QPushButton#drawShapeOptionLast:disabled {{ background: {c.disabled_bg}; color: {c.disabled_text}; }}
QPushButton#samAdvancedButton {{ background: {c.surface}; color: {c.text}; border: 1px solid {c.input_border}; border-radius: 6px; padding: 0 8px; font-size: 14px; }}
QPushButton#samAdvancedButton:hover {{ background: {c.surface_alt}; border-color: {c.border_strong}; }}
QPushButton#samAdvancedButton:disabled {{ background: {c.disabled_bg}; color: {c.disabled_text}; border-color: {c.border}; }}
"""


def build_sam_advanced_style(mode: object = "light") -> str:
    c = theme_colors(mode)
    return f"""
QDialog#samAdvancedDialog {{ background: {c.surface}; color: {c.text}; }}
QLabel {{ color: {c.text}; font-size: 14px; }}
QLabel#samAdvancedCaption {{ color: {c.text_muted}; }}
QLabel#samAdvancedSectionTitle {{ font-size: 16px; font-weight: 600; }}
QFrame#samAdvancedSeparator {{ background: {c.border}; border: 0; }}
QPushButton {{ min-height: 34px; padding: 0 16px; border: 1px solid {c.input_border}; border-radius: 6px; background: {c.surface}; color: {c.text}; }}
QPushButton:hover {{ background: {c.surface_alt}; border-color: {c.border_strong}; }}
QPushButton#samSegmentLeft, QPushButton#samSegmentRight {{ min-height: 32px; padding: 0 12px; border-radius: 0; }}
QPushButton#samSegmentLeft {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; }}
QPushButton#samSegmentRight {{ border-left: 0; border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
QPushButton#samSegmentLeft:checked, QPushButton#samSegmentRight:checked {{ background: {c.success_soft}; border-color: {c.success}; color: {c.success_text}; font-weight: 600; }}
QPushButton#samAdvancedReset {{ background: transparent; color: {c.text_muted}; }}
QPushButton#samAdvancedSave {{ background: {c.success}; border-color: {c.success}; color: #FFFFFF; font-weight: 600; min-width: 72px; }}
QPushButton#samAdvancedSave:hover {{ background: {c.success_hover}; border-color: {c.success_hover}; }}
QComboBox#samAdvancedModelCombo {{ min-height: 32px; border: 1px solid {c.input_border}; border-radius: 6px; padding: 0 8px; background: {c.input_bg}; color: {c.text}; }}
QComboBox#samAdvancedModelCombo:focus {{ border-color: {c.success}; }}
QPushButton#samOpenModelFolder {{ min-height: 32px; padding: 0 8px; border: 1px solid {c.input_border}; border-radius: 6px; background: {c.surface}; color: {c.text}; }}
QPushButton#samOpenModelFolder:hover {{ background: {c.surface_alt}; border-color: {c.border_strong}; }}
QPushButton#samOpenModelFolder:disabled {{ background: {c.disabled_bg}; color: {c.disabled_text}; border-color: {c.border}; }}
QSpinBox, QDoubleSpinBox {{ min-height: 32px; border: 1px solid {c.input_border}; border-radius: 6px; padding: 0 8px; background: {c.input_bg}; color: {c.text}; }}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {c.success}; }}
QSlider::groove:horizontal {{ height: 4px; border-radius: 2px; background: {c.border}; }}
QSlider::sub-page:horizontal {{ background: {c.success}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 16px; margin: -6px 0; border-radius: 8px; background: {c.surface}; border: 2px solid {c.success}; }}
"""


def build_release_dialog_style(mode: object = "light") -> str:
    c = theme_colors(mode)
    return f"""
QDialog#releaseUpdateDialog {{ background: {c.surface}; color: {c.text}; border: 1px solid {c.border}; border-radius: 12px; }}
QLabel#releaseDialogTitle {{ color: {c.text}; font-size: 20px; font-weight: 700; }}
QLabel#releaseDialogCurrent, QLabel#releaseProgressMessage {{ color: {c.text_muted}; font-size: 13px; }}
QLabel#releaseProgressMessage[warning="true"] {{ color: {c.warning}; font-weight: 700; }}
QLabel#releaseMetricLabel {{ color: {c.text_muted}; font-size: 15px; min-width: 120px; }}
QLabel#releaseMetricValue {{ color: {c.text}; font-size: 16px; font-weight: 700; }}
QFrame#releaseMetricRow {{ border-bottom: 1px solid {c.border}; }}
QLabel#releaseDialogSection {{ color: {c.text}; font-size: 15px; font-weight: 700; }}
QPlainTextEdit#releaseDialogNotes {{ background: {c.input_bg}; color: {c.text}; border: 1px solid {c.input_border}; border-radius: 6px; padding: 10px; font-size: 14px; }}
QFrame#releaseProgressPanel, QFrame#releaseEnvironmentNotice {{ background: {c.surface_alt}; border: 1px solid {c.border}; border-radius: 8px; }}
QLabel#releaseEnvironmentTitle {{ color: {c.text}; font-size: 14px; font-weight: 700; }}
QLabel#releaseEnvironmentText {{ color: {c.text_muted}; font-size: 13px; }}
QLabel#releaseProgressPercent, QLabel#releaseDownloadSpeed, QLabel#releaseDownloadSize, QLabel#releaseDownloadOptionsTitle {{ color: {c.text_muted}; font-size: 13px; }}
QCheckBox {{ color: {c.text}; font-size: 13px; }}
QProgressBar#releaseProgressBar {{ background: {c.progress_track}; border: 0; border-radius: 4px; }}
QProgressBar#releaseProgressBar::chunk {{ background: {c.accent}; border-radius: 4px; }}
QPushButton {{ min-height: 34px; padding: 0 14px; border-radius: 6px; font-size: 14px; }}
QPushButton#releaseDownloadButton {{ background: {c.primary_bg}; color: {c.primary_text}; border: 0; }}
QPushButton#releaseDownloadButton:hover {{ background: {c.primary_hover}; }}
QPushButton#releaseDownloadButton:disabled {{ background: {c.disabled_bg}; color: {c.disabled_text}; }}
QPushButton#releaseGithubButton, QPushButton#releaseRefreshButton, QPushButton#releasePauseButton,
QPushButton#releaseStopButton, QPushButton#releaseCloseButton {{ background: {c.surface_alt}; color: {c.text}; border: 1px solid {c.border}; }}
QPushButton#releaseGithubButton:hover, QPushButton#releaseRefreshButton:hover, QPushButton#releasePauseButton:hover,
QPushButton#releaseStopButton:hover, QPushButton#releaseCloseButton:hover {{ background: {c.elevated}; border-color: {c.border_strong}; }}
"""


__all__ = [
    "DARK_COLORS",
    "LIGHT_COLORS",
    "STYLE",
    "ThemeColors",
    "ThemeMode",
    "build_draw_shape_style",
    "build_release_dialog_style",
    "build_sam_advanced_style",
    "build_style",
    "normalize_theme_mode",
    "theme_colors",
]

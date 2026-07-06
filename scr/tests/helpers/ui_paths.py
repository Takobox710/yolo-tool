from __future__ import annotations

from pathlib import Path

APP = Path("scr/ui/app.py")
ICON_PNG = Path("scr/assets/app_icon.png")
ICON_ICO = Path("scr/assets/app_icon.ico")
WINDOW = Path("scr/ui/window.py")
PAGE_BASE = Path("scr/ui/page_base.py")
FORMS = Path("scr/ui/forms.py")
HOME_VIEW = Path("scr/ui/views/home.py")
DATA_VIEW = Path("scr/ui/views/data.py")
TRAIN_VIEW = Path("scr/ui/views/training.py")
TRAIN_FORM_VIEW = Path("scr/ui/views/training_form.py")
VALIDATE_VIEW = Path("scr/ui/views/validation.py")
VALIDATE_LAYOUT_VIEW = Path("scr/ui/views/validation_layout.py")
SETTINGS_VIEW = Path("scr/ui/views/settings.py")
PACKAGING_SPEC = Path("installer/YOLOTool.spec")
PACKAGING_SCRIPT = Path("installer/build_windows.ps1")
PACKAGING_ONE_CLICK_SCRIPT = Path("installer/打包程序.ps1")
INSTALLER_ISS = Path("installer/yolo_tool.iss")
PACKAGING_DOC = Path("docs/packaging-windows.md")

UI_BUNDLE_PATHS = [
    APP,
    WINDOW,
    PAGE_BASE,
    FORMS,
    HOME_VIEW,
    DATA_VIEW,
    TRAIN_VIEW,
    TRAIN_FORM_VIEW,
    VALIDATE_VIEW,
    VALIDATE_LAYOUT_VIEW,
    SETTINGS_VIEW,
]

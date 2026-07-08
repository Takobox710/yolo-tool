from __future__ import annotations

from pathlib import Path

APP = Path("src/ui/app.py")
ICON_PNG = Path("src/assets/app_icon.png")
ICON_ICO = Path("src/assets/app_icon.ico")
WINDOW = Path("src/ui/shell/window.py")
PAGE_BASE = Path("src/ui/shared/page_base.py")
FORMS = Path("src/ui/shared/forms.py")
HOME_VIEW = Path("src/ui/features/home/page.py")
HOME_LAYOUT_VIEW = Path("src/ui/features/home/layout.py")
HOME_DATA_VIEW = Path("src/ui/features/home/data.py")
DATA_VIEW = Path("src/ui/features/data/page.py")
TRAIN_VIEW = Path("src/ui/features/training/page.py")
TRAIN_FORM_VIEW = Path("src/ui/features/training/form.py")
TRAIN_RUNTIME_VIEW = Path("src/ui/features/training/runtime.py")
TRAIN_STATE_VIEW = Path("src/ui/features/training/state.py")
VALIDATE_VIEW = Path("src/ui/features/validation/page.py")
VALIDATE_LAYOUT_VIEW = Path("src/ui/features/validation/layout.py")
VALIDATE_RESULTS_VIEW = Path("src/ui/features/validation/results.py")
VALIDATE_STATE_VIEW = Path("src/ui/features/validation/state.py")
VALIDATE_RUNTIME_VIEW = Path("src/ui/features/validation/runtime.py")
VALIDATE_MODELS_VIEW = Path("src/ui/features/validation/models.py")
VALIDATE_SOURCES_VIEW = Path("src/ui/features/validation/sources.py")
VALIDATE_DATASET_MODE_VIEW = Path("src/ui/features/validation/dataset_mode.py")
VALIDATE_RESULT_LIST_VIEW = Path("src/ui/features/validation/result_list.py")
SETTINGS_VIEW = Path("src/ui/features/settings/page.py")
SETTINGS_LAYOUT_VIEW = Path("src/ui/features/settings/layout.py")
SETTINGS_STATE_VIEW = Path("src/ui/features/settings/state.py")
ANNOTATION_VIEW = Path("src/ui/features/annotation/page.py")
ANNOTATION_DIALOGS_VIEW = Path("src/ui/features/annotation/dialogs.py")
ANNOTATION_CANVAS_VIEW = Path("src/ui/features/annotation/canvas/widget.py")
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
    HOME_LAYOUT_VIEW,
    HOME_DATA_VIEW,
    DATA_VIEW,
    TRAIN_VIEW,
    TRAIN_FORM_VIEW,
    TRAIN_RUNTIME_VIEW,
    TRAIN_STATE_VIEW,
    VALIDATE_VIEW,
    VALIDATE_LAYOUT_VIEW,
    VALIDATE_RESULTS_VIEW,
    VALIDATE_STATE_VIEW,
    VALIDATE_RUNTIME_VIEW,
    VALIDATE_MODELS_VIEW,
    VALIDATE_SOURCES_VIEW,
    VALIDATE_DATASET_MODE_VIEW,
    VALIDATE_RESULT_LIST_VIEW,
    SETTINGS_VIEW,
    SETTINGS_LAYOUT_VIEW,
    SETTINGS_STATE_VIEW,
    ANNOTATION_VIEW,
    ANNOTATION_DIALOGS_VIEW,
    ANNOTATION_CANVAS_VIEW,
]


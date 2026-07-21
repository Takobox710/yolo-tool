from pathlib import Path

import os

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
    VALIDATE_LAYOUT_VIEW,
    VALIDATE_VIEW,
    WINDOW,
)


def _read_app():
    return APP.read_text(encoding="utf-8")

def _read_ui_bundle():
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_BUNDLE_PATHS)


def test_project_path_helpers_display_relative_and_resolve_user_text(tmp_path):
    from src.ui.helpers import display_project_path, resolve_project_path

    inside = tmp_path / "data" / "data.yaml"
    outside = tmp_path.parent / "outside" / "model.pt"

    assert display_project_path(str(inside), tmp_path) == str(
        Path("data") / "data.yaml"
    )
    assert display_project_path(str(outside), tmp_path) == str(outside.resolve())
    assert Path(resolve_project_path("data/data.yaml", tmp_path)) == inside.resolve()
    assert (
        Path(resolve_project_path(str(inside).replace(os.sep, "/"), tmp_path))
        == inside.resolve()
    )


def test_qt_app_uses_project_local_icon_assets():
    src = _read_ui_bundle()
    app_src = APP.read_text(encoding="utf-8")
    assert "from src.shared.paths import ICON_PNG" in src
    assert "if ICON_PNG.exists():" in src
    assert "app.setWindowIcon(QIcon(str(ICON_PNG)))" in app_src
    assert "self.setWindowIcon(app_icon)" in src
    assert ICON_PNG.exists()
    assert ICON_ICO.exists()


def test_app_file_has_direct_script_import_bootstrap():
    src = Path("src/main.py").read_text(encoding="utf-8")
    assert "freeze_support()" in src
    assert "from src.app import run_app" in src
    assert "run_app()" in src


def test_shared_paths_use_repo_root_in_dev_mode():
    from src.shared.paths import (
        ASSETS_ROOT,
        DATA_ROOT,
        ICON_ICO,
        ICON_PNG,
        PACKAGE_ROOT,
        ROOT,
        RUNTIME_ROOT,
    )

    repo_root = Path.cwd().resolve()

    assert ROOT == repo_root
    assert PACKAGE_ROOT == repo_root / "src"
    assert ASSETS_ROOT == repo_root / "src" / "assets"
    assert DATA_ROOT == repo_root / "data"
    assert RUNTIME_ROOT == repo_root / "data" / "runtime"
    assert ICON_PNG == repo_root / "src" / "assets" / "app_icon.png"
    assert ICON_ICO == repo_root / "src" / "assets" / "app_icon.ico"


def test_direct_script_hidden_train_entry_has_package_context():
    result = subprocess.run(
        [sys.executable, "src/main.py", "--yolo-train"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "Usage: --yolo-train" in result.stderr
    assert "attempted relative import" not in result.stderr


def test_direct_script_hidden_val_entry_has_package_context():
    result = subprocess.run(
        [sys.executable, "src/main.py", "--yolo-val"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "Usage: --yolo-val" in result.stderr
    assert "attempted relative import" not in result.stderr


def test_windows_packaging_files_document_project_local_runtime_settings():
    assert PACKAGING_SPEC.exists()
    assert PACKAGING_SCRIPT.exists()
    assert PACKAGING_ONE_CLICK_SCRIPT.exists()
    assert INSTALLER_ISS.exists()
    assert PACKAGING_DOC.exists()

    spec = PACKAGING_SPEC.read_text(encoding="utf-8")
    script = PACKAGING_SCRIPT.read_text(encoding="utf-8")
    one_click_script = PACKAGING_ONE_CLICK_SCRIPT.read_text(encoding="utf-8")
    iss = INSTALLER_ISS.read_text(encoding="utf-8")
    doc = PACKAGING_DOC.read_text(encoding="utf-8")

    assert "onedir" in doc
    assert "Mode dev" in doc or "-Mode dev" in doc
    assert "YOLOTool-dev" in doc
    assert "data/runtime/settings.json" in doc
    assert "src/main.py" in spec
    assert 'mode = os.environ.get("YOLO_TOOL_BUILD_MODE", "release")' in spec
    assert '"PySide6.scripts.deploy_lib"' in spec
    assert '"torch.utils.tensorboard"' in spec
    assert "excludedimports = [\"torch.utils.tensorboard\"]" in Path("installer/hooks/hook-torch.py").read_text(encoding="utf-8")
    assert 'module_collection_mode = "pyz+py"' in Path("installer/hooks/hook-torch.py").read_text(encoding="utf-8")
    assert 'collect_submodules("torch")' in Path("installer/hooks/hook-torch.py").read_text(encoding="utf-8")
    assert "pyinstaller" in script
    assert 'ValidateSet("release", "dev")' in script
    assert 'YOLO_TOOL_BUILD_MODE' in script
    assert 'ROOT_MODEL_FILES = [' in spec
    assert '"data/models"' in spec
    assert 'HOOKS_DIR = ROOT / "installer" / "hooks"' in spec
    assert 'SetupIconFile=..\\src\\assets\\app_icon.ico' in iss
    assert 'Source: "..\\dist\\YOLOTool\\{#MyAppExeName}"' in iss
    assert 'Source: "..\\dist\\YOLOTool\\*.pt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist' in iss
    assert '$TargetModelPath = Join-Path $TargetModelsDir $ModelFile.Name' in script
    assert 'Copy-Item -LiteralPath $RootModelPath -Destination $TargetRootModelPath -Force' in script
    assert 'Build output is missing root model file: yolo26n.pt' in script
    assert 'Build output is missing model files under data/models' in script
    assert 'from src.services.settings import build_default_settings, save_last_project_root' in script
    assert 'settings = build_default_settings(app_dir)' in script
    assert 'save_last_project_root(app_dir, app_dir / "data" / "runtime" / "app_state.json")' in script
    assert 'Build output is missing runtime settings file: data/runtime/settings.json' in script
    assert 'Build output is missing app state file: data/runtime/app_state.json' in script
    assert "build_windows.ps1" in one_click_script


def test_qt_app_matches_reference_ui_sections():
    src = _read_ui_bundle()
    for expected in [
        "欢迎使用 YOLO 本地训练工作台",
        "项目概览",
        "各类别图片分布",
        "训练历史",
        "项目文件夹",
        "图片路径",
        "标注路径",
        "结果路径",
        "图片数量",
        "标注数量",
        "随机拼图",
        "图片检测",
        "QComboBox",
        "tool_stack",
        "dataNavButton",
        "show_tool",
        "标注转换",
        "标注预览",
        "批量重命名",
        "图片压缩",
            "批量检测结果",
            "show_result_list",
            "open_detection_save_dir",
            "模型配置",
            "源",
            "检测结果",
        "检测结果详情表",
        "status_cards",
        "QStackedWidget",
        "数据集与增强配置",
        "训练参数",
        "GPU",
        "显存占用",
        "CPU占用",
        "内存占用",
        "inline_field",
        "inline_combo_field",
        "short_gpu_name",
        "left_shell = Card()",
    ]:
        assert expected in src
    assert 'page.start_btn = QPushButton("开始训练")' in src
    assert "sidebar.setFixedWidth(178)" in src
    assert 'title = QLabel("模型训练")' not in src
    assert 'title = QLabel("模型验证")' not in src
    assert 'QLabel("模型配置")' in VALIDATE_LAYOUT_VIEW.read_text(encoding="utf-8")
    assert "最近活动" not in src
    assert '"自动任务类型"' not in src
    assert '"导出格式"' not in src
    assert 'Card("训练控制")' not in src
    assert 'Card("系统状态")' not in src
    assert 'Card("任务类型")' not in src
    assert "log_panel = Card()" in src
    assert 'Card("训练日志")' not in src
    assert 'Card("训练曲线")' not in src
    assert "TrainingCurveWidget" in src
    assert "配置项目路径、检查数据状态、查看训练结果。" not in src


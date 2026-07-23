from pathlib import Path

import os

import subprocess

import sys

from types import SimpleNamespace

from src.tests.helpers.ui_paths import (
    ICON_ICO,
    ICON_PNG,
    INSTALLER_ISS,
    PACKAGING_DOC,
    PACKAGING_ONE_CLICK_SCRIPT,
    PACKAGING_SCRIPT,
    PACKAGING_SPEC,
)


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


def test_shared_paths_use_dev_and_frozen_resource_roots(monkeypatch, tmp_path):
    import importlib

    import src.shared.paths as paths
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

    resource_root = tmp_path / "_internal"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(resource_root), raising=False)
    frozen_paths = importlib.reload(paths)

    assert frozen_paths.ROOT == Path(sys.executable).resolve().parent
    assert frozen_paths.PACKAGE_ROOT == resource_root / "src"
    assert frozen_paths.ASSETS_ROOT == Path(sys.executable).resolve().parent / "app_assets"

    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    importlib.reload(paths)


def test_direct_script_hidden_cli_entries_have_package_context():
    for option in ("--yolo-train", "--yolo-val"):
        result = subprocess.run(
            [sys.executable, "src/main.py", option],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            timeout=30,
        )

        assert result.returncode != 0
        assert f"Usage: {option}" in result.stderr
        assert "attempted relative import" not in result.stderr


def test_windows_packaging_files_document_project_local_runtime_settings():
    assert PACKAGING_SPEC.exists()
    assert PACKAGING_SCRIPT.exists()
    assert PACKAGING_ONE_CLICK_SCRIPT.exists()
    assert INSTALLER_ISS.exists()
    assert PACKAGING_DOC.exists()
    assert ICON_PNG.exists()
    assert ICON_ICO.exists()

    spec = PACKAGING_SPEC.read_text(encoding="utf-8")
    script = PACKAGING_SCRIPT.read_text(encoding="utf-8")
    one_click_script = PACKAGING_ONE_CLICK_SCRIPT.read_text(encoding="utf-8")
    iss = INSTALLER_ISS.read_text(encoding="utf-8")
    doc = PACKAGING_DOC.read_text(encoding="utf-8")

    assert "onedir" in doc and "YOLOTool-dev" in doc
    assert "data/runtime/settings.json" in doc
    assert "src/main.py" in spec
    assert 'mode = os.environ.get("YOLO_TOOL_BUILD_MODE", "release")' in spec
    assert 'HOOKS_DIR = ROOT / "installer" / "hooks"' in spec
    assert 'SetupIconFile=..\\src\\assets\\app_icon.ico' in iss
    assert 'Source: "..\\dist\\packages\\{#PackageType}\\YOLOTool.exe"' in iss
    assert 'PackageType == "RuntimeFull"' in iss
    assert "pyinstaller" in script and "app_assets" in script
    assert "src.devtools.release_package" in script and "PackageType" in script
    assert '$TargetModelPath = Join-Path $TargetModelsDir $ModelFile.Name' in script
    assert 'save_last_project_root(app_dir, app_dir / "data" / "runtime" / "app_state.json")' in script
    assert "build_windows.ps1" in one_click_script

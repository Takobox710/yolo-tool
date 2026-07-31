from pathlib import Path

import os

import subprocess

import sys

from types import SimpleNamespace

import json

from src.tests.helpers.ui_paths import (
    ICON_ICO,
    ICON_PNG,
    INSTALLER_ISS,
    PACKAGING_DOC,
    PACKAGING_PACKAGE_SCRIPT,
    PACKAGING_FULL_BAT,
    PACKAGING_PROGRAM_ONLY_BAT,
    PACKAGING_SCRIPT,
    PACKAGING_SPEC,
)


def test_runtime_probe_only_compares_program_and_base_runtime_versions(
    monkeypatch, capsys
):
    from src.services.runtime import release_manifest
    from src.train_cli import run_runtime_probe_cli

    monkeypatch.setattr(
        release_manifest,
        "check_runtime_compatibility",
        lambda: release_manifest.RuntimeCompatibility(
            True, "runtime-1", "runtime-1", "运行环境匹配"
        ),
    )

    assert run_runtime_probe_cli([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "runtime_version": "runtime-1",
        "required_runtime_version": "runtime-1",
        "reason": "运行环境匹配",
    }


def test_runtime_probe_returns_failure_for_runtime_version_mismatch(
    monkeypatch, capsys
):
    from src.services.runtime import release_manifest
    from src.train_cli import run_runtime_probe_cli

    monkeypatch.setattr(
        release_manifest,
        "check_runtime_compatibility",
        lambda: release_manifest.RuntimeCompatibility(
            False,
            "runtime-1",
            "runtime-2",
            "当前运行环境为 runtime-1，程序要求 runtime-2",
        ),
    )

    assert run_runtime_probe_cli([]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["runtime_version"] == "runtime-1"
    assert payload["required_runtime_version"] == "runtime-2"


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
        SAM_ASSIST_ICON,
    )

    repo_root = Path.cwd().resolve()

    assert ROOT == repo_root
    assert PACKAGE_ROOT == repo_root / "src"
    assert ASSETS_ROOT == repo_root / "src" / "assets"
    assert DATA_ROOT == repo_root / "data"
    assert RUNTIME_ROOT == repo_root / "data" / "runtime"
    assert ICON_PNG == repo_root / "src" / "assets" / "app_icon.png"
    assert ICON_ICO == repo_root / "src" / "assets" / "app_icon.ico"
    assert SAM_ASSIST_ICON == repo_root / "src" / "assets" / "sam_assist.svg"

    resource_root = tmp_path / "_internal"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(resource_root), raising=False)
    frozen_paths = importlib.reload(paths)

    assert frozen_paths.ROOT == Path(sys.executable).resolve().parent
    assert frozen_paths.PACKAGE_ROOT == resource_root / "src"
    assert frozen_paths.ASSETS_ROOT == resource_root / "src" / "assets"

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
    assert PACKAGING_PACKAGE_SCRIPT.exists()
    assert PACKAGING_FULL_BAT.exists()
    assert PACKAGING_PROGRAM_ONLY_BAT.exists()
    assert INSTALLER_ISS.exists()
    assert PACKAGING_DOC.exists()
    assert ICON_PNG.exists()
    assert ICON_ICO.exists()

    spec = PACKAGING_SPEC.read_text(encoding="utf-8")
    script = PACKAGING_SCRIPT.read_text(encoding="utf-8")
    package_windows_script = PACKAGING_PACKAGE_SCRIPT.read_text(encoding="utf-8")
    full_bat_bytes = PACKAGING_FULL_BAT.read_bytes()
    program_only_bat_bytes = PACKAGING_PROGRAM_ONLY_BAT.read_bytes()
    full_bat = full_bat_bytes.decode("ascii")
    program_only_bat = program_only_bat_bytes.decode("ascii")
    iss = INSTALLER_ISS.read_text(encoding="utf-8")
    doc = PACKAGING_DOC.read_text(encoding="utf-8")

    assert "onedir" in doc and "YOLOTool-dev" in doc
    assert "data/runtime/settings.json" in doc
    assert "src/main.py" in spec
    assert 'mode = os.environ.get("YOLO_TOOL_BUILD_MODE", "release")' in spec
    assert 'HOOKS_DIR = ROOT / "installer" / "hooks"' in spec
    assert 'SetupIconFile=..\\src\\assets\\app_icon.ico' in iss
    assert 'Source: "..\\dist\\packages\\Program\\YOLOTool.exe"' in iss
    assert 'Source: "{code:GetBaseArchivePath}"' in iss
    assert "ArchiveExtraction=full" in iss
    assert "CreateUninstallRegKey=no" in iss
    assert "YOLOTool_' + PathInstanceId" in iss
    assert "WriteUninstallRegistration" in iss
    assert "CreateCustomPage(wpSelectDir, '选择安装组件'" in iss
    assert "--remove-managed-models" in iss
    assert 'Source: "..\\dist\\packages\\Program\\_internal' not in iss
    assert "Full" not in iss and "AppUpdate" not in iss and "RuntimeFull" not in iss
    assert "pyinstaller" in script and "app_assets" not in script
    assert Path("src/assets.qrc").exists()
    assert "assets_rc" in Path("src/ui/shared/assets.py").read_text(encoding="utf-8")
    assert "sam_assist.svg" in Path("src/assets.qrc").read_text(encoding="utf-8")
    assert "load_sam_assist_icon" in Path("src/ui/shared/assets.py").read_text(
        encoding="utf-8"
    )
    assert "src.devtools.release_package" in script and "PackageType" in script
    assert '"sam2.1_hiera_base_plus.pt"' in script
    assert 'save_last_project_root(app_dir, app_dir / "data" / "runtime" / "app_state.json")' in script
    assert "BuildBaseRuntimeModels" in package_windows_script
    assert "BuildModelExportRuntime" in package_windows_script
    assert "SkipModelExportRuntime" in package_windows_script
    assert "package_windows.ps1" in full_bat
    assert "-BuildBaseRuntimeModels" in full_bat
    assert "-BuildModelExportRuntime" in full_bat
    assert 'set /p "PACKAGE_MODE=' in full_bat
    assert 'if /i "%PACKAGE_MODE%"=="C"' in full_bat
    assert 'else if /i "%PACKAGE_MODE%"=="G"' in full_bat
    assert "pwsh.exe -NoProfile" in full_bat
    assert "WindowsPowerShell" not in full_bat
    assert 'set "PACKAGE_ARGS=-BuildBaseRuntimeModels"' in full_bat
    assert 'set "PACKAGE_ARGS=-BuildBaseRuntimeModels -BuildModelExportRuntime"' in full_bat
    assert "package_windows.ps1" in program_only_bat
    assert "-BuildBaseRuntimeModels" not in program_only_bat
    assert "-BuildModelExportRuntime" not in program_only_bat
    assert b"\r\n" in full_bat_bytes and b"\r\n" in program_only_bat_bytes

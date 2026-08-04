from __future__ import annotations

from pathlib import Path


INSTALLER = Path("installer/yolo_tool.iss")


def _section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]

def test_release_artifact_names_and_versions_are_short_and_stable():
    installer = INSTALLER.read_text(encoding="utf-8")
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")
    base_builder = Path("src/devtools/base_runtime_builder.py").read_text(encoding="utf-8")
    base_archive = Path("src/devtools/archive_builder.py").read_text(encoding="utf-8")
    extra_builder = Path("src/devtools/model_export_package.py").read_text(
        encoding="utf-8"
    )

    assert "OutputBaseFilename={#ArtifactPrefix}_Setup_{#MyAppVersion}" in installer
    assert "${ArtifactPrefix}_BaseEnv_${BaseVersion}.7z" in package_script
    assert "-SplitBaseArchive:$SplitBaseArchive" in package_script
    assert "-NoArchive" in package_script
    assert "YOLOTool_ExtraEnv_${ExtensionVersion}.7z" in package_script
    assert "_BaseEnv_{package_version}.7z" in base_builder
    assert "BASE_ARCHIVE_VOLUME_BYTES" in base_builder
    assert 'command.append(f"-v{volume_bytes}b")' in base_archive
    assert "YOLOTool_ExtraEnv_{version}.7z" in extra_builder
    assert Path("installer/base-runtime-models-version.txt").read_text().strip() == "v3"
    assert Path("installer/model-export-runtime-version.txt").read_text().strip() == "v3"
    assert Path("installer/runtime-version.txt").read_text().strip() == "runtime-2"

def test_inno_setup_7_compiler_is_required():
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")

    assert '"Inno Setup 7\\ISCC.exe"' in package_script
    assert 'DisplayName -match "^Inno Setup(?: version)?\\s+7' in package_script
    assert "Inno Setup 7 Command-Line Compiler" in package_script
    assert "Install Inno Setup 7.0.2 or newer." in package_script

def test_cpu_installer_uses_short_cpu_shortcut_name():
    installer = INSTALLER.read_text(encoding="utf-8")
    package_script = Path("installer/package_windows.ps1").read_text(encoding="utf-8")

    assert '#ifndef ShortcutName' in installer
    assert "if '{#ShortcutName}' <> '' then" in installer
    assert '"/DShortcutName=YOLOTool_CPU"' in package_script

def test_base_runtime_uses_parallel_python_source_copy_with_fallback():
    source = Path("src/devtools/release_package.py").read_text(encoding="utf-8")

    assert 'shutil.which("robocopy") if os.name == "nt" else None' in source
    assert '"/MT:16"' in source
    assert '"*.py"' in source
    assert '"/XD"' in source
    assert "for source in sorted(site_packages.rglob(\"*.py\"))" in source

def test_component_page_uses_environment_version_without_archive_hashing():
    source = INSTALLER.read_text(encoding="utf-8")
    prepare = _section(source, "function PrepareToInstall", "procedure CurStepChanged")

    assert "GetSHA256OfFile" not in source
    assert "FileSize64(FileName, ActualSize)" not in source
    assert "IsVersionedArchiveCandidate(BaseArchivePath" in source
    assert "ArchiveExtraction=full" in source
    assert "CompareText(ExtractFileExt(FileName), '.7z') = 0" in source
    assert "ChangeFileExt(FileName, '.003')" in source
    assert "IsVersionedArchiveCandidate(ExtensionArchivePath" in source
    assert "BaseCompressedSize" not in source
    assert "ExtensionCompressedSize" not in source
    assert "VerifyArchiveHash" not in prepare

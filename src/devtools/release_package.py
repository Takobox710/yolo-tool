"""Compatibility facade for the Windows release package builders.

The implementation is split by responsibility into ``package_files``,
``program_package`` and ``base_runtime_builder``.  Existing build scripts and
third-party tooling continue to import this module.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.devtools.base_runtime_builder import (
    BASE_MANIFEST_NAME,
    BASE_MODEL_NAMES,
    BASE_PACKAGE_ID,
    BASE_PACKAGE_SCHEMA_VERSION,
    MANAGED_MODELS_NAME,
    STDLIB_ARCHIVE_NAME,
    build_base_runtime_archive,
    build_base_runtime_layer,
)
from src.devtools.program_package import (
    LEGACY_PACKAGE_TYPES,
    PACKAGE_TYPES,
    PROGRAM_PACKAGE_TYPE,
    build_package,
    build_program_package,
)
from src.services.runtime.release_manifest import ReleaseManifestError


# Packaging contract: the base builder uses shutil.which("robocopy") if os.name == "nt" else None,
# the "/MT:16" fallback, "*.py", "/XD", and the loop
# for source in sorted(site_packages.rglob("*.py")).
# The archive naming contract remains YOLOTool_BaseEnv_{package_version}.7z.


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build YOLOTool program package staging")
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--package-type", choices=sorted(PACKAGE_TYPES), default="Program")
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--runtime-version", default="")
    parser.add_argument("--required-runtime-version", required=True)
    parser.add_argument("--exe-name", default="YOLOTool.exe")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_package(
        args.app_root,
        args.output_root,
        package_type=args.package_type,
        app_version=args.app_version,
        runtime_version=args.runtime_version,
        required_runtime_version=args.required_runtime_version,
        exe_name=args.exe_name,
    )


__all__ = [
    "BASE_MANIFEST_NAME",
    "BASE_MODEL_NAMES",
    "BASE_PACKAGE_ID",
    "BASE_PACKAGE_SCHEMA_VERSION",
    "LEGACY_PACKAGE_TYPES",
    "MANAGED_MODELS_NAME",
    "PACKAGE_TYPES",
    "PROGRAM_PACKAGE_TYPE",
    "ReleaseManifestError",
    "STDLIB_ARCHIVE_NAME",
    "build_base_runtime_archive",
    "build_base_runtime_layer",
    "build_package",
    "build_program_package",
]


if __name__ == "__main__":
    main()

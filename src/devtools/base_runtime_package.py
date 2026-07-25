from __future__ import annotations

import argparse
from pathlib import Path

from src.devtools.release_package import build_base_runtime_archive
from src.devtools.package_cache import cache_matches
from src.devtools.release_package import _base_runtime_fingerprint


def main() -> None:
    parser = argparse.ArgumentParser(description="Build base runtime and models archive")
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--runtime-version", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check-current", action="store_true")
    args = parser.parse_args()
    archive_path = args.output_dir / f"YOLOTool_BaseEnv_{args.version}.7z"
    fingerprint = _base_runtime_fingerprint(
        args.app_root,
        package_version=args.version,
        runtime_version=args.runtime_version,
    )
    if args.check_current:
        print(str(cache_matches(archive_path, fingerprint)).lower())
        return
    print(
        build_base_runtime_archive(
            args.app_root,
            args.staging_root,
            args.output_dir,
            package_version=args.version,
            runtime_version=args.runtime_version,
            force=args.force,
        )
    )


if __name__ == "__main__":
    main()

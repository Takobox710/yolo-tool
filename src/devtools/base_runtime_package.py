from __future__ import annotations

import argparse
from pathlib import Path

from src.devtools.release_package import build_base_runtime_archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Build base runtime and models archive")
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--runtime-version", required=True)
    args = parser.parse_args()
    print(
        build_base_runtime_archive(
            args.app_root,
            args.staging_root,
            args.output_dir,
            package_version=args.version,
            runtime_version=args.runtime_version,
        )
    )


if __name__ == "__main__":
    main()

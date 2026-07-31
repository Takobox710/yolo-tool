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
    parser.add_argument("--variant", default="gpu")
    parser.add_argument(
        "--split",
        action="store_true",
        help="使用固定大小生成基础环境分卷；默认生成单个 .7z 文件。",
    )
    parser.add_argument(
        "--staging-only",
        action="store_true",
        help="只生成基础运行时 staging，不生成压缩包。",
    )
    args = parser.parse_args()
    if args.staging_only and args.split:
        parser.error("--staging-only 不能与 --split 同时使用")
    if args.staging_only:
        from src.devtools.base_runtime_builder import build_base_runtime_layer

        result = build_base_runtime_layer(
            args.app_root,
            args.staging_root,
            package_version=args.version,
            runtime_version=args.runtime_version,
            variant=args.variant,
        )
    else:
        result = build_base_runtime_archive(
            args.app_root,
            args.staging_root,
            args.output_dir,
            package_version=args.version,
            runtime_version=args.runtime_version,
            variant=args.variant,
            split=args.split,
        )
    print(result)


if __name__ == "__main__":
    main()

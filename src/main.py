from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    from multiprocessing import freeze_support
    import sys

    # PyInstaller on Windows re-enters the same executable for multiprocessing
    # workers; freeze_support() must run before normal GUI startup branching.
    freeze_support()

    flag = sys.argv[1] if len(sys.argv) > 1 else None
    if flag in {"--yolo-export", "--yolo-export-probe"}:
        from src.services.model_export.activation import activate_installed_extension

        activate_installed_extension()

    # The installer invokes this immediately after committing the new program
    # and runtime manifests. Its job is to test imports, while the installer
    # itself already validated the package/runtime version pair.
    from src.bootstrap.cli_dispatch import dispatch_cli, run_torch_summary_cli

    if flag == "--runtime-probe":
        raise SystemExit(dispatch_cli(flag, sys.argv[2:]))

    if len(sys.argv) > 1:
        from src.services.runtime import check_runtime_compatibility

        compatibility = check_runtime_compatibility()
        if not compatibility.compatible:
            sys.stderr.write(f"YOLOTool 运行环境不兼容：{compatibility.reason}\n")
            raise SystemExit(78)

    if flag == "--torch-summary":
        raise SystemExit(run_torch_summary_cli(sys.argv[2:]))
    if flag is not None:
        result = dispatch_cli(flag, sys.argv[2:])
        if result is not None:
            raise SystemExit(result)

    from src.app import run_app

    run_app()


if __name__ == "__main__":
    main()

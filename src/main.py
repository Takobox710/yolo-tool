from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    from multiprocessing import freeze_support
    import json
    import sys

    # PyInstaller on Windows re-enters the same executable for multiprocessing
    # workers; freeze_support() must run before normal GUI startup branching.
    freeze_support()

    if len(sys.argv) > 1:
        from src.services.runtime import check_runtime_compatibility

        compatibility = check_runtime_compatibility()
        if not compatibility.compatible:
            sys.stderr.write(f"YOLOTool 运行环境不兼容：{compatibility.reason}\n")
            raise SystemExit(78)

    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-train":
        from src.bootstrap.cli_dispatch import run_train_cli

        raise SystemExit(run_train_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-export":
        from src.bootstrap.cli_dispatch import run_export_cli

        raise SystemExit(run_export_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-val":
        from src.bootstrap.cli_dispatch import run_val_cli

        raise SystemExit(run_val_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-predict":
        from src.bootstrap.cli_dispatch import run_predict_cli

        raise SystemExit(run_predict_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-ai-label":
        from src.bootstrap.cli_dispatch import run_ai_label_cli

        raise SystemExit(run_ai_label_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-ai-runtime":
        from src.bootstrap.cli_dispatch import run_ai_runtime_cli

        raise SystemExit(run_ai_runtime_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-model-labels":
        from src.bootstrap.cli_dispatch import run_model_labels_cli

        raise SystemExit(run_model_labels_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--torch-summary":
        from src.services.runtime import preload_torch_runtime

        sys.stdout.write(
            json.dumps(preload_torch_runtime(), ensure_ascii=False)
        )
        raise SystemExit(0)

    from src.app import run_app

    run_app()


if __name__ == "__main__":
    main()


from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-train":
        from scr.train_cli import run_train_cli

        raise SystemExit(run_train_cli(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "--yolo-export":
        from scr.train_cli import run_export_cli

        raise SystemExit(run_export_cli(sys.argv[2:]))

    from scr.app import run_app

    run_app()


if __name__ == "__main__":
    main()

from src.devtools.window_lifecycle_monitor import (
    EVENT_OBJECT_CREATE,
    EVENT_OBJECT_DESTROY,
    event_name,
    parse_args,
)


def test_window_monitor_parser_accepts_target_filters(tmp_path):
    output = tmp_path / "windows.jsonl"

    args = parse_args(
        [
            "--duration", "2.5", "--pid", "42", "--title", "Release",
            "--process-name", "YOLOTool.exe", "--visible-only", "--jsonl", str(output),
        ]
    )

    assert args.duration == 2.5
    assert args.pid == 42
    assert args.title == "Release"
    assert args.process_name == "YOLOTool.exe"
    assert args.visible_only is True
    assert args.jsonl == output


def test_window_monitor_uses_stable_event_names():
    assert event_name(EVENT_OBJECT_CREATE) == "created"
    assert event_name(EVENT_OBJECT_DESTROY) == "destroyed"
    assert event_name(0xBEEF) == "event_0xBEEF"

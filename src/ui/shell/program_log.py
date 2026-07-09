from __future__ import annotations

from datetime import datetime


def append_program_log(window, message: str, *, level: str = "INFO") -> None:
    text = str(message or "").strip()
    if not text:
        return
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {text}"
    window._program_logs.append(entry)
    settings_page = window.pages.get("settings")
    target = getattr(settings_page, "inner_page", settings_page)
    hook = getattr(target, "append_program_log_entry", None)
    if callable(hook):
        hook(entry)


def program_log_text(window) -> str:
    if not window._program_logs:
        return "等待程序日志..."
    return "\n".join(window._program_logs)


def should_log_background_kind(kind: str) -> bool:
    return kind not in {"env", "env_auto", "home_summary", "train_status"}

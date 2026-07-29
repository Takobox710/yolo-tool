from __future__ import annotations


def clear_active_log(page):
    page.detect_log.clear()
    page.val_log.clear()


def append_active_log(page, text: str):
    if page.is_val_mode():
        page.val_log.append(text)
        return
    page.detect_log.append(text)


def handle_video_progress(page, payload: dict):
    percent = max(0, min(100, int(payload.get("percent") or 0)))
    frame = int(payload.get("frame") or 0)
    total_frames = int(payload.get("total_frames") or 0)
    frames_last_second = int(payload.get("frames_last_second") or 0)
    if total_frames:
        message = (
            f"视频检测进度：{percent}%（{frame}/{total_frames}帧） | "
            f"上一秒：{frames_last_second}帧"
        )
    else:
        message = f"视频检测进度：{percent}% | 上一秒：{frames_last_second}帧"
    page.append_active_log(message)


__all__ = ["append_active_log", "clear_active_log", "handle_video_progress"]

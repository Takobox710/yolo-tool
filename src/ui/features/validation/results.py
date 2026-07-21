from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.services.validation import (
    build_detection_log_message,
    detection_counter_text,
    is_live_source_mode,
    should_store_detection_history,
)
from src.shared.qt import QTableWidgetItem


def _lightweight_payload(payload: dict) -> dict:
    cached = dict(payload)
    cached.pop("source_image", None)
    cached.pop("result_image", None)
    return cached


def _load_display_images(payload: dict) -> tuple[Image.Image, Image.Image]:
    source_image = payload.get("source_image")
    result_image = payload.get("result_image")
    if source_image is None:
        source_path = payload.get("display_source_path") or payload.get("source_path")
        if not source_path:
            raise ValueError("缺少原图路径，无法显示检测结果。")
        with Image.open(source_path) as image:
            source_image = image.convert("RGB")
    if result_image is None:
        result_path = payload.get("result_path")
        if not result_path:
            raise ValueError("缺少结果图路径，无法显示检测结果。")
        with Image.open(result_path) as image:
            result_image = image.convert("RGB")
    return source_image, result_image


def handle_detection_result(page, payload: dict) -> None:
    if payload.get("video_mode"):
        page.show_detection_payload(payload)
        return
    if is_live_source_mode(page.mode_combo.currentText()):
        page.detect_index = 0
        page.show_detection_payload(payload)
        return
    if (
        not should_store_detection_history(page.mode_combo.currentText())
        or not payload.get("result_path")
    ):
        page.show_detection_payload(payload)
        return
    cached_payload = _lightweight_payload(payload)
    page.detect_results.append(cached_payload)
    source_path = payload.get("source_path")
    if source_path:
        page.result_by_source[str(Path(source_path).resolve())] = cached_payload
    if len(page.detect_results) == 1 or (
        not page.is_batch_detection and not page.user_selected_result
    ):
        page.detect_index = len(page.detect_results) - 1
        page.show_detection_payload(payload)
        return
    page.counter.setText(
        detection_counter_text(
            page.mode_combo.currentText(),
            page.detect_index,
            len(page.detect_results),
        )
    )
    page.append_active_log(build_detection_log_message(payload))


def show_detection_payload(page, payload: dict) -> None:
    if payload.get("video_mode"):
        show_video_payload(page, payload)
        return
    source_image, result_image = _load_display_images(payload)
    page.source_view.set_pil_image(source_image)
    page.result_view.set_pil_image(result_image)
    page.table.setRowCount(len(payload["items"]))
    for row, item in enumerate(payload["items"]):
        values = [
            item.label,
            f"{item.confidence:.3f}",
            f"({item.center_x:.1f}, {item.center_y:.1f})",
            f"{item.width:.1f}×{item.height:.1f}",
            f"{item.angle:.1f}",
        ]
        for column, value in enumerate(values):
            page.table.setItem(row, column, QTableWidgetItem(str(value)))
    page.counter.setText(
        detection_counter_text(
            page.mode_combo.currentText(),
            page.detect_index,
            len(page.detect_results),
        )
    )
    if not payload.get("video_mode"):
        page.append_active_log(build_detection_log_message(payload))


def show_source_preview(page, path: Path) -> None:
    if page.is_video_detection_mode():
        page.load_video_source(path)
        return
    page.source_view.clear_image("源图")
    page.result_view.clear_image("检测结果图")
    page.table.setRowCount(0)
    try:
        with Image.open(path) as image:
            source_image = image.convert("RGB")
    except (OSError, ValueError):
        return
    page.source_view.set_pil_image(source_image)
    page.counter.setText("0/0")


def clear_validation_previews(page) -> None:
    page.source_view.clear_image("源图")
    page.result_view.clear_image("检测结果图")
    page.video_playback.stop()
    page.source_video_player.clear()
    page.result_video_player.clear()
    page.video_progress.setValue(0)
    page.current_video_source_path = None
    page.current_video_result_path = None
    page.table.setRowCount(0)


def show_video_payload(page, payload: dict) -> None:
    source_path = payload.get("source_path")
    if source_path and str(Path(source_path).resolve()) != str(page.current_video_source_path):
        return
    result_path = payload.get("result_path")
    if (
        result_path
        and source_path
        and str(Path(source_path).resolve())
        == str(page.current_video_source_path)
    ):
        page.current_video_result_path = Path(result_path).resolve()
    items = payload.get("items") or []
    page.table.setRowCount(len(items))
    for row, item in enumerate(items):
        values = [
            item.label,
            f"{item.confidence:.3f}",
            f"({item.center_x:.1f}, {item.center_y:.1f})",
            f"{item.width:.1f}×{item.height:.1f}",
            f"{item.angle:.1f}",
        ]
        for column, value in enumerate(values):
            page.table.setItem(row, column, QTableWidgetItem(str(value)))
    page.counter.setText("视频播放")


def show_cached_source_result(page, path: Path) -> bool:
    cached = page.result_by_source.get(str(Path(path).resolve()))
    if not cached:
        return False
    page.user_selected_result = True
    page.detect_index = page.detect_results.index(cached)
    page.show_detection_payload(cached)
    return True



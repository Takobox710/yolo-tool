from __future__ import annotations

from pathlib import Path

from PIL import Image

from scr.services.detection_service import (
    build_detection_log_message,
    detection_counter_text,
    is_live_source_mode,
    should_store_detection_history,
)
from scr.ui.qt import QTableWidgetItem


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
    page.append_active_log(build_detection_log_message(payload))


def show_cached_source_result(page, path: Path) -> bool:
    cached = page.result_by_source.get(str(Path(path).resolve()))
    if not cached:
        return False
    page.user_selected_result = True
    page.detect_index = page.detect_results.index(cached)
    page.show_detection_payload(cached)
    return True

from __future__ import annotations

import time
from math import hypot
from pathlib import Path
from typing import Any


class SamHoverSchedulerMixin:

    def request_hover(self, point: tuple[float, float], shape: str) -> None:
        if not self.enabled or self.state not in {"ready", "predicting"}:
            return
        point = (float(point[0]), float(point[1]))
        shape = str(shape)
        if self._last_hover_point is not None and shape == self._last_hover_shape:
            distance = hypot(
                point[0] - self._last_hover_point[0],
                point[1] - self._last_hover_point[1],
            )
            if distance < self._HOVER_MIN_MOVE_PX:
                return
        self.hover_generation += 1
        self._last_hover_point = point
        self._last_hover_shape = shape
        self._hover_payload = {
            "x": point[0],
            "y": point[1],
            "shape": shape,
            "hover_generation": self.hover_generation,
            "model_generation": self.model_generation,
            "image_generation": self.image_generation,
            **self.parameters(),
        }
        self._hover_payload["simplification_ratio"] = self._hover_payload.pop(
            "polygon_simplification_ratio"
        )
        if not self._hover_inflight and not self._hover_timer.isActive():
            self._submit_hover()


    def _hover_interval_ms(self) -> int:
        """Return a bounded interval derived from recent SAM latency."""
        if self._hover_ema_ms is None:
            return self._HOVER_DEFAULT_INTERVAL_MS
        interval = int(round(self._hover_ema_ms * 0.75))
        return max(self._HOVER_MIN_INTERVAL_MS, min(self._HOVER_MAX_INTERVAL_MS, interval))


    def _encode_image(self, image_path: Path) -> None:
        if self._worker is None:
            return
        self._set_state("encoding_image")
        self._worker.set_image(
            {
                "image_path": str(Path(image_path).resolve()),
                "model_generation": self.model_generation,
                "image_generation": self.image_generation,
            }
        )


    def _submit_hover(self) -> None:
        if (
            self._worker is None
            or self._hover_payload is None
            or not self.enabled
            or self._hover_inflight
        ):
            return
        payload = self._hover_payload
        self._hover_payload = None
        self._hover_timer.stop()
        self._hover_inflight = True
        self._hover_started_at = time.monotonic()
        self._last_hover_submit_at = self._hover_started_at
        self._set_state("predicting")
        self._worker.predict_point(payload)


    def set_current_image(self, image_path: Path | None) -> None:
        self.image_generation += 1
        self.hover_generation += 1
        self._minimum_hover_generation = self.hover_generation
        self._hover_timer.stop()
        self._hover_payload = None
        self._image_ready = False
        self._last_hover_point = None
        self._last_hover_shape = ""
        self.page.canvas.clear_sam_preview()
        if not self.enabled:
            return
        if image_path is None:
            self._set_state("waiting_image")
            return
        if self.state not in {"model_ready", "ready", "predicting", "encoding_image"}:
            return
        self._encode_image(image_path)


    def _schedule_latest_hover(self) -> None:
        if not self.enabled or self._hover_payload is None or self._hover_inflight:
            return
        elapsed_ms = (time.monotonic() - self._last_hover_submit_at) * 1000.0
        delay_ms = max(0.0, self._hover_interval_ms() - elapsed_ms)
        if delay_ms <= 0:
            self._submit_hover()
        else:
            self._hover_timer.start(max(1, int(delay_ms + 0.5)))


    def cancel_hover(self) -> None:
        self.hover_generation += 1
        self._minimum_hover_generation = self.hover_generation
        self._hover_timer.stop()
        self._hover_payload = None
        self._last_hover_point = None
        self._last_hover_shape = ""
        if self.enabled and self.state == "predicting":
            self._set_state("ready")


    def _finish_hover_request(self, *, keep_predicting: bool = False) -> None:
        if self._hover_inflight:
            elapsed_ms = max(0.0, (time.monotonic() - self._hover_started_at) * 1000.0)
            if self._hover_ema_ms is None:
                self._hover_ema_ms = elapsed_ms
            else:
                alpha = self._HOVER_EMA_ALPHA
                self._hover_ema_ms = (alpha * elapsed_ms) + ((1.0 - alpha) * self._hover_ema_ms)
            self._hover_inflight = False
            self._hover_started_at = 0.0
        if self._hover_payload is not None:
            self._schedule_latest_hover()
        elif self.enabled and self.state == "predicting" and not keep_predicting:
            self._set_state("ready")


__all__ = ['SamHoverSchedulerMixin']

from __future__ import annotations

import os  # noqa: F401
from pathlib import Path
from queue import Queue

# Keep these imports available as module-level compatibility seams for older
# tests and integrations that patch the historical tab module.
from src.services.model_export import (  # noqa: F401
    ModelExportConfig,
    build_model_export_command,
    capabilities_for,
    cleanup_stale_export_workdirs,
    download_generic_calibration_pack,
    export_artifact_path,
    export_capability,
    export_display_names,
    export_model_display_path,
    find_export_model_paths,
    generic_calibration_pack_path,
    model_kind_from_path,
    normalize_model_export_config,
    resolve_export_format,
    validate_model_export_config,
    validate_model_export_source,
)
from src.shared.qt import QFileDialog, QMessageBox, QTimer  # noqa: F401
from src.shared.paths import ROOT  # noqa: F401
from src.services.runtime import spawn_structured_process, stop_process  # noqa: F401
from src.ui.features.data.model_export.compat import ModelExportCompatibilityMixin
from src.ui.features.data.model_export.layout import (
    build_model_export_layout,
    update_model_export_card_ratio,
)
from src.ui.features.data.model_export.state import ModelExportStateMixin
from src.ui.features.data.model_export.visibility import ModelExportVisibilityMixin
from src.ui.shared.model_export_package import ModelExportPackageDropMixin
from src.ui.shared.page_base import BasePage
from src.ui.shared.workers import Worker  # noqa: F401


class ModelExportTab(
    ModelExportPackageDropMixin,
    ModelExportVisibilityMixin,
    ModelExportCompatibilityMixin,
    ModelExportStateMixin,
    BasePage,
):
    def __init__(self, context):
        super().__init__(context)
        self.is_exporting = False
        self.stop_requested = False
        self._format_option_cache: dict[str, dict] = {}
        self._format_switching = False
        self._active_format_argument = resolve_export_format(
            self.context.settings.model_export.format
        ).argument
        self.log_queue: Queue | None = None
        self.result_path: Path | None = None
        self._export_process = None
        self._export_lease = None
        self._calibration_worker: Worker | None = None
        self._model_display_paths: dict[str, Path] = {}
        self.setup_model_export_package_drop()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_export_queue)

        build_model_export_layout(self)

        self.refresh_model_choices()
        self._connect_persistence()
        self.format_combo.currentTextChanged.connect(self.update_environment_status)
        self.model_combo.currentTextChanged.connect(self.update_option_visibility)
        self.update_environment_status()
        self.update_option_visibility()
        self.finalize_model_export_package_drop()
        QTimer.singleShot(0, self, self._reflow_layout)

    def _reflow_layout(self):
        if getattr(self, "_reflowing_layout", False):
            return
        self._reflowing_layout = True
        try:
            for widget in (self, self.onnx_top_box, self.source_card, self.inference_card):
                widget.updateGeometry()
                layout = widget.layout
                if callable(layout):
                    layout = layout()
                if layout is not None:
                    layout.invalidate()
            self.layout().activate()
            update_model_export_card_ratio(self)
            self.layout().activate()
        finally:
            self._reflowing_layout = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_layout()

    def _runtime_capability_for(
        self, export_format: str, model_kind: str, precision: str
    ):
        """Preserve the historical tab-module monkeypatch seam."""
        try:
            return export_capability(
                export_format,
                model_kind=model_kind,
                precision=precision,
            )
        except TypeError:
            return export_capability(export_format)


__all__ = ["ModelExportTab"]

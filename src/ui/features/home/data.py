from __future__ import annotations

import os
from pathlib import Path

from src.services.home import build_home_summary, collect_home_history_entries
from src.ui.helpers import (
    _history_model_sort_key,
    _history_number_sort_key,
    _history_time_sort_key,
    _home_column_widths,
    _relative_path,
)
from src.ui.shared.page_base import _SortItem
from src.shared.qt import QFileDialog, QTimer, Qt


class HomePageDataMixin:
    def _has_overview_stat_value(self, key: str) -> bool:
        value = getattr(self, "_overview_raw_values", {}).get(key)
        return bool(value and str(value).strip() and str(value) != "-")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_home_column_widths()
        self._apply_history_column_widths()

    def _apply_history_column_widths(self):
        if not hasattr(self, "history_table"):
            return
        available = max(1, self.history_table.viewport().width() - 2)
        weights = [170, 82, 128, 88, 112, 98, 88]
        total = sum(weights)
        widths = [available * weight // total for weight in weights]
        widths[-1] += available - sum(widths)
        header = self.history_table.horizontalHeader()
        for column, width in enumerate(widths):
            header.resizeSection(column, max(1, width))

    def _apply_home_column_widths(self):
        margins = self.layout().contentsMargins()
        total_margins = margins.left() + margins.right()
        left_width, right_width = _home_column_widths(
            self.width(), total_margins, self._home_grid_spacing
        )
        for card in self._home_left_cards:
            card.setFixedWidth(left_width)
        for card in self._home_right_cards:
            card.setFixedWidth(right_width)
        self._refresh_overview_elides()
        self._apply_history_column_widths()

    def _elide_overview_text(self, text: str, label) -> str:
        available_width = max(label.width(), 24)
        return label.fontMetrics().elidedText(
            str(text), Qt.TextElideMode.ElideMiddle, available_width
        )

    def _refresh_overview_elides(self):
        for key, text in getattr(self, "_overview_raw_values", {}).items():
            self.overview_stats[key].setText(
                self._elide_overview_text(text, self.overview_stats[key])
            )

    def _set_overview_stat(
        self, key: str, text: str, *, tooltip: str | None = None
    ) -> None:
        self._overview_raw_values[key] = text
        self.overview_stats[key].setText(
            self._elide_overview_text(text, self.overview_stats[key])
        )
        self.overview_stats[key].setToolTip(text if tooltip is None else tooltip)

    def on_show(self):
        paths = self.app.settings["paths"]
        project_root = self.app.settings["project"]["root"]
        self._set_overview_stat("project", project_root)
        self._set_overview_stat(
            "images", _relative_path(paths["images_dir"], project_root)
        )
        self._set_overview_stat(
            "annotations", _relative_path(paths["annotations_dir"], project_root)
        )
        self._set_overview_stat(
            "result", _relative_path(paths["result_dir"], project_root)
        )
        if not self._has_overview_stat_value("image_count"):
            self._set_overview_stat("image_count", "加载中...")
        if not self._has_overview_stat_value("label_count"):
            self._set_overview_stat("label_count", "加载中...")
        self._home_summary_request_id += 1
        request_id = self._home_summary_request_id
        payload_loader = lambda request_id=request_id: self._load_home_summary_payload(  # noqa: E731
            request_id
        )
        run_background = getattr(self.app, "run_background", None)
        if callable(run_background):
            run_background("home_summary", payload_loader)
            return
        self.apply_home_summary(payload_loader())

    def _load_home_summary_payload(self, request_id: int) -> dict:
        paths = self.app.settings["paths"]
        return {
            "request_id": request_id,
            "summary": build_home_summary(
                images_dir=Path(paths["images_dir"]),
                annotations_dir=Path(paths["annotations_dir"]),
                labels_dir=Path(paths["labels_dir"]),
                dataset_dir=Path(paths["dataset_dir"]),
                result_dir=Path(paths["result_dir"]),
                configured_class_names=self.app.settings.get("dataset", {}).get(
                    "class_names", []
                ),
            ),
        }

    def apply_home_summary(self, payload: dict) -> None:
        if payload.get("request_id") != self._home_summary_request_id:
            return
        summary = payload.get("summary") or {}
        self._set_overview_stat("image_count", str(summary.get("image_count", 0)))
        self._set_overview_stat("label_count", str(summary.get("label_count", 0)))
        single_counts = summary.get("single_counts") or {}
        multi_counts = summary.get("multi_counts") or {}
        class_names = summary.get("class_names") or []
        standard_counts = summary.get("standard_counts") or {}
        multi_class_mode = self.app.settings.get("features", {}).get(
            "distribution_multi_class_mode", False
        )
        self.distribution_title.setText(
            "多类别标注分布" if multi_class_mode else "各类别图片分布"
        )
        if multi_class_mode:
            self.distribution_view.set_multi_class_counts(multi_counts)
        else:
            default_class = (
                class_names[0]
                if len(class_names) == 1
                else ""
            )
            if not class_names:
                default_class = "目标名称"
            self.distribution_view.set_standard_counts(
                standard_counts.get("total_images", 0),
                standard_counts.get("split_counts", single_counts),
                standard_counts.get("unannotated_images", 0),
                default_class,
            )
        self.curve_view.set_curve_data(summary.get("curve_data") or {})
        self._apply_history_entries(summary.get("history_entries") or [])

    def refresh_history(self):
        self._apply_history_entries(
            collect_home_history_entries(
                Path(self.app.settings["paths"]["result_dir"])
            )
        )

    def _apply_history_entries(self, entries: list[dict]) -> None:
        was_sorting = self.history_table.isSortingEnabled()
        self.history_table.setSortingEnabled(False)
        self.history_table.clearContents()
        self.history_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            train_id = str(entry.get("train_id") or "")
            model_name = str(entry.get("model_name") or "")
            metrics = entry.get("metrics") or {}
            model_id = f"{train_id}（{model_name.replace('.pt', '')}）"
            values = [
                model_id,
                str(metrics.get("epochs", "")),
                str(metrics.get("train_time", "")),
                str(metrics.get("map50", "")),
                str(metrics.get("map50_95", "")),
                str(metrics.get("box_loss", "")),
                str(metrics.get("recall", "")),
            ]
            for column, value in enumerate(values):
                sort_key = float(row)
                if column == 0:
                    sort_key = _history_model_sort_key(train_id, model_name)
                elif column == 1:
                    sort_key = _history_number_sort_key(value)
                elif column == 2:
                    sort_key = _history_time_sort_key(value)
                elif column in (3, 4, 5, 6):
                    sort_key = _history_number_sort_key(value)
                item = _SortItem(value, sort_key)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.history_table.setItem(row, column, item)
        self.history_table.setSortingEnabled(was_sorting)
        self.history_table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self._apply_history_column_widths()
        QTimer.singleShot(50, self, self._apply_history_column_widths)

    def pick_project_root(self):
        path = QFileDialog.getExistingDirectory(
            self, "设置项目目录", self.app.settings["project"]["root"]
        )
        if path:
            self.app.switch_project_root(path)

    def open_result_dir(self):
        path = Path(self.app.settings["paths"]["result_dir"])
        if path.exists():
            os.startfile(path)

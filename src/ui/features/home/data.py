from __future__ import annotations

import json
import os
from pathlib import Path

from src.services.training import read_results_csv_for_curves, read_train_metrics
from src.services.validation import scan_candidate_models
from src.ui.helpers import (
    _history_model_sort_key,
    _history_number_sort_key,
    _history_time_sort_key,
    _home_column_widths,
    _relative_path,
)
from src.ui.shared.page_base import _IMAGE_SUFFIXES, _SortItem
from src.shared.qt import QFileDialog, QTimer, Qt


class HomePageDataMixin:
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

    def on_show(self):
        paths = self.app.settings["paths"]
        project_root = self.app.settings["project"]["root"]
        images = Path(paths["images_dir"])
        image_count = (
            len([p for p in images.glob("*") if p.suffix.lower() in _IMAGE_SUFFIXES])
            if images.exists()
            else 0
        )
        label_count = self._count_annotation_files(
            Path(paths["annotations_dir"]), Path(paths["labels_dir"])
        )

        def set_overview_stat(key: str, text: str):
            self._overview_raw_values[key] = text
            self.overview_stats[key].setText(
                self._elide_overview_text(text, self.overview_stats[key])
            )
            self.overview_stats[key].setToolTip(text)

        set_overview_stat("project", project_root)
        set_overview_stat("images", _relative_path(paths["images_dir"], project_root))
        set_overview_stat("annotations", _relative_path(paths["annotations_dir"], project_root))
        set_overview_stat("result", _relative_path(paths["result_dir"], project_root))
        set_overview_stat("image_count", str(image_count))
        set_overview_stat("label_count", str(label_count))

        single_counts, multi_counts, class_names = self._build_distribution_data(
            Path(paths["dataset_dir"])
        )
        if self.app.settings.get("features", {}).get("distribution_multi_class_mode", False) and len(multi_counts) > 1:
            self.distribution_view.set_multi_class_counts(multi_counts)
        else:
            default_class = class_names[0] if class_names else "数据集"
            self.distribution_view.set_single_class_counts(single_counts, default_class)
        self.curve_view.set_curve_data(read_results_csv_for_curves(Path(paths["result_dir"])))
        self.refresh_history()

    def _build_distribution_data(
        self, dataset_dir: Path
    ) -> tuple[dict[str, int], dict[str, int], list[str]]:
        class_names = self._resolve_dataset_class_names(dataset_dir)
        split_class_counts: dict[str, dict[str, int]] = {
            split: {name: 0 for name in class_names} for split in ("train", "val", "test")
        }
        for split in ("train", "val", "test"):
            label_dir = dataset_dir / split / "labels"
            if not label_dir.exists():
                continue
            for label_path in sorted(label_dir.glob("*.txt")):
                present_ids = self._read_label_class_ids(label_path)
                for class_id in present_ids:
                    if 0 <= class_id < len(class_names):
                        split_class_counts[split][class_names[class_id]] += 1
        default_class = class_names[0] if class_names else "数据集"
        single_counts = {
            split: split_class_counts[split].get(default_class, 0)
            for split in ("train", "val", "test")
        }
        multi_counts = {
            name: sum(split_class_counts[split].get(name, 0) for split in ("train", "val", "test"))
            for name in class_names
        }
        return single_counts, multi_counts, class_names

    def _resolve_dataset_class_names(self, dataset_dir: Path) -> list[str]:
        yaml_path = dataset_dir / "data.yaml"
        if yaml_path.exists():
            text = yaml_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.strip().startswith("names:"):
                    _, raw_names = line.split(":", 1)
                    raw_names = raw_names.strip()
                    try:
                        parsed = json.loads(raw_names.replace("'", '"'))
                    except json.JSONDecodeError:
                        parsed = []
                    names = [str(name).strip() for name in parsed if str(name).strip()]
                    if names:
                        return names
        names = [
            str(name).strip()
            for name in self.app.settings.get("dataset", {}).get("class_names", [])
            if str(name).strip()
        ]
        return names or ["weld"]

    @staticmethod
    def _read_label_class_ids(label_path: Path) -> set[int]:
        present_ids: set[int] = set()
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                present_ids.add(int(float(parts[0])))
            except ValueError:
                continue
        return present_ids

    def _count_annotation_files(self, annotations_dir: Path, labels_dir: Path) -> int:
        json_count = self._count_labelme_annotation_files(annotations_dir)
        if json_count:
            return json_count
        return self._count_yolo_annotation_files(labels_dir)

    @staticmethod
    def _count_labelme_annotation_files(annotations_dir: Path) -> int:
        if not annotations_dir.exists():
            return 0
        total = 0
        for label_path in annotations_dir.glob("*.json"):
            try:
                payload = json.loads(label_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if payload.get("shapes"):
                total += 1
        return total

    @staticmethod
    def _count_yolo_annotation_files(labels_dir: Path) -> int:
        if not labels_dir.exists():
            return 0
        total = 0
        for label_path in labels_dir.glob("*.txt"):
            try:
                has_label = any(line.strip() for line in label_path.read_text(encoding="utf-8").splitlines())
            except OSError:
                continue
            if has_label:
                total += 1
        return total

    def refresh_history(self):
        result_dir = Path(self.app.settings["paths"]["result_dir"])
        candidates = scan_candidate_models(result_dir)
        was_sorting = self.history_table.isSortingEnabled()
        self.history_table.setSortingEnabled(False)
        self.history_table.clearContents()
        self.history_table.setRowCount(len(candidates[:8]))
        for row, candidate in enumerate(candidates[:8]):
            run_dir = candidate.parent.parent
            train_id = run_dir.name
            model_name = candidate.name
            metrics = read_train_metrics(run_dir, model_name)
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
        QTimer.singleShot(50, self._apply_history_column_widths)

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

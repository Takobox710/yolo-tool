from __future__ import annotations

import os
from pathlib import Path

from scr.services.detection_service import scan_candidate_models
from scr.services.training_service import read_results_csv_for_curves, read_train_metrics
from scr.ui.helpers import _history_model_sort_key, _home_column_widths, _history_time_sort_key, _relative_path
from scr.ui.page_base import BasePage, Card, _IMAGE_SUFFIXES, _SortItem, _history_number_sort_key
from scr.ui.qt import Qt, QFileDialog, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTableWidget, QTimer, QVBoxLayout
from scr.ui.widgets.charts import DatasetDistributionWidget, TrainingCurveWidget

class HomePage(BasePage):
    def __init__(self, app):
        super().__init__(app)
        self.setMinimumHeight(700)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = self.page_layout()
        self._home_grid_spacing = 12
        # Hero
        hero = QHBoxLayout()
        copy = QVBoxLayout()
        title = QLabel("欢迎使用 YOLO 本地训练工作台")
        title.setObjectName("pageTitle")
        copy.addWidget(title)
        hero.addLayout(copy, 1)
        for text in ["pixi env: local", "Python 3.12", "CUDA 13.0"]:
            pill = QLabel(text)
            pill.setObjectName("envPill")
            hero.addWidget(pill)
        layout.addLayout(hero)

        # Task 5: 2-row grid with column stretch 1:2 and row stretch 58:42
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setRowStretch(0, 58)
        grid.setRowStretch(1, 42)
        grid.setSpacing(self._home_grid_spacing)
        layout.addLayout(grid, 1)

        # --- Task 2: Project overview - title and button on same line ---
        overview = Card()
        header_row = QHBoxLayout()
        ov_title = QLabel("项目概览")
        ov_title.setObjectName("sectionTitle")
        header_row.addWidget(ov_title)
        header_row.addStretch(1)
        pick = QPushButton("设置项目目录")
        pick.setObjectName("compactSoftButton")
        pick.setFixedWidth(108)
        pick.setFixedHeight(30)
        pick.clicked.connect(self.pick_project_root)
        header_row.addWidget(pick)
        overview.layout.addLayout(header_row)
        self.overview_stats = {}
        for key, label in [
            ("project", "项目文件夹"),
            ("images", "图片路径"),
            ("annotations", "标注路径"),
            ("result", "结果路径"),
            ("image_count", "图片数量"),
            ("label_count", "标签文件"),
        ]:
            card, value = self.stat_card(label)
            overview.layout.addWidget(card)
            self.overview_stats[key] = value
        grid.addWidget(overview, 0, 0)

        # --- Task 6: Distribution with train/val/test ---
        distribution = Card("各类别图片分布")
        self.distribution_view = DatasetDistributionWidget()
        distribution.layout.addWidget(self.distribution_view, 1)
        grid.addWidget(distribution, 0, 1)

        # --- Task 7: Training curves ---
        curve = Card()
        self.curve_view = TrainingCurveWidget()
        curve.layout.addWidget(self.curve_view, 1)
        grid.addWidget(curve, 1, 0)

        # --- Task 4: Training history - button same line as title, no sort triangles ---
        history = Card()
        hist_header = QHBoxLayout()
        hist_title = QLabel("训练历史")
        hist_title.setObjectName("sectionTitle")
        hist_header.addWidget(hist_title)
        hist_header.addStretch(1)
        open_button = QPushButton("打开结果目录")
        open_button.setObjectName("compactSoftButton")
        open_button.setFixedWidth(100)
        open_button.setFixedHeight(30)
        open_button.clicked.connect(self.open_result_dir)
        hist_header.addWidget(open_button)
        history.layout.addLayout(hist_header)
        history.layout.addSpacing(3)
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels(
            ["模型ID", "Epochs", "Time", "mAP50", "mAP50-95", "Box Loss", "Recall"]
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.history_table.setSortingEnabled(True)
        self.history_table.horizontalHeader().setSortIndicatorShown(False)
        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        history.layout.addWidget(self.history_table, 1)
        grid.addWidget(history, 1, 1)
        self._home_left_cards = [overview, curve]
        self._home_right_cards = [distribution, history]
        self._overview_raw_values = {}
        self._apply_home_column_widths()
        QTimer.singleShot(0, self._apply_history_column_widths)
        QTimer.singleShot(50, self._apply_history_column_widths)

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

    def _elide_overview_text(self, text: str, label: QLabel) -> str:
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
        labels = Path(paths["labels_dir"])
        image_count = (
            len([p for p in images.glob("*") if p.suffix.lower() in _IMAGE_SUFFIXES])
            if images.exists()
            else 0
        )
        label_count = len(list(labels.glob("*.txt"))) if labels.exists() else 0

        # Task 3: relative paths (except project folder)
        def set_overview_stat(key: str, text: str):
            self._overview_raw_values[key] = text
            self.overview_stats[key].setText(
                self._elide_overview_text(text, self.overview_stats[key])
            )
            self.overview_stats[key].setToolTip(text)

        set_overview_stat("project", project_root)
        set_overview_stat(
            "images", _relative_path(paths["images_dir"], project_root)
        )
        set_overview_stat(
            "annotations", _relative_path(paths["annotations_dir"], project_root)
        )
        set_overview_stat(
            "result", _relative_path(paths["result_dir"], project_root)
        )
        set_overview_stat("image_count", str(image_count))
        set_overview_stat("label_count", str(label_count))

        dataset_dir = Path(paths["dataset_dir"])
        split_counts = {}
        for split in ("train", "val", "test"):
            img_dir = dataset_dir / split / "images"
            split_counts[split] = (
                len(
                    [
                        p
                        for p in img_dir.glob("*")
                        if p.suffix.lower() in _IMAGE_SUFFIXES
                    ]
                )
                if img_dir.exists()
                else 0
            )
        self.distribution_view.set_counts(
            split_counts, self.app.settings["dataset"]["class_names"]
        )
        self.curve_view.set_curve_data(
            read_results_csv_for_curves(Path(paths["result_dir"]))
        )
        self.refresh_history()

    def refresh_history(self):
        paths = self.app.settings["paths"]
        result_dir = Path(paths["result_dir"])
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
            self.app.settings["project"]["root"] = path
            self.app.settings_service.save(self.app.settings)
            self.on_show()

    def open_result_dir(self):
        path = Path(self.app.settings["paths"]["result_dir"])
        if path.exists():
            os.startfile(path)

# ===================================================================
#  Data page
# ===================================================================

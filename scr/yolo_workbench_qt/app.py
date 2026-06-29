from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from pathlib import Path
from queue import Queue

from PIL import Image

from scr.yolo_workbench.services.annotation_service import load_yolo_annotations, render_annotation_preview
from scr.yolo_workbench.services.conversion_service import ConversionConfig, preview_conversion, run_conversion
from scr.yolo_workbench.services.detection_service import run_prediction, scan_candidate_models
from scr.yolo_workbench.services.environment_service import detect_modules, pixi_available, system_status, torch_cuda_summary
from scr.yolo_workbench.services.rename_service import execute_rename, preview_rename
from scr.yolo_workbench.services.resize_service import ResizeConfig, preview_resize, run_resize
from scr.yolo_workbench.services.runtime_service import spawn_logged_process, stop_process
from scr.yolo_workbench.services.settings_service import ROOT, SettingsService
from scr.yolo_workbench.services.training_service import (
    build_train_command,
    infer_task_mode_from_model,
    read_train_metrics,
    read_results_csv_for_curves,
)

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}

# --- Task 3: path helpers ---
def _relative_path(path_str: str, project_root: str | Path = ROOT) -> str:
    """Return a display-friendly relative path from the project root."""
    if not path_str:
        return ""
    try:
        p = Path(path_str)
        return str(p.relative_to(Path(project_root)))
    except ValueError:
        return str(path_str)


def _simplified_model_path(path_str: str) -> str:
    """Simplify result\\train-12\\weights\\best.pt -> train-12\\best.pt"""
    rel = _relative_path(path_str)
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0].lower() == "result" and parts[-2].lower() == "weights":
        return str(Path(*parts[1:-2] + (parts[-1],)))
    return rel


def _find_models_in_dir(result_dir: Path) -> list[str]:
    """Scan for .pt models in result dir, return simplified display names."""
    models = scan_candidate_models(result_dir)
    return [_simplified_model_path(str(m)) for m in models]


def _find_models_full_paths(result_dir: Path) -> list[Path]:
    return scan_candidate_models(result_dir)


def _find_model_yaml_files(data_dir: Path) -> list[str]:
    """Find .yaml files in data/ for model YAML selection."""
    if not data_dir.exists():
        return []
    return [str(f) for f in sorted(data_dir.glob("*.yaml")) if f.is_file()]


def _find_pt_files_in_data_models(project_root: Path) -> list[str]:
    """Find .pt files in data/models/ directory for pretrained model selection."""
    models_dir = project_root / "data" / "models"
    if not models_dir.exists():
        return []
    return [f.name for f in sorted(models_dir.glob("*.pt")) if f.is_file()]


# ---------------------------------------------------------------------------
def run_app() -> None:
    try:
        from PySide6.QtCore import Qt, QThread, QTimer, Signal
        from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap, QIcon, QPainterPath
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QDialogButtonBox,
            QFileDialog,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QProgressBar,
            QScrollArea,
            QSizePolicy,
            QStackedWidget,
            QTableWidget,
            QTableWidgetItem,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError as exc:
        raise SystemExit(f"缺少 Qt 依赖：{exc.name}。请先执行 pixi install 后运行 pixi run app。") from exc

    IMAGE_SUFFIXES = _IMAGE_SUFFIXES

    def pil_to_pixmap(image: Image.Image) -> QPixmap:
        rgba = image.convert("RGBA")
        data = rgba.tobytes("raw", "RGBA")
        qimage = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage.copy())

    # --- Task 1: helper to load nav icon ---
    def _load_nav_icon() -> QPixmap | None:
        icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path))
            if not pix.isNull():
                return pix.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return None

    class Worker(QThread):
        finished_with_payload = Signal(str, object)

        def __init__(self, kind: str, fn):
            super().__init__()
            self.kind = kind
            self.fn = fn

        def run(self):
            try:
                payload = self.fn()
            except Exception:
                payload = {"error": traceback.format_exc()}
            self.finished_with_payload.emit(self.kind, payload)

    class DetectionWorker(QThread):
        result_payload = Signal(object)
        finished_with_results = Signal(object)
        failed = Signal(str)

        def __init__(self, config: dict, stop_event: threading.Event):
            super().__init__()
            self.config = config
            self.stop_event = stop_event
            self.results = []

        def run(self):
            try:
                def forward(payload):
                    self.results.append(payload)
                    self.result_payload.emit(payload)

                run_prediction(self.config, self.stop_event, forward)
                self.finished_with_results.emit(self.results)
            except Exception:
                self.failed.emit(traceback.format_exc())

    class Card(QFrame):
        def __init__(self, title: str = ""):
            super().__init__()
            self.setObjectName("card")
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(16, 14, 16, 16)
            self.layout.setSpacing(10)
            if title:
                label = QLabel(title)
                label.setObjectName("sectionTitle")
                self.layout.addWidget(label)

    class CardNoPad(QFrame):
        """Card with minimal padding for compact grid items."""
        def __init__(self):
            super().__init__()
            self.setObjectName("card")
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(12, 10, 12, 10)
            self.layout.setSpacing(6)

    class ImageView(QLabel):
        def __init__(self, text: str):
            super().__init__(text)
            self.setObjectName("imageView")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setMinimumHeight(260)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._pixmap: QPixmap | None = None

        def set_pil_image(self, image: Image.Image):
            self._pixmap = pil_to_pixmap(image)
            self._rescale()

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self._rescale()

        def _rescale(self):
            if self._pixmap is None or self.width() <= 0 or self.height() <= 0:
                return
            scaled = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(scaled)

    class _SortItem(QTableWidgetItem):
        def __init__(self, text: str, sort_key: float = 0.0):
            super().__init__(text)
            self.setData(Qt.ItemDataRole.UserRole, sort_key)

        def __lt__(self, other):
            if isinstance(other, QTableWidgetItem):
                a = self.data(Qt.ItemDataRole.UserRole)
                b = other.data(Qt.ItemDataRole.UserRole)
                if a is not None and b is not None:
                    try:
                        return float(a) < float(b)
                    except (ValueError, TypeError):
                        pass
            return super().__lt__(other)

    # --- Task 10: Custom command dialog ---
    class CommandDialog(QDialog):
        def __init__(self, command: list[str], parent=None):
            super().__init__(parent)
            self.setWindowTitle("确认训练命令")
            self.setMinimumWidth(600)
            self.setMinimumHeight(200)
            layout = QVBoxLayout(self)
            hint = QLabel("以下为本次训练将执行的命令，可直接修改：")
            hint.setObjectName("fieldLabel")
            layout.addWidget(hint)
            self.command_edit = QTextEdit()
            self.command_edit.setPlainText(" ".join(command))
            self.command_edit.setFont(QFont("Consolas", 11))
            layout.addWidget(self.command_edit, 1)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

        def get_command(self) -> list[str]:
            return self.command_edit.toPlainText().strip().split()

    class WorkbenchWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.settings_service = SettingsService()
            self.settings = self.settings_service.load()
            # Ensure new fields exist
            self.settings.setdefault("features", {}).setdefault("custom_command_dialog", True)
            self.settings.setdefault("training", {}).setdefault("optimizer", "auto")
            self.workers: list[Worker] = []
            self.pages: dict[str, QWidget] = {}
            self.training_handle = None
            self.export_handle = None
            self.page_order = ["home", "data", "train", "validate", "settings"]
            self.page_titles = {
                "home": "主页",
                "data": "数据处理",
                "train": "模型训练",
                "validate": "模型验证",
                "settings": "系统设置",
            }
            # Task 1: set window icon
            icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
            if icon_path.exists():
                app_icon = QIcon(str(icon_path))
                self.setWindowIcon(app_icon)
            self.setWindowTitle("YOLO 本地训练工作台")
            self.resize(1100, 780)
            self.setMinimumSize(1100, 780)
            self._build()

        def _build(self):
            root = QWidget()
            root_layout = QVBoxLayout(root)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(0)

            nav = QFrame()
            nav.setObjectName("nav")
            nav_layout = QHBoxLayout(nav)
            nav_layout.setContentsMargins(22, 14, 22, 14)
            nav_layout.setSpacing(10)
            # Task 1: icon in nav
            nav_pix = _load_nav_icon()
            if nav_pix is not None:
                icon_label = QLabel()
                icon_label.setPixmap(nav_pix)
                nav_layout.addWidget(icon_label)
            brand = QLabel("YOLO 本地训练工作台")
            brand.setObjectName("brand")
            nav_layout.addWidget(brand)
            nav_layout.addStretch(1)
            self.nav_buttons = {}
            for key in self.page_order:
                button = QPushButton(self.page_titles[key])
                button.setObjectName("navButton")
                button.setCheckable(True)
                button.clicked.connect(lambda _checked=False, page=key: self.show_page(page))
                nav_layout.addWidget(button)
                self.nav_buttons[key] = button
            root_layout.addWidget(nav)

            self.stack = QStackedWidget()
            self.stack.setObjectName("stack")
            root_layout.addWidget(self.stack, 1)

            self.status = QLabel("就绪")
            self.status.setObjectName("status")
            self.status.setContentsMargins(14, 5, 14, 5)
            root_layout.addWidget(self.status)
            self.setCentralWidget(root)
            self.setStyleSheet(STYLE)
            self.show_page(self.settings["ui"].get("last_page", "home"))

        def show_page(self, key: str):
            if key not in self.page_titles:
                key = "home"
            if key not in self.pages:
                page = self.create_page(key)
                self.pages[key] = page
                self.stack.addWidget(page)
            self.stack.setCurrentWidget(self.pages[key])
            for name, button in self.nav_buttons.items():
                button.setChecked(name == key)
            self.settings["ui"]["last_page"] = key
            self.status.setText(f"当前页面：{self.page_titles[key]}")
            active_page = getattr(self.pages[key], "inner_page", self.pages[key])
            hook = getattr(active_page, "on_show", None)
            if hook:
                hook()

        def create_page(self, key: str):
            if key == "home":
                return HomePage(self)
            if key == "data":
                return scroll_page(DataPage(self))
            if key == "train":
                return scroll_page(TrainPage(self))
            if key == "validate":
                return scroll_page(ValidatePage(self))
            return scroll_page(SettingsPage(self))

        def run_background(self, kind: str, fn):
            worker = Worker(kind, fn)
            self.workers.append(worker)
            worker.finished_with_payload.connect(self.handle_background)
            worker.finished.connect(lambda w=worker: self.workers.remove(w) if w in self.workers else None)
            worker.start()

        def handle_background(self, kind: str, payload):
            if isinstance(payload, dict) and payload.get("error"):
                self.status.setText("后台任务异常")
                QMessageBox.warning(self, "后台任务异常", payload["error"])
                return
            current = self.stack.currentWidget()
            current = getattr(current, "inner_page", current)
            handler = getattr(current, f"apply_{kind}", None)
            if handler:
                handler(payload)

        def closeEvent(self, event):
            self.settings["ui"]["window_width"] = 1100
            self.settings["ui"]["window_height"] = 780
            self.settings_service.save(self.settings)
            stop_process(self.training_handle)
            stop_process(self.export_handle)
            super().closeEvent(event)

    class BasePage(QWidget):
        def __init__(self, app: WorkbenchWindow):
            super().__init__()
            self.app = app

        def page_layout(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(14)
            return layout

        def field(self, label: str, value: str = "", browse=None):
            box = QWidget()
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("fieldLabel")
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(str(value))
            row.addWidget(edit, 1)
            if browse:
                button = QPushButton("选择")
                button.setObjectName("softButton")
                button.clicked.connect(lambda: browse(edit))
                row.addWidget(button)
            layout.addWidget(caption)
            layout.addLayout(row)
            return box, edit

        def combo_field(self, label: str, value: str, values: list[str]):
            box = QWidget()
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("fieldLabel")
            combo = QComboBox()
            combo.addItems(values)
            if value in values:
                combo.setCurrentText(value)
            layout.addWidget(caption)
            layout.addWidget(combo)
            return box, combo

        def inline_field(self, label: str, value: str = "", browse=None):
            box = QWidget()
            layout = QHBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("inlineFieldLabel")
            caption.setFixedWidth(88)
            edit = QLineEdit(str(value))
            layout.addWidget(caption)
            layout.addWidget(edit, 1)
            if browse:
                button = QPushButton("选择")
                button.setObjectName("softButton")
                button.clicked.connect(lambda: browse(edit))
                layout.addWidget(button)
            return box, edit

        def inline_combo_field(self, label: str, value: str, values: list[str]):
            box = QWidget()
            layout = QHBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("inlineFieldLabel")
            caption.setFixedWidth(88)
            combo = QComboBox()
            combo.addItems(values)
            if value in values:
                combo.setCurrentText(value)
            layout.addWidget(caption)
            layout.addWidget(combo, 1)
            return box, combo

        def choose_dir(self, edit: QLineEdit):
            path = QFileDialog.getExistingDirectory(self, "选择文件夹", edit.text() or str(ROOT))
            if path:
                edit.setText(path)

        def choose_file(self, edit: QLineEdit, caption: str = "选择文件"):
            path, _ = QFileDialog.getOpenFileName(self, caption, edit.text() or str(ROOT), "All Files (*)")
            if path:
                edit.setText(path)

        def stat_card(self, label: str, value: str = "-"):
            card = QFrame()
            card.setObjectName("statCard")
            layout = QHBoxLayout(card)
            layout.setContentsMargins(12, 8, 12, 8)
            name = QLabel(label)
            name.setObjectName("fieldLabel")
            name.setFixedWidth(88)
            metric = QLabel(value)
            metric.setObjectName("statValue")
            metric.setWordWrap(True)
            layout.addWidget(name)
            layout.addWidget(metric, 1)
            return card, metric

        def metric_card(self, label: str, value: str = "待检测"):
            card = QFrame()
            card.setObjectName("metricCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(12, 10, 12, 10)
            name = QLabel(label)
            name.setObjectName("fieldLabel")
            metric = QLabel(value)
            metric.setObjectName("metricValue")
            metric.setWordWrap(True)
            layout.addWidget(name)
            layout.addWidget(metric)
            return card, metric

        def short_gpu_name(self, name: str):
            cleaned = str(name or "").replace("NVIDIA GeForce ", "").replace("NVIDIA ", "").replace(" Laptop GPU", "")
            cleaned = cleaned.replace("RTX", "RTX ").replace("  ", " ").strip()
            return cleaned or "待检测"

    def scroll_page(widget: QWidget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.inner_page = widget
        return scroll

    # ===================================================================
    #  Task 5: Home page with 2x2 grid (1:2 cols, 58:42 rows)
    # ===================================================================
    class HomePage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            # Hero
            hero = QHBoxLayout()
            copy = QVBoxLayout()
            title = QLabel("欢迎使用 YOLO 本地训练工作台")
            title.setObjectName("pageTitle")
            subtitle = QLabel("配置项目路径、检查数据状态、查看训练结果。")
            subtitle.setObjectName("fieldLabel")
            copy.addWidget(title)
            copy.addWidget(subtitle)
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
            grid.setSpacing(12)
            layout.addLayout(grid, 1)

            # --- Task 2: Project overview - title and button on same line ---
            overview = Card()
            header_row = QHBoxLayout()
            ov_title = QLabel("项目概览")
            ov_title.setObjectName("sectionTitle")
            header_row.addWidget(ov_title)
            header_row.addStretch(1)
            pick = QPushButton("设置项目目录")
            pick.setObjectName("softButton")
            pick.setFixedWidth(100)
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
            self.distribution_view = QLabel()
            self.distribution_view.setObjectName("chartView")
            self.distribution_view.setMinimumHeight(200)
            distribution.layout.addWidget(self.distribution_view, 1)
            grid.addWidget(distribution, 0, 1)

            # --- Task 7: Training curves ---
            curve = Card("训练曲线")
            self.curve_view = QLabel()
            self.curve_view.setObjectName("chartView")
            self.curve_view.setMinimumHeight(180)
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
            open_button.setObjectName("softButton")
            open_button.setFixedWidth(100)
            open_button.clicked.connect(self.open_result_dir)
            hist_header.addWidget(open_button)
            history.layout.addLayout(hist_header)
            self.history_table = QTableWidget(0, 7)
            self.history_table.setHorizontalHeaderLabels(["模型ID", "Epochs", "Time", "mAP50", "mAP50-95", "Box Loss", "Recall"])
            self.history_table.setSortingEnabled(True)
            self.history_table.horizontalHeader().setSortIndicatorShown(False)
            self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            self.history_table.setColumnWidth(0, 130)
            history.layout.addWidget(self.history_table, 1)
            grid.addWidget(history, 1, 1)

        def on_show(self):
            paths = self.app.settings["paths"]
            project_root = self.app.settings["project"]["root"]
            images = Path(paths["images_dir"])
            labels = Path(paths["labels_dir"])
            image_count = len([p for p in images.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES]) if images.exists() else 0
            label_count = len(list(labels.glob("*.txt"))) if labels.exists() else 0

            # Task 3: relative paths (except project folder)
            self.overview_stats["project"].setText(project_root)
            self.overview_stats["images"].setText(_relative_path(paths["images_dir"], project_root))
            self.overview_stats["annotations"].setText(_relative_path(paths["annotations_dir"], project_root))
            self.overview_stats["result"].setText(_relative_path(paths["result_dir"], project_root))
            self.overview_stats["image_count"].setText(str(image_count))
            self.overview_stats["label_count"].setText(str(label_count))

            self.draw_distribution()
            self.draw_training_curves()
            self.refresh_history()

        def refresh_history(self):
            paths = self.app.settings["paths"]
            result_dir = Path(paths["result_dir"])
            candidates = scan_candidate_models(result_dir)
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
                    if column == 1:
                        try:
                            sort_key = float(value)
                        except (ValueError, TypeError):
                            sort_key = 0.0
                    elif column in (3, 4):
                        try:
                            sort_key = float(value.replace('%', ''))
                        except (ValueError, TypeError):
                            sort_key = 0.0
                    elif column == 5:
                        try:
                            sort_key = -float(value)
                        except (ValueError, TypeError):
                            sort_key = 0.0
                    elif column == 6:
                        try:
                            sort_key = float(value.replace('%', ''))
                        except (ValueError, TypeError):
                            sort_key = 0.0
                    item = _SortItem(value, sort_key)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.history_table.setItem(row, column, item)
            self.history_table.sortItems(0, Qt.SortOrder.AscendingOrder)

        def pick_project_root(self):
            path = QFileDialog.getExistingDirectory(self, "设置项目目录", self.app.settings["project"]["root"])
            if path:
                self.app.settings["project"]["root"] = path
                self.app.settings_service.save(self.app.settings)
                self.on_show()

        def open_result_dir(self):
            path = Path(self.app.settings["paths"]["result_dir"])
            if path.exists():
                os.startfile(path)

        # Task 6: distribution with train/val/test bars
        def draw_distribution(self):
            paths = self.app.settings["paths"]
            project_root = Path(self.app.settings["project"]["root"])
            dataset_dir = Path(paths["dataset_dir"])
            class_names = self.app.settings["dataset"]["class_names"]

            # Count images per split
            split_counts = {}
            for split in ("train", "val", "test"):
                img_dir = dataset_dir / split / "images"
                if img_dir.exists():
                    split_counts[split] = len([p for p in img_dir.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES])
                else:
                    split_counts[split] = 0
            total = sum(split_counts.values())

            pixmap = QPixmap(620, 250)
            pixmap.fill(Qt.GlobalColor.white)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Title
            painter.setPen(QPen(QColor("#14233A"), 2))
            painter.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
            title_text = f"{', '.join(class_names)} | 总计 {total} 张"
            painter.drawText(0, 26, pixmap.width(), 24, Qt.AlignmentFlag.AlignCenter, title_text)

            # Axes
            y_bottom = 210
            y_top = 48
            x_left = 70
            x_right = 580
            painter.setPen(QPen(QColor("#14233A"), 1))
            painter.drawLine(x_left, y_bottom, x_right, y_bottom)
            painter.drawLine(x_left, y_bottom, x_left, y_top)

            max_count = max(max(split_counts.values()), 1)
            bar_w = 80
            colors = {"train": QColor("#4A90D9"), "val": QColor("#22B765"), "test": QColor("#F4B42E")}
            labels_cn = {"train": "训练", "val": "验证", "test": "测试"}
            total_w = len(split_counts) * bar_w + (len(split_counts) - 1) * 40
            x_start = x_left + (x_right - x_left - total_w) // 2

            painter.setFont(QFont("Microsoft YaHei UI", 10))
            for i, (split, count) in enumerate(split_counts.items()):
                x = x_start + i * (bar_w + 40)
                h = int((count / max_count) * (y_bottom - y_top - 20))
                painter.fillRect(x, y_bottom - h, bar_w, h, QBrush(colors[split]))
                # Count label above bar
                painter.setPen(QColor("#14233A"))
                painter.drawText(x, y_bottom - h - 18, bar_w, 16, Qt.AlignmentFlag.AlignCenter, str(count))
                # Category label below
                painter.drawText(x, y_bottom + 6, bar_w, 16, Qt.AlignmentFlag.AlignCenter, labels_cn[split])

            painter.end()
            self.distribution_view.setPixmap(pixmap)

        # Task 7: training curves from results.csv
        def draw_training_curves(self):
            result_dir = Path(self.app.settings["paths"]["result_dir"])
            data = read_results_csv_for_curves(result_dir)

            w, h = 420, 210
            pixmap = QPixmap(w, h)
            pixmap.fill(Qt.GlobalColor.white)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if not data:
                painter.setPen(QColor("#94A2AD"))
                painter.setFont(QFont("Microsoft YaHei UI", 11))
                painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "暂无训练记录\n请进行模型训练")
                painter.end()
                self.curve_view.setPixmap(pixmap)
                return

            # Select curves to plot
            curve_defs = [
                ("train/box_loss", QColor("#E74C3C"), "Box Loss"),
                ("val/box_loss", QColor("#E67E22"), "Val Box Loss"),
            ]
            # Try to find mAP columns
            for col_name in data:
                if "mAP50(" in col_name and "95" not in col_name:
                    curve_defs.append((col_name, QColor("#3498DB"), "mAP50"))
                    break
            for col_name in data:
                if "mAP50-95(" in col_name:
                    curve_defs.append((col_name, QColor("#2ECC71"), "mAP50-95"))
                    break

            x_left, x_right = 50, w - 20
            y_top, y_bottom = 30, h - 30
            x_range = x_right - x_left
            y_range = y_bottom - y_top

            # Axes
            painter.setPen(QPen(QColor("#14233A"), 1))
            painter.drawLine(x_left, y_bottom, x_right, y_bottom)
            painter.drawLine(x_left, y_bottom, x_left, y_top)

            for col_name, color, label in curve_defs:
                vals = data.get(col_name, [])
                if not vals:
                    continue
                mn, mx = min(vals), max(vals)
                if mx == mn:
                    mx = mn + 1
                painter.setPen(QPen(color, 2))
                path = QPainterPath()
                for j, v in enumerate(vals):
                    x = x_left + (j / max(len(vals) - 1, 1)) * x_range
                    y = y_bottom - ((v - mn) / (mx - mn)) * y_range
                    if j == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                painter.drawPath(path)

            # Legend at top right
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            lx = x_right - 10
            ly = y_top + 4
            for col_name, color, label in reversed(curve_defs):
                vals = data.get(col_name, [])
                if not vals:
                    continue
                lw = painter.fontMetrics().horizontalAdvance(label) + 24
                lx -= lw
                painter.setPen(QPen(color, 3))
                painter.drawLine(lx, ly + 6, lx + 14, ly + 6)
                painter.setPen(QColor("#14233A"))
                painter.drawText(lx + 18, ly, lw - 18, 14, Qt.AlignmentFlag.AlignVCenter, label)
                ly += 16

            painter.end()
            self.curve_view.setPixmap(pixmap)

    # ===================================================================
    #  Data page
    # ===================================================================
    class DataPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = self.page_layout()
            content = QHBoxLayout()
            layout.addLayout(content, 1)
            sidebar = QFrame()
            sidebar.setObjectName("dataSidebar")
            sidebar.setFixedWidth(180)
            side_layout = QVBoxLayout(sidebar)
            side_layout.setContentsMargins(12, 18, 12, 18)
            title = QLabel("数据处理")
            title.setObjectName("sideTitle")
            side_layout.addWidget(title)
            self.tool_stack = QStackedWidget()
            self.tools = {
                "convert": ConvertTab(app),
                "preview": PreviewTab(app),
                "rename": RenameTab(app),
                "resize": ResizeTab(app),
            }
            self.tool_buttons = {}
            for key, label in [("convert", "标注转换"), ("preview", "标注预览"), ("rename", "批量重命名"), ("resize", "图片压缩")]:
                button = QPushButton(label)
                button.setObjectName("dataNavButton")
                button.setCheckable(True)
                button.clicked.connect(lambda _checked=False, name=key: self.show_tool(name))
                side_layout.addWidget(button)
                self.tool_buttons[key] = button
                self.tool_stack.addWidget(self.tools[key])
            side_layout.addStretch(1)
            content.addWidget(sidebar)
            content.addWidget(self.tool_stack, 1)
            self.show_tool("convert")

        def show_tool(self, key: str):
            self.tool_stack.setCurrentWidget(self.tools[key])
            for name, button in self.tool_buttons.items():
                button.setChecked(name == key)

    class ConvertTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            paths = app.settings["paths"]
            dataset = app.settings["dataset"]
            grid = QGridLayout()
            self.images_box, self.images_edit = self.field("图片目录", paths["images_dir"], self.choose_dir)
            self.annotations_box, self.annotations_edit = self.field("Labelme目录", paths["annotations_dir"], self.choose_dir)
            self.output_box, self.output_edit = self.field("输出目录", paths["dataset_dir"], self.choose_dir)
            self.classes_box, self.classes_edit = self.field("类别名称", ",".join(dataset["class_names"]))
            self.task_box, self.task_combo = self.combo_field("任务类型", app.settings["task"]["mode"], ["obb", "detect"])
            ratios = dataset["split_ratios"]
            self.ratio_box, self.ratio_edit = self.field("划分比例", f"{ratios['train']},{ratios['val']},{ratios['test']}")
            self.seed_box, self.seed_edit = self.field("随机种子", str(dataset["random_seed"]))
            self.line_box, self.line_edit = self.field("线宽半径", str(dataset["line_to_obb"]["half_width"]))
            for index, widget in enumerate([self.images_box, self.annotations_box, self.output_box, self.classes_box, self.task_box, self.ratio_box, self.seed_box, self.line_box]):
                grid.addWidget(widget, index // 2, index % 2)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            preview_button = QPushButton("预览转换")
            preview_button.clicked.connect(self.preview)
            run_button = QPushButton("执行转换")
            run_button.clicked.connect(self.run)
            actions.addWidget(preview_button)
            actions.addWidget(run_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

        def config(self):
            train, val, test = [float(item.strip()) for item in self.ratio_edit.text().split(",")]
            return ConversionConfig(
                task_mode=self.task_combo.currentText(),
                images_dir=Path(self.images_edit.text()),
                annotations_dir=Path(self.annotations_edit.text()),
                output_dir=Path(self.output_edit.text()),
                labels_dir=Path(self.app.settings["paths"]["labels_dir"]),
                class_names=[item.strip() for item in self.classes_edit.text().split(",") if item.strip()],
                train_ratio=train,
                val_ratio=val,
                test_ratio=test,
                line_to_obb=True,
                line_half_width=float(self.line_edit.text()),
            )

        def preview(self):
            try:
                result = preview_conversion(self.config())
                self.log.setPlainText(f"有标注图片: {result.labeled_count}\n无标注图片: {result.unlabeled_count}\n计划划分: {result.planned_splits}\n未执行任何写入。")
            except Exception as exc:
                self.log.setPlainText(str(exc))

        def run(self):
            try:
                result = run_conversion(self.config())
                self.log.append(f"转换完成: train={result.labeled_train_count}, val={result.labeled_val_count}, test={result.labeled_test_count}, boxes={result.total_boxes}")
            except Exception:
                self.log.append(traceback.format_exc())

    class PreviewTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.preview_items: list[Path] = []
            self.preview_index = 0
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            grid = QGridLayout()
            self.image_box, self.image_edit = self.field("图片文件夹", app.settings["paths"]["images_dir"], self.choose_dir)
            self.label_box, self.label_edit = self.field("标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir)
            grid.addWidget(self.image_box, 0, 0)
            grid.addWidget(self.label_box, 0, 1)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            for text, slot in [("扫描", self.load_preview_items), ("上一张", self.prev_image), ("下一张", self.next_image)]:
                button = QPushButton(text)
                button.clicked.connect(slot)
                actions.addWidget(button)
            self.current_label = QLabel("等待扫描图片")
            actions.addWidget(self.current_label, 1)
            layout.addLayout(actions)
            images = QHBoxLayout()
            self.source_view = ImageView("原始图片")
            self.result_view = ImageView("标注预览")
            images.addWidget(self.source_view)
            images.addWidget(self.result_view)
            layout.addLayout(images, 1)

        def load_preview_items(self):
            image_dir = Path(self.image_edit.text())
            self.preview_items = sorted(path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES) if image_dir.exists() else []
            self.preview_index = 0
            self.render_current()

        def prev_image(self):
            if not self.preview_items:
                self.load_preview_items()
                return
            self.preview_index = (self.preview_index - 1) % len(self.preview_items)
            self.render_current()

        def next_image(self):
            if not self.preview_items:
                self.load_preview_items()
                return
            self.preview_index = (self.preview_index + 1) % len(self.preview_items)
            self.render_current()

        def render_current(self):
            if not self.preview_items:
                self.current_label.setText("未找到图片")
                return
            image_path = self.preview_items[self.preview_index]
            label_path = Path(self.label_edit.text()) / f"{image_path.stem}.txt"
            self.current_label.setText(f"{self.preview_index + 1}/{len(self.preview_items)}  {image_path.name}")
            image = Image.open(image_path).convert("RGB")
            annotations = load_yolo_annotations(image.size, label_path, self.app.settings["task"]["mode"], self.app.settings["dataset"]["class_names"])
            preview = render_annotation_preview(image_path, annotations)
            self.source_view.set_pil_image(image)
            self.result_view.set_pil_image(preview)

    class RenameTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.plan = []
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            grid = QGridLayout()
            self.folder_box, self.folder_edit = self.field("文件夹", app.settings["paths"]["images_dir"], self.choose_dir)
            self.label_box, self.label_edit = self.field("标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir)
            self.prefix_box, self.prefix_edit = self.field("命名前缀", "A")
            self.start_box, self.start_edit = self.field("起始编号", "1")
            self.padding_box, self.padding_edit = self.field("编号位数", "3")
            for index, widget in enumerate([self.folder_box, self.label_box, self.prefix_box, self.start_box, self.padding_box]):
                grid.addWidget(widget, index // 2, index % 2)
            self.include_labels = QCheckBox("标注文件一并更改")
            self.include_labels.setChecked(True)
            grid.addWidget(self.include_labels, 2, 1)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            preview_button = QPushButton("预览")
            preview_button.clicked.connect(self.preview)
            run_button = QPushButton("执行重命名")
            run_button.clicked.connect(self.run)
            actions.addWidget(preview_button)
            actions.addWidget(run_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.table = QTableWidget(0, 5)
            self.table.setHorizontalHeaderLabels(["序号", "原文件名", "新文件名", "图片冲突", "标注状态"])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.table, 1)
            for edit in [self.folder_edit, self.label_edit, self.prefix_edit, self.start_edit, self.padding_edit]:
                edit.textChanged.connect(lambda _text: self.preview())
            self.include_labels.stateChanged.connect(lambda _state: self.preview())
            QTimer.singleShot(100, self.preview)

        def preview(self):
            try:
                self.plan = preview_rename(
                    Path(self.folder_edit.text()),
                    self.prefix_edit.text(),
                    int(self.start_edit.text()),
                    int(self.padding_edit.text()),
                    labels_dir=Path(self.label_edit.text()),
                    include_labels=self.include_labels.isChecked(),
                )
            except Exception:
                return
            self.table.setRowCount(len(self.plan))
            for row, item in enumerate(self.plan):
                label_status = item.note or (f"{item.label_source.name} -> {item.label_target.name}" if item.label_source and item.label_target else "不处理")
                values = [item.index, item.old_name, item.new_name, "是" if item.conflict else "无", label_status]
                for column, value in enumerate(values):
                    self.table.setItem(row, column, QTableWidgetItem(str(value)))

        def run(self):
            result = execute_rename(self.plan)
            if result.renamed_count == 0 and result.skipped_count:
                QMessageBox.warning(self, "发现冲突", "检测到标注文件目标名称冲突，已取消本次重命名。")
            else:
                QMessageBox.information(self, "重命名完成", f"已重命名图片 {result.renamed_count} 个，标注 {result.label_renamed_count} 个。")
            self.preview()

    class ResizeTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            resize = app.settings["image_resize"]
            grid = QGridLayout()
            self.source_box, self.source_edit = self.field("图片目录", app.settings["paths"]["images_dir"], self.choose_dir)
            self.backup_box, self.backup_edit = self.field("备份目录", resize["backup_dir"], self.choose_dir)
            self.output_box, self.output_edit = self.field("输出目录", resize["output_dir"], self.choose_dir)
            self.long_box, self.long_edit = self.field("长边缩放", str(resize["long_edge"]))
            self.canvas_box, self.canvas_edit = self.field("画布尺寸", str(resize["canvas_size"]))
            self.bg_box, self.bg_combo = self.combo_field("背景颜色", resize["background"], ["white", "black"])
            self.output_mode_box, self.output_mode_combo = self.combo_field("输出方式", "输出到新文件夹", ["输出到新文件夹", "覆盖原文件"])
            self.save_format_box, self.save_format_combo = self.combo_field("保存格式", "保持原格式", ["保持原格式", "jpg", "png"])
            for index, widget in enumerate([self.source_box, self.backup_box, self.output_box, self.output_mode_box, self.long_box, self.canvas_box, self.bg_box, self.save_format_box]):
                grid.addWidget(widget, index // 2, index % 2)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            preview_button = QPushButton("预览压缩")
            preview_button.clicked.connect(self.preview)
            run_button = QPushButton("执行压缩")
            run_button.clicked.connect(self.run)
            actions.addWidget(preview_button)
            actions.addWidget(run_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

        def config(self):
            return ResizeConfig(
                source_dir=Path(self.source_edit.text()),
                output_dir=Path(self.output_edit.text()),
                backup_dir=Path(self.backup_edit.text()),
                long_edge=int(self.long_edit.text()),
                canvas_size=int(self.canvas_edit.text()),
                background=self.bg_combo.currentText(),
            )

        def preview(self):
            result = preview_resize(self.config())
            self.log.setPlainText(f"计划处理 {len(result.items)} 张图片\n输出方式: {self.output_mode_combo.currentText()}\n保存格式: {self.save_format_combo.currentText()}\n")
            for item in result.items[:80]:
                self.log.append(f"{item.source.name}: {item.original_size} -> {item.resized_size}, scale={item.scale:.3f}")

        def run(self):
            result = run_resize(self.config())
            self.log.append(f"\n压缩完成: {result.processed_count} 张，输出目录: {result.output_dir}")

    # ===================================================================
    #  Task 12: Train page - reordered fields, optimizer, no log title/progress
    #  Task 9: Prevent double-start
    #  Task 10: Custom command dialog
    # ===================================================================
    class TrainPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.edits = {}
            self.checks = {}
            self.metric_labels = {}
            self.log_queue: Queue | None = None
            self.is_training = False
            self.poll_timer = QTimer(self)
            self.poll_timer.timeout.connect(self.poll_training_queue)
            layout = self.page_layout()
            top = QGridLayout()
            top.setColumnStretch(0, 115)
            top.setColumnStretch(1, 85)
            layout.addLayout(top)
            training = self.app.settings["training"]

            left = Card("数据集与增强配置")
            right = Card("训练参数")
            top.addWidget(left, 0, 0)
            top.addWidget(right, 0, 1)

            # Task 12: Reordered layout
            # Row 0: 基础模型 (model dropdown), 数据集YAML
            # Row 1: 模型YAML (blank default), 项目输出
            left_form = QGridLayout()
            left.layout.addLayout(left_form)

            # 基础模型 - dropdown from data/models/*.pt
            model_files = _find_pt_files_in_data_models(Path(self.app.settings["project"]["root"]))
            base_label = QLabel("基础模型")
            base_label.setObjectName("inlineFieldLabel")
            self.pretrained_combo = QComboBox()
            self.pretrained_combo.setEditable(True)
            if model_files:
                self.pretrained_combo.addItems(model_files)
            current_pretrained = training.get("pretrained", "")
            # If current is just a filename, show it
            current_name = Path(current_pretrained).name if current_pretrained else ""
            if current_name:
                self.pretrained_combo.setCurrentText(current_name)
            left_form.addWidget(base_label, 0, 0)
            left_form.addWidget(self.pretrained_combo, 0, 1)

            # 数据集YAML
            self.edits["data"], _ = None, None
            data_box, data_edit = self.inline_field("数据集YAML", training.get("data", ""), self.choose_file)
            self.edits["data"] = data_edit
            left_form.addWidget(data_box, 0, 2, 1, 2)

            # 模型YAML (default blank)
            model_yaml_box, model_yaml_edit = self.inline_field("模型YAML", "", self.choose_file)
            self.edits["model_yaml"] = model_yaml_edit
            left_form.addWidget(model_yaml_box, 1, 0, 1, 2)

            # 项目输出
            project_box, project_edit = self.inline_field("项目输出", training.get("project", ""), self.choose_dir)
            self.edits["project"] = project_edit
            left_form.addWidget(project_box, 1, 2, 1, 2)

            # Augmentation checkboxes
            aug = QGridLayout()
            left.layout.addLayout(aug)
            for index, (key, label) in enumerate([("mosaic", "马赛克"), ("fliplr", "左右翻转"), ("flipud", "上下翻转"), ("mixup", "MixUp"), ("scale", "缩放"), ("translate", "平移"), ("degrees", "旋转"), ("hsv", "HSV")]):
                check = QCheckBox(label)
                check.setChecked(float(training.get(key, 0)) > 0)
                self.checks[key] = check
                aug.addWidget(check, index // 4, index % 4)

            # Right side: training params
            params = QGridLayout()
            right.layout.addLayout(params)

            # Task 12: Optimizer combo
            optimizer_box = QWidget()
            optimizer_layout = QHBoxLayout(optimizer_box)
            optimizer_layout.setContentsMargins(0, 0, 0, 0)
            opt_label = QLabel("优化器")
            opt_label.setObjectName("inlineFieldLabel")
            opt_label.setFixedWidth(88)
            self.optimizer_combo = QComboBox()
            self.optimizer_combo.addItems(["auto", "SGD", "Adam", "AdamW", "RMSProp"])
            current_opt = training.get("optimizer", "auto")
            if current_opt in ["auto", "SGD", "Adam", "AdamW", "RMSProp"]:
                self.optimizer_combo.setCurrentText(current_opt)
            optimizer_layout.addWidget(opt_label)
            optimizer_layout.addWidget(self.optimizer_combo, 1)
            params.addWidget(optimizer_box, 0, 0, 1, 2)

            # Device combo
            self.device_box, self.device_combo = self.inline_combo_field("设备", str(training.get("device", "0")), ["0", "cpu", "0,1"])
            params.addWidget(self.device_box, 1, 0, 1, 2)

            # Other params
            param_idx = 2
            for key, label in [("lr", "学习率"), ("epochs", "Epochs"), ("patience", "Patience"), ("workers", "Workers"), ("batch", "Batch"), ("imgsz", "图片尺寸")]:
                box, edit = self.inline_field(label, training.get(key, ""))
                self.edits[key] = edit
                params.addWidget(box, param_idx // 2, param_idx % 2)
                param_idx += 1

            # Task 9: Control buttons
            actions = QHBoxLayout()
            layout.addLayout(actions)
            control = Card()
            control_body = QGridLayout()
            control.layout.addLayout(control_body)
            self.start_btn = QPushButton("开始训练")
            self.start_btn.clicked.connect(self.start)
            self.stop_btn = QPushButton("停止训练")
            self.stop_btn.setObjectName("softButton")
            self.stop_btn.clicked.connect(self.stop)
            report = QPushButton("查看模型报告")
            report.setObjectName("softButton")
            report.clicked.connect(self.open_result)
            control_body.addWidget(self.start_btn, 0, 0, 1, 2)
            control_body.addWidget(self.stop_btn, 1, 0)
            control_body.addWidget(report, 1, 1)
            actions.addWidget(control, 1)

            status = Card()
            status_body = QGridLayout()
            status.layout.addLayout(status_body)
            for index, (key, label) in enumerate([("gpu", "GPU"), ("vram", "显存占用"), ("cpu", "CPU占用"), ("memory", "内存占用")]):
                card, metric = self.metric_card(label)
                status_body.addWidget(card, 0, index)
                self.metric_labels[key] = metric
            actions.addWidget(status, 3)

            # Task 11: No title, no progress bar - just the log text panel
            log_panel = Card()
            self.log = QTextEdit()
            self.log.setReadOnly(True)
            log_panel.layout.addWidget(self.log, 1)
            layout.addWidget(log_panel, 1)
            self.refresh_command_preview()

        def on_show(self):
            for metric in self.metric_labels.values():
                metric.setText("检测中...")
            self.app.run_background("train_status", lambda: {"status": system_status(), "cuda": torch_cuda_summary()})

        def apply_train_status(self, payload):
            status = payload["status"]
            cuda = payload["cuda"]
            self.metric_labels["gpu"].setText(f"{self.short_gpu_name(status.get('gpu') or cuda.get('gpu', '待检测'))} · {status.get('gpu_usage', '待检测')}")
            self.metric_labels["vram"].setText(status.get("vram", "待检测"))
            self.metric_labels["cpu"].setText(status.get("cpu", "待检测"))
            self.metric_labels["memory"].setText(status.get("memory", "待检测"))

        def collect_config(self):
            config = {}
            config["data"] = self.edits["data"].text() if self.edits["data"] else ""
            config["model_yaml"] = self.edits["model_yaml"].text() if self.edits["model_yaml"] else ""
            config["project"] = self.edits["project"].text() if self.edits["project"] else ""
            config["lr"] = self.edits["lr"].text() if self.edits.get("lr") else "0.001"
            config["epochs"] = self.edits["epochs"].text() if self.edits.get("epochs") else "800"
            config["patience"] = self.edits["patience"].text() if self.edits.get("patience") else "150"
            config["workers"] = self.edits["workers"].text() if self.edits.get("workers") else "2"
            config["batch"] = self.edits["batch"].text() if self.edits.get("batch") else "16"
            config["imgsz"] = self.edits["imgsz"].text() if self.edits.get("imgsz") else "640"
            config["device"] = self.device_combo.currentText()
            config["base_model"] = self.pretrained_combo.currentText()
            config["pretrained"] = self.pretrained_combo.currentText()
            config["optimizer"] = self.optimizer_combo.currentText()
            for key in ("epochs", "patience", "workers", "batch", "imgsz"):
                try:
                    config[key] = int(config[key])
                except (ValueError, TypeError):
                    config[key] = int(self.app.settings["training"].get(key, 0))
            try:
                config["lr"] = float(config["lr"])
            except (ValueError, TypeError):
                config["lr"] = float(self.app.settings["training"].get("lr", 0.001))
            config["task_mode"] = infer_task_mode_from_model(config.get("model_yaml") or config.get("base_model") or config.get("pretrained"))
            for key, check in self.checks.items():
                config[key] = self.app.settings["training"].get(key, 0) if check.isChecked() else 0
            # Resolve pretrained path - if just a name, look in data/models
            pretrained_val = config.get("pretrained", "")
            if pretrained_val and not Path(pretrained_val).exists():
                models_dir = Path(self.app.settings["project"]["root"]) / "data" / "models"
                candidate = models_dir / pretrained_val
                if candidate.exists():
                    config["pretrained"] = str(candidate)
            return config

        def refresh_command_preview(self):
            self.log.setPlainText(" ".join(build_train_command(self.collect_config())) + "\n等待开始训练...")

        # Task 9: Only allow one training at a time
        # Task 10: Custom command dialog
        def start(self):
            if self.is_training:
                return
            config = self.collect_config()
            command = build_train_command(config)

            # Task 10: Custom command dialog if enabled
            if self.app.settings.get("features", {}).get("custom_command_dialog", True):
                dialog = CommandDialog(command, self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return
                command = dialog.get_command()

            self.is_training = True
            self.start_btn.setEnabled(False)
            self.log.clear()
            self.log.append(" ".join(command))
            self.log_queue = Queue()
            self.app.training_handle = spawn_logged_process(command, str(ROOT), self.log_queue)
            self.poll_timer.start(150)
            self.app.status.setText("训练中")

        def poll_training_queue(self):
            if self.log_queue is None:
                return
            while not self.log_queue.empty():
                event, payload = self.log_queue.get()
                if event == "log":
                    self.log.append(payload)
                elif event == "exit":
                    self.log.append(f"训练进程结束，退出码：{payload}")
                    self.poll_timer.stop()
                    self.is_training = False
                    self.start_btn.setEnabled(True)
                    self.app.status.setText("训练结束")

        def stop(self):
            stop_process(self.app.training_handle)
            self.log.append("已请求停止训练。")

        def open_result(self):
            path = Path(self.edits["project"].text() if self.edits.get("project") else self.app.settings["paths"]["result_dir"])
            if path.exists():
                os.startfile(path)

    # ===================================================================
    #  Task 14: Validate page - model dropdown, first/last buttons
    #  Task 9: Prevent double-start
    #  Task 3: Relative paths
    # ===================================================================
    class ValidatePage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.detect_results = []
            self.detect_index = -1
            self.detect_stop = threading.Event()
            self.detect_worker = None
            self.is_detecting = False
            self._all_model_paths: list[Path] = []
            layout = self.page_layout()
            split = QHBoxLayout()
            layout.addLayout(split, 1)

            # Left column
            left_shell = Card()
            left_column = left_shell.layout
            validation = app.settings["validation"]

            # Model config - Task 14: dropdown for models
            model_title = QLabel("模型配置")
            model_title.setObjectName("sectionTitle")
            left_column.addWidget(model_title)
            model_row = QHBoxLayout()
            model_label = QLabel("选择模型")
            model_label.setObjectName("inlineFieldLabel")
            model_label.setFixedWidth(70)
            self.model_combo = QComboBox()
            self.model_combo.setEditable(True)
            self.model_combo.setMinimumWidth(200)
            model_row.addWidget(model_label)
            model_row.addWidget(self.model_combo, 1)
            left_column.addLayout(model_row)

            conf_row = QHBoxLayout()
            self.conf_box, self.conf_edit = self.field("置信度", str(validation["confidence"]))
            self.iou_box, self.iou_edit = self.field("IoU", str(validation["iou"]))
            conf_row.addWidget(self.conf_box)
            conf_row.addWidget(self.iou_box)
            left_column.addLayout(conf_row)

            # Source config
            source_title = QLabel("检测源配置")
            source_title.setObjectName("sectionTitle")
            left_column.addWidget(source_title)
            self.mode_box, self.mode_combo = self.combo_field("检测模式", "图片/视频文件夹", ["图片/视频文件夹", "摄像头"])
            left_column.addWidget(self.mode_box)
            self.source_box, self.source_edit = self.field("输入源", validation["source_path"], self.choose_dir)
            left_column.addWidget(self.source_box)
            self.camera_box, self.camera_combo = self.combo_field("摄像头", str(validation["camera_index"]), ["0", "1", "2", "3"])
            left_column.addWidget(self.camera_box)

            # Control
            control_title = QLabel("检测控制")
            control_title.setObjectName("sectionTitle")
            left_column.addWidget(control_title)
            controls = QHBoxLayout()
            self.start_det_btn = QPushButton("开始检测")
            self.start_det_btn.clicked.connect(self.start_detection)
            pause = QPushButton("暂停")
            pause.setObjectName("softButton")
            self.stop_det_btn = QPushButton("停止")
            self.stop_det_btn.setObjectName("softButton")
            self.stop_det_btn.clicked.connect(self.stop_detection)
            controls.addWidget(self.start_det_btn)
            controls.addWidget(pause)
            controls.addWidget(self.stop_det_btn)
            left_column.addLayout(controls)

            log_title = QLabel("检测日志")
            log_title.setObjectName("sectionTitle")
            left_column.addWidget(log_title)
            self.detect_log = QTextEdit()
            self.detect_log.setReadOnly(True)
            left_column.addWidget(self.detect_log, 1)
            split.addWidget(left_shell, 3)

            # Right column
            right = QVBoxLayout()
            toolbar = QHBoxLayout()
            toolbar.addWidget(QLabel("批量检测结果"))
            for text, slot in [("上一张", self.prev_result), ("第一张", self.first_result), ("下一张", self.next_result), ("最后一张", self.last_result), ("保存结果", self.save_current_result), ("清空结果", self.clear_results)]:
                button = QPushButton(text)
                button.setObjectName("softButton")
                button.clicked.connect(slot)
                toolbar.addWidget(button)
            self.counter = QLabel("0/0")
            toolbar.addWidget(self.counter)
            toolbar.addStretch(1)
            right.addLayout(toolbar)
            views = QHBoxLayout()
            source_panel = Card("源")
            self.source_view = ImageView("源图")
            source_panel.layout.addWidget(self.source_view, 1)
            result_panel = Card("检测结果")
            self.result_view = ImageView("检测结果图")
            result_panel.layout.addWidget(self.result_view, 1)
            views.addWidget(source_panel)
            views.addWidget(result_panel)
            right.addLayout(views, 1)
            table_panel = Card("检测结果详情表")
            self.table = QTableWidget(0, 6)
            self.table.setHorizontalHeaderLabels(["序号", "类别", "置信度", "坐标(x,y)", "尺寸(w×h)", "角度"])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table_panel.layout.addWidget(self.table)
            right.addWidget(table_panel)
            right_widget = QWidget()
            right_widget.setLayout(right)
            split.addWidget(right_widget, 7)

            self.mode_combo.currentTextChanged.connect(self.update_source_mode)
            self.update_source_mode(self.mode_combo.currentText())

        def update_source_mode(self, value):
            camera = value == "摄像头"
            self.source_box.setVisible(not camera)
            self.camera_box.setVisible(camera)

        def on_show(self):
            # Scan models and populate dropdown
            result_dir = Path(self.app.settings["paths"]["result_dir"])
            self._all_model_paths = _find_models_full_paths(result_dir)
            display_names = [_simplified_model_path(str(m)) for m in self._all_model_paths]
            self.model_combo.clear()
            self.model_combo.addItems(display_names)
            # Set current from settings
            current = self.app.settings["validation"].get("model_path", "")
            if current:
                display = _simplified_model_path(current)
                idx = self.model_combo.findText(display)
                if idx >= 0:
                    self.model_combo.setCurrentIndex(idx)
                else:
                    self.model_combo.setEditText(current)

        def _get_model_path(self) -> str:
            """Resolve the selected model combo to an absolute path."""
            text = self.model_combo.currentText()
            # Try to find it in our known paths
            for p in self._all_model_paths:
                if _simplified_model_path(str(p)) == text or str(p) == text:
                    return str(p)
            # Maybe it's already a full path
            if Path(text).exists():
                return text
            return text

        def config(self):
            return {
                "model_path": self._get_model_path(),
                "source_mode": "摄像头" if self.mode_combo.currentText() == "摄像头" else "图片文件夹",
                "source_path": self.source_edit.text(),
                "camera_index": int(self.camera_combo.currentText()),
                "confidence": float(self.conf_edit.text()),
                "iou": float(self.iou_edit.text()),
                "save_dir": self.app.settings["validation"]["save_dir"],
            }

        # Task 9: Only allow one detection at a time
        def start_detection(self):
            if self.is_detecting:
                return
            self.is_detecting = True
            self.start_det_btn.setEnabled(False)
            self.detect_log.clear()
            self.detect_stop.clear()
            self.detect_results.clear()
            self.detect_index = -1
            self.counter.setText("0/0")
            self.table.setRowCount(0)
            self.app.status.setText("检测中")
            self.detect_worker = DetectionWorker(self.config(), self.detect_stop)
            self.detect_worker.result_payload.connect(self.handle_result)
            self.detect_worker.finished_with_results.connect(self.apply_detect_done)
            self.detect_worker.failed.connect(self.apply_detect_error)
            self.detect_worker.start()

        def apply_detect_done(self, results):
            self.detect_log.append("检测任务结束。")
            self.app.status.setText("检测结束")
            self.detect_worker = None
            self.is_detecting = False
            self.start_det_btn.setEnabled(True)

        def apply_detect_error(self, message):
            self.detect_log.append(message)
            self.app.status.setText("检测异常")
            self.detect_worker = None
            self.is_detecting = False
            self.start_det_btn.setEnabled(True)

        def stop_detection(self):
            self.detect_stop.set()
            self.detect_log.append("已请求停止检测。")

        def handle_result(self, payload):
            self.detect_results.append(payload)
            self.detect_index = len(self.detect_results) - 1
            # Task 14: For batch, always show the first image
            if len(self.detect_results) == 1:
                self.show_detection_payload(payload)
            else:
                # Just update counter and log, don't switch view
                self.counter.setText(f"{self.detect_index + 1}/{len(self.detect_results)}")
                self.detect_log.append(f"{payload.get('status')} | 结果: {len(payload['items'])} 个")

        def show_detection_payload(self, payload):
            self.source_view.set_pil_image(payload["source_image"])
            self.result_view.set_pil_image(payload["result_image"])
            self.table.setRowCount(len(payload["items"]))
            for row, item in enumerate(payload["items"]):
                values = [row + 1, item.label, f"{item.confidence:.3f}", f"({item.center_x:.1f}, {item.center_y:.1f})", f"{item.width:.1f}×{item.height:.1f}", f"{item.angle:.1f}"]
                for column, value in enumerate(values):
                    self.table.setItem(row, column, QTableWidgetItem(str(value)))
            self.counter.setText(f"{self.detect_index + 1}/{len(self.detect_results)}")
            elapsed = payload.get("elapsed", 0.0)
            fps = (1 / elapsed) if elapsed else 0
            self.detect_log.append(f"{payload.get('status')} | 单张耗时: {elapsed * 1000:.1f}ms | FPS: {fps:.1f} | 结果: {len(payload['items'])} 个")

        def first_result(self):
            if not self.detect_results:
                return
            self.detect_index = 0
            self.show_detection_payload(self.detect_results[0])

        def last_result(self):
            if not self.detect_results:
                return
            self.detect_index = len(self.detect_results) - 1
            self.show_detection_payload(self.detect_results[-1])

        def prev_result(self):
            if not self.detect_results:
                return
            self.detect_index = (self.detect_index - 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def next_result(self):
            if not self.detect_results:
                return
            self.detect_index = (self.detect_index + 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def save_current_result(self):
            if not self.detect_results or self.detect_index < 0:
                return
            payload = self.detect_results[self.detect_index]
            save_dir = Path(self.app.settings["validation"]["save_dir"])
            save_dir.mkdir(parents=True, exist_ok=True)
            filename = f"gui_result_{self.detect_index + 1:04d}.png"
            payload["result_image"].save(save_dir / filename)
            self.detect_log.append(f"已保存结果: {save_dir / filename}")

        def clear_results(self):
            self.detect_results.clear()
            self.detect_index = -1
            self.counter.setText("0/0")
            self.source_view.clear()
            self.source_view.setText("源图")
            self.result_view.clear()
            self.result_view.setText("检测结果图")
            self.table.setRowCount(0)
            self.detect_log.append("已清空检测结果。")

    # ===================================================================
    #  Task 13: Settings page - system info style + auto-refresh
    #  Task 10: Custom command toggle
    # ===================================================================
    class SettingsPage(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self._refresh_count = 0
            layout = self.page_layout()
            title = QLabel("系统设置")
            title.setObjectName("pageTitle")
            layout.addWidget(title)

            # Task 10: Custom command dialog toggle
            feat_row = QHBoxLayout()
            feat_label = QLabel("训练前显示自定义命令框")
            feat_label.setObjectName("inlineFieldLabel")
            self.cmd_dialog_check = QCheckBox()
            self.cmd_dialog_check.setChecked(self.app.settings.get("features", {}).get("custom_command_dialog", True))
            self.cmd_dialog_check.stateChanged.connect(self._toggle_custom_cmd)
            feat_row.addWidget(feat_label)
            feat_row.addWidget(self.cmd_dialog_check)
            feat_row.addStretch(1)
            layout.addLayout(feat_row)

            # Task 13: System info - white outer card, gray inner cards
            info_outer = QFrame()
            info_outer.setObjectName("systemInfoOuter")
            info_outer_layout = QGridLayout(info_outer)
            info_outer_layout.setContentsMargins(0, 0, 0, 0)
            info_outer_layout.setSpacing(0)
            info_grid = QGridLayout()
            info_grid.setContentsMargins(12, 12, 12, 12)
            info_grid.setSpacing(8)
            self.status_cards = {}
            for index, label in enumerate(["Pixi", "Torch/CUDA", "GPU", "显存", "CPU", "内存", "磁盘", "模块"]):
                inner = QFrame()
                inner.setObjectName("systemInfoInner")
                inner_layout = QVBoxLayout(inner)
                inner_layout.setContentsMargins(10, 8, 10, 8)
                lbl = QLabel(label)
                lbl.setObjectName("fieldLabel")
                value = QLabel("待检测")
                value.setObjectName("metricValue")
                value.setWordWrap(True)
                inner_layout.addWidget(lbl)
                inner_layout.addWidget(value)
                self.status_cards[label] = value
                info_grid.addWidget(inner, index // 4, index % 4)
            info_outer_layout.addLayout(info_grid)
            layout.addWidget(info_outer)

            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

            # Task 13: Auto-refresh timer every 0.5s
            self._auto_refresh_timer = QTimer(self)
            self._auto_refresh_timer.timeout.connect(self._auto_refresh)
            self._auto_refresh_timer.start(500)

        def _toggle_custom_cmd(self, state):
            self.app.settings.setdefault("features", {})["custom_command_dialog"] = state == Qt.CheckState.Checked.value
            self.app.settings_service.save(self.app.settings)

        def _auto_refresh(self):
            self._refresh_count += 1
            self.app.run_background("env_auto", lambda: {
                "pixi": pixi_available(),
                "modules": detect_modules(),
                "cuda": torch_cuda_summary(),
                "status": system_status(),
                "settings": self.app.settings,
            })

        def on_show(self):
            for label in self.status_cards:
                self.set_status_card(label, "检测中...")
            self.log.setPlainText("正在后台检测环境...")
            self.app.run_background(
                "env",
                lambda: {
                    "pixi": pixi_available(),
                    "modules": detect_modules(),
                    "cuda": torch_cuda_summary(),
                    "status": system_status(),
                    "settings": self.app.settings,
                },
            )

        def set_status_card(self, label: str, value: str):
            self.status_cards[label].setText(value)

        def apply_env(self, payload):
            self._apply_env_data(payload)
            self.log.setPlainText("当前设置:\n" + json.dumps(payload["settings"], ensure_ascii=False, indent=2))

        def apply_env_auto(self, payload):
            self._apply_env_data(payload)

        def _apply_env_data(self, payload):
            cuda = payload["cuda"]
            status = payload["status"]
            modules = payload["modules"]
            module_summary = " / ".join(f"{name}:{'ok' if ok else '缺失'}" for name, ok in modules.items())
            self.set_status_card("Pixi", "可用" if payload["pixi"] else "不可用")
            self.set_status_card("Torch/CUDA", f"{cuda.get('torch', '未知')} / CUDA {cuda.get('cuda', '未知')}")
            self.set_status_card("GPU", self.short_gpu_name(status.get("gpu") or cuda.get("gpu", "待检测")))
            self.set_status_card("显存", status.get("vram", "待检测"))
            self.set_status_card("CPU", status.get("cpu", "待检测"))
            self.set_status_card("内存", status.get("memory", "待检测"))
            self.set_status_card("磁盘", status.get("disk", "待检测"))
            self.set_status_card("模块", module_summary)

    # ===================================================================
    #  QSS Styles
    # ===================================================================
    STYLE = """
    QWidget { font-family: "Microsoft YaHei UI"; font-size: 14px; color: #14233A; }
    #nav { background: #26394D; }
    #brand { color: white; font-size: 24px; font-weight: 700; }
    #navButton { color: white; background: transparent; border: 0; padding: 10px 14px; font-weight: 700; }
    #navButton:checked, #navButton:hover { background: #344D66; border-radius: 6px; }
    #dataSidebar { background: #26394D; border-radius: 8px; }
    #sideTitle { color: white; font-size: 18px; font-weight: 700; padding: 8px; }
    #dataNavButton { color: white; background: transparent; border: 0; padding: 10px 14px; text-align: left; }
    #dataNavButton:checked, #dataNavButton:hover { background: #344D66; border-radius: 6px; }
    #stack { background: #EEF2F6; }
    #status { background: #F7FAFC; color: #627286; }
    #card { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
    #pageTitle { color: #1A3857; font-size: 28px; font-weight: 700; }
    #sectionTitle { color: #18344F; font-size: 18px; font-weight: 700; }
    #metricValue { color: #0D2B49; font-size: 16px; font-weight: 700; }
    #statValue { color: #0D2B49; font-size: 14px; font-weight: 700; }
    #fieldLabel { color: #627286; font-size: 12px; }
    #inlineFieldLabel { color: #14233A; font-size: 14px; font-weight: 600; }
    #imageView { background: #F8FBFD; border: 1px solid #D9E3EC; border-radius: 6px; color: #627286; }
    #statCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
    #metricCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
    #chartView { background: white; border: 1px solid #D9E3EC; border-radius: 6px; }
    #systemInfoOuter { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
    #systemInfoInner { background: #F0F2F5; border: 1px solid #E0E3E8; border-radius: 6px; }
    QLineEdit, QTextEdit, QComboBox, QTableWidget { background: white; border: 1px solid #CFD9E3; border-radius: 5px; padding: 7px; }
    QPushButton { background: #208FD4; color: white; border: 0; border-radius: 5px; padding: 9px 14px; }
    QPushButton:hover { background: #1A7ABF; }
    QPushButton#softButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; }
    QPushButton#softButton:hover { background: #E8EDF2; border-color: #B8C4D0; }
    QPushButton:disabled { background: #C0CCD8; color: #8899AA; }
    QTabWidget::pane { border: 1px solid #D9E3EC; background: white; border-radius: 6px; }
    QTabBar::tab { padding: 9px 16px; background: #F5F8FB; border: 1px solid #D9E3EC; }
    QTabBar::tab:selected { background: white; color: #208FD4; }
    QTableWidget::item:hover { background: #EBF2F8; }
    QHeaderView::section { background: #F5F8FB; border: 1px solid #D9E3EC; padding: 6px; font-weight: 600; }
    """

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())

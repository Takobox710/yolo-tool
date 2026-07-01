from __future__ import annotations

import json
import os
import re
import sys
import threading
import traceback
from pathlib import Path
from queue import Queue

from PIL import Image

from scr.yolo_workbench.services.annotation_service import (
    load_yolo_annotations,
    render_annotation_preview,
)
from scr.yolo_workbench.services.conversion_service import (
    ConversionConfig,
    format_conversion_result,
    preview_conversion,
    run_conversion,
)
from scr.yolo_workbench.services.detection_service import (
    collect_prediction_sources,
    run_prediction,
    scan_candidate_models,
)
from scr.yolo_workbench.services.environment_service import (
    detect_modules,
    pixi_available,
    system_status,
    torch_cuda_summary,
)
from scr.yolo_workbench.services.rename_service import (
    execute_rename,
    natural_sort_key,
    preview_rename,
)
from scr.yolo_workbench.services.resize_service import (
    ResizeConfig,
    preview_resize,
    run_resize,
)
from scr.yolo_workbench.services.runtime_service import (
    spawn_logged_process,
    stop_process,
)
from scr.yolo_workbench.services.settings_service import ROOT, SettingsService
from scr.yolo_workbench.services.training_service import (
    build_train_command,
    infer_task_mode_from_model,
    read_train_metrics,
    read_results_csv_for_curves,
)
from scr.yolo_workbench_qt.home_charts import (
    DatasetDistributionWidget,
    TrainingCurveWidget,
)

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


# --- Task 3: path helpers ---
def _resolve_project_path(path_str: str, project_root: str | Path = ROOT) -> str:
    """Resolve user-entered relative or absolute path text against project root."""
    text = str(path_str or "").strip().strip('"')
    if not text:
        return ""
    root = Path(project_root).expanduser().resolve()
    path = Path(os.path.expandvars(text)).expanduser()
    if path.is_absolute():
        return str(path.resolve())
    return str((root / path).resolve())


def _display_project_path(path_str: str, project_root: str | Path = ROOT) -> str:
    """Display project-local paths as relative and external paths as absolute."""
    if not path_str:
        return ""
    root = Path(project_root).expanduser().resolve()
    resolved = Path(_resolve_project_path(path_str, root))
    try:
        common = os.path.commonpath([str(root), str(resolved)])
    except ValueError:
        return str(resolved)
    if os.path.normcase(common) == os.path.normcase(str(root)):
        return os.path.relpath(str(resolved), str(root))
    return str(resolved)


def _relative_path(path_str: str, project_root: str | Path = ROOT) -> str:
    """Return a display-friendly relative path from the project root."""
    return _display_project_path(path_str, project_root)


def _simplified_model_path(path_str: str) -> str:
    """Simplify result\\train-12\\weights\\best.pt -> train-12\\best.pt"""
    rel = _relative_path(path_str)
    parts = Path(rel).parts
    if (
        len(parts) >= 3
        and parts[0].lower() == "result"
        and parts[-2].lower() == "weights"
    ):
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
    """Find .pt files in project root and data/models/ directory."""
    names: list[str] = []
    for f in sorted(project_root.glob("*.pt")):
        if f.is_file():
            names.append(f.name)
    models_dir = project_root / "data" / "models"
    if models_dir.exists():
        for f in sorted(models_dir.glob("*.pt")):
            if f.is_file() and f.name not in names:
                names.append(f.name)
    return names


def _home_column_widths(
    total_width: int, margins: int = 32, spacing: int = 12
) -> tuple[int, int]:
    content_width = max(int(total_width) - margins - spacing, 3)
    left = content_width * 3 // 10
    right = content_width - left
    return left, right


def _history_model_sort_key(train_id: str, model_name: str) -> float:
    match = re.fullmatch(r"train(?:-(\d+))?", str(train_id).strip())
    run_number = int(match.group(1) or 1) if match else 0
    model_priority = 1 if str(model_name).lower() == "best.pt" else 0
    return float(-(run_number * 10 + model_priority))


def _parse_padding_text(text: str) -> int:
    value = str(text or "").strip()
    return int(value) if value else 0


def _is_live_source_mode(source_mode: str) -> bool:
    return str(source_mode).strip() == "摄像头"


def _should_store_detection_history(source_mode: str) -> bool:
    return not _is_live_source_mode(source_mode)


def _detection_counter_text(
    source_mode: str, detect_index: int, result_count: int
) -> str:
    if _is_live_source_mode(source_mode):
        return "实时预览"
    if result_count <= 0 or detect_index < 0:
        return "0/0"
    return f"{detect_index + 1}/{result_count}"


def _build_detection_log_message(payload: dict) -> str:
    elapsed = float(payload.get("elapsed") or 0.0)
    fps = payload.get("fps")
    if fps is None:
        fps = (1 / elapsed) if elapsed else 0.0
    fps_text = (
        f"实时帧率 FPS: {fps:.1f}" if payload.get("stream_mode") else f"FPS: {fps:.1f}"
    )
    return f"{payload.get('status')} | 单张耗时: {elapsed * 1000:.1f}ms | {fps_text} | 结果: {len(payload.get('items') or [])} 个"


# ---------------------------------------------------------------------------
def run_app() -> None:
    try:
        from PySide6.QtCore import Qt, QThread, QTimer, Signal
        from PySide6.QtGui import QFont, QImage, QPixmap, QIcon
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
            QListWidget,
            QListWidgetItem,
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
        raise SystemExit(
            f"缺少 Qt 依赖：{exc.name}。请先执行 pixi install 后运行 pixi run app。"
        ) from exc

    IMAGE_SUFFIXES = _IMAGE_SUFFIXES

    def pil_to_pixmap(image: Image.Image) -> QPixmap:
        rgba = image.convert("RGBA")
        data = rgba.tobytes("raw", "RGBA")
        qimage = QImage(
            data, rgba.width, rgba.height, rgba.width * 4, QImage.Format.Format_RGBA8888
        )
        return QPixmap.fromImage(qimage.copy())

    # --- Task 1: helper to load nav icon ---
    def _load_nav_icon() -> QPixmap | None:
        icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
        if icon_path.exists():
            pix = QPixmap(str(icon_path))
            if not pix.isNull():
                return pix.scaled(
                    28,
                    28,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
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
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
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
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
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

    def _history_number_sort_key(value: object) -> float:
        try:
            return float(str(value).strip().replace("%", ""))
        except (ValueError, TypeError):
            return 0.0

    def _history_time_sort_key(value: object) -> float:
        text = str(value).strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            pass
        match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text)
        if not match:
            return 0.0
        hours, minutes, seconds = (int(part or 0) for part in match.groups())
        return float(hours * 3600 + minutes * 60 + seconds)

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
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
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
            self.settings.setdefault("features", {}).setdefault(
                "custom_command_dialog", True
            )
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
            self.setMinimumSize(980, 720)
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
                button.clicked.connect(
                    lambda _checked=False, page=key: self.show_page(page)
                )
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
            self.show_page("home")

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
                QTimer.singleShot(0, hook)

        def create_page(self, key: str):
            if key == "home":
                return scroll_page(HomePage(self))
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
            worker.finished.connect(
                lambda w=worker: self.workers.remove(w) if w in self.workers else None
            )
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

        def project_root(self) -> Path:
            return Path(self.app.settings["project"]["root"])

        def display_path(self, path: str | Path) -> str:
            return _display_project_path(str(path), self.project_root())

        def resolve_path_text(self, edit: QLineEdit) -> str:
            return _resolve_project_path(edit.text(), self.project_root())

        def path_from_edit(self, edit: QLineEdit) -> Path:
            return Path(self.resolve_path_text(edit))

        def page_layout(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(14)
            return layout

        def field(
            self, label: str, value: str = "", browse=None, placeholder: str = ""
        ):
            box = QWidget()
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("fieldLabel")
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(str(value))
            if placeholder:
                edit.setPlaceholderText(placeholder)
            row.addWidget(edit, 1)
            if browse:
                button = QPushButton("选择")
                button.setObjectName("softButton")
                button.clicked.connect(lambda: browse(edit))
                row.addWidget(button)
            layout.addWidget(caption)
            layout.addLayout(row)
            return box, edit

        def path_field(
            self, label: str, value: str = "", browse=None, placeholder: str = ""
        ):
            return self.field(label, self.display_path(value), browse, placeholder)

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

        def inline_field(
            self, label: str, value: str = "", browse=None, placeholder: str = ""
        ):
            box = QWidget()
            layout = QHBoxLayout(box)
            layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setObjectName("inlineFieldLabel")
            caption.setFixedWidth(88)
            edit = QLineEdit(str(value))
            if placeholder:
                edit.setPlaceholderText(placeholder)
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

        def stacked_field(
            self, label: str, value: str = "", browse=None, placeholder: str = ""
        ):
            """Label on top, input + optional browse button below."""
            box = QWidget()
            outer = QVBoxLayout(box)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(4)
            lbl = QLabel(label)
            lbl.setObjectName("fieldLabel")
            outer.addWidget(lbl)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(str(value))
            if placeholder:
                edit.setPlaceholderText(placeholder)
            row.addWidget(edit, 1)
            if browse:
                btn = QPushButton("选择")
                btn.setObjectName("softButton")
                btn.clicked.connect(lambda: browse(edit))
                row.addWidget(btn)
            outer.addLayout(row)
            return box, edit

        def stacked_path_field(
            self, label: str, value: str = "", browse=None, placeholder: str = ""
        ):
            return self.stacked_field(
                label, self.display_path(value), browse, placeholder
            )

        def stacked_combo_field(
            self,
            label: str,
            value: str,
            values: list[str],
            browse=None,
            placeholder: str = "",
        ):
            """Label on top, combo + optional browse button below."""
            box = QWidget()
            outer = QVBoxLayout(box)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(4)
            lbl = QLabel(label)
            lbl.setObjectName("fieldLabel")
            outer.addWidget(lbl)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(values)
            if placeholder and combo.lineEdit():
                combo.lineEdit().setPlaceholderText(placeholder)
            if value in values:
                combo.setCurrentText(value)
            row.addWidget(combo, 1)
            if browse:
                btn = QPushButton("选择")
                btn.setObjectName("softButton")
                btn.clicked.connect(lambda: browse(combo))
                row.addWidget(btn)
            outer.addLayout(row)
            return box, combo

        def choose_dir(self, edit: QLineEdit):
            current = (
                self.resolve_path_text(edit)
                if edit.text()
                else str(self.project_root())
            )
            path = QFileDialog.getExistingDirectory(self, "选择文件夹", current)
            if path:
                edit.setText(self.display_path(path))

        def choose_file(self, edit: QLineEdit, caption: str = "选择文件"):
            current = (
                self.resolve_path_text(edit)
                if edit.text()
                else str(self.project_root())
            )
            path, _ = QFileDialog.getOpenFileName(
                self, caption, current, "All Files (*)"
            )
            if path:
                edit.setText(self.display_path(path))

        def _choose_pt_for_combo(self, combo: QComboBox):
            path, _ = QFileDialog.getOpenFileName(
                self, "选择模型文件", str(ROOT), "PyTorch 模型 (*.pt);;所有文件 (*)"
            )
            if path:
                combo.setCurrentText(self.display_path(path))

        def stat_card(self, label: str, value: str = "-"):
            card = QFrame()
            card.setObjectName("statCard")
            layout = QHBoxLayout(card)
            layout.setContentsMargins(12, 8, 12, 8)
            layout.setSpacing(8)
            name = QLabel(label)
            name.setObjectName("fieldLabel")
            name.setFixedWidth(90)
            metric = QLabel(value)
            metric.setObjectName("statValue")
            metric.setWordWrap(False)
            metric.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            metric.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
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
            cleaned = (
                str(name or "")
                .replace("NVIDIA GeForce ", "")
                .replace("NVIDIA ", "")
                .replace(" Laptop GPU", "")
            )
            cleaned = cleaned.replace("RTX", "RTX ").replace("  ", " ").strip()
            return cleaned or "待检测"

    class PageScrollArea(QScrollArea):
        def resizeEvent(self, event):
            super().resizeEvent(event)
            if hasattr(self, "inner_page"):
                self.inner_page.setMaximumWidth(self.viewport().width())
                relayout = getattr(self.inner_page, "_apply_home_column_widths", None)
                if relayout:
                    relayout()

    def scroll_page(widget: QWidget):
        scroll = PageScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.inner_page = widget
        widget.setMaximumWidth(scroll.viewport().width())
        return scroll

    # ===================================================================
    #  Task 5: Home page with 2x2 grid (1:2 cols, 58:42 rows)
    # ===================================================================
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
            open_button.setFixedWidth(120)
            open_button.setFixedHeight(32)
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
                card.setMinimumWidth(0)
                card.setMaximumWidth(left_width)
                card.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
            for card in self._home_right_cards:
                card.setMinimumWidth(0)
                card.setMaximumWidth(right_width)
                card.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
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
                len([p for p in images.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES])
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
                            if p.suffix.lower() in IMAGE_SUFFIXES
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
            for key, label in [
                ("convert", "标注转换"),
                ("preview", "标注预览"),
                ("rename", "批量重命名"),
                ("resize", "图片压缩"),
            ]:
                button = QPushButton(label)
                button.setObjectName("dataNavButton")
                button.setCheckable(True)
                button.clicked.connect(
                    lambda _checked=False, name=key: self.show_tool(name)
                )
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
            layout.setSpacing(12)
            paths = app.settings["paths"]
            dataset = app.settings["dataset"]

            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.setSpacing(16)

            left_card = Card("数据集与转换配置")
            left_grid = QGridLayout()
            left_grid.setHorizontalSpacing(12)
            left_grid.setVerticalSpacing(10)
            self.images_box, self.images_edit = self.path_field(
                "图片目录", paths["images_dir"], self.choose_dir
            )
            self.annotations_box, self.annotations_edit = self.path_field(
                "Labelme 标注目录", paths["annotations_dir"], self.choose_dir
            )
            self.yolo_labels_box, self.yolo_labels_edit = self.path_field(
                "YOLO 标注目录", paths["labels_dir"], self.choose_dir
            )
            self.output_box, self.output_edit = self.path_field(
                "输出目录", paths["dataset_dir"], self.choose_dir
            )
            left_grid.addWidget(self.images_box, 0, 0)
            left_grid.addWidget(self.annotations_box, 0, 1)
            left_grid.addWidget(self.yolo_labels_box, 1, 0)
            left_grid.addWidget(self.output_box, 1, 1)
            left_card.layout.addLayout(left_grid)
            self.labelme_check = QCheckBox("Labelme 转 YOLO (?)")
            self.labelme_check.setToolTip(
                "开启时自动识别 Labelme 类别并转换为 YOLO；关闭时只对已有 YOLO txt 标注重新分组。"
            )
            self.labelme_check.setChecked(True)
            self.labelme_check.stateChanged.connect(self.refresh_mode_state)
            left_card.layout.addWidget(self.labelme_check)

            right_card = Card("转换参数")
            param_grid = QGridLayout()
            param_grid.setHorizontalSpacing(12)
            param_grid.setVerticalSpacing(10)
            self.task_box, self.task_combo = self.hint_combo_field(
                "任务类型",
                app.settings["task"]["mode"],
                ["obb", "detect"],
                "OBB 输出旋转框标签；detect 输出普通矩形框标签。",
            )
            ratios = dataset["split_ratios"]
            self.train_ratio_box, self.train_ratio_edit = self.hint_field(
                "训练",
                str(ratios["train"]),
                "训练集比例，三项合计必须为 1.0。",
                placeholder="0.0 - 1.0",
            )
            self.val_ratio_box, self.val_ratio_edit = self.hint_field(
                "验证",
                str(ratios["val"]),
                "验证集比例，用于训练中评估模型。",
                placeholder="0.0 - 1.0",
            )
            self.test_ratio_box, self.test_ratio_edit = self.hint_field(
                "测试",
                str(ratios["test"]),
                "测试集比例，用于最终检测泛化效果。",
                placeholder="0.0 - 1.0",
            )
            self.seed_box, self.seed_edit = self.hint_field(
                "随机种子",
                str(dataset["random_seed"]),
                "控制随机划分的可复现性；同一数据和种子会得到相同划分。",
            )
            line_box = QWidget()
            line_layout = QVBoxLayout(line_box)
            line_layout.setContentsMargins(0, 0, 0, 0)
            line_layout.setSpacing(4)
            self.line_label = self.hint_label(
                "直线拓展宽度",
                "仅在 OBB + Labelme line 标注时生效，按该半宽把直线扩展成旋转矩形。",
            )
            self.line_label.setObjectName("fieldLabel")
            self.line_edit = QLineEdit(str(dataset["line_to_obb"]["half_width"]))
            self.line_edit.setPlaceholderText("仅 OBB + Labelme line")
            line_layout.addWidget(self.line_label)
            line_layout.addWidget(self.line_edit)
            param_grid.addWidget(self.task_box, 0, 0)
            param_grid.addWidget(self.train_ratio_box, 0, 1)
            param_grid.addWidget(self.val_ratio_box, 1, 0)
            param_grid.addWidget(self.test_ratio_box, 1, 1)
            param_grid.addWidget(self.seed_box, 2, 0)
            param_grid.addWidget(line_box, 2, 1)
            right_card.layout.addLayout(param_grid)

            top_row.addWidget(left_card, 3)
            top_row.addWidget(right_card, 2)
            layout.addLayout(top_row)

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
            self.log.setPlaceholderText(
                "预览或执行后将在这里显示数据集划分、类别统计、跳过标签与输出路径。"
            )
            layout.addWidget(self.log, 1)
            self.task_combo.currentTextChanged.connect(self.refresh_mode_state)
            self.refresh_mode_state()

        def _section_card(self, title: str, content_layout):
            card = Card(title)
            card.layout.addLayout(content_layout)
            return card

        def hint_label(self, text: str, tooltip: str):
            label = QLabel(f"{text} (?)")
            label.setToolTip(tooltip)
            return label

        def hint_field(
            self, label: str, value: str, tooltip: str, placeholder: str = ""
        ):
            box = QWidget()
            field_layout = QVBoxLayout(box)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(4)
            caption = self.hint_label(label, tooltip)
            caption.setObjectName("fieldLabel")
            edit = QLineEdit(str(value))
            if placeholder:
                edit.setPlaceholderText(placeholder)
            field_layout.addWidget(caption)
            field_layout.addWidget(edit)
            return box, edit

        def hint_combo_field(
            self, label: str, value: str, values: list[str], tooltip: str
        ):
            box = QWidget()
            field_layout = QVBoxLayout(box)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(4)
            caption = self.hint_label(label, tooltip)
            caption.setObjectName("fieldLabel")
            combo = QComboBox()
            combo.addItems(values)
            if value in values:
                combo.setCurrentText(value)
            field_layout.addWidget(caption)
            field_layout.addWidget(combo)
            return box, combo

        def refresh_mode_state(self):
            labelme_enabled = self.labelme_check.isChecked()
            self.annotations_box.setEnabled(labelme_enabled)
            self.yolo_labels_box.setEnabled(not labelme_enabled)
            enabled = labelme_enabled and self.task_combo.currentText() == "obb"
            for widget in (self.line_label, self.line_edit):
                widget.setEnabled(enabled)

        def ratios(self) -> tuple[float, float, float]:
            return (
                float(self.train_ratio_edit.text().strip()),
                float(self.val_ratio_edit.text().strip()),
                float(self.test_ratio_edit.text().strip()),
            )

        def config(self):
            train, val, test = self.ratios()
            return ConversionConfig(
                task_mode=self.task_combo.currentText(),
                images_dir=self.path_from_edit(self.images_edit),
                annotations_dir=self.path_from_edit(
                    self.annotations_edit
                    if self.labelme_check.isChecked()
                    else self.yolo_labels_edit
                ),
                output_dir=self.path_from_edit(self.output_edit),
                labels_dir=Path(self.app.settings["paths"]["labels_dir"]),
                class_names=[],
                source_format="labelme" if self.labelme_check.isChecked() else "yolo",
                train_ratio=train,
                val_ratio=val,
                test_ratio=test,
                line_to_obb=self.labelme_check.isChecked()
                and self.task_combo.currentText() == "obb",
                line_half_width=float(self.line_edit.text()),
            )

        def preview(self):
            try:
                config = self.config()
                result = preview_conversion(config)
                preview_result = type(
                    "PreviewReport",
                    (),
                    {
                        "labeled_train_count": result.planned_splits.get("train", 0),
                        "labeled_val_count": result.planned_splits.get("val", 0),
                        "labeled_test_count": result.planned_splits.get("test", 0),
                        "total_boxes": 0,
                        "unlabeled_count": result.unlabeled_count,
                        "yaml_path": result.output_dir / "data.yaml",
                        "labels_dir": result.labels_dir,
                        "missing_labels": {},
                        "stats": {"train": {}, "val": {}, "test": {}},
                        "class_names": [],
                    },
                )()
                self.log.setPlainText(
                    format_conversion_result(preview_result, config, preview=True)
                )
            except Exception as exc:
                self.log.setPlainText(str(exc))

        def run(self):
            try:
                config = self.config()
                result = run_conversion(config)
                self.log.setPlainText(format_conversion_result(result, config))
            except Exception:
                self.log.setPlainText(traceback.format_exc())

    class PreviewTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            self.preview_items: list[Path] = []
            self.preview_index = 0
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            grid = QGridLayout()
            self.image_box, self.image_edit = self.path_field(
                "图片文件夹", app.settings["paths"]["images_dir"], self.choose_dir
            )
            self.label_box, self.label_edit = self.path_field(
                "标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir
            )
            grid.addWidget(self.image_box, 0, 0)
            grid.addWidget(self.label_box, 0, 1)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            for text, slot in [
                ("扫描", self.load_preview_items),
                ("上一张", self.prev_image),
                ("下一张", self.next_image),
                ("列表", self.show_preview_list),
            ]:
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
            image_dir = self.path_from_edit(self.image_edit)
            self.preview_items = (
                sorted(
                    (
                        path
                        for path in image_dir.iterdir()
                        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
                    ),
                    key=natural_sort_key,
                )
                if image_dir.exists()
                else []
            )
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

        def show_preview_index(self, index: int):
            if not self.preview_items:
                self.load_preview_items()
                return
            self.preview_index = index % len(self.preview_items)
            self.render_current()

        def show_preview_list(self):
            if not self.preview_items:
                self.load_preview_items()
            if not self.preview_items:
                QMessageBox.information(
                    self, "图片列表", "当前图片文件夹没有可预览的图片。"
                )
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("图片列表")
            dialog.resize(320, 520)
            dialog.setMinimumSize(200, 200)
            layout = QVBoxLayout(dialog)
            listing = QListWidget()
            layout.addWidget(listing, 1)
            search = QLineEdit()
            search.setPlaceholderText("搜索文件名")
            layout.addWidget(search)
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            layout.addWidget(buttons)
            visible_paths: list[Path] = []

            def filter_items(text: str = ""):
                nonlocal visible_paths
                needle = text.strip().lower()
                visible_paths = [
                    path
                    for path in self.preview_items
                    if not needle or needle in path.name.lower()
                ]
                listing.clear()
                for path in visible_paths:
                    listing.addItem(path.name)
                if visible_paths:
                    current_path = (
                        self.preview_items[self.preview_index]
                        if 0 <= self.preview_index < len(self.preview_items)
                        else visible_paths[0]
                    )
                    current_row = (
                        visible_paths.index(current_path)
                        if current_path in visible_paths
                        else 0
                    )
                    listing.setCurrentRow(current_row)

            def jump_to_current():
                row = listing.currentRow()
                if 0 <= row < len(visible_paths):
                    self.preview_index = self.preview_items.index(visible_paths[row])
                    self.render_current()
                    dialog.accept()

            filter_items()
            search.textChanged.connect(filter_items)
            listing.itemDoubleClicked.connect(lambda _item: jump_to_current())
            buttons.accepted.connect(jump_to_current)
            buttons.rejected.connect(dialog.reject)
            dialog.exec()

        def render_current(self):
            if not self.preview_items:
                self.current_label.setText("未找到图片")
                return
            image_path = self.preview_items[self.preview_index]
            label_path = self.path_from_edit(self.label_edit) / f"{image_path.stem}.txt"
            self.current_label.setText(
                f"{self.preview_index + 1}/{len(self.preview_items)}  {image_path.name}"
            )
            image = Image.open(image_path).convert("RGB")
            annotations = load_yolo_annotations(
                image.size,
                label_path,
                self.app.settings["task"]["mode"],
                self.app.settings["dataset"]["class_names"],
            )
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
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(10)
            self.folder_box, self.folder_edit = self.path_field(
                "图片文件夹", app.settings["paths"]["images_dir"], self.choose_dir
            )
            self.labelme_box, self.labelme_edit = self.path_field(
                "Labelme 标注文件夹",
                app.settings["paths"]["annotations_dir"],
                self.choose_dir,
            )
            self.yolo_box, self.yolo_edit = self.path_field(
                "YOLO 标注文件夹", app.settings["paths"]["labels_dir"], self.choose_dir
            )
            self.prefix_box, self.prefix_edit = self.field("命名前缀", "A")
            self.start_box, self.start_edit = self.field("起始编号", "1")
            self.padding_box, self.padding_combo = self.combo_field(
                "编号位数", "1", ["1", "2", "3", "4"]
            )
            for index, widget in enumerate(
                [
                    self.folder_box,
                    self.labelme_box,
                    self.yolo_box,
                    self.prefix_box,
                    self.start_box,
                    self.padding_box,
                ]
            ):
                grid.addWidget(widget, index // 3, index % 3)
            self.include_labelme = QCheckBox("Labelme 标注文件一并更改")
            self.include_labelme.setChecked(False)
            self.include_yolo = QCheckBox("YOLO 标注文件一并更改")
            self.include_yolo.setChecked(False)
            grid.addWidget(self.include_labelme, 2, 0)
            grid.addWidget(self.include_yolo, 2, 1)
            layout.addLayout(grid)
            actions = QHBoxLayout()
            run_button = QPushButton("执行重命名")
            run_button.clicked.connect(self.run)
            actions.addWidget(run_button)
            actions.addStretch(1)
            layout.addLayout(actions)
            self.table = QTableWidget(0, 3)
            self.table.setHorizontalHeaderLabels(
                ["图片文件状态", "Labelme 标注状态", "YOLO 标注状态"]
            )
            self.table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            layout.addWidget(self.table, 1)
            for edit in [
                self.folder_edit,
                self.labelme_edit,
                self.yolo_edit,
                self.prefix_edit,
                self.start_edit,
            ]:
                edit.textChanged.connect(lambda _text: self.preview())
            self.padding_combo.currentTextChanged.connect(lambda _text: self.preview())
            self.include_labelme.stateChanged.connect(lambda _state: self.preview())
            self.include_yolo.stateChanged.connect(lambda _state: self.preview())
            QTimer.singleShot(100, self.preview)

        def label_status(
            self, source: Path | None, target: Path | None, note: str
        ) -> str:
            if note:
                return note
            if source and target:
                return f"{source.name} -> {target.name}"
            return "不处理"

        def image_status(self, item) -> str:
            if item.conflict:
                return f"目标已存在: {item.new_name}"
            return f"{item.old_name} -> {item.new_name}"

        def preview(self):
            try:
                self.plan = preview_rename(
                    self.path_from_edit(self.folder_edit),
                    self.prefix_edit.text(),
                    int(self.start_edit.text()),
                    _parse_padding_text(self.padding_combo.currentText()),
                    labelme_dir=self.path_from_edit(self.labelme_edit),
                    include_labelme=self.include_labelme.isChecked(),
                    labels_dir=self.path_from_edit(self.yolo_edit),
                    include_labels=self.include_yolo.isChecked(),
                )
            except Exception:
                return
            self.table.setRowCount(len(self.plan))
            for row, item in enumerate(self.plan):
                image_status = self.image_status(item)
                labelme_status = self.label_status(
                    item.labelme_source, item.labelme_target, item.labelme_note
                )
                yolo_status = self.label_status(
                    item.label_source, item.label_target, item.note
                )
                values = [image_status, labelme_status, yolo_status]
                for column, value in enumerate(values):
                    table_item = QTableWidgetItem(str(value))
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, column, table_item)

        def run(self):
            result = execute_rename(self.plan)
            if result.renamed_count == 0 and result.skipped_count:
                QMessageBox.warning(
                    self, "发现冲突", "检测到标注文件目标名称冲突，已取消本次重命名。"
                )
            else:
                QMessageBox.information(
                    self,
                    "重命名完成",
                    f"已重命名图片 {result.renamed_count} 个，Labelme 标注 {result.labelme_renamed_count} 个，YOLO 标注 {result.label_renamed_count} 个。",
                )
            self.preview()

    class ResizeTab(BasePage):
        def __init__(self, app):
            super().__init__(app)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(12, 12, 12, 12)
            resize = app.settings["image_resize"]
            grid = QGridLayout()
            self.source_box, self.source_edit = self.path_field(
                "图片目录", app.settings["paths"]["images_dir"], self.choose_dir
            )
            self.backup_box, self.backup_edit = self.path_field(
                "备份目录", resize["backup_dir"], self.choose_dir
            )
            self.output_box, self.output_edit = self.path_field(
                "输出目录", resize["output_dir"], self.choose_dir
            )
            self.long_box, self.long_edit = self.field(
                "长边缩放", str(resize["long_edge"])
            )
            self.canvas_box, self.canvas_edit = self.field(
                "画布尺寸", str(resize["canvas_size"])
            )
            self.bg_box, self.bg_combo = self.combo_field(
                "背景颜色", resize["background"], ["white", "black"]
            )
            self.output_mode_box, self.output_mode_combo = self.combo_field(
                "输出方式", "输出到新文件夹", ["输出到新文件夹", "覆盖原文件"]
            )
            self.save_format_box, self.save_format_combo = self.combo_field(
                "保存格式", "保持原格式", ["保持原格式", "jpg", "png"]
            )
            for index, widget in enumerate(
                [
                    self.source_box,
                    self.backup_box,
                    self.output_box,
                    self.output_mode_box,
                    self.long_box,
                    self.canvas_box,
                    self.bg_box,
                    self.save_format_box,
                ]
            ):
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
                source_dir=self.path_from_edit(self.source_edit),
                output_dir=self.path_from_edit(self.output_edit),
                backup_dir=self.path_from_edit(self.backup_edit),
                long_edge=int(self.long_edit.text()),
                canvas_size=int(self.canvas_edit.text()),
                background=self.bg_combo.currentText(),
            )

        def preview(self):
            result = preview_resize(self.config())
            self.log.setPlainText(
                f"计划处理 {len(result.items)} 张图片\n输出方式: {self.output_mode_combo.currentText()}\n保存格式: {self.save_format_combo.currentText()}\n"
            )
            for item in result.items[:80]:
                self.log.append(
                    f"{item.source.name}: {item.original_size} -> {item.resized_size}, scale={item.scale:.3f}"
                )

        def run(self):
            result = run_resize(self.config())
            self.log.append(
                f"\n压缩完成: {result.processed_count} 张，输出目录: {result.output_dir}"
            )

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
            self.train_status_timer = QTimer(self)
            self.train_status_timer.timeout.connect(self.refresh_train_status)
            self.train_status_timer.start(500)
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

            # Stacked layout: label on top, input + button below
            left_form = QGridLayout()
            left_form.setContentsMargins(0, 0, 0, 0)
            left_form.setHorizontalSpacing(12)
            left_form.setVerticalSpacing(10)
            left.layout.addLayout(left_form)

            # 基础模型 - stacked combo
            model_files = _find_pt_files_in_data_models(
                Path(self.app.settings["project"]["root"])
            )
            current_pretrained = training.get("pretrained", "")
            current_name = Path(current_pretrained).name if current_pretrained else ""
            base_box, self.pretrained_combo = self.stacked_combo_field(
                "基础模型",
                current_name,
                model_files,
                browse=lambda combo: self._choose_pt_for_combo(combo),
                placeholder="选择或输入 .pt 模型",
            )
            left_form.addWidget(base_box, 0, 0)

            # 数据集YAML
            self.edits["data"], _ = None, None
            data_box, data_edit = self.stacked_path_field(
                "数据集YAML",
                training.get("data", ""),
                self.choose_file,
                "选择 data.yaml",
            )
            self.edits["data"] = data_edit
            left_form.addWidget(data_box, 0, 1)

            # 模型YAML (default blank)
            model_yaml_box, model_yaml_edit = self.stacked_path_field(
                "模型YAML", "", self.choose_file, "可选，留空使用基础模型"
            )
            self.edits["model_yaml"] = model_yaml_edit
            left_form.addWidget(model_yaml_box, 1, 0)

            # 项目输出
            project_box, project_edit = self.stacked_path_field(
                "项目输出",
                training.get("project", ""),
                self.choose_dir,
                "选择训练结果输出目录",
            )
            self.edits["project"] = project_edit
            left_form.addWidget(project_box, 1, 1)

            # Augmentation checkboxes
            aug = QGridLayout()
            left.layout.addLayout(aug)
            for index, (key, label) in enumerate(
                [
                    ("mosaic", "马赛克"),
                    ("scale", "缩放"),
                    ("translate", "平移"),
                    ("hsv_h", "HSV"),
                    ("fliplr", "左右翻转"),
                    ("flipud", "上下翻转"),
                    ("degrees", "旋转"),
                    ("mixup", "MixUp"),
                ]
            ):
                check = QCheckBox(label)
                check.setChecked(float(training.get(key, 0)) > 0)
                self.checks[key] = check
                aug.addWidget(check, index // 4, index % 4)

            # Right side: training params
            params = QGridLayout()
            right.layout.addLayout(params)

            # Row 0: optimizer | lr
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
            params.addWidget(optimizer_box, 0, 0)

            lr_box, lr_edit = self.inline_field("学习率", training.get("lr", ""))
            self.edits["lr"] = lr_edit
            params.addWidget(lr_box, 0, 1)

            # Rows 1-3: remaining params, device last (next to 图片尺寸)
            param_order = [
                ("epochs", "Epochs"),
                ("patience", "Patience"),
                ("workers", "Workers"),
                ("batch", "Batch"),
                ("imgsz", "图片尺寸"),
            ]
            for i, (key, label) in enumerate(param_order):
                box, edit = self.inline_field(label, training.get(key, ""))
                self.edits[key] = edit
                params.addWidget(box, 1 + i // 2, i % 2)

            # Device at row 3 col 1, next to 图片尺寸
            self.device_box, self.device_combo = self.inline_combo_field(
                "设备", str(training.get("device", "0")), ["0", "cpu", "0,1"]
            )
            params.addWidget(self.device_box, 3, 1)
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
            for index, (key, label) in enumerate(
                [
                    ("gpu", "GPU"),
                    ("vram", "显存占用"),
                    ("cpu", "CPU占用"),
                    ("memory", "内存占用"),
                ]
            ):
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
            self.refresh_train_status()

        def refresh_train_status(self):
            self.app.run_background(
                "train_status",
                lambda: {"status": system_status(), "cuda": torch_cuda_summary()},
            )

        def apply_train_status(self, payload):
            status = payload["status"]
            cuda = payload["cuda"]
            self.metric_labels["gpu"].setText(
                f"{self.short_gpu_name(status.get('gpu') or cuda.get('gpu', '待检测'))} · {status.get('gpu_usage', '待检测')}"
            )
            self.metric_labels["vram"].setText(status.get("vram", "待检测"))
            self.metric_labels["cpu"].setText(status.get("cpu", "待检测"))
            self.metric_labels["memory"].setText(status.get("memory", "待检测"))

        def collect_config(self):
            config = {}
            config["data"] = (
                self.resolve_path_text(self.edits["data"]) if self.edits["data"] else ""
            )
            config["model_yaml"] = (
                self.resolve_path_text(self.edits["model_yaml"])
                if self.edits["model_yaml"]
                else ""
            )
            config["project"] = (
                self.resolve_path_text(self.edits["project"])
                if self.edits["project"]
                else ""
            )
            config["lr"] = self.edits["lr"].text() if self.edits.get("lr") else "0.001"
            config["epochs"] = (
                self.edits["epochs"].text() if self.edits.get("epochs") else "800"
            )
            config["patience"] = (
                self.edits["patience"].text() if self.edits.get("patience") else "150"
            )
            config["workers"] = (
                self.edits["workers"].text() if self.edits.get("workers") else "2"
            )
            config["batch"] = (
                self.edits["batch"].text() if self.edits.get("batch") else "16"
            )
            config["imgsz"] = (
                self.edits["imgsz"].text() if self.edits.get("imgsz") else "640"
            )
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
            config["task_mode"] = infer_task_mode_from_model(
                config.get("model_yaml")
                or config.get("base_model")
                or config.get("pretrained")
            )
            for key, check in self.checks.items():
                if key == "hsv_h":
                    continue
                config[key] = (
                    self.app.settings["training"].get(key, 0)
                    if check.isChecked()
                    else 0
                )
            hsv_enabled = self.checks["hsv_h"].isChecked()
            config["hsv_h"] = (
                self.app.settings["training"].get("hsv_h", 0) if hsv_enabled else 0
            )
            config["hsv_s"] = (
                self.app.settings["training"].get("hsv_s", 0) if hsv_enabled else 0
            )
            config["hsv_v"] = (
                self.app.settings["training"].get("hsv_v", 0) if hsv_enabled else 0
            )
            # Resolve pretrained path - check project root then data/models
            pretrained_val = config.get("pretrained", "")
            if pretrained_val and not Path(pretrained_val).exists():
                project_root = Path(self.app.settings["project"]["root"])
                candidate = project_root / pretrained_val
                if candidate.exists():
                    config["pretrained"] = str(candidate)
                else:
                    models_dir = project_root / "data" / "models"
                    candidate = models_dir / pretrained_val
                    if candidate.exists():
                        config["pretrained"] = str(candidate)
            return config

        def refresh_command_preview(self):
            self.log.setPlainText(
                " ".join(build_train_command(self.collect_config()))
                + "\n等待开始训练..."
            )

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
            self.app.training_handle = spawn_logged_process(
                command, str(ROOT), self.log_queue
            )
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
            path = Path(
                self.resolve_path_text(self.edits["project"])
                if self.edits.get("project")
                else self.app.settings["paths"]["result_dir"]
            )
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
            self.is_batch_detection = False
            self._all_model_paths: list[Path] = []
            self.source_items: list[Path] = []
            self.source_index = -1
            self.result_by_source: dict[str, dict] = {}
            self.user_selected_result = False
            self.result_nav_buttons: list[QPushButton] = []
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
            model_box, self.model_combo = self.stacked_combo_field(
                "选择模型",
                "",
                [],
                browse=lambda combo: self._choose_pt_for_combo(combo),
                placeholder="选择或输入模型路径",
            )
            self.model_combo.setMinimumWidth(140)
            left_column.addWidget(model_box)

            conf_row = QHBoxLayout()
            self.conf_box, self.conf_edit = self.field(
                "置信度", str(validation["confidence"])
            )
            self.iou_box, self.iou_edit = self.field("IoU", str(validation["iou"]))
            conf_row.addWidget(self.conf_box)
            conf_row.addWidget(self.iou_box)
            left_column.addLayout(conf_row)

            # Source config
            self.mode_box, self.mode_combo = self.combo_field(
                "检测模式",
                "图片/视频文件夹",
                ["图片/视频文件夹", "图片/视频", "摄像头"],
            )
            left_column.addWidget(self.mode_box)
            self.source_box, self.source_edit = self.path_field(
                "输入源", validation["source_path"], self.choose_detection_source
            )
            left_column.addWidget(self.source_box)
            self.camera_box, self.camera_combo = self.combo_field(
                "摄像头", str(validation["camera_index"]), ["0", "1", "2", "3"]
            )
            left_column.addWidget(self.camera_box)

            # Control
            control_title = QLabel("检测控制")
            control_title.setObjectName("sectionTitle")
            left_column.addWidget(control_title)
            controls = QHBoxLayout()
            self.start_det_btn = QPushButton("批量检测")
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
            split.addWidget(left_shell)

            # Right column
            right = QVBoxLayout()
            toolbar = QHBoxLayout()
            toolbar.addWidget(QLabel("批量检测结果"))
            for text, slot in [
                ("上一张", self.prev_result),
                ("下一张", self.next_result),
                ("第一张", self.first_result),
                ("最后一张", self.last_result),
                ("列表", self.show_result_list),
                ("打开保存文件夹", self.open_detection_save_dir),
            ]:
                button = QPushButton(text)
                button.setObjectName("softButton")
                button.clicked.connect(slot)
                toolbar.addWidget(button)
                if text != "打开保存文件夹":
                    self.result_nav_buttons.append(button)
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
            right.addLayout(views, 2)
            table_panel = Card("检测结果详情表")
            self.table = QTableWidget(0, 5)
            self.table.setHorizontalHeaderLabels(
                ["类别", "置信度", "坐标(x,y)", "尺寸(w×h)", "角度"]
            )
            self.table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            table_panel.layout.addWidget(self.table)
            right.addWidget(table_panel, 1)
            right_widget = QWidget()
            right_widget.setLayout(right)
            split.addWidget(right_widget)
            split.setStretch(0, 2)
            split.setStretch(1, 7)

            self.mode_combo.currentTextChanged.connect(self.update_source_mode)
            self.update_source_mode(self.mode_combo.currentText())
            self.update_detection_button_text()

        def update_source_mode(self, value):
            camera = value == "摄像头"
            self.source_box.setVisible(not camera)
            self.camera_box.setVisible(camera)
            self.set_result_navigation_enabled(not camera)
            if camera:
                self.counter.setText("实时预览")
            elif not self.detect_results:
                self.counter.setText("0/0")
            self.update_detection_button_text()
            self.refresh_source_items()

        def set_result_navigation_enabled(self, enabled: bool):
            for button in self.result_nav_buttons:
                button.setEnabled(enabled)

        def update_detection_button_text(self):
            self.start_det_btn.setText(
                "开始检测"
                if self.mode_combo.currentText() == "图片/视频"
                else "批量检测"
            )

        def choose_detection_source(self, edit: QLineEdit):
            current = (
                self.resolve_path_text(edit)
                if edit.text()
                else str(self.project_root())
            )
            if self.mode_combo.currentText() == "图片/视频":
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    "选择图片或视频",
                    current,
                    "图片/视频 (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov *.mkv);;所有文件 (*)",
                )
                if path:
                    edit.setText(self.display_path(path))
                    self.refresh_source_items()
                return
            self.choose_dir(edit)
            self.refresh_source_items()

        def refresh_source_items(self):
            if self.mode_combo.currentText() == "摄像头":
                self.source_items = []
                self.source_index = -1
                return
            self.source_items = collect_prediction_sources(
                self.mode_combo.currentText(), self.resolve_path_text(self.source_edit)
            )
            if not self.source_items:
                self.source_index = -1
                return
            if self.source_index < 0 or self.source_index >= len(self.source_items):
                self.source_index = 0

        def on_show(self):
            # Scan models and populate dropdown
            result_dir = Path(self.app.settings["paths"]["result_dir"])
            self._all_model_paths = _find_models_full_paths(result_dir)
            display_names = [
                _simplified_model_path(str(m)) for m in self._all_model_paths
            ]
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
                if (
                    _simplified_model_path(str(p)) == text
                    or self.display_path(p) == text
                    or str(p) == text
                ):
                    return str(p)
            # Maybe it's already a full path
            if Path(text).exists():
                return text
            resolved = self.resolve_combo_path_text(text)
            return resolved if resolved else text

        def resolve_combo_path_text(self, text: str) -> str:
            return _resolve_project_path(text, self.project_root())

        def config(self):
            return {
                "model_path": self._get_model_path(),
                "source_mode": self.mode_combo.currentText(),
                "source_path": self.resolve_path_text(self.source_edit),
                "camera_index": int(self.camera_combo.currentText()),
                "confidence": float(self.conf_edit.text()),
                "iou": float(self.iou_edit.text()),
                "save_dir": self.app.settings["validation"]["save_dir"],
            }

        def single_file_config(self, path: Path) -> dict:
            config = self.config()
            config["source_mode"] = "图片/视频"
            config["source_path"] = str(path)
            return config

        # Task 9: Only allow one detection at a time
        def start_detection(self):
            if self.is_detecting:
                return
            self.refresh_source_items()
            if self.mode_combo.currentText() == "图片/视频":
                if not self.source_items:
                    QMessageBox.information(
                        self, "输入源为空", "请选择一张图片或一段视频。"
                    )
                    return
                self.source_index = max(
                    0, min(self.source_index, len(self.source_items) - 1)
                )
                self.start_current_source_detection()
                return
            self.is_detecting = True
            self.start_det_btn.setEnabled(False)
            self.detect_log.clear()
            self.detect_stop.clear()
            self.detect_results.clear()
            self.result_by_source.clear()
            self.user_selected_result = False
            self.is_batch_detection = not _is_live_source_mode(
                self.mode_combo.currentText()
            )
            self.detect_index = -1
            self.counter.setText(
                "实时预览"
                if _is_live_source_mode(self.mode_combo.currentText())
                else "0/0"
            )
            self.table.setRowCount(0)
            self.app.status.setText("检测中")
            self.detect_worker = DetectionWorker(self.config(), self.detect_stop)
            self.detect_worker.result_payload.connect(self.handle_result)
            self.detect_worker.finished_with_results.connect(self.apply_detect_done)
            self.detect_worker.failed.connect(self.apply_detect_error)
            self.detect_worker.start()

        def start_current_source_detection(self):
            if not self.source_items:
                return
            self.source_index = max(
                0, min(self.source_index, len(self.source_items) - 1)
            )
            self.start_single_detection(self.source_items[self.source_index])

        def start_single_detection(self, path: Path):
            if self.is_detecting:
                return
            self.refresh_source_items()
            source_key = str(Path(path).resolve())
            cached = self.result_by_source.get(source_key)
            if cached:
                self.detect_index = (
                    self.detect_results.index(cached)
                    if cached in self.detect_results
                    else self.detect_index
                )
                self.show_detection_payload(cached)
                return
            self.is_detecting = True
            self.is_batch_detection = False
            self.start_det_btn.setEnabled(False)
            self.detect_stop.clear()
            self.app.status.setText("检测中")
            self.detect_worker = DetectionWorker(
                self.single_file_config(path), self.detect_stop
            )
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
            if _is_live_source_mode(self.mode_combo.currentText()):
                self.detect_index = 0
                self.show_detection_payload(payload)
                return
            if not _should_store_detection_history(self.mode_combo.currentText()):
                self.show_detection_payload(payload)
                return
            self.detect_results.append(payload)
            source_path = payload.get("source_path")
            if source_path:
                self.result_by_source[str(Path(source_path).resolve())] = payload
            # Task 14: For batch, always show the first image
            if len(self.detect_results) == 1 or (
                not self.is_batch_detection and not self.user_selected_result
            ):
                self.detect_index = len(self.detect_results) - 1
                self.show_detection_payload(payload)
            else:
                # Just update counter and log, don't switch view
                self.counter.setText(
                    _detection_counter_text(
                        self.mode_combo.currentText(),
                        self.detect_index,
                        len(self.detect_results),
                    )
                )
                self.detect_log.append(_build_detection_log_message(payload))

        def show_detection_payload(self, payload):
            self.source_view.set_pil_image(payload["source_image"])
            self.result_view.set_pil_image(payload["result_image"])
            self.table.setRowCount(len(payload["items"]))
            for row, item in enumerate(payload["items"]):
                values = [
                    item.label,
                    f"{item.confidence:.3f}",
                    f"({item.center_x:.1f}, {item.center_y:.1f})",
                    f"{item.width:.1f}×{item.height:.1f}",
                    f"{item.angle:.1f}",
                ]
                for column, value in enumerate(values):
                    self.table.setItem(row, column, QTableWidgetItem(str(value)))
            self.counter.setText(
                _detection_counter_text(
                    self.mode_combo.currentText(),
                    self.detect_index,
                    len(self.detect_results),
                )
            )
            self.detect_log.append(_build_detection_log_message(payload))

        def first_result(self):
            if not self.detect_results:
                return
            self.user_selected_result = True
            self.detect_index = 0
            self.show_detection_payload(self.detect_results[0])

        def last_result(self):
            if not self.detect_results:
                return
            self.user_selected_result = True
            self.detect_index = len(self.detect_results) - 1
            self.show_detection_payload(self.detect_results[-1])

        def prev_result(self):
            if not self.detect_results:
                return
            self.user_selected_result = True
            self.detect_index = (self.detect_index - 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def next_result(self):
            if not self.detect_results:
                return
            self.user_selected_result = True
            self.detect_index = (self.detect_index + 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def show_source_index(self, index: int):
            self.refresh_source_items()
            if not self.source_items:
                return
            self.source_index = index % len(self.source_items)

        def show_cached_source_result(self, path: Path) -> bool:
            cached = self.result_by_source.get(str(Path(path).resolve()))
            if not cached:
                return False
            self.user_selected_result = True
            self.detect_index = self.detect_results.index(cached)
            self.show_detection_payload(cached)
            return True

        def show_result_list(self):
            self.refresh_source_items()
            if not self.source_items:
                QMessageBox.information(
                    self, "输入源列表", "当前输入源没有可选择的图片或视频。"
                )
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("输入源列表")
            dialog.resize(320, 520)
            dialog.setMinimumSize(200, 200)
            layout = QVBoxLayout(dialog)
            listing = QListWidget()
            layout.addWidget(listing, 1)
            search = QLineEdit()
            search.setPlaceholderText("搜索文件名")
            layout.addWidget(search)
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            layout.addWidget(buttons)
            visible_paths: list[Path] = []

            def filter_items(text: str = ""):
                nonlocal visible_paths
                needle = text.strip().lower()
                visible_paths = [
                    path
                    for path in self.source_items
                    if not needle or needle in path.name.lower()
                ]
                listing.clear()
                for path in visible_paths:
                    listing.addItem(path.name)
                if visible_paths:
                    current_path = (
                        self.source_items[self.source_index]
                        if 0 <= self.source_index < len(self.source_items)
                        else visible_paths[0]
                    )
                    current_row = (
                        visible_paths.index(current_path)
                        if current_path in visible_paths
                        else 0
                    )
                    listing.setCurrentRow(current_row)

            def jump_to_current():
                row = listing.currentRow()
                if 0 <= row < len(visible_paths):
                    path = visible_paths[row]
                    self.source_index = self.source_items.index(path)
                    self.show_cached_source_result(path)
                dialog.accept()

            filter_items()
            search.textChanged.connect(filter_items)
            listing.itemDoubleClicked.connect(lambda _item: jump_to_current())
            buttons.accepted.connect(jump_to_current)
            buttons.rejected.connect(dialog.reject)
            dialog.exec()

        def open_detection_save_dir(self):
            save_dir = Path(self.app.settings["validation"]["save_dir"])
            save_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(save_dir)

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
            self.cmd_dialog_check.setChecked(
                self.app.settings.get("features", {}).get("custom_command_dialog", True)
            )
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
            for index, label in enumerate(
                ["Pixi", "Torch/CUDA", "GPU", "显存", "CPU", "内存", "磁盘", "模块"]
            ):
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
            info_outer_layout.addLayout(info_grid, 0, 0)
            layout.addWidget(info_outer)

            self.log = QTextEdit()
            self.log.setReadOnly(True)
            layout.addWidget(self.log, 1)

            # Task 13: Auto-refresh timer every 0.5s
            self._auto_refresh_timer = QTimer(self)
            self._auto_refresh_timer.timeout.connect(self._auto_refresh)
            self._auto_refresh_timer.start(500)

        def _toggle_custom_cmd(self, state):
            self.app.settings.setdefault("features", {})["custom_command_dialog"] = (
                state == Qt.CheckState.Checked.value
            )
            self.app.settings_service.save(self.app.settings)

        def _auto_refresh(self):
            self._refresh_count += 1
            self.app.run_background(
                "env_auto",
                lambda: {
                    "pixi": pixi_available(),
                    "modules": detect_modules(),
                    "cuda": torch_cuda_summary(),
                    "status": system_status(),
                    "settings": self.app.settings,
                },
            )

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
            self.log.setPlainText(
                "当前设置:\n"
                + json.dumps(payload["settings"], ensure_ascii=False, indent=2)
            )

        def apply_env_auto(self, payload):
            self._apply_env_data(payload)

        def _apply_env_data(self, payload):
            cuda = payload["cuda"]
            status = payload["status"]
            modules = payload["modules"]
            module_summary = " / ".join(
                f"{name}:{'ok' if ok else '缺失'}" for name, ok in modules.items()
            )
            self.set_status_card("Pixi", "可用" if payload["pixi"] else "不可用")
            self.set_status_card(
                "Torch/CUDA",
                f"{cuda.get('torch', '未知')} / CUDA {cuda.get('cuda', '未知')}",
            )
            self.set_status_card(
                "GPU",
                self.short_gpu_name(status.get("gpu") or cuda.get("gpu", "待检测")),
            )
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
    #helpText { color: #627286; font-size: 12px; line-height: 18px; }
    #inlineFieldLabel { color: #14233A; font-size: 14px; font-weight: 600; }
    #imageView { background: #F8FBFD; border: 1px solid #D9E3EC; border-radius: 6px; color: #627286; }
    #statCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
    #metricCard { background: #F5F8FB; border: 1px solid #E8EDF2; border-radius: 6px; }
    #chartView { background: white; border: 1px solid #D9E3EC; border-radius: 6px; }
    #systemInfoOuter { background: white; border: 1px solid #D9E3EC; border-radius: 8px; }
    #systemInfoInner { background: #F0F2F5; border: 1px solid #E0E3E8; border-radius: 6px; }
    QLineEdit, QTextEdit, QComboBox, QTableWidget { background: white; border: 1px solid #CFD9E3; border-radius: 5px; padding: 7px; }
    QTableWidget { background: #FFFFFF; alternate-background-color: #F7FAFC; gridline-color: #E1E8F0; selection-background-color: #DCEEFF; selection-color: #0D2B49; }
    QTableWidget::item { padding: 6px; border-bottom: 1px solid #E8EDF2; }
    QTableWidget::item:hover { background: #EEF6FF; }
    QHeaderView::section { background: #EAF1F8; color: #0D2B49; border: 0; border-right: 1px solid #D8E2EC; border-bottom: 1px solid #CBD8E4; padding: 7px 6px; font-weight: 700; }
    QHeaderView::up-arrow { image: none; width: 0px; height: 0px; }
    QHeaderView::down-arrow { image: none; width: 0px; height: 0px; }
    QPushButton { background: #208FD4; color: white; border: 0; border-radius: 5px; padding: 9px 14px; }
    QPushButton:hover { background: #1A7ABF; }
    QPushButton#softButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; }
    QPushButton#softButton:hover { background: #E8EDF2; border-color: #B8C4D0; }
    QPushButton#compactSoftButton { background: #F5F8FB; color: #14233A; border: 1px solid #D9E3EC; border-radius: 5px; padding: 4px 10px; font-size: 14px; }
    QPushButton#compactSoftButton:hover { background: #E8EDF2; border-color: #B8C4D0; }
    QPushButton:disabled { background: #C0CCD8; color: #8899AA; }
    QTabWidget::pane { border: 1px solid #D9E3EC; background: white; border-radius: 6px; }
    QTabBar::tab { padding: 9px 16px; background: #F5F8FB; border: 1px solid #D9E3EC; }
    QTabBar::tab:selected { background: white; color: #208FD4; }
    QToolTip { background: #14233A; color: white; border: 0; border-radius: 4px; padding: 6px 8px; }
    """

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    app.setStyleSheet(STYLE)
    window = WorkbenchWindow()
    window.show()
    raise SystemExit(app.exec())

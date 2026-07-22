from __future__ import annotations

from src.ui.shared.page_base import Card
from src.shared.qt import QSizePolicy
from src.shared.qt import (
    Qt,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTimer,
    QVBoxLayout,
)
from src.ui.shared.widgets.charts import DatasetDistributionWidget, TrainingCurveWidget


def build_home_layout(page) -> None:
    page.setMinimumHeight(650)
    page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    layout = page.page_layout()
    layout.setContentsMargins(16, 16, 16, 4)
    page._home_grid_spacing = 12

    hero = QHBoxLayout()
    copy = QVBoxLayout()
    title = QLabel("欢迎使用 YOLO 本地训练工作台")
    title.setObjectName("pageTitle")
    copy.addWidget(title)
    hero.addLayout(copy, 1)
    for text in ["Python 3.12", "CUDA 13.0"]:
        pill = QLabel(text)
        pill.setObjectName("envPill")
        hero.addWidget(pill)
    layout.addLayout(hero)

    grid = QGridLayout()
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 2)
    grid.setRowStretch(0, 58)
    grid.setRowStretch(1, 42)
    grid.setSpacing(page._home_grid_spacing)
    layout.addLayout(grid, 1)

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
    pick.clicked.connect(page.pick_project_root)
    header_row.addWidget(pick)
    overview.layout.addLayout(header_row)
    page.overview_stats = {}
    for key, label in [
        ("project", "项目文件夹"),
        ("images", "图片路径"),
        ("annotations", "标注路径"),
        ("result", "结果路径"),
        ("image_count", "图片数量"),
        ("label_count", "标注数量"),
    ]:
        card, value = page.stat_card(label)
        overview.layout.addWidget(card)
        page.overview_stats[key] = value
    grid.addWidget(overview, 0, 0)

    distribution = Card("各类别图片分布")
    page.distribution_view = DatasetDistributionWidget()
    distribution.layout.addWidget(page.distribution_view, 1)
    grid.addWidget(distribution, 0, 1)

    curve = Card()
    page.curve_view = TrainingCurveWidget()
    curve.layout.addWidget(page.curve_view, 1)
    grid.addWidget(curve, 1, 0)

    history = Card()
    hist_header = QHBoxLayout()
    hist_title = QLabel("训练历史")
    hist_title.setObjectName("sectionTitle")
    hist_header.addWidget(hist_title)
    hist_header.addStretch(1)
    open_button = QPushButton("打开结果目录")
    open_button.setObjectName("compactSoftButton")
    open_button.setFixedWidth(110)
    open_button.setFixedHeight(30)
    open_button.clicked.connect(page.open_result_dir)
    hist_header.addWidget(open_button)
    history.layout.addLayout(hist_header)
    history.layout.addSpacing(3)
    page.history_table = QTableWidget(0, 7)
    page.history_table.setHorizontalHeaderLabels(
        ["模型ID", "Epochs", "Time", "mAP50", "mAP50-95", "Box Loss", "Recall"]
    )
    page.history_table.setAlternatingRowColors(True)
    page.history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    page.history_table.setSortingEnabled(True)
    page.history_table.horizontalHeader().setSortIndicatorShown(False)
    page.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    history.layout.addWidget(page.history_table, 1)
    grid.addWidget(history, 1, 1)

    page._home_left_cards = [overview, curve]
    page._home_right_cards = [distribution, history]
    page._overview_raw_values = {}
    page._apply_home_column_widths()
    QTimer.singleShot(0, page, page._apply_history_column_widths)
    QTimer.singleShot(50, page, page._apply_history_column_widths)

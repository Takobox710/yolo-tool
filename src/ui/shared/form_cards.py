from __future__ import annotations

from src.shared.qt import QFrame, QLabel, QSizePolicy, Qt, QHBoxLayout, QVBoxLayout


def stat_card(label: str, value: str = "-"):
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


def metric_card(label: str, value: str = "待检测"):
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

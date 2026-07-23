import os


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_home_chart_uses_class_counts_as_percentage_total():
    from src.shared.qt import QApplication
    from src.ui.shared.widgets.charts import DatasetDistributionWidget

    app = QApplication.instance() or QApplication([])
    chart = DatasetDistributionWidget()
    chart.set_multi_class_counts({"weld": 2, "scratch": 3})

    assert chart._bars == [("总标注", 5), ("scratch", 3), ("weld", 2)]
    assert chart._percent_total() == 5


def test_home_chart_hides_zero_unannotated_bar_and_multi_class_name():
    from src.shared.qt import QApplication
    from src.ui.shared.widgets.charts import DatasetDistributionWidget

    app = QApplication.instance() or QApplication([])
    chart = DatasetDistributionWidget()
    chart.set_standard_counts(7, {"train": 4, "val": 2, "test": 1}, 0, "")

    assert chart._bars == [
        ("总图片", 7),
        ("训练", 4),
        ("验证", 2),
        ("测试", 1),
    ]
    assert chart._single_class_name == ""


def test_home_chart_frame_matches_training_history_round_frame():
    from src.shared.theme import STYLE
    from src.ui.shared.widgets.charts import _CHART_FRAME_COLOR, _CHART_FRAME_RADIUS

    chart_rule = STYLE.split("#chartView", 1)[1].split("}", 1)[0]

    assert "border: 0" in chart_rule
    assert _CHART_FRAME_COLOR == "#CFD9E3"
    assert _CHART_FRAME_RADIUS == 5


def test_training_curve_uses_epoch_values_for_x_axis_ticks_and_points():
    from src.shared.qt import QApplication
    from src.ui.shared.widgets.charts import TrainingCurveWidget

    app = QApplication.instance() or QApplication([])
    chart = TrainingCurveWidget()
    chart.set_curve_data(
        {
            "epoch": [0, 1, 2, 3, 4],
            "metrics/mAP50(B)": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
    )

    assert chart._epoch_values(5) == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert chart._epoch_ticks([0.0, 1.0, 2.0, 3.0, 4.0]) == [
        (0.0, 0.0),
        (1.0, 0.25),
        (2.0, 0.5),
        (3.0, 0.75),
        (4.0, 1.0),
    ]

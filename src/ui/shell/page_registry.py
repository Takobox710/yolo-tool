from __future__ import annotations

from src.ui.features.annotation.page import AnnotationPage
from src.ui.features.data.page import DataPage
from src.ui.features.home.page import HomePage
from src.ui.features.settings.page import SettingsPage
from src.ui.features.training.page import TrainPage
from src.ui.features.validation.page import ValidatePage
from src.ui.shared.widgets.base import scroll_page

PAGE_ORDER = ["home", "annotation", "data", "train", "validate", "settings"]
PAGE_TITLES = {
    "home": "主页",
    "annotation": "数据标注",
    "data": "数据处理",
    "train": "模型训练",
    "validate": "模型验证",
    "settings": "系统设置",
}


def create_page(window, key: str):
    context = window.context
    if key == "home":
        return scroll_page(HomePage(context))
    if key == "annotation":
        return AnnotationPage(context)
    if key == "data":
        return scroll_page(DataPage(context))
    if key == "train":
        return scroll_page(TrainPage(context))
    if key == "validate":
        return scroll_page(ValidatePage(context))
    return scroll_page(SettingsPage(context))

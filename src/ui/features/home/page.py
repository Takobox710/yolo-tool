from __future__ import annotations

from src.ui.features.home.data import HomePageDataMixin
from src.ui.features.home.layout import build_home_layout
from src.ui.shared.page_base import BasePage


class HomePage(HomePageDataMixin, BasePage):
    def __init__(self, app):
        super().__init__(app)
        build_home_layout(self)



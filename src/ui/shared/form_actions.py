from __future__ import annotations

from src.ui.shared import form_cards, form_pickers


class FormActionMixin:
    def choose_dir(self, edit):
        form_pickers.choose_dir(self, edit)

    def choose_file(self, edit, caption: str = "选择文件"):
        form_pickers.choose_file(self, edit, caption)

    def _choose_pt_for_combo(self, combo):
        form_pickers.choose_pt_for_combo(self, combo)

    def stat_card(self, label: str, value: str = "-"):
        return form_cards.stat_card(label, value)

    def metric_card(self, label: str, value: str = "待检测"):
        return form_cards.metric_card(label, value)


__all__ = ["FormActionMixin"]

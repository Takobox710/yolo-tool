from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml


def dataset_yaml_root(payload: dict, data_path: Path) -> Path:
    root_value = payload.get("path")
    if not root_value:
        return data_path.parent.resolve()
    root = Path(str(root_value))
    if root.is_absolute():
        return root.resolve()
    return (data_path.parent / root).resolve()


def validation_val_override(
    data_path: Path,
    scope: str,
    target: Path,
    images_dir: Path,
) -> str:
    payload = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return str(target)
    dataset_root = dataset_yaml_root(payload, data_path)
    if scope == "全部图片" and target == images_dir:
        return "images"
    try:
        relative = os.path.relpath(str(target), str(dataset_root))
        return str(Path(relative))
    except ValueError:
        return str(target)


@dataclass
class ValidationYamlPatch:
    path: Path | None = None
    original_text: str | None = None
    pending: bool = False

    def prepare(self, data_path: Path, val_value: str) -> None:
        original_text = data_path.read_text(encoding="utf-8")
        payload = yaml.safe_load(original_text)
        if not isinstance(payload, dict):
            return
        payload["val"] = val_value
        patched_text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
        if patched_text == original_text:
            return
        data_path.write_text(patched_text, encoding="utf-8")
        self.path = data_path
        self.original_text = original_text
        self.pending = True

    def restore_if_needed(self) -> None:
        if not self.pending or self.path is None:
            return
        if self.original_text is not None:
            self.path.write_text(self.original_text, encoding="utf-8")
        self.pending = False
        self.path = None
        self.original_text = None


class ResultNavigator:
    def __init__(
        self,
        results_getter: Callable[[], list[dict]],
        index_getter: Callable[[], int],
        index_setter: Callable[[int], None],
        selected_setter: Callable[[bool], None],
        show_payload: Callable[[dict], None],
    ):
        self._results_getter = results_getter
        self._index_getter = index_getter
        self._index_setter = index_setter
        self._selected_setter = selected_setter
        self._show_payload = show_payload

    def show_first(self) -> bool:
        results = self._results_getter()
        if not results:
            return False
        self._selected_setter(True)
        self._index_setter(0)
        self._show_payload(results[0])
        return True

    def show_last(self) -> bool:
        results = self._results_getter()
        if not results:
            return False
        self._selected_setter(True)
        self._index_setter(len(results) - 1)
        self._show_payload(results[-1])
        return True

    def show_previous(self) -> bool:
        results = self._results_getter()
        if not results:
            return False
        self._selected_setter(True)
        index = (self._index_getter() - 1) % len(results)
        self._index_setter(index)
        self._show_payload(results[index])
        return True

    def show_next(self) -> bool:
        results = self._results_getter()
        if not results:
            return False
        self._selected_setter(True)
        index = (self._index_getter() + 1) % len(results)
        self._index_setter(index)
        self._show_payload(results[index])
        return True

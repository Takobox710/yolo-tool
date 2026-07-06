from __future__ import annotations

import ast
from pathlib import Path


def _imports_scr_ui(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "scr.ui" or alias.name.startswith("scr.ui."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "scr.ui" or module.startswith("scr.ui."):
                return True
    return False


def test_services_do_not_import_ui_layer():
    offenders = [
        str(path)
        for path in Path("scr/services").glob("*.py")
        if path.name != "__init__.py" and _imports_scr_ui(path)
    ]

    assert offenders == []


def test_agents_md_links_specs_and_layering_rules():
    text = Path("AGENTS.md").read_text(encoding="utf-8")

    assert "docs/spec/" in text
    assert "scr/services/" in text
    assert "不得导入 `scr/ui/`" in text


def test_view_files_stay_below_maintenance_threshold():
    threshold = 800
    offenders = []
    for path in Path("scr/ui/views").glob("*.py"):
        if path.name == "__init__.py":
            continue
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > threshold:
            offenders.append(f"{path}:{lines}")

    assert offenders == []


def test_ui_helpers_does_not_reexport_service_model_discovery_helpers():
    text = Path("scr/ui/helpers.py").read_text(encoding="utf-8")

    forbidden = [
        "find_training_model_names(",
        "find_training_model_paths(",
        "resolve_training_model_reference(",
        "find_models_full_paths(",
        "find_model_yaml_files(",
    ]

    assert all(token not in text for token in forbidden)

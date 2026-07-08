from __future__ import annotations

import ast
from pathlib import Path

from src.devtools.generate_code_inventory import render_inventory


PROJECT_TEXT_ROOTS = [
    Path("src"),
    Path("docs"),
    Path("installer"),
    Path("README.md"),
    Path("AGENTS.md"),
    Path("pixi.toml"),
]
FORBIDDEN_IMPORT_TOKENS = (
    "from src.ui.views",
    "import src.ui.views",
    "from src.ui.legacy",
    "import src.ui.legacy",
    "from src.ui.window",
    "import src.ui.window",
    "from src.ui.workers",
    "import src.ui.workers",
    "from src.ui.page_base",
    "import src.ui.page_base",
    "from src.ui.forms",
    "import src.ui.forms",
    "from src.ui.dialogs",
    "import src.ui.dialogs",
    "from src.ui.qt",
    "import src.ui.qt",
    "from src.paths",
    "import src.paths",
    "from src.theme",
    "import src.theme",
    "from src.context",
    "import src.context",
    "cli_dispatch_legacy.py",
    "from src.bootstrap.cli_dispatch_legacy",
    "import src.bootstrap.cli_dispatch_legacy",
    "from src.services.settings_service",
    "import src.services.settings_service",
    "from src.services.runtime_service",
    "import src.services.runtime_service",
    "from src.services.environment_service",
    "import src.services.environment_service",
    "from src.services.path_service",
    "import src.services.path_service",
    "from src.services.training_service",
    "import src.services.training_service",
    "from src.services.detection_service",
    "import src.services.detection_service",
    "from src.services.editable_annotation_service",
    "import src.services.editable_annotation_service",
    "from src.services.annotation_ai_service",
    "import src.services.annotation_ai_service",
    "from src.services.annotation_service",
    "import src.services.annotation_service",
    "from src.services.conversion_service",
    "import src.services.conversion_service",
    "from src.services.rename_service",
    "import src.services.rename_service",
    "from src.services.resize_service",
    "import src.services.resize_service",
    "from src.services.process_utils",
    "import src.services.process_utils",
)


def test_services_do_not_import_ui_layer():
    offenders = [
        str(path)
        for path in Path("src/services").rglob("*.py")
        if path.name != "__init__.py" and _imports_ui_layer(path)
    ]
    assert offenders == []


def test_agents_md_links_specs_and_layering_rules():
    text = Path("AGENTS.md").read_text(encoding="utf-8")
    assert "docs/spec/" in text
    assert "src/services/" in text
    assert "不得导入 `src/ui/`" in text
    assert "src/ui/features/*/page.py" in text
    assert "src/services/runtime/" in text


def test_removed_legacy_paths_stay_deleted():
    removed_paths = (
        Path("src/ui/views"),
        Path("src/ui/legacy"),
        Path("src/ui/window.py"),
        Path("src/ui/workers.py"),
        Path("src/ui/page_base.py"),
        Path("src/ui/forms.py"),
        Path("src/ui/dialogs.py"),
        Path("src/ui/qt.py"),
        Path("src/ui/shared/workers/legacy.py"),
        Path("src/bootstrap/cli_dispatch_legacy.py"),
        Path("src/paths.py"),
        Path("src/theme.py"),
        Path("src/context.py"),
    )
    for path in removed_paths:
        assert not path.exists(), str(path)


def test_flat_service_modules_are_removed():
    offenders = sorted(Path("src/services").glob("*_service.py"))
    assert offenders == []


def test_workspace_no_longer_contains_scr_business_source_tree_or_refs():
    assert not Path("scr").exists()

    offenders = []
    self_path = Path(__file__).resolve()
    legacy_root = "s" + "cr"
    patterns = (
        f"from {legacy_root}.",
        f"import {legacy_root}.",
        f"python -m {legacy_root}.main",
        f"{legacy_root}/",
        f"{legacy_root}\\",
    )
    for path in _iter_project_text_files():
        if path.resolve() == self_path:
            continue
        text = _safe_read(path)
        if text is not None and any(pattern in text for pattern in patterns):
            offenders.append(path.as_posix())
    assert offenders == []


def test_workspace_text_files_do_not_reference_removed_legacy_paths():
    self_path = Path(__file__).resolve()
    offenders = []
    for path in _iter_project_text_files():
        if path.resolve() == self_path:
            continue
        text = _safe_read(path)
        if text is not None and any(token in text for token in FORBIDDEN_IMPORT_TOKENS):
            offenders.append(path.as_posix())
    assert offenders == []


def test_flat_root_test_modules_are_migrated_into_final_subpackages():
    root_tests = sorted(
        path.as_posix()
        for path in Path("src/tests").glob("test_*.py")
        if path.name not in {"test_app_entry.py"}
    )
    assert root_tests == []


def test_feature_pages_stay_small():
    offenders = _files_over_limit(Path("src/ui/features"), "page.py", 250)
    assert offenders == []


def test_annotation_canvas_modules_stay_small():
    offenders = _python_files_over_limit(Path("src/ui/features/annotation/canvas"), 250)
    assert offenders == []


def test_shared_workers_stay_small():
    offenders = _python_files_over_limit(Path("src/ui/shared/workers"), 220)
    assert offenders == []


def test_service_domain_modules_stay_small():
    offenders = _python_files_over_limit(Path("src/services"), 300, skip_init=True)
    assert offenders == []


def test_no_transition_lambda_binding_patterns_remain():
    offenders = []
    for path in Path("src/ui/features").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "= lambda self:" in text:
            offenders.append(path.as_posix())
    assert offenders == []


def test_no_import_star_from_implementation_modules():
    offenders = []
    for path in Path("src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                offenders.append(path.as_posix())
                break
    assert offenders == []


def test_page_base_does_not_include_feature_specific_page_names():
    text = Path("src/ui/shared/page_base.py").read_text(encoding="utf-8")
    forbidden = (
        "AnnotationPage",
        "ValidatePage",
        "TrainPage",
        "SettingsPage",
        "HomePage",
        "DataPage",
    )
    assert all(token not in text for token in forbidden)


def test_ui_shared_does_not_depend_on_features_or_shell():
    offenders = _imports_from_prefixes(
        Path("src/ui/shared"),
        ("src.ui.features", "src.ui.shell"),
    )
    assert offenders == []


def test_features_do_not_depend_on_shell_layer():
    offenders = _imports_from_prefixes(
        Path("src/ui/features"),
        ("src.ui.shell",),
    )
    assert offenders == []


def test_shared_layer_does_not_depend_on_ui_or_services():
    offenders = _imports_from_prefixes(
        Path("src/shared"),
        ("src.ui", "src.services"),
    )
    assert offenders == []


def test_service_package_init_files_remain_lightweight():
    offenders = []
    for path in Path("src/services").glob("*/__init__.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > 80:
            offenders.append(f"{path.as_posix()} ({lines})")
    assert offenders == []


def test_code_inventory_is_current():
    inventory_path = Path("docs/code-inventory.md")
    assert inventory_path.read_text(encoding="utf-8") == render_inventory()


def test_architecture_doc_matches_final_structure_terms():
    text = Path("docs/architecture.md").read_text(encoding="utf-8")
    required = (
        "src/ui/features/",
        "src/ui/shared/",
        "src/ui/shell/",
        "src/services/settings/",
        "src/services/training/",
        "src/services/validation/",
        "src/tests/ui/",
        "src/tests/architecture/",
    )
    assert all(token in text for token in required)
    forbidden = ("src/ui/views/", "src/ui/legacy/", "src/ui/window.py", "src/services/*_service.py")
    assert all(token not in text for token in forbidden)


def _imports_ui_layer(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "src.ui" or alias.name.startswith("src.ui."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "src.ui" or module.startswith("src.ui."):
                return True
    return False


def _imports_from_prefixes(root: Path, prefixes: tuple[str, ...]) -> list[str]:
    offenders = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(
                name == prefix or name.startswith(prefix + ".")
                for name in names
                for prefix in prefixes
            ):
                offenders.append(path.as_posix())
                break
    return offenders


def _files_over_limit(root: Path, file_name: str, limit: int) -> list[str]:
    return [
        f"{path.as_posix()} ({_line_count(path)})"
        for path in root.rglob(file_name)
        if _line_count(path) > limit
    ]


def _python_files_over_limit(root: Path, limit: int, *, skip_init: bool = False) -> list[str]:
    offenders = []
    for path in root.rglob("*.py"):
        if skip_init and path.name == "__init__.py":
            continue
        if _line_count(path) > limit:
            offenders.append(f"{path.as_posix()} ({_line_count(path)})")
    return offenders


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _iter_project_text_files():
    for root in PROJECT_TEXT_ROOTS:
        if root.is_file():
            yield root
            continue
        yield from (
            path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts
        )


def _safe_read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None

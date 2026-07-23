from __future__ import annotations

import ast
from pathlib import Path


def test_layer_dependencies_follow_architecture_boundaries():
    checks = (
        (Path("src/services"), ("src.ui",)),
        (Path("src/shared"), ("src.ui", "src.services")),
        (Path("src/ui/shared"), ("src.ui.features", "src.ui.shell")),
        (Path("src/ui/features"), ("src.ui.shell",)),
    )
    offenders = []
    for root, forbidden_prefixes in checks:
        for path in root.rglob("*.py"):
            for imported in _imported_modules(path):
                if any(
                    imported == prefix or imported.startswith(prefix + ".")
                    for prefix in forbidden_prefixes
                ):
                    offenders.append(f"{path.as_posix()}: {imported}")
    assert offenders == []


def test_legacy_paths_and_imports_stay_removed():
    removed_paths = (
        "src/ui/views",
        "src/ui/legacy",
        "src/ui/window.py",
        "src/ui/workers.py",
        "src/ui/page_base.py",
        "src/ui/forms.py",
        "src/ui/dialogs.py",
        "src/ui/qt.py",
        "src/bootstrap/cli_dispatch_legacy.py",
        "src/paths.py",
        "src/theme.py",
        "src/context.py",
        "scr",
    )
    assert [path for path in removed_paths if Path(path).exists()] == []
    assert list(Path("src/services").glob("*_service.py")) == []
    assert list(Path("src/tests").glob("test_*.py")) == []

    forbidden_prefixes = (
        "src.ui.views",
        "src.ui.legacy",
        "src.ui.window",
        "src.ui.workers",
        "src.ui.page_base",
        "src.ui.forms",
        "src.ui.dialogs",
        "src.ui.qt",
        "src.bootstrap.cli_dispatch_legacy",
        "src.services.settings_service",
        "src.services.runtime_service",
        "src.services.environment_service",
        "src.services.path_service",
        "src.services.training_service",
        "src.services.detection_service",
        "src.services.annotation_service",
        "src.services.conversion_service",
        "src.services.rename_service",
        "src.services.resize_service",
        "src.services.process_utils",
        "src.paths",
        "src.theme",
        "src.context",
    )
    offenders = []
    for path in Path("src").rglob("*.py"):
        for imported in _imported_modules(path):
            if any(
                imported == prefix or imported.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            ):
                offenders.append(f"{path.as_posix()}: {imported}")
    assert offenders == []


def test_modules_and_service_exports_stay_within_size_limits():
    limits = (
        (Path("src/ui/features"), "page.py", 350, False),
        (Path("src/ui/features/annotation/canvas"), "*.py", 350, False),
        (Path("src/ui/shared/workers"), "*.py", 300, False),
        (Path("src/services"), "*.py", 400, True),
    )
    offenders = []
    for root, pattern, limit, skip_init in limits:
        for path in root.rglob(pattern):
            if skip_init and path.name == "__init__.py":
                continue
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > limit:
                offenders.append(f"{path.as_posix()} ({lines} > {limit})")

    for path in Path("src/services").glob("*/__init__.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > 80:
            offenders.append(f"{path.as_posix()} ({lines} > 80)")
    assert offenders == [], (
        "Modules exceeded the architecture safety ceiling. Split them by "
        "responsibility; do not compress formatting merely to reduce line counts: "
        + ", ".join(offenders)
    )


def test_python_imports_and_qt_delayed_callbacks_use_safe_patterns():
    star_imports = []
    unsafe_timers = []
    for path in Path("src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(
                alias.name == "*" for alias in node.names
            ):
                star_imports.append(path.as_posix())
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "singleShot"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "QTimer"
                and len(node.args) < 3
            ):
                unsafe_timers.append(f"{path.as_posix()}:{node.lineno}")

    assert star_imports == []
    assert unsafe_timers == []


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    return imported

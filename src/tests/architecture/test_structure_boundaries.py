from __future__ import annotations

import ast
import re
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
    assert list(Path("src/ui/widgets").glob("*.py")) == []
    assert not Path("src/bootstrap/context.py").exists()
    assert not Path("src/shared/types.py").exists()
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
    for path in Path("src/devtools").glob("*.py"):
        if path.name in {"__init__.py", "generate_code_inventory.py"}:
            continue
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > 400:
            offenders.append(f"{path.as_posix()} ({lines} > 400)")
    assert offenders == [], (
        "Modules exceeded the architecture safety ceiling. Split them by "
        "responsibility; do not compress formatting merely to reduce line counts: "
        + ", ".join(offenders)
    )


def test_targeted_refactor_facades_stay_small():
    limits = {
        Path("src/ui/features/annotation/sam/settings_dialog.py"): 180,
        Path("src/ui/features/annotation/ai/dialog.py"): 180,
        Path("src/ui/features/annotation/draw_shape_dialog.py"): 180,
        Path("src/ui/features/annotation/canvas/widget.py"): 160,
        Path("src/bootstrap/cli_annotation.py"): 80,
        Path("src/bootstrap/cli_validation.py"): 80,
        Path("src/ui/shared/forms.py"): 80,
    }
    offenders = [
        f"{path.as_posix()} ({len(path.read_text(encoding='utf-8').splitlines())} > {limit})"
        for path, limit in limits.items()
        if len(path.read_text(encoding="utf-8").splitlines()) > limit
    ]
    assert offenders == []


def test_targeted_refactor_facades_keep_compatibility_exports():
    from src.bootstrap.cli_annotation import (
        _run_ai_label_cli_impl,
        _run_ai_runtime_cli_impl,
        _run_model_labels_cli_impl,
        _run_sam_assist_runtime_cli_impl,
    )
    from src.bootstrap.cli_validation import _run_predict_cli_impl, _run_val_cli_impl
    from src.ui.features.annotation.ai.dialog import (
        AiPrelabelDialog,
        CustomAiImageSelectionDialog,
    )
    from src.ui.features.annotation.canvas.widget import (
        AnnotationCanvas,
        SAM_SUPPORTED_SHAPES,
    )
    from src.ui.features.annotation.draw_shape_dialog import DrawShapeDialog
    from src.ui.features.annotation.sam.settings_dialog import (
        SAM_ASSIST_PARAMETER_DEFAULTS,
        SamAdvancedSettingsDialog,
    )
    from src.ui.shared.forms import FormPageMixin

    assert all(
        callable(item)
        for item in (
            _run_ai_label_cli_impl,
            _run_ai_runtime_cli_impl,
            _run_model_labels_cli_impl,
            _run_sam_assist_runtime_cli_impl,
            _run_predict_cli_impl,
            _run_val_cli_impl,
            AiPrelabelDialog,
            CustomAiImageSelectionDialog,
            AnnotationCanvas,
            DrawShapeDialog,
            SamAdvancedSettingsDialog,
            FormPageMixin,
        )
    )
    assert SAM_ASSIST_PARAMETER_DEFAULTS["minimum_area"] == 4
    assert SAM_SUPPORTED_SHAPES == {"rect", "obb_single", "obb_mirror", "polygon"}


def test_feature_modules_keep_explicit_top_level_class_boundaries():
    expected = {
        Path("src/ui/features/validation/helpers.py"): 2,
        Path("src/ui/features/validation/video_player.py"): 2,
    }
    actual = {}
    for path in Path("src/ui/features").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        class_count = sum(isinstance(node, ast.ClassDef) for node in tree.body)
        if class_count > 1:
            actual[path] = class_count
    assert actual == expected, (
        "Feature modules with multiple top-level classes must be explicitly "
        f"partitioned or registered: {actual}"
    )


def test_large_feature_modules_stay_within_reviewed_safety_ceilings():
    reviewed = {
        Path("src/ui/features/annotation/ai/dialog.py"): 900,
        Path("src/ui/features/settings/update_dialog.py"): 900,
    }
    offenders = []
    unreviewed = []
    for path in Path("src/ui/features").rglob("*.py"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        limit = reviewed.get(path)
        if limit is None:
            if lines > 600:
                unreviewed.append(f"{path.as_posix()} ({lines} > 600 review trigger)")
        elif lines > limit:
            offenders.append(f"{path.as_posix()} ({lines} > {limit})")
    assert unreviewed == [] and offenders == [], (
        "Large feature modules need an explicit responsibility review or split: "
        + ", ".join(unreviewed + offenders)
    )


def test_model_export_ui_support_modules_keep_small_responsibilities():
    expected = {
        Path("src/ui/features/data/model_export/availability.py"): 300,
        Path("src/ui/features/data/model_export/config.py"): 300,
        Path("src/ui/features/data/model_export/layout.py"): 80,
        Path("src/ui/features/data/model_export/layout_options.py"): 300,
        Path("src/ui/features/data/model_export/layout_actions.py"): 120,
        Path("src/ui/features/data/model_export/layout_base.py"): 220,
        Path("src/ui/features/data/model_export/layout_components.py"): 80,
        Path("src/ui/features/data/model_export/layout_responsive.py"): 180,
        Path("src/ui/features/data/model_export/runtime_actions.py"): 300,
        Path("src/ui/features/data/model_export/selection.py"): 300,
        Path("src/ui/features/data/model_export/tab.py"): 350,
    }
    offenders = []
    for path, limit in expected.items():
        assert path.exists(), f"Expected model-export module is missing: {path}"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > limit:
            offenders.append(f"{path.as_posix()} ({lines} > {limit})")
    assert offenders == []


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


def test_ui_features_use_explicit_context_and_no_legacy_host_access():
    offenders = []
    for path in Path("src/ui/features").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for marker in (r"\bself\.app\b", r"\bpage\.app\b", r"\bapp\.settings\b", r"\bcontext\.pages\b", r"\bcontext\.workers\b"):
            if re.search(marker, text):
                offenders.append(f"{path.as_posix()}: {marker}")
    assert offenders == []


def test_internal_src_import_graph_has_no_cycles():
    modules = {
        _module_name(path)
        for path in Path("src").rglob("*.py")
    }
    graph: dict[str, set[str]] = {}
    for path in Path("src").rglob("*.py"):
        module = _module_name(path)
        graph[module] = _runtime_imports(path, modules)

    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[str] = []

    def visit(module: str, trail: list[str]) -> None:
        if module in visiting:
            cycles.append(" -> ".join(trail + [module]))
            return
        if module in visited:
            return
        visiting.add(module)
        for dependency in graph.get(module, ()):
            visit(dependency, trail + [module])
        visiting.remove(module)
        visited.add(module)

    for module in graph:
        visit(module, [])
    assert cycles == []


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    return imported


def _module_name(path: Path) -> str:
    relative = path.relative_to(Path("src")).with_suffix("")
    parts = ["src", *relative.parts]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _runtime_imports(path: Path, modules: set[str]) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If):
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                return
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    imports.add(alias.name)

        def visit_ImportFrom(self, node: ast.ImportFrom):
            module = node.module or ""
            if not module.startswith("src."):
                return
            for alias in node.names:
                candidate = f"{module}.{alias.name}"
                imports.add(candidate if candidate in modules else module)

    Visitor().visit(tree)
    return imports

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "code-inventory.md"
SECTIONS = [
    ROOT / "src",
    ROOT / "docs",
    ROOT / "installer",
]
TEXT_SUFFIXES = {".md", ".py", ".ps1", ".toml", ".json", ".iss", ".spec", ".txt", ".pyw"}


@dataclass(slots=True)
class InventoryRow:
    path: Path
    lines: int


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def _count_lines(path: Path) -> int:
    if not _is_text_file(path):
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def _collect_rows(base: Path) -> list[InventoryRow]:
    return [
        InventoryRow(path=path, lines=_count_lines(path))
        for path in sorted(base.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def _describe(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("src/bootstrap/"):
        return "启动装配、GUI/CLI 分发与应用上下文入口。"
    if rel.startswith("src/shared/"):
        return "跨层共享基础模块、Qt 出口、路径与主题支持。"
    if rel.startswith("src/services/"):
        return "服务层与可测试业务逻辑实现。"
    if rel.startswith("src/ui/shell/"):
        return "主窗口壳层、样式与页面协调。"
    if rel.startswith("src/ui/shared/workers/"):
        return "共享后台工作线程与子进程桥接。"
    if rel.startswith("src/ui/shared/"):
        return "跨页面复用的表单、对话框与页面基类。"
    if rel.startswith("src/ui/features/"):
        return "按功能分包的页面真实实现。"
    if rel.startswith("src/ui/widgets/"):
        return "图表与基础复用控件。"
    if rel.startswith("src/tests/"):
        return "pytest 测试、结构约束与回归用例。"
    if rel.startswith("src/assets/"):
        return "应用图标与静态资源。"
    if rel.startswith("src/runtime/"):
        return "源码内默认配置参考。"
    if rel.startswith("docs/spec/"):
        return "页面与功能规格说明。"
    if rel.startswith("docs/"):
        return "项目架构、打包与维护文档。"
    if rel.startswith("installer/"):
        return "Windows 打包脚本与安装配置。"
    if rel == "README.md":
        return "项目概览、命令入口与使用说明。"
    if rel == "AGENTS.md":
        return "本仓库 AI 执行约束与开发规则。"
    if rel == "pixi.toml":
        return "Pixi 环境、依赖与任务命令定义。"
    if rel == "refactor_plan.md":
        return "本次 src 重构目标结构与验收计划。"
    return "仓库文件。"


def _summary_rows() -> list[str]:
    rows: list[str] = []
    for base in SECTIONS:
        files = [path for path in base.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
        text_lines = sum(_count_lines(path) for path in files)
        rel = base.relative_to(ROOT).as_posix()
        if rel == "src":
            desc = "主源码目录，包含入口、共享层、服务层、UI 与测试。"
        elif rel == "docs":
            desc = "架构、规格、打包与代码清单文档。"
        else:
            desc = "Windows 打包脚本、PyInstaller 与 Inno Setup 配置。"
        rows.append(f"- `{rel}`: {len(files)} 个文件，{text_lines} 行文本；{desc}")
    return rows


def render_inventory() -> str:
    lines = [
        "# Code Inventory",
        "",
        "此文件由 `python -m src.devtools.generate_code_inventory` 生成，请勿手工长期维护。",
        "",
        "## 目录摘要",
        "",
        *_summary_rows(),
        "",
        "## 文件清单",
        "",
        "| 路径 | 行数 | 说明 |",
        "| --- | ---: | --- |",
    ]
    roots = [
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "pixi.toml",
        ROOT / "refactor_plan.md",
        ROOT / "second_stage_plan.md",
    ]
    rows = [InventoryRow(path=path, lines=_count_lines(path)) for path in roots if path.exists()]
    for base in SECTIONS:
        rows.extend(_collect_rows(base))
    for row in rows:
        rel = row.path.relative_to(ROOT).as_posix()
        lines.append(f"| `{rel}` | {row.lines} | {_describe(row.path)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUTPUT.write_text(render_inventory(), encoding="utf-8")


if __name__ == "__main__":
    main()

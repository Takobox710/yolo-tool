# Code Inventory

此文件由 `python -m src.devtools.generate_code_inventory` 生成，请勿手工长期维护。

## 目录摘要

- `src`: 202 个文件，23708 行文本；主源码目录，包含入口、共享层、服务层、UI 与测试。
- `docs`: 9 个文件，845 行文本；架构、规格、打包与代码清单文档。
- `installer`: 15 个文件，498 行文本；Windows 打包脚本、PyInstaller 与 Inno Setup 配置。

## 文件清单

| 路径 | 行数 | 说明 |
| --- | ---: | --- |
| `AGENTS.md` | 138 | 本仓库 AI 执行约束与开发规则。 |
| `README.md` | 393 | 项目概览、命令入口与使用说明。 |
| `pixi.toml` | 32 | Pixi 环境、依赖与任务命令定义。 |
| `src/__init__.py` | 1 | 仓库文件。 |
| `src/app.py` | 8 | 仓库文件。 |
| `src/assets/app_icon.ico` | 0 | 应用图标与静态资源。 |
| `src/assets/app_icon.png` | 0 | 应用图标与静态资源。 |
| `src/bootstrap/__init__.py` | 1 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/app_factory.py` | 7 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_dispatch.py` | 21 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/context.py` | 25 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/data/runtime/app_state.json` | 3 | 仓库文件。 |
| `src/data/runtime/settings.json` | 118 | 仓库文件。 |
| `src/devtools/__init__.py` | 1 | 仓库文件。 |
| `src/devtools/generate_code_inventory.py` | 135 | 仓库文件。 |
| `src/main.py` | 62 | 仓库文件。 |
| `src/open_yolo_tool.pyw` | 32 | 仓库文件。 |
| `src/runtime/settings.json` | 107 | 源码内默认配置参考。 |
| `src/services/__init__.py` | 2 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/__init__.py` | 62 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/ai_labeling.py` | 283 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/circle_geometry.py` | 16 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/editable_document.py` | 295 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/file_index.py` | 57 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/preview_render.py` | 146 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/__init__.py` | 34 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/backup.py` | 37 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/class_mapping.py` | 155 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/dataset_split.py` | 96 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/dataset_yaml.py` | 29 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/execute.py` | 138 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/formatting.py` | 72 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/labelme_parser.py` | 105 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/types.py` | 77 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/__init__.py` | 44 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/path_display.py` | 56 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/rename.py` | 142 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/resize.py` | 103 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/__init__.py` | 5 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/summary.py` | 162 | 服务层与可测试业务逻辑实现。 |
| `src/services/models/__init__.py` | 1 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/__init__.py` | 44 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/environment_probe.py` | 192 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/process_runner.py` | 204 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/windows_spawn.py` | 11 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/__init__.py` | 28 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/defaults.py` | 116 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/project_settings.py` | 89 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/storage.py` | 146 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/__init__.py` | 44 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/commands.py` | 116 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/model_catalog.py` | 133 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/model_resolution.py` | 59 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/results_reader.py` | 153 | 服务层与可测试业务逻辑实现。 |
| `src/services/ultralytics_compat.py` | 29 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/__init__.py` | 46 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/model_catalog.py` | 77 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/prediction_runner.py` | 160 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/rendering.py` | 147 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/runtime_cleanup.py` | 22 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/source_collectors.py` | 156 | 服务层与可测试业务逻辑实现。 |
| `src/shared/__init__.py` | 1 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/paths.py` | 20 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/qt.py` | 46 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/theme.py` | 60 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/types.py` | 5 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/utils/__init__.py` | 1 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/tests/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/architecture/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/architecture/test_structure_boundaries.py` | 337 | pytest 测试、结构约束与回归用例。 |
| `src/tests/conftest.py` | 47 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/ui_paths.py` | 69 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_annotation_services.py` | 187 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/conversion/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/conversion/test_conversion_services.py` | 432 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/test_rename.py` | 108 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/test_resize.py` | 106 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/home/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/home/test_summary.py` | 124 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_environment_probe.py` | 180 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_process_runner.py` | 88 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/settings/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/settings/test_project_settings.py` | 175 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/training/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/training/test_training_services.py` | 278 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/test_model_catalog.py` | 34 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/test_prediction_services.py` | 276 | pytest 测试、结构约束与回归用例。 |
| `src/tests/test_app_entry.py` | 229 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_page.py` | 2052 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data/test_convert_tab.py` | 94 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data/test_resize_tab.py` | 108 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_settings_page.py` | 378 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shared/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shared/test_page_base.py` | 46 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shell/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shell/test_shell_pages.py` | 632 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/training/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/training/test_training_page.py` | 336 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/validation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/validation/test_validation_page.py` | 761 | pytest 测试、结构约束与回归用例。 |
| `src/train_cli.py` | 562 | 仓库文件。 |
| `src/ui/__init__.py` | 1 | 仓库文件。 |
| `src/ui/app.py` | 19 | 仓库文件。 |
| `src/ui/features/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/actions.py` | 73 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/dialog.py` | 600 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/image_selection_dialog.py` | 285 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/mapping.py` | 121 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/preferences.py` | 82 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/context_menu.py` | 151 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/drawing.py` | 158 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/editing.py` | 61 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/geometry.py` | 138 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/hit_test.py` | 90 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/interaction.py` | 242 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/render.py` | 250 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/state.py` | 26 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/status.py` | 47 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/widget.py` | 229 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/class_panel.py` | 74 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/dialogs.py` | 394 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/file_browser.py` | 360 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/layout.py` | 82 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/menus.py` | 165 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/page.py` | 215 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/persistence.py` | 117 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/selection.py` | 57 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/settings_actions.py` | 89 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/shortcuts.py` | 48 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/toolbar.py` | 61 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/convert/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/convert/tab.py` | 365 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/page.py` | 68 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/preview/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/preview/tab.py` | 190 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/rename/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/rename/tab.py` | 218 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/resize/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/resize/tab.py` | 170 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/data.py` | 193 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/layout.py` | 114 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/page.py` | 14 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/constants.py` | 12 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/layout.py` | 73 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/page.py` | 82 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/state.py` | 208 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/form.py` | 220 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/page.py` | 122 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/runtime.py` | 118 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/state.py` | 279 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/dataset_mode.py` | 94 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/helpers.py` | 121 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/layout.py` | 309 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/models.py` | 92 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/page.py` | 45 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/page_actions.py` | 355 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/result_list.py` | 85 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/results.py` | 141 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/runtime.py` | 214 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/sources.py` | 56 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/state.py` | 403 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/video_player.py` | 162 | 按功能分包的页面真实实现。 |
| `src/ui/helpers.py` | 66 | 仓库文件。 |
| `src/ui/shared/__init__.py` | 1 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/dialogs.py` | 211 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/forms.py` | 355 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/page_base.py` | 168 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/__init__.py` | 1 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/base.py` | 90 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/charts.py` | 332 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/workers/__init__.py` | 13 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/ai_runtime.py` | 219 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/annotation_ai.py` | 93 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/base.py` | 22 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/detection.py` | 114 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/model_labels.py` | 48 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shell/__init__.py` | 1 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/close_guard.py` | 46 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/navigation.py` | 48 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/page_registry.py` | 34 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/program_log.py` | 27 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/style.py` | 7 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/window.py` | 229 | 主窗口壳层、样式与页面协调。 |
| `src/ui/widgets/__init__.py` | 1 | 图表与基础复用控件。 |
| `src/ui/widgets/base.py` | 90 | 图表与基础复用控件。 |
| `src/ui/widgets/charts.py` | 332 | 图表与基础复用控件。 |
| `docs/architecture.md` | 193 | 项目架构、打包与维护文档。 |
| `docs/code-inventory.md` | 243 | 项目架构、打包与维护文档。 |
| `docs/packaging-windows.md` | 38 | 项目架构、打包与维护文档。 |
| `docs/spec/annotation.md` | 109 | 页面与功能规格说明。 |
| `docs/spec/data-processing.md` | 61 | 页面与功能规格说明。 |
| `docs/spec/home.md` | 39 | 页面与功能规格说明。 |
| `docs/spec/settings.md` | 27 | 页面与功能规格说明。 |
| `docs/spec/training.md` | 70 | 页面与功能规格说明。 |
| `docs/spec/validation.md` | 65 | 页面与功能规格说明。 |
| `installer/build_windows.ps1` | 122 | Windows 打包脚本与安装配置。 |
| `installer/hooks/hook-PySide6.scripts.deploy_lib.py` | 1 | Windows 打包脚本与安装配置。 |
| `installer/hooks/hook-torch.py` | 26 | Windows 打包脚本与安装配置。 |
| `installer/hooks/hook-torch.utils.tensorboard.py` | 1 | Windows 打包脚本与安装配置。 |
| `installer/output/YOLOTool_Setup_1.0.0.exe` | 0 | Windows 打包脚本与安装配置。 |
| `installer/output/YOLOTool_Setup_1.1.0.exe` | 0 | Windows 打包脚本与安装配置。 |
| `installer/output/YOLOTool_Setup_1.2.0.exe` | 0 | Windows 打包脚本与安装配置。 |
| `installer/output/YOLOTool_Setup_1.2.1.exe` | 0 | Windows 打包脚本与安装配置。 |
| `installer/output/YOLOTool_Setup_1.2.2.exe` | 0 | Windows 打包脚本与安装配置。 |
| `installer/output/YOLOTool_Setup_1.2.3.exe` | 0 | Windows 打包脚本与安装配置。 |
| `installer/output/YOLOTool_Setup_1.2.4.exe` | 0 | Windows 打包脚本与安装配置。 |
| `installer/package_windows.ps1` | 79 | Windows 打包脚本与安装配置。 |
| `installer/yolo_tool.iss` | 83 | Windows 打包脚本与安装配置。 |
| `installer/YOLOTool.spec` | 107 | Windows 打包脚本与安装配置。 |
| `installer/打包程序.ps1` | 79 | Windows 打包脚本与安装配置。 |

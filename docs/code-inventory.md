# Code Inventory

此文件由 `python -m src.devtools.generate_code_inventory` 生成，请勿手工长期维护。

## 目录摘要

- `src`: 262 个文件，34023 行文本；主源码目录，包含入口、共享层、服务层、UI 与测试。
- `docs`: 8 个文件，848 行文本；架构、规格、打包与代码清单文档。
- `installer`: 15 个文件，2299 行文本；Windows 打包脚本、PyInstaller 与 Inno Setup 配置。

## 文件清单

| 路径 | 行数 | 说明 |
| --- | ---: | --- |
| `AGENTS.md` | 176 | 本仓库 AI 执行约束与开发规则。 |
| `README.md` | 425 | 项目概览、命令入口与使用说明。 |
| `pixi.toml` | 71 | Pixi 环境、依赖与任务命令定义。 |
| `src/__init__.py` | 1 | 仓库文件。 |
| `src/app.py` | 8 | 仓库文件。 |
| `src/assets/app_icon.ico` | 0 | 应用图标与静态资源。 |
| `src/assets/app_icon.png` | 0 | 应用图标与静态资源。 |
| `src/assets/sam_assist.svg` | 0 | 应用图标与静态资源。 |
| `src/assets.qrc` | 0 | 仓库文件。 |
| `src/assets_rc.py` | 1049 | 仓库文件。 |
| `src/bootstrap/__init__.py` | 1 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/app_factory.py` | 7 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_dispatch.py` | 110 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/handlers.py` | 45 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/devtools/__init__.py` | 1 | 仓库文件。 |
| `src/devtools/base_runtime_package.py` | 29 | 仓库文件。 |
| `src/devtools/companion_catalog.py` | 94 | 仓库文件。 |
| `src/devtools/generate_code_inventory.py` | 151 | 仓库文件。 |
| `src/devtools/model_export_package.py` | 187 | 仓库文件。 |
| `src/devtools/release_package.py` | 445 | 仓库文件。 |
| `src/main.py` | 53 | 仓库文件。 |
| `src/open_yolo_tool.pyw` | 32 | 仓库文件。 |
| `src/runtime/settings.json` | 132 | 源码内默认配置参考。 |
| `src/services/__init__.py` | 2 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/__init__.py` | 78 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/ai_labeling.py` | 374 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/circle_geometry.py` | 16 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/class_names.py` | 89 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/editable_document.py` | 311 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/file_index.py` | 57 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/preview_render.py` | 146 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/sam3_text.py` | 224 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/sam_assist.py` | 195 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/sam_runtime.py` | 139 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/__init__.py` | 34 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/backup.py` | 37 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/class_mapping.py` | 155 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/dataset_split.py` | 96 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/dataset_yaml.py` | 29 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/execute.py` | 138 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/formatting.py` | 72 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/labelme_parser.py` | 105 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/types.py` | 77 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/__init__.py` | 45 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/path_display.py` | 56 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/rename.py` | 139 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/resize.py` | 103 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/sorting.py` | 14 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/__init__.py` | 5 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/distribution.py` | 192 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/summary.py` | 84 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/__init__.py` | 70 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/activation.py` | 46 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/archive_extract.py` | 53 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/commands.py` | 51 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/execute.py` | 98 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/formats.py` | 70 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/inspection.py` | 54 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/manifest.py` | 101 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/native_archive.py` | 150 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/package.py` | 325 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/probe.py` | 48 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/runtime.py` | 65 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/types.py` | 39 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/verification.py` | 22 | 服务层与可测试业务逻辑实现。 |
| `src/services/models/__init__.py` | 1 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/__init__.py` | 80 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/environment_probe.py` | 240 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/install_instance.py` | 124 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/managed_models.py` | 55 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/metadata.py` | 24 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/process_runner.py` | 204 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_environment.py` | 118 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_manifest.py` | 150 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_updates.py` | 400 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_versions.py` | 61 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/windows_spawn.py` | 11 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/__init__.py` | 76 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/defaults.py` | 155 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/model.py` | 329 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/project_settings.py` | 166 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/storage.py` | 149 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/__init__.py` | 44 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/commands.py` | 113 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/model_catalog.py` | 133 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/model_resolution.py` | 59 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/results_reader.py` | 153 | 服务层与可测试业务逻辑实现。 |
| `src/services/ultralytics_compat.py` | 29 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/__init__.py` | 46 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/model_catalog.py` | 72 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/prediction_runner.py` | 164 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/rendering.py` | 147 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/runtime_cleanup.py` | 22 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/source_collectors.py` | 158 | 服务层与可测试业务逻辑实现。 |
| `src/shared/__init__.py` | 1 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/paths.py` | 47 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/qt.py` | 71 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/theme.py` | 73 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/utils/__init__.py` | 1 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/tests/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/architecture/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/architecture/test_structure_boundaries.py` | 221 | pytest 测试、结构约束与回归用例。 |
| `src/tests/conftest.py` | 49 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/ui_paths.py` | 70 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_app_entry.py` | 202 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_installer_contract.py` | 260 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_model_export_packaging.py` | 65 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_annotation_services.py` | 243 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_sam3_text.py` | 220 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_sam_assist.py` | 108 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/conversion/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/conversion/test_conversion_services.py` | 317 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/test_rename.py` | 95 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/test_resize.py` | 77 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/home/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/home/test_summary.py` | 197 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_activation.py` | 43 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_export_cli.py` | 95 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_extension_package.py` | 294 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_model_export_services.py` | 196 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_package_collector.py` | 97 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_companion_catalog.py` | 82 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_environment_probe.py` | 99 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_install_instance.py` | 107 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_managed_models.py` | 44 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_process_runner.py` | 79 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_release_manifest.py` | 217 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_release_updates.py` | 302 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/settings/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/settings/test_project_settings.py` | 117 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/training/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/training/test_training_services.py` | 200 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/test_model_catalog.py` | 33 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/test_prediction_services.py` | 265 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_page.py` | 1348 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_model_export_tab.py` | 180 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_resize_tab.py` | 97 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/home/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/home/test_home_charts.py` | 67 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_updates.py` | 747 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_settings_page.py` | 209 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shared/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shell/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shell/test_shell_pages.py` | 163 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/training/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/training/test_training_page.py` | 200 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/validation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/validation/test_validation_page.py` | 269 | pytest 测试、结构约束与回归用例。 |
| `src/train_cli.py` | 859 | 仓库文件。 |
| `src/ui/__init__.py` | 1 | 仓库文件。 |
| `src/ui/app.py` | 20 | 仓库文件。 |
| `src/ui/features/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/actions.py` | 73 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/dialog.py` | 842 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/image_selection_dialog.py` | 285 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/mapping.py` | 189 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/preferences.py` | 112 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/context_menu.py` | 197 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/drawing.py` | 158 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/editing.py` | 140 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/geometry.py` | 195 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/handle_render.py` | 72 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/hit_test.py` | 122 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/interaction.py` | 266 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/render.py` | 243 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/state.py` | 25 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/status.py` | 33 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/widget.py` | 313 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/class_panel.py` | 82 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/dialogs.py` | 624 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/file_browser.py` | 362 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/layout.py` | 101 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/menus.py` | 166 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/page.py` | 257 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/persistence.py` | 132 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/__init__.py` | 3 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/controller.py` | 435 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/runtime.py` | 190 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/selection.py` | 82 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/settings_actions.py` | 135 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/shortcuts.py` | 56 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/toolbar.py` | 61 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/convert/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/convert/tab.py` | 364 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/__init__.py` | 3 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/state.py` | 73 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/tab.py` | 365 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/page.py` | 79 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/preview/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/preview/tab.py` | 188 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/rename/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/rename/tab.py` | 216 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/resize/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/resize/tab.py` | 166 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/data.py` | 203 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/layout.py` | 121 | 按功能分包的页面真实实现。 |
| `src/ui/features/home/page.py` | 12 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/constants.py` | 12 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/layout.py` | 141 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/page.py` | 104 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/state.py` | 303 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_dialog.py` | 801 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_toast.py` | 127 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/form.py` | 218 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/page.py` | 122 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/runtime.py` | 118 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/state.py` | 270 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/dataset_mode.py` | 102 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/helpers.py` | 121 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/layout.py` | 363 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/models.py` | 92 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/page.py` | 49 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/page_actions.py` | 522 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/result_list.py` | 85 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/results.py` | 169 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/runtime.py` | 228 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/sources.py` | 65 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/state.py` | 428 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/video_player.py` | 162 | 按功能分包的页面真实实现。 |
| `src/ui/helpers.py` | 53 | 仓库文件。 |
| `src/ui/shared/__init__.py` | 1 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/assets.py` | 41 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/context.py` | 131 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/dialogs.py` | 217 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/forms.py` | 355 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/model_export_package.py` | 149 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/page_base.py` | 206 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/tasks.py` | 83 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/__init__.py` | 1 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/base.py` | 101 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/charts.py` | 492 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/toggle_switch.py` | 77 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/workers/__init__.py` | 13 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/ai_runtime.py` | 219 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/annotation_ai.py` | 93 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/base.py` | 27 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/detection.py` | 114 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/model_labels.py` | 48 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shell/__init__.py` | 1 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/close_guard.py` | 44 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/navigation.py` | 50 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/page_registry.py` | 34 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/program_log.py` | 27 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/style.py` | 7 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/window.py` | 296 | 主窗口壳层、样式与页面协调。 |
| `docs/architecture.md` | 253 | 项目架构、打包与维护文档。 |
| `docs/packaging-windows.md` | 125 | 项目架构、打包与维护文档。 |
| `docs/spec/annotation.md` | 150 | 页面与功能规格说明。 |
| `docs/spec/data-processing.md` | 84 | 页面与功能规格说明。 |
| `docs/spec/home.md` | 43 | 页面与功能规格说明。 |
| `docs/spec/settings.md` | 49 | 页面与功能规格说明。 |
| `docs/spec/training.md` | 72 | 页面与功能规格说明。 |
| `docs/spec/validation.md` | 72 | 页面与功能规格说明。 |
| `installer/base-runtime-models-version.txt` | 1 | Windows 打包脚本与安装配置。 |
| `installer/build_base_runtime_models.ps1` | 41 | Windows 打包脚本与安装配置。 |
| `installer/build_model_export_runtime.ps1` | 35 | Windows 打包脚本与安装配置。 |
| `installer/build_windows.ps1` | 239 | Windows 打包脚本与安装配置。 |
| `installer/hooks/hook-torch.py` | 26 | Windows 打包脚本与安装配置。 |
| `installer/hooks/program_external_runtime.py` | 50 | Windows 打包脚本与安装配置。 |
| `installer/languages/ChineseSimplified.isl` | 0 | Windows 打包脚本与安装配置。 |
| `installer/model-export-runtime-version.txt` | 1 | Windows 打包脚本与安装配置。 |
| `installer/package_windows.ps1` | 197 | Windows 打包脚本与安装配置。 |
| `installer/runtime-version.txt` | 1 | Windows 打包脚本与安装配置。 |
| `installer/vendor/sam2-1.1.0-cp312-cp312-win_amd64.whl` | 0 | Windows 打包脚本与安装配置。 |
| `installer/vendor/sam3-0.1.0-py3-none-any.whl` | 0 | Windows 打包脚本与安装配置。 |
| `installer/vendor/sam3-LICENSE.txt` | 61 | Windows 打包脚本与安装配置。 |
| `installer/yolo_tool.iss` | 1410 | Windows 打包脚本与安装配置。 |
| `installer/YOLOTool.spec` | 237 | Windows 打包脚本与安装配置。 |

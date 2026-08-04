# Code Inventory

此文件由 `python -m src.devtools.generate_code_inventory` 生成，请勿手工长期维护。

## 目录摘要

- `src`: 433 个文件，46348 行文本；主源码目录，包含入口、共享层、服务层、UI 与测试。
- `docs`: 8 个文件，946 行文本；架构、规格、打包与代码清单文档。
- `installer`: 16 个文件，2774 行文本；Windows 打包脚本、PyInstaller 与 Inno Setup 配置。

## 文件清单

| 路径 | 行数 | 说明 |
| --- | ---: | --- |
| `AGENTS.md` | 192 | 本仓库 AI 执行约束与开发规则。 |
| `README.md` | 227 | 项目概览、命令入口与使用说明。 |
| `pixi.toml` | 87 | Pixi 环境、依赖与任务命令定义。 |
| `src/__init__.py` | 1 | 仓库文件。 |
| `src/app.py` | 8 | 仓库文件。 |
| `src/assets/app_icon.ico` | 0 | 应用图标与静态资源。 |
| `src/assets/app_icon.png` | 0 | 应用图标与静态资源。 |
| `src/assets/sam_assist.svg` | 0 | 应用图标与静态资源。 |
| `src/assets.qrc` | 0 | 仓库文件。 |
| `src/assets_rc.py` | 1049 | 仓库文件。 |
| `src/bootstrap/__init__.py` | 1 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/app_factory.py` | 7 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_annotation.py` | 25 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_annotation_batch.py` | 62 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_annotation_labels.py` | 14 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_annotation_runtime.py` | 150 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_common.py` | 72 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_dispatch.py` | 116 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_legacy.py` | 46 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_model_export.py` | 184 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_predict.py` | 257 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_runtime.py` | 56 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_sam_runtime.py` | 71 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_training.py` | 46 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_val.py` | 32 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/cli_validation.py` | 17 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/handlers.py` | 103 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/bootstrap/runtime_protocol.py` | 13 | 启动装配、GUI/CLI 分发与应用上下文入口。 |
| `src/data/runtime/app_state.json` | 3 | 仓库文件。 |
| `src/data/runtime/settings.json` | 119 | 仓库文件。 |
| `src/devtools/__init__.py` | 1 | 仓库文件。 |
| `src/devtools/archive_builder.py` | 65 | 仓库文件。 |
| `src/devtools/base_runtime_builder.py` | 78 | 仓库文件。 |
| `src/devtools/base_runtime_dependencies.py` | 56 | 仓库文件。 |
| `src/devtools/base_runtime_package.py` | 61 | 仓库文件。 |
| `src/devtools/base_runtime_spec.py` | 21 | 仓库文件。 |
| `src/devtools/base_runtime_staging.py` | 106 | 仓库文件。 |
| `src/devtools/companion_catalog.py` | 163 | 仓库文件。 |
| `src/devtools/cpu_package_guard.py` | 189 | 仓库文件。 |
| `src/devtools/generate_code_inventory.py` | 151 | 仓库文件。 |
| `src/devtools/model_export_collector.py` | 56 | 仓库文件。 |
| `src/devtools/model_export_package.py` | 97 | 仓库文件。 |
| `src/devtools/model_export_staging.py` | 56 | 仓库文件。 |
| `src/devtools/package_files.py` | 171 | 仓库文件。 |
| `src/devtools/program_package.py` | 75 | 仓库文件。 |
| `src/devtools/release_package.py` | 90 | 仓库文件。 |
| `src/devtools/runtime_package_boundaries.py` | 131 | 仓库文件。 |
| `src/devtools/window_lifecycle_monitor.py` | 295 | 仓库文件。 |
| `src/main.py` | 53 | 仓库文件。 |
| `src/open_yolo_tool.pyw` | 32 | 仓库文件。 |
| `src/runtime/settings.json` | 155 | 源码内默认配置参考。 |
| `src/services/__init__.py` | 2 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/__init__.py` | 80 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/ai_labeling.py` | 218 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/ai_prediction.py` | 111 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/ai_targets.py` | 68 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/annotation_models.py` | 14 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/circle_geometry.py` | 37 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/class_names.py` | 89 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/editable_document.py` | 27 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/file_index.py` | 57 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/geometry.py` | 42 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/history.py` | 123 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/labelme_document.py` | 99 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/preview_render.py` | 148 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/sam3_text.py` | 224 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/sam_assist.py` | 298 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/sam_onnx_canvas.py` | 110 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/sam_runtime.py` | 298 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/yolo_document.py` | 99 | 服务层与可测试业务逻辑实现。 |
| `src/services/annotation/yolo_format.py` | 71 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/__init__.py` | 34 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/backup.py` | 37 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/class_mapping.py` | 155 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/dataset_split.py` | 96 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/dataset_yaml.py` | 29 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/execute.py` | 138 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/formatting.py` | 72 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/labelme_parser.py` | 144 | 服务层与可测试业务逻辑实现。 |
| `src/services/conversion/types.py` | 77 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/__init__.py` | 45 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/path_display.py` | 56 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/rename.py` | 139 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/resize.py` | 103 | 服务层与可测试业务逻辑实现。 |
| `src/services/data_ops/sorting.py` | 14 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/__init__.py` | 5 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/distribution.py` | 192 | 服务层与可测试业务逻辑实现。 |
| `src/services/home/summary.py` | 84 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/__init__.py` | 48 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/activation.py` | 106 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/archive_extract.py` | 53 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/backend.py` | 136 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/calibration.py` | 36 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/calibration_images.py` | 45 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/calibration_pack.py` | 149 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/calibration_sources.py` | 104 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/capabilities.py` | 283 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/capability_rules.py` | 48 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/commands.py` | 105 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/execute.py` | 283 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/formats.py` | 159 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/inspection.py` | 54 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/manifest.py` | 107 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/native_archive.py` | 150 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/onnx_quantization.py` | 75 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/onnx_utils.py` | 124 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/onnx_validation.py` | 59 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/options.py` | 108 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/package.py` | 223 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/package_inspection.py` | 110 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/probe.py` | 48 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/runtime.py` | 132 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/sam_onnx.py` | 146 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/sam_onnx_components.py` | 105 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/sam_onnx_metadata.py` | 40 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/sam_onnx_runtime.py` | 140 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/sam_onnx_transaction.py` | 47 | 服务层与可测试业务逻辑实现。 |
| `src/services/model_export/types.py` | 80 | 服务层与可测试业务逻辑实现。 |
| `src/services/models/__init__.py` | 1 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/__init__.py` | 75 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/environment_probe.py` | 245 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/install_instance.py` | 126 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/managed_models.py` | 57 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/metadata.py` | 24 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/process_runner.py` | 204 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_catalog.py` | 183 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_download.py` | 91 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_environment.py` | 161 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_installer.py` | 49 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_manifest.py` | 123 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_updates.py` | 180 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/release_versions.py` | 61 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/variant.py` | 67 | 服务层与可测试业务逻辑实现。 |
| `src/services/runtime/windows_spawn.py` | 11 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/__init__.py` | 76 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/defaults.py` | 179 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/model.py` | 142 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/project_settings.py` | 177 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/storage.py` | 150 | 服务层与可测试业务逻辑实现。 |
| `src/services/settings/types.py` | 234 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/__init__.py` | 44 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/commands.py` | 113 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/model_catalog.py` | 136 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/model_resolution.py` | 59 | 服务层与可测试业务逻辑实现。 |
| `src/services/training/results_reader.py` | 153 | 服务层与可测试业务逻辑实现。 |
| `src/services/ultralytics_compat.py` | 29 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/__init__.py` | 46 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/model_catalog.py` | 72 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/prediction_runner.py` | 168 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/rendering.py` | 188 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/runtime_cleanup.py` | 22 | 服务层与可测试业务逻辑实现。 |
| `src/services/validation/source_collectors.py` | 158 | 服务层与可测试业务逻辑实现。 |
| `src/shared/__init__.py` | 1 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/paths.py` | 47 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/qt.py` | 72 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/theme.py` | 74 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/shared/utils/__init__.py` | 1 | 跨层共享基础模块、Qt 出口、路径与主题支持。 |
| `src/tests/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/architecture/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/architecture/test_structure_boundaries.py` | 350 | pytest 测试、结构约束与回归用例。 |
| `src/tests/conftest.py` | 82 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/images.py` | 11 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/ui_paths.py` | 69 | pytest 测试、结构约束与回归用例。 |
| `src/tests/helpers/ui_source.py` | 18 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_app_entry.py` | 228 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_cli_facades.py` | 18 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_cpu_package_guard.py` | 54 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_installer_artifacts.py` | 72 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_installer_lifecycle.py` | 118 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_installer_packaging_wiring.py` | 144 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_installer_variants.py` | 136 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_model_export_packaging.py` | 135 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_refactor_facades.py` | 25 | pytest 测试、结构约束与回归用例。 |
| `src/tests/integration/test_window_lifecycle_monitor.py` | 30 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/conftest.py` | 10 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_annotation_classes.py` | 59 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_annotation_document.py` | 184 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_annotation_history_and_targets.py` | 155 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_sam3_text.py` | 220 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/annotation/test_sam_assist.py` | 350 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/conversion/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/conversion/test_conversion_services.py` | 363 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/test_rename.py` | 87 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/data_ops/test_resize.py` | 74 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/home/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/home/test_summary.py` | 197 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/conftest.py` | 19 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_activation.py` | 65 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_calibration_pack.py` | 76 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_calibration_workflow.py` | 191 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_capability_matrix.py` | 148 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_command_generation.py` | 156 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_export_cli.py` | 120 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_extension_package.py` | 297 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_model_export_services.py` | 331 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_package_collector.py` | 220 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/model_export/test_sam2_export.py` | 275 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/conftest.py` | 21 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_companion_catalog.py` | 133 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_environment_probe.py` | 91 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_environment_updates.py` | 80 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_install_instance.py` | 109 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_managed_models.py` | 44 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_process_runner.py` | 73 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_release_archives.py` | 115 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_release_discovery.py` | 242 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_release_download.py` | 110 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_release_manifest_layers.py` | 239 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/runtime/test_variant.py` | 33 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/settings/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/settings/test_project_settings.py` | 183 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/training/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/training/test_training_services.py` | 198 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/test_model_catalog.py` | 25 | pytest 测试、结构约束与回归用例。 |
| `src/tests/services/validation/test_prediction_services.py` | 296 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_ai_prelabel.py` | 225 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_canvas_editing.py` | 195 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_classes.py` | 189 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_history.py` | 195 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_page_basics.py` | 195 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_page_commands.py` | 214 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_refactor_helpers.py` | 13 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_sam_dialogs.py` | 316 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_sam_lifecycle.py` | 241 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_sam_preview.py` | 167 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_sam_worker.py` | 152 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/annotation/test_annotation_task_mode.py` | 222 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/conftest.py` | 20 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_model_export_config.py` | 153 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_model_export_controls.py` | 220 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_model_export_discovery.py` | 81 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_model_export_drop_flow.py` | 72 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_model_export_format_matrix.py` | 135 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/data_processing/test_resize_tab.py` | 135 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/home/__init__.py` | 1 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/home/test_home_charts.py` | 67 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_dialog_messages.py` | 180 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_dialog_ownership.py` | 86 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_download_lifecycle.py` | 81 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_installer_lifecycle.py` | 106 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_resource_selection.py` | 299 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_selection_warnings.py` | 65 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_release_status.py` | 197 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/settings/test_settings_page.py` | 209 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shared/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shell/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/shell/test_shell_pages.py` | 194 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/training/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/training/test_training_page.py` | 200 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/validation/__init__.py` | 0 | pytest 测试、结构约束与回归用例。 |
| `src/tests/ui/validation/test_validation_page.py` | 269 | pytest 测试、结构约束与回归用例。 |
| `src/train_cli.py` | 118 | 仓库文件。 |
| `src/ui/__init__.py` | 1 | 仓库文件。 |
| `src/ui/app.py` | 20 | 仓库文件。 |
| `src/ui/features/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/actions.py` | 143 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/dialog.py` | 110 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/dialog_model_layout.py` | 126 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/dialog_result_layout.py` | 77 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/dialog_scope_layout.py` | 62 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/image_selection_dialog.py` | 285 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/mapping.py` | 192 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/preferences.py` | 112 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/prelabel_mapping.py` | 219 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/prelabel_runtime.py` | 185 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/ai/prelabel_state.py` | 224 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/annotation_settings_dialog.py` | 218 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/annotation_status_scan.py` | 88 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/commands.py` | 101 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/configuration.py` | 42 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/context_menu.py` | 217 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/drawing.py` | 159 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/editing.py` | 140 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/geometry.py` | 195 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/handle_render.py` | 72 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/history.py` | 34 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/hit_test.py` | 122 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/interaction.py` | 271 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/lifecycle.py` | 137 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/render.py` | 243 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/state.py` | 83 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/status.py` | 33 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/canvas/widget.py` | 46 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/class_conversion_dialog.py` | 85 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/class_dialogs.py` | 5 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/class_manager_dialog.py` | 198 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/class_panel.py` | 79 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/dialogs.py` | 7 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/draw_shape_dialog.py` | 125 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/draw_shape_layout.py` | 222 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/file_browser.py` | 66 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/file_item.py` | 82 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/file_list_render.py` | 151 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/layout.py` | 104 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/lifecycle.py` | 77 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/menus.py` | 172 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/page.py` | 114 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/persistence.py` | 171 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/project_paths.py` | 66 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/__init__.py` | 3 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/controller.py` | 66 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/hover_scheduler.py` | 139 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/model_state.py` | 130 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/runtime.py` | 190 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/runtime_bridge.py` | 228 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/settings_dialog.py` | 137 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/settings_layout.py` | 218 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/sam/settings_model.py` | 40 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/selection.py` | 80 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/settings_actions.py` | 152 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/shortcuts.py` | 66 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/task_mode.py` | 79 | 按功能分包的页面真实实现。 |
| `src/ui/features/annotation/toolbar.py` | 61 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/convert/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/convert/layout.py` | 89 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/convert/tab.py` | 203 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/__init__.py` | 3 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/availability.py` | 81 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/compat.py` | 85 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/config.py` | 96 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/controls.py` | 66 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/layout.py` | 34 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/layout_actions.py` | 38 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/layout_base.py` | 141 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/layout_components.py` | 17 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/layout_options.py` | 158 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/layout_primitives.py` | 50 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/layout_responsive.py` | 56 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/registry.py` | 17 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/runtime_actions.py` | 211 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/selection.py` | 130 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/state.py` | 294 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/tab.py` | 115 | 按功能分包的页面真实实现。 |
| `src/ui/features/data/model_export/visibility.py` | 176 | 按功能分包的页面真实实现。 |
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
| `src/ui/features/settings/environment_state.py` | 132 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/layout.py` | 141 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/page.py` | 104 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/release_state.py` | 121 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/state.py` | 61 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_dialog.py` | 115 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_dialog_download.py` | 267 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_dialog_install.py` | 174 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_dialog_layout.py` | 193 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_dialog_selection.py` | 241 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_dialog_state.py` | 283 | 按功能分包的页面真实实现。 |
| `src/ui/features/settings/update_toast.py` | 127 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/form.py` | 218 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/page.py` | 122 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/runtime.py` | 118 | 按功能分包的页面真实实现。 |
| `src/ui/features/training/state.py` | 270 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/__init__.py` | 1 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/_state_impl.py` | 42 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/config_state.py` | 114 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/dataset_mode.py` | 102 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/detection_actions.py` | 180 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/helpers.py` | 121 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/layout.py` | 19 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/left_layout.py` | 89 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/log_state.py` | 31 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/mode_state.py` | 129 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/models.py` | 92 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/page.py` | 49 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/page_actions.py` | 20 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/persistence_state.py` | 103 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/result_actions.py` | 171 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/result_layout.py` | 137 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/result_list.py` | 85 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/results.py` | 169 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/runtime.py` | 228 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/source_actions.py` | 296 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/source_state.py` | 93 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/sources.py` | 65 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/state.py` | 78 | 按功能分包的页面真实实现。 |
| `src/ui/features/validation/video_player.py` | 162 | 按功能分包的页面真实实现。 |
| `src/ui/helpers.py` | 53 | 仓库文件。 |
| `src/ui/shared/__init__.py` | 1 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/assets.py` | 41 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/context.py` | 131 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/dialogs.py` | 217 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/form_actions.py` | 23 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/form_cards.py` | 37 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/form_fields.py` | 297 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/form_pickers.py` | 27 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/forms.py` | 11 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/model_export_package.py` | 149 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/page_base.py` | 206 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/tasks.py` | 83 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/__init__.py` | 1 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/base.py` | 101 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/chart_primitives.py` | 42 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/charts.py` | 266 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/toggle_switch.py` | 77 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/widgets/training_curve.py` | 214 | 跨页面复用的表单、对话框与页面基类。 |
| `src/ui/shared/workers/__init__.py` | 13 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/ai_runtime.py` | 219 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/annotation_ai.py` | 93 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/base.py` | 30 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/detection.py` | 115 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shared/workers/model_labels.py` | 48 | 共享后台工作线程与子进程桥接。 |
| `src/ui/shell/__init__.py` | 1 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/close_guard.py` | 47 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/navigation.py` | 50 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/page_registry.py` | 34 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/program_log.py` | 27 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/style.py` | 7 | 主窗口壳层、样式与页面协调。 |
| `src/ui/shell/window.py` | 296 | 主窗口壳层、样式与页面协调。 |
| `docs/architecture.md` | 280 | 项目架构、打包与维护文档。 |
| `docs/packaging-windows.md` | 150 | 项目架构、打包与维护文档。 |
| `docs/spec/annotation.md` | 159 | 页面与功能规格说明。 |
| `docs/spec/data-processing.md` | 84 | 页面与功能规格说明。 |
| `docs/spec/home.md` | 45 | 页面与功能规格说明。 |
| `docs/spec/settings.md` | 75 | 页面与功能规格说明。 |
| `docs/spec/training.md` | 75 | 页面与功能规格说明。 |
| `docs/spec/validation.md` | 78 | 页面与功能规格说明。 |
| `installer/base-runtime-models-version.txt` | 1 | Windows 打包脚本与安装配置。 |
| `installer/build_base_runtime_models.ps1` | 94 | Windows 打包脚本与安装配置。 |
| `installer/build_model_export_runtime.ps1` | 58 | Windows 打包脚本与安装配置。 |
| `installer/build_windows.ps1` | 275 | Windows 打包脚本与安装配置。 |
| `installer/hooks/hook-torch.py` | 26 | Windows 打包脚本与安装配置。 |
| `installer/hooks/program_external_runtime.py` | 51 | Windows 打包脚本与安装配置。 |
| `installer/languages/ChineseSimplified.isl` | 0 | Windows 打包脚本与安装配置。 |
| `installer/model-export-runtime-version.txt` | 1 | Windows 打包脚本与安装配置。 |
| `installer/package_windows.ps1` | 309 | Windows 打包脚本与安装配置。 |
| `installer/packaging_menu.ps1` | 143 | Windows 打包脚本与安装配置。 |
| `installer/runtime-version.txt` | 1 | Windows 打包脚本与安装配置。 |
| `installer/vendor/sam2-1.1.0-cp312-cp312-win_amd64.whl` | 0 | Windows 打包脚本与安装配置。 |
| `installer/vendor/sam3-0.1.0-py3-none-any.whl` | 0 | Windows 打包脚本与安装配置。 |
| `installer/vendor/sam3-LICENSE.txt` | 61 | Windows 打包脚本与安装配置。 |
| `installer/yolo_tool.iss` | 1440 | Windows 打包脚本与安装配置。 |
| `installer/YOLOTool.spec` | 314 | Windows 打包脚本与安装配置。 |

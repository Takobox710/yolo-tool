# 代码与结构清单

该文档由扫描仓库生成，统计了主要源码、测试、文档和打包脚本的行数与职责。

## 目录摘要

- `(root)`: 7 个文件，1950 行文本；仓库根目录入口与说明文件。
- `scr/services`: 15 个文件，2923 行文本；服务层，可测试业务逻辑。
- `scr/ui/views`: 29 个文件，6400 行文本；各功能页面与训练/验证页拆分模块。
- `scr/ui/widgets`: 3 个文件，421 行文本；共享控件。
- `scr/ui`: 9 个文件，1113 行文本；主窗口、页面基类、表单混入、工作线程与 UI 辅助。
- `scr/tests`: 23 个文件，3818 行文本；pytest 测试。
- `docs/spec`: 6 个文件，268 行文本；功能规格文档。
- `docs`: 3 个文件，363 行文本；架构、清单与打包文档。
- `installer/hooks`: 3 个文件，28 行文本；PyInstaller hooks。
- `installer`: 5 个文件，410 行文本；Windows 打包与安装脚本。
- `scr/assets`: 2 个文件，0 行文本；图标资源。
- `scr/runtime`: 1 个文件，95 行文本；默认配置参考。
- `scr`: 8 个文件，282 行文本；应用入口与核心包。

## 文件清单

| 文件 | 行数 | 作用 |
|---|---:|---|
| `AGENTS.md` | 127 | 项目级 AI 协作约束、目录职责、修改流程与测试要求。 |
| `codex_patch.diff` | 103 | 最近一次补丁变更记录，主要用于人工对照。 |
| `docs/architecture.md` | 201 | 项目架构、分层边界、维护阈值与拆分策略说明。 |
| `docs/code-inventory.md` | 130 | 仓库代码与结构清单，统计主要文件行数与职责。 |
| `docs/packaging-windows.md` | 32 | Windows 打包命令与推荐模式说明。 |
| `docs/spec/annotation.md` | 47 | 数据标注页交互与布局规格。 |
| `docs/spec/data-processing.md` | 47 | 数据处理子模块规格。 |
| `docs/spec/home.md` | 35 | 主页信息布局与展示规格。 |
| `docs/spec/settings.md` | 18 | 系统设置页规格与系统信息要求。 |
| `docs/spec/training.md` | 67 | 训练页字段、模型选择与运行交互规格。 |
| `docs/spec/validation.md` | 54 | 验证页布局、模式与结果展示规格。 |
| `installer/build_windows.ps1` | 63 | 正式版或开发版 Windows 构建入口。 |
| `installer/hooks/hook-PySide6.scripts.deploy_lib.py` | 1 | PyInstaller hook 占位，补齐 PySide6 部署依赖。 |
| `installer/hooks/hook-torch.py` | 26 | PyInstaller hook，补齐 torch 打包依赖。 |
| `installer/hooks/hook-torch.utils.tensorboard.py` | 1 | PyInstaller hook 占位，补齐 tensorboard 依赖。 |
| `installer/package_windows.ps1` | 79 | PyInstaller/Inno Setup 打包协调脚本。 |
| `installer/yolo_tool.iss` | 83 | Inno Setup 安装包脚本。 |
| `installer/YOLOTool.spec` | 106 | PyInstaller 打包清单与资源收集配置。 |
| `installer/打包程序.ps1` | 79 | 中文别名的一键打包脚本。 |
| `pixi.lock` | 1319 | Pixi 锁文件，固定依赖版本与平台解析结果。 |
| `pixi.toml` | 31 | Pixi 工作区、依赖与运行任务定义。 |
| `README.md` | 356 | 项目说明、功能概览、使用方法与开发打包指南。 |
| `scr/__init__.py` | 1 | 源码包标记文件。 |
| `scr/app.py` | 7 | 对外暴露的 GUI 启动包装函数。 |
| `scr/assets/app_icon.ico` | 二进制 | Windows 应用图标资源。 |
| `scr/assets/app_icon.png` | 二进制 | 应用图标 PNG 资源。 |
| `scr/context.py` | 25 | 应用上下文与服务容器定义。 |
| `scr/main.py` | 37 | 统一入口，负责 GUI/隐藏 CLI 启动分发。 |
| `scr/open_yolo_tool.pyw` | 32 | Windows 无控制台启动器与启动失败提示。 |
| `scr/paths.py` | 20 | 应用根路径解析工具。 |
| `scr/runtime/settings.json` | 95 | 源码内默认设置参考模板。 |
| `scr/services/__init__.py` | 2 | 服务层包标记与导出。 |
| `scr/services/annotation_ai_service.py` | 265 | AI 预标注服务，负责模型解析、图片筛选与批量标注写回。 |
| `scr/services/annotation_service.py` | 146 | YOLO 标注读取与预览渲染服务。 |
| `scr/services/conversion_service.py` | 570 | Labelme/YOLO 转换、类别映射、划分与执行主服务。 |
| `scr/services/detection_service.py` | 423 | 验证/检测模型扫描、输入源收集、结果提取、日志文案与结果保存服务。 |
| `scr/services/editable_annotation_service.py` | 287 | 可编辑标注与 Labelme/YOLO 双向读写服务。 |
| `scr/services/environment_service.py` | 85 | Pixi、Torch/CUDA 与系统环境探测服务。 |
| `scr/services/path_service.py` | 43 | 项目路径解析、相对路径显示与训练结果模型简化显示服务。 |
| `scr/services/process_utils.py` | 11 | Windows 隐藏子进程启动参数工具。 |
| `scr/services/rename_service.py` | 142 | 图片与标签重命名预览和执行服务。 |
| `scr/services/resize_service.py` | 102 | 图片缩放预览与批量执行服务。 |
| `scr/services/runtime_service.py` | 122 | 后台进程启动、日志清洗与停止控制服务。 |
| `scr/services/settings_service.py` | 323 | 项目设置、默认值、深合并与路径序列化服务。 |
| `scr/services/training_service.py` | 373 | 训练模型发现、模型 YAML 扫描、任务模式推断与训练命令拼装服务。 |
| `scr/services/ultralytics_compat.py` | 29 | Ultralytics 与 cv2 HighGUI 兼容处理。 |
| `scr/tests/conftest.py` | 7 | pytest 共享夹具入口。 |
| `scr/tests/helpers/__init__.py` | 0 | 测试辅助包标记文件。 |
| `scr/tests/helpers/ui_paths.py` | 36 | UI 测试用路径与模块读取辅助。 |
| `scr/tests/test_app_entry.py` | 198 | 入口、打包文档、图标与 UI 源码结构相关测试。 |
| `scr/tests/test_architecture_boundaries.py` | 63 | 分层边界、文件体量与 helper 边界约束测试。 |
| `scr/tests/test_services_annotation.py` | 113 | 标注服务测试。 |
| `scr/tests/test_services_conversion.py` | 376 | 转换服务测试。 |
| `scr/tests/test_services_detection.py` | 205 | 检测服务测试。 |
| `scr/tests/test_services_environment.py` | 96 | 环境探测服务测试。 |
| `scr/tests/test_services_misc.py` | 33 | 杂项服务与工具行为测试。 |
| `scr/tests/test_services_rename.py` | 107 | 重命名服务测试。 |
| `scr/tests/test_services_resize.py` | 105 | 缩放服务测试。 |
| `scr/tests/test_services_runtime.py` | 87 | 运行时进程与日志处理测试。 |
| `scr/tests/test_services_settings.py` | 172 | 设置加载、深合并与恢复默认值测试。 |
| `scr/tests/test_services_training.py` | 268 | 训练命令、模型解析与训练指标读取测试。 |
| `scr/tests/test_ui_annotation.py` | 435 | 标注页面与 AI 预标注交互测试。 |
| `scr/tests/test_ui_convert.py` | 92 | 转换页面与类别映射弹窗测试。 |
| `scr/tests/test_ui_misc.py` | 44 | 页面基类与共享 UI 杂项测试。 |
| `scr/tests/test_ui_resize.py` | 79 | 缩放页面布局与默认值测试。 |
| `scr/tests/test_ui_settings.py` | 162 | 设置页布局、刷新与恢复默认值测试。 |
| `scr/tests/test_ui_shell.py` | 453 | 主壳窗口、导航、页面装配与共享 UI 行为测试。 |
| `scr/tests/test_ui_training.py` | 306 | 训练页模型选择、持久化与停止流程测试。 |
| `scr/tests/test_ui_validation.py` | 381 | 验证页模型列表、模式切换与检测流程测试。 |
| `scr/theme.py` | 59 | 全局 Qt 主题样式表。 |
| `scr/train_cli.py` | 101 | 打包后训练、导出、验证命令行入口。 |
| `scr/ui/__init__.py` | 1 | UI 包标记文件。 |
| `scr/ui/app.py` | 14 | Qt 应用实例创建与主窗口启动。 |
| `scr/ui/dialogs.py` | 209 | 通用命令弹窗和类别映射弹窗。 |
| `scr/ui/forms.py` | 353 | 表单字段、帮助提示、通用文件选择与卡片构建混入。 |
| `scr/ui/helpers.py` | 64 | UI 层轻量纯函数，如首页布局与排序辅助。 |
| `scr/ui/page_base.py` | 139 | 页面基类、状态栏和只读日志文本框等共享基础能力。 |
| `scr/ui/qt.py` | 41 | PySide6/Qt 常用符号集中导入出口。 |
| `scr/ui/views/__init__.py` | 1 | 页面子模块包标记文件。 |
| `scr/ui/views/annotation.py` | 544 | 数据标注主页面，组织图片列表、画布、类别与 AI 标注流程。 |
| `scr/ui/views/annotation_ai_dialog.py` | 592 | AI 预标注主对话框，配置模型、范围、映射与执行。 |
| `scr/ui/views/annotation_ai_image_dialog.py` | 283 | 自定义 AI 预标注图片选择对话框。 |
| `scr/ui/views/annotation_ai_mapping.py` | 112 | AI 标签映射表配置与状态汇总辅助函数。 |
| `scr/ui/views/annotation_ai_preferences.py` | 82 | AI 预标注偏好读取、保存与展示辅助函数。 |
| `scr/ui/views/annotation_canvas.py` | 776 | 标注画布，负责绘制、编辑、缩放和交互。 |
| `scr/ui/views/annotation_dialogs.py` | 252 | 标注设置、绘制形状、类别管理相关对话框。 |
| `scr/ui/views/convert.py` | 349 | 标注转换页面。 |
| `scr/ui/views/data.py` | 55 | 数据处理页面容器，挂载转换/预览/重命名/缩放子页。 |
| `scr/ui/views/home.py` | 369 | 主页总览，展示项目概况、曲线和模型摘要。 |
| `scr/ui/views/preview.py` | 174 | 标注预览页面。 |
| `scr/ui/views/rename.py` | 203 | 文件重命名页面。 |
| `scr/ui/views/resize.py` | 150 | 图片缩放页面。 |
| `scr/ui/views/settings.py` | 268 | 系统设置页面。 |
| `scr/ui/views/training.py` | 83 | 训练页面入口，负责页面装配与方法兼容导出。 |
| `scr/ui/views/training_form.py` | 218 | 训练页表单、状态卡和日志面板布局构建。 |
| `scr/ui/views/training_runtime.py` | 115 | 训练启动、停止、日志轮询与结果目录打开逻辑。 |
| `scr/ui/views/training_state.py` | 275 | 训练配置收集、设置持久化和命令预览逻辑。 |
| `scr/ui/views/validation.py` | 318 | 验证页面入口，负责装配、导航和兼容方法外观。 |
| `scr/ui/views/validation_dataset.py` | 92 | 数据集验证模式的启动、轮询、恢复与收尾逻辑。 |
| `scr/ui/views/validation_helpers.py` | 121 | 验证页 YAML 补丁、结果导航等辅助逻辑。 |
| `scr/ui/views/validation_layout.py` | 184 | 验证页布局构建函数。 |
| `scr/ui/views/validation_models.py` | 87 | 验证模型候选项构建与封装。 |
| `scr/ui/views/validation_result_list.py` | 83 | 检测结果列表弹窗或列表展示辅助。 |
| `scr/ui/views/validation_results.py` | 73 | 检测结果渲染与缓存结果回显逻辑。 |
| `scr/ui/views/validation_runtime.py` | 180 | 验证页检测启动、停止、worker 管理与数据集验证桥接逻辑。 |
| `scr/ui/views/validation_sources.py` | 57 | 验证输入源路径解析与采集逻辑。 |
| `scr/ui/views/validation_state.py` | 304 | 验证页模型状态、设置持久化、输入源与临时 YAML 管理逻辑。 |
| `scr/ui/widgets/__init__.py` | 1 | 共享控件包标记文件。 |
| `scr/ui/widgets/base.py` | 88 | 基础卡片、图片视图与滚动区控件。 |
| `scr/ui/widgets/charts.py` | 332 | 数据集分布图和训练曲线图控件。 |
| `scr/ui/window.py` | 201 | 主工作台窗口、导航与页面装配。 |
| `scr/ui/workers.py` | 91 | 线程工作器，封装检测与 AI 预标注后台任务。 |
| `YOLOTool.lnk` | 二进制 | 桌面快捷方式二进制文件。 |
| `打包程序.bat` | 14 | Windows 下调用 PowerShell 打包脚本的批处理入口。 |

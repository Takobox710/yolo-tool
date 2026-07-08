# 第二阶段收口计划（去兼容层、定型 `src` 结构、建立长期稳定架构）

## 摘要

本阶段目标不是继续“迁移到 `src`”，而是把当前过渡态彻底收口成唯一真结构。最终交付标准是：项目在 `src/` 下只保留一套真实实现路径，不再存在 `ui/legacy`、`ui/views`、顶层 `ui` 壳、`*_service.py`、`cli_dispatch_legacy.py` 这类长期兼容层；测试、文档、打包、架构约束全部以新结构为准。

已锁定的长期策略：完全删旧路径。允许在单个实现分支中短暂用 re-export 过渡，但最终合入前必须删掉所有旧路径与兼容桥，只保留公开类名和入口命令，不保留旧模块导入路径。

最终结构原则：

- `src/main.py`、`src/app.py`、`src/train_cli.py` 保留为公开入口
- `src/ui/features/*` 是页面真实实现
- `src/ui/shared/*` 是跨页面共享 UI 能力
- `src/ui/shell/*` 是主窗口与导航壳
- `src/services/<domain>/*` 是唯一业务实现
- `src/shared/*` 是跨层共享基础模块
- `src/tests/*` 只引用新结构，不再引用旧壳

## 关键实现变更

### 1. 清空所有兼容层并建立唯一导入面

最终删除以下过渡层：

- `src/ui/legacy/`
- `src/ui/views/`
- `src/ui/window.py`
- `src/ui/workers.py`
- `src/ui/page_base.py`
- `src/ui/forms.py`
- `src/ui/dialogs.py`
- `src/ui/qt.py`
- `src/context.py`
- `src/paths.py`
- `src/theme.py`
- `src/bootstrap/cli_dispatch_legacy.py`
- `src/services/*_service.py` 整体旧平铺实现

最终唯一保留的顶层公开入口：

- `src/main.py`
- `src/app.py`
- `src/train_cli.py`

最终唯一保留的公开页面类名：

- `AnnotationPage`
- `HomePage`
- `TrainPage`
- `ValidatePage`
- `SettingsPage`
- `DataPage`
- `ConvertTab`
- `PreviewTab`
- `RenameTab`
- `ResizeTab`

这些类名保留，但定义位置改为新结构内真实实现，不再通过旧 `views` 间接转发。

### 2. UI 页面层完全迁入 `features`

把当前仍在 `src/ui/views/*.py` 中承载真实逻辑的实现，完整迁入 `src/ui/features/*`：

- `home`
  - `page.py` 承载真实 `HomePage`
  - 可新增 `summary_cards.py`、`dataset_stats.py`、`training_summary.py`
- `data`
  - `page.py` 承载真实 `DataPage`
  - `convert/preview/rename/resize` 各自承载真实 tab
- `training`
  - `page.py` 承载真实 `TrainPage`
  - `form.py`、`state.py`、`runtime.py`、`command_preview.py`
  - 删除当前 `lambda self` 方式绑定方法，全部改为显式方法或组合式 helper
- `validation`
  - `page.py` 承载真实 `ValidatePage`
  - `layout.py`、`state.py`、`runtime.py`、`dataset_mode.py`、`results.py`、`result_list.py`、`models.py`、`sources.py`
- `settings`
  - `page.py` 承载真实 `SettingsPage`
  - `environment_panel.py`、`preferences_panel.py`、`program_log_panel.py`
- `annotation`
  - `page.py` 承载真实 `AnnotationPage`
  - `toolbar.py`、`file_browser.py`、`class_panel.py`、`selection.py`、`persistence.py`、`actions.py`、`dialogs.py`
  - `ai/` 下承载 AI 预标注相关 UI

迁移完成后，`features/*/page.py` 不允许再 `from src.ui.views... import ...`，必须直接定义真实类。

### 3. 标注模块作为第二阶段主战场彻底拆分

这是本阶段最高优先级，因为当前最大历史包袱在：

- `src/ui/legacy/annotation_page_impl.py`
- `src/ui/legacy/annotation_canvas_impl.py`
- `src/tests/test_ui_annotation.py`

固定拆分方案：

- 页面逻辑迁入 `src/ui/features/annotation/`
  - `page.py`
  - `toolbar.py`
  - `file_browser.py`
  - `class_panel.py`
  - `selection.py`
  - `persistence.py`
  - `actions.py`
  - `dialogs.py`
  - `ai/dialog.py`
  - `ai/image_selection_dialog.py`
  - `ai/mapping.py`
  - `ai/preferences.py`
  - `ai/controller.py`
- 画布逻辑迁入 `src/ui/features/annotation/canvas/`
  - `widget.py`
  - `render.py`
  - `geometry.py`
  - `hit_test.py`
  - `interaction.py`
  - `context_menu.py`
  - `state.py`
  - `shortcuts.py`

要求：

- `widget.py` 只保留 Qt 事件入口、信号、状态对象挂接
- 绘制、命中测试、手柄逻辑、坐标换算、hover/flash、右键菜单都必须脱离单文件巨石
- `AnnotationPage` 不再直接写文件删除、批量刷新、上下文菜单拼装、AI 对话框细节
- 可抽出稳定内部类型到 `src/shared/types.py` 或 `src/services/annotation/types.py`，至少包括：
  - `AnnotationSession`
  - `CanvasViewState`
  - `AnnotationAction`
  - `DrawShapeMode`

阶段完成标志：

- `src/ui/legacy/` 全目录删除
- `src/ui/features/annotation/page.py` 和 `canvas/widget.py` 不再有 `import *`
- `test_ui_annotation.py` 不再依赖 `src.ui.views.annotation*` 或 `src.ui.legacy.*`

### 4. 共享 UI 和主窗口壳彻底定型

把现在“新目录 + 旧实现”的共享层收口成真实结构：

- `src/ui/shell/`
  - `window.py`：唯一 `WorkbenchWindow`
  - `navigation.py`：页面创建、切页
  - `page_registry.py`：页面名到工厂映射
  - `close_guard.py`：关闭确认、未保存标注、训练中确认
  - `program_log.py`：程序日志缓冲与系统设置日志展示
  - `style.py`：唯一 `build_style`
- `src/ui/shared/`
  - `page_base.py`：唯一基础页面能力
  - `forms.py`：唯一表单字段和通用文件选择
  - `dialogs.py`：唯一共享弹窗
  - `widgets/base.py`、`widgets/charts.py`
  - `workers/`
    - `base.py`
    - `detection.py`
    - `ai_runtime.py`
    - `annotation_ai.py`
    - `model_labels.py`

要求：

- `src/ui/shared/workers/legacy.py` 删除
- 每个 worker 文件必须包含真实实现，不再只是转发 6 行壳
- `src/ui/window.py`、`src/ui/workers.py` 删除
- `src/ui/page_base.py`、`src/ui/forms.py`、`src/ui/dialogs.py`、`src/ui/qt.py` 删除
- 所有 UI 代码统一从 `src.ui.shared` 和 `src.shared.qt` 导入，不再混用顶层壳

### 5. 服务层从“平铺 + 空分包”收口为真实领域包

最终状态是：`src/services/*.py` 旧平铺实现全部拆完并删除，只保留领域包。

固定拆分目标：

- `src/services/settings/`
  - `defaults.py`
  - `project_settings.py`
  - `app_state.py`
  - `merge.py`
  - `schema.py`
- `src/services/runtime/`
  - `process_runner.py`
  - `log_sanitizer.py`
  - `environment_probe.py`
  - `windows_spawn.py`
- `src/services/models/`
  - `catalog.py`
  - `references.py`
  - `yaml_registry.py`
  - `types.py`
- `src/services/annotation/`
  - `labelme_io.py`
  - `yolo_io.py`
  - `editable_document.py`
  - `preview_render.py`
  - `geometry.py`
  - `ai_labeling.py`
  - `types.py`
- `src/services/conversion/`
  - `preview.py`
  - `execute.py`
  - `class_mapping.py`
  - `labelme_parser.py`
  - `dataset_split.py`
  - `dataset_yaml.py`
  - `backup.py`
  - `formatting.py`
  - `types.py`
- `src/services/training/`
  - `command_builder.py`
  - `model_resolution.py`
  - `results_reader.py`
  - `dataset_repair.py`
  - `types.py`
- `src/services/validation/`
  - `source_collectors.py`
  - `result_parser.py`
  - `prediction_runner.py`
  - `save_outputs.py`
  - `dataset_validation.py`
  - `rendering.py`
  - `types.py`
- `src/services/data_ops/`
  - `rename.py`
  - `resize.py`
  - `path_display.py`

要求：

- `src/services/annotation_ai_service.py`
- `src/services/annotation_service.py`
- `src/services/conversion_service.py`
- `src/services/detection_service.py`
- `src/services/editable_annotation_service.py`
- `src/services/environment_service.py`
- `src/services/path_service.py`
- `src/services/process_utils.py`
- `src/services/rename_service.py`
- `src/services/resize_service.py`
- `src/services/runtime_service.py`
- `src/services/settings_service.py`
- `src/services/training_service.py`

这些旧文件在阶段结束时全部删除或只在分支中临时辅助迁移，最终合入前不得保留。

统一规则：

- 所有 UI 和 CLI 只依赖 `src.services.<domain>.*`
- `src.services` 继续禁止导入 `src.ui`
- 模型发现统一走 `src.services.models.catalog`
- 后台进程、日志清洗、隐藏窗口参数统一走 `src.services.runtime.*`

### 6. CLI、入口与共享基础层收口

最终只保留一套基础模块位置：

- `src/bootstrap/context.py` 为唯一上下文定义
- `src/shared/paths.py` 为唯一路径定义
- `src/shared/theme.py` 为唯一主题定义
- `src/shared/qt.py` 为唯一 Qt 导出
- `src/bootstrap/cli_dispatch.py` 为唯一 CLI 分发

要求：

- 删除 `src/context.py`
- 删除 `src/paths.py`
- 删除 `src/theme.py`
- 删除 `src/bootstrap/cli_dispatch_legacy.py`
- `src/train_cli.py` 只做参数解析和向 `cli_dispatch.py` 分发
- `src/main.py` 不再直接引用旧平铺服务模块
- `src/open_yolo_tool.pyw`、打包脚本、README 命令示例全部只引用最终入口

### 7. 测试体系从旧路径切换到最终结构

测试本身也是兼容层残留的来源，必须同时迁。

测试目录组织最终定型为：

- `src/tests/architecture/`
- `src/tests/services/annotation/`
- `src/tests/services/conversion/`
- `src/tests/services/training/`
- `src/tests/services/validation/`
- `src/tests/services/settings/`
- `src/tests/services/runtime/`
- `src/tests/ui/annotation/`
- `src/tests/ui/training/`
- `src/tests/ui/validation/`
- `src/tests/ui/settings/`
- `src/tests/ui/shell/`
- `src/tests/ui/data/`
- `src/tests/integration/`

要求：

- 现有平铺 `test_ui_*.py` 和 `test_services_*.py` 迁入对应子目录
- `src/tests/helpers/ui_paths.py` 只指向新结构，不再引用 `src/ui/views/*`
- 所有测试 import 最终改为：
  - `src.ui.features.*`
  - `src.ui.shared.*`
  - `src.ui.shell.*`
  - `src.services.<domain>.*`
- 测试不得再导入：
  - `src.ui.views.*`
  - `src.ui.legacy.*`
  - `src.services.*_service`
  - `src.ui.window`
  - `src.ui.workers`
  - `src.context`
  - `src.paths`
  - `src.theme`

### 8. 架构约束升级为“防退化围栏”

当前结构测试过于宽松，第二阶段必须升级成最终围栏。

新增或改造以下架构约束：

- 禁止仓库内业务代码与测试导入 `src.ui.views.*`
- 禁止仓库内业务代码与测试导入 `src.ui.legacy.*`
- 禁止出现 `import *` 从实现模块导入
- 禁止保留 `src/services/*_service.py`
- 禁止保留 `src/ui/shared/workers/legacy.py`
- 禁止保留 `src/ui/window.py`、`src/ui/workers.py`、`src/ui/page_base.py`、`src/ui/forms.py`、`src/ui/dialogs.py`、`src/ui/qt.py`
- `src/ui/features/*/page.py` 文件上限 `250` 行
- `src/ui/features/annotation/canvas/*` 文件上限 `250` 行
- `src/ui/shared/workers/*` 文件上限 `220` 行
- `src/services/<domain>/*` 文件上限 `300` 行
- `src/ui/shared/page_base.py` 禁止包含页面专属业务逻辑
- `src/services/<domain>/__init__.py` 只能做轻量导出，不能塞实现
- `docs/code-inventory.md` 必须由 `src/devtools/generate_code_inventory.py` 生成，并由测试校验其最新性
- `docs/architecture.md` 中声明的目录边界必须与当前真实路径一致

### 9. 文档、打包与规范同步到最终结构

阶段结束前必须同步回写：

- `AGENTS.md`
  - 删除对 `src/ui/views/`、顶层 `ui/page_base.py`、`process_utils.py`、`runtime_service.py` 这类旧路径的直接结构说明
  - 改为最终 `features/shared/shell/services/<domain>` 结构
  - 保留不变的外部入口和 5 次失败停止规则
- `docs/architecture.md`
  - 以最终目录重写，不再描述迁移态
- `docs/spec/*.md`
  - 引用最终页面实现路径与共享模块路径
- `docs/code-inventory.md`
  - 重新生成，反映最终结构
- `docs/packaging-windows.md`
  - 只描述最终入口和打包链路
- `installer/YOLOTool.spec`
- `installer/build_windows.ps1`
- `installer/yolo_tool.iss`

要求：

- 打包说明与实际 `src/main.py`、`src/train_cli.py`、`src/assets/*` 路径一致
- 文档中不再把旧路径描述成仍然存在的真实结构

## 测试与验收

必须完成以下检查才允许结束第二阶段：

- `pixi run check`
- `pixi run test`
- `pixi run app`
- `python -m src.main`
- Windows 打包脚本至少做一次可执行验证
- `YOLOTool.exe --yolo-train / --yolo-export / --yolo-val` 入口约定保持不变

必须覆盖的回归场景：

- 标注页
  - 打开目录、切图、选中、删除、撤销
  - detect / obb / polygon 绘制
  - Labelme / YOLO 保存
  - 脏状态提示
  - AI 预标注
- 训练页
  - 模型选择
  - 命令预览
  - 开始 / 停止
  - 结果目录打开
  - 曲线读取
- 验证页
  - 模型扫描
  - 单图 / 批量 / 摄像头 / 数据集验证
  - 结果展示
  - 标签导出
  - `best.pt / last.pt` 开关
- 设置页
  - 默认值
  - 恢复默认
  - 最近项目
  - 环境信息
  - 程序日志面板
- 数据处理页
  - 转换、预览、重命名、压缩页可构造并维持原有行为
- 架构与文档
  - 无旧路径导入
  - 无旧兼容文件残留
  - 文档与代码一致
  - inventory 生成通过

最终完成标准：

- `src/ui/legacy/` 不存在
- `src/ui/views/` 不存在
- `src/services/*_service.py` 不存在
- `src/ui/shared/workers/legacy.py` 不存在
- 业务代码和测试不再引用任何旧兼容模块
- 新结构成为唯一真结构
- 后续新增功能只需要在 `features/shared/shell/services/<domain>` 中按局部演进，不再需要第三次大重构

## 假设与默认决策

- 默认允许在实现分支中短暂使用 re-export 迁移，但最终提交前必须删净
- 公开入口与公开类名保持不变，模块路径不保持兼容
- 本阶段不新增业务功能，只做结构收口、测试迁移、文档同步、打包对齐
- `data/runtime/settings.json`、`data/runtime/app_state.json`、`data/models/` 规则不改
- 训练、验证、AI 预标注继续使用后台隐藏子进程
- 如果编译或测试连续 5 次失败仍未解决，必须立即停止并汇报
- 如果最终需要 git 提交，只允许在全部完成后做一次总提交

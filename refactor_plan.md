# YOLO Tool 一步到位重构总计划（结构优化 + `scr` 全量迁移到 `src`）

## 摘要

本次重构把两件事合并为同一次、同一分支、一次收口的工作：

1. 彻底把源码根目录从 `scr/` 更正为 `src/`
2. 同时完成项目结构的深度重组，解决当前 UI 巨型文件、服务层职责过宽、测试平铺、文档失真、壳层膨胀等问题

这次不是“先改名、再优化”，也不是“先优化、以后再改名”，而是直接落到最终结构，避免二次搬迁和重复改测试、文档、打包链路。

已确认的触发点：

- `annotation.py`、`annotation_canvas.py` 已明显超维护阈值，且 `test_architecture_boundaries` 已真实失败
- `workers.py`、`window.py`、`train_cli.py` 已经开始承担过多职责
- `conversion_service.py`、`detection_service.py` 等服务文件继续增长会进一步恶化
- 仓库内对 `scr` 的命令、导入、路径、文档、打包配置存在大量硬编码，适合借这次大重构一次性统一清掉
- 目录名改为 `src`，并且不保留旧 `scr` 路径兼容

本计划默认目标是：最终仓库里不再保留业务相关的 `scr` 引用，源码、测试、打包、文档、规范统一使用 `src`。

## 外部契约与最终口径

这次保留的对外契约只有“能力”和“页面类名”，不保留旧路径。

保留不变：

- GUI 仍由 `main.py` 统一分发 GUI / 隐藏 CLI 入口
- 打包后训练、导出、验证仍通过 `YOLOTool.exe --yolo-train / --yolo-export / --yolo-val` 进入 Python 入口
- 公开页面类名继续保留：`AnnotationPage`、`ValidatePage`、`TrainPage`、`HomePage`
- 数据与设置落盘规则保持不变：
  - `data/runtime/settings.json`
  - `data/runtime/app_state.json`
  - `data/models/`
- Windows 隐藏后台子进程、日志清洗、训练 / 验证单实例等行为规则保持不变

明确变更：

- `python -m scr.main` 改为 `python -m src.main`
- `pixi run app`、`pixi run app-qt` 改为调用 `python -m src.main`
- `pixi run test` 改为 `pytest src/tests -q`
- `pixi run check` 改为 `python -m compileall src`
- 所有 `from scr...` / `import scr...` 改为 `src...`
- 所有文档、架构规则、打包配置、测试断言统一改为 `src`

不保留：

- `scr/` 兼容壳
- `scr.*` 导入兼容
- `python -m scr.main` 兼容命令
- 旧扁平目录为了兼容而保留的历史文件

## 目标结构

最终结构直接落到 `src/`，并按“功能优先 + 包内分层”重建：

```text
src/
├── __init__.py
├── main.py
├── app.py
├── train_cli.py
├── open_yolo_tool.pyw
├── bootstrap/
│   ├── __init__.py
│   ├── context.py
│   ├── app_factory.py
│   └── cli_dispatch.py
├── shared/
│   ├── __init__.py
│   ├── paths.py
│   ├── theme.py
│   ├── qt.py
│   ├── types.py
│   └── utils/
├── runtime/
│   └── settings.json
├── assets/
│   ├── app_icon.png
│   └── app_icon.ico
├── services/
│   ├── __init__.py
│   ├── settings/
│   ├── runtime/
│   ├── models/
│   ├── annotation/
│   ├── conversion/
│   ├── training/
│   ├── validation/
│   └── data_ops/
├── ui/
│   ├── __init__.py
│   ├── shell/
│   ├── shared/
│   └── features/
│       ├── home/
│       ├── data/
│       ├── annotation/
│       ├── training/
│       ├── validation/
│       └── settings/
└── tests/
    ├── conftest.py
    ├── helpers/
    ├── architecture/
    ├── services/
    ├── ui/
    └── integration/
```

设计原则固定如下：

- `main.py`、`app.py`、`train_cli.py` 只做稳定入口，不承载复杂实现
- `ui/features/*` 负责页面装配、控件状态、信号连接
- `ui/shared/*` 负责跨页面 Qt 组件、基类、通用对话框、worker
- `services/*` 承担可测试业务逻辑，不导入任何 `src.ui`
- `shared/*` 放跨层共用的基础模块与类型
- 所有“扁平大文件”优先拆成功能包，而不是拆成更多扁平文件

## 关键结构重组

### 1. 启动与基础层重组

把当前顶层杂项模块整理为稳定基础层：

- `src/main.py`
  - 只负责识别 GUI 模式与隐藏 CLI 模式
  - 只做入口分发，不承载训练、验证细节
- `src/app.py`
  - 保留 GUI 启动门面
- `src/train_cli.py`
  - 保留打包后 CLI 门面
  - 具体逻辑迁入 `src/bootstrap/cli_dispatch.py`
- `src/bootstrap/context.py`
  - 原 `context.py` 迁入这里
  - 作为应用上下文、服务装配与根对象创建点
- `src/shared/paths.py`
  - 原 `paths.py` 迁入这里
- `src/shared/theme.py`
  - 原 `theme.py` 迁入这里
- `src/shared/qt.py`
  - 原 `ui/qt.py` 上移为全局共享 Qt 出口

要求：

- 顶层文件不再承载业务逻辑
- 顶层只保留“入口职责”，其余实现都进入 `bootstrap/shared/services/ui`
- 新代码禁止再往 `main.py`、`app.py`、`train_cli.py` 里堆功能

### 2. UI 壳层重组

当前 `window.py` 和部分共享 UI 模块继续变大会形成第二批巨石，因此直接拆成专门的 shell/shared 结构。

`src/ui/shell/` 固定拆分为：

- `window.py`
  - `WorkbenchWindow` 主壳
  - 只保留窗口生命周期、页面切换协调、总入口行为
- `navigation.py`
  - 页面注册、页面创建、切页逻辑
- `page_registry.py`
  - 页面名到页面工厂的注册表
- `close_guard.py`
  - 关闭前确认、未保存标注检查、训练中断确认
- `program_log.py`
  - 程序级日志缓冲与系统设置日志窗展示逻辑
- `style.py`
  - 原 `build_style` 迁入这里

`src/ui/shared/` 固定拆分为：

- `page_base.py`
  - 只保留真正跨页面的基础能力
- `forms.py`
  - 通用字段、帮助提示、文件选择
- `dialogs.py`
  - 通用命令弹窗、共享选择弹窗
- `widgets/`
  - `base.py`
  - `charts.py`
- `workers/`
  - `base.py`
  - `detection.py`
  - `ai_runtime.py`
  - `annotation_ai.py`
  - `model_labels.py`

要求：

- `WorkbenchWindow` 不再直接 import 过多具体页面实现细节
- worker 按任务类型拆分，不再全部堆在一个文件
- `page_base.py` 禁止继续吸纳页面专属逻辑

### 3. 页面层按功能分包

把现在的 `ui/views/` 扁平结构改为 `ui/features/`，每个功能独立成包。

#### `src/ui/features/home/`

- `page.py`
- `summary_cards.py`
- `dataset_stats.py`
- `training_summary.py`

主页负责展示，不负责统计规则本身；统计逻辑落服务层。

#### `src/ui/features/data/`

- `page.py`
- `convert/`
- `preview/`
- `rename/`
- `resize/`

`DataPage` 只做容器页，四个子能力各自有独立页面或组件包。

#### `src/ui/features/training/`

- `page.py`
- `form.py`
- `state.py`
- `runtime.py`
- `command_preview.py`

去掉当前用 lambda 给类补方法的组织方式，改为正常类方法或组合式辅助器。

#### `src/ui/features/validation/`

- `page.py`
- `layout.py`
- `state.py`
- `runtime.py`
- `dataset_mode.py`
- `results.py`
- `result_list.py`
- `models.py`
- `sources.py`
- `helpers.py`

保留现有“入口 + state/runtime/layout”方向，但落到更稳定的功能包里。

#### `src/ui/features/settings/`

- `page.py`
- `environment_panel.py`
- `preferences_panel.py`
- `program_log_panel.py`

设置页展示环境信息，但运行时探测逻辑必须在服务层。

### 4. 标注模块彻底重建

这是本次收益最大的模块，按“一步到位”的力度彻底拆掉当前结构。

`src/ui/features/annotation/` 固定拆分为：

- `page.py`
  - `AnnotationPage`
  - 只负责页面组装与跨子模块协调
- `toolbar.py`
  - 顶部工具栏、绘制模式切换、文件夹选择、保存入口
- `file_browser.py`
  - 图片目录、标注目录、文件列表、计数、右键菜单
- `class_panel.py`
  - 类别面板、当前类别、形状切换、右侧信息区
- `selection.py`
  - 页面级选区同步、列表同步、当前选中状态
- `persistence.py`
  - 加载当前图片、保存 Labelme、保存 YOLO、自动保存、脏状态、删除与恢复
- `actions.py`
  - 清空、删除、撤销、默认保存入口等页面动作
- `dialogs.py`
  - 标注设置、类别管理、绘制形状相关对话框
- `ai/`
  - `dialog.py`
  - `image_selection_dialog.py`
  - `mapping.py`
  - `preferences.py`
  - `controller.py`

`src/ui/features/annotation/canvas/` 固定拆为：

- `widget.py`
  - `AnnotationCanvas`
  - 只保留 Qt 事件入口、信号出口、状态对象挂接
- `render.py`
  - 框、OBB、多边形、预览点、预览线、手柄绘制
- `geometry.py`
  - 坐标换算、line 扩展、旋转矩形角点重建、坐标归一化
- `hit_test.py`
  - 标注命中、手柄命中、hover 判定
- `interaction.py`
  - 绘制、拖拽、移动、缩放、选中状态机
- `context_menu.py`
  - 右键菜单构造与动作绑定
- `state.py`
  - hover、selected handle、drawing points、flash 等瞬时状态
- `shortcuts.py`
  - 画布快捷键与按键分发

标注模块新增稳定内部类型：

- `AnnotationSession`
- `CanvasViewState`
- `AnnotationAction`
- `DrawShapeMode`
- `SelectionSnapshot`

要求：

- `AnnotationPage` 不再直接承载保存细节、列表刷新细节、上下文菜单细节
- `AnnotationCanvas` 不再同时承担绘制、几何、命中测试、状态机、菜单生成五类职责
- 纯几何、文件 IO、Labelme / YOLO 读写、编辑模型必须下沉到服务层

### 5. 服务层按领域重建

当前 `src/services/*.py` 扁平服务层改成领域包，禁止继续堆大型单文件。

#### `src/services/settings/`

- `defaults.py`
- `project_settings.py`
- `app_state.py`
- `merge.py`
- `schema.py`

负责默认值、深合并、恢复默认、路径序列化、项目设置和应用状态。

#### `src/services/runtime/`

- `process_runner.py`
- `log_sanitizer.py`
- `environment_probe.py`
- `windows_spawn.py`

负责后台子进程、日志清洗、Torch/CUDA/系统信息探测、Windows 隐藏窗口参数。

#### `src/services/models/`

- `catalog.py`
- `references.py`
- `yaml_registry.py`
- `types.py`

统一模型扫描：基础模型目录、训练结果 `best.pt / last.pt`、模型 YAML 列表等，训练页、验证页、AI 预标注统一使用。

#### `src/services/annotation/`

- `labelme_io.py`
- `yolo_io.py`
- `editable_document.py`
- `preview_render.py`
- `geometry.py`
- `ai_labeling.py`

负责标注读写、预览绘制数据、可编辑标注模型、几何转换、AI 预标注写回。

#### `src/services/conversion/`

- `types.py`
- `preview.py`
- `execute.py`
- `class_mapping.py`
- `labelme_parser.py`
- `dataset_split.py`
- `dataset_yaml.py`
- `backup.py`
- `formatting.py`

由当前 `conversion_service.py` 拆出“预览 / 执行 / 类别映射 / 数据集划分 / 备份 / 格式化”。

#### `src/services/training/`

- `request_builder.py`
- `command_builder.py`
- `model_resolution.py`
- `results_reader.py`
- `dataset_repair.py`

负责训练命令组装、模型解析、结果曲线读取、`data.yaml` 修复。

#### `src/services/validation/`

- `types.py`
- `source_collectors.py`
- `result_parser.py`
- `prediction_runner.py`
- `save_outputs.py`
- `dataset_validation.py`
- `rendering.py`

由当前 `detection_service.py` 拆出“输入源收集 / 结果解析 / 推理执行 / 标签导出 / 数据集验证”。

#### `src/services/data_ops/`

- `rename.py`
- `resize.py`
- `path_display.py`

把重命名、压缩、路径显示这类共用数据处理逻辑聚合。

要求：

- 服务层统一只依赖标准库、第三方库、其他服务、共享类型
- 禁止任何 `src.services` 导入 `src.ui`
- 同一规则只保留一个真源，不允许训练页和验证页各自维护模型扫描逻辑

### 6. CLI 与隐藏子进程链路重建

`src/train_cli.py` 保留门面，但内部彻底瘦身：

- `src/train_cli.py`
  - 参数解析
  - 分发到 `src/bootstrap/cli_dispatch.py`
- `src/bootstrap/cli_dispatch.py`
  - `train`
  - `export`
  - `val`
  - `predict`
  - `model-labels`
  - `ai-label`
  - `ai-runtime`

对应能力分别落到：

- `src/services/training/*`
- `src/services/validation/*`
- `src/services/annotation/ai_labeling.py`
- `src/services/models/catalog.py`

要求：

- `run_train_cli`、`run_export_cli`、`run_val_cli`、`run_predict_cli`、`run_ai_label_cli`、`run_ai_runtime_cli` 可以保留函数名，但只是 façade
- 打包后行为不变，内部实现完全重组
- 所有后台推理仍通过隐藏子进程执行，避免 GUI 主进程常驻大运行时

## `scr -> src` 全量迁移范围

本次 rename 不是只改目录名，而是全仓一致性迁移，必须覆盖：

- Python 源码导入
- `pixi.toml`
- README 命令示例
- AGENTS 规范
- `docs/architecture.md`
- `docs/spec/*.md`
- `docs/code-inventory.md`
- `installer/YOLOTool.spec`
- `installer/yolo_tool.iss`
- `installer/build_windows.ps1`
- 测试中的路径断言、源码路径常量、导入路径、命令断言
- 任何硬编码字符串里的 `scr/`、`scr\\`、`python -m scr.main`

迁移完成后的统一口径：

- 源码目录：`src/`
- 测试目录：`src/tests/`
- 主入口：`python -m src.main`
- 打包入口：`src/main.py`
- 隐藏 CLI 门面：`src/train_cli.py`

## 测试体系重构

当前测试文件体量也开始失衡，这次与代码结构一起重排。

新测试结构：

- `src/tests/architecture/`
  - 导入边界
  - 文件体量阈值
  - `src` 根目录约束
  - 文档、命令、打包路径一致性
- `src/tests/services/annotation/`
- `src/tests/services/conversion/`
- `src/tests/services/training/`
- `src/tests/services/validation/`
- `src/tests/services/settings/`
- `src/tests/services/runtime/`
- `src/tests/ui/annotation/`
- `src/tests/ui/training/`
- `src/tests/ui/validation/`
- `src/tests/ui/shell/`
- `src/tests/ui/settings/`
- `src/tests/ui/data/`
- `src/tests/integration/`
  - app entry
  - CLI entry
  - packaging contract

新增必须通过的结构规则：

- 仓库内不得再出现 `from scr.` / `import scr.`
- 文档、命令、打包配置不得再引用 `scr`
- `src/ui/features/*/page.py` 不得超过 `250` 行
- `src/ui/features/annotation/canvas/*` 单文件不得超过 `250` 行
- `src/ui/shared/workers/*` 单文件不得超过 `220` 行
- `src/services/*` 任一实现文件不得超过 `300` 行
- `src/services` 禁止导入 `src.ui`
- `src/ui/shared/page_base.py` 禁止承载页面专属逻辑
- `docs/code-inventory.md` 必须由脚本生成，不允许手写长期漂移

## 文档与规范回写

这次必须同步回写文档，不允许“代码改完、文档以后再说”。

必须更新：

- `AGENTS.md`
  - 把所有 `scr/` 改为 `src/`
  - 删除“不要改成 `src/`”这类旧约束
  - 保留“5 次测试失败立即停止”的规则
  - 保留“完成所有任务后一次总提交”的规则
- `README.md`
  - 目录树改成 `src/`
  - 命令示例改成 `python -m src.main`
  - 源码路径说明全部更新
- `docs/architecture.md`
  - 用新结构重写，不再描述旧扁平 `views/services`
- `docs/spec/*.md`
  - 路径示例统一改为 `src/...`
  - 增加新分层规则的引用
- `docs/code-inventory.md`
  - 改为脚本生成
- `docs/packaging-windows.md`
  - 打包入口路径与命令统一为 `src`

新增开发脚本：

- `src/devtools/generate_code_inventory.py`
  - 扫描仓库
  - 生成 `docs/code-inventory.md`
  - 测试校验生成结果未过期

## 仓库清理与根目录规范

结合第一份计划一起收口，根目录也要同步收紧：

- 保留：
  - `README.md`
  - `AGENTS.md`
  - `pixi.toml`
  - `pixi.lock`
  - `docs/`
  - `installer/`
  - `src/`
  - 必要打包脚本
- 清理跟踪：
  - `YOLOTool.lnk`
  - `codex_patch.diff`
- 根目录不再允许出现模型权重、快捷方式、临时补丁、截图类文件
- 本地模型统一放 `data/models/`
- `.gitignore` 继续忽略：
  - `.pixi/`
  - `build/`
  - `dist/`
  - `data/`
  - `*.pt`
  - 其他临时产物

## 实施顺序

为了避免半旧半新结构，执行顺序固定如下：

1. 建立 `src/` 新目录骨架与目标包结构
2. 迁移 `main/app/train_cli/context/paths/theme/qt` 到新结构
3. 全量替换导入、路径字符串、命令字符串，从 `scr` 切到 `src`
4. 更新 `pixi.toml`、打包脚本、PyInstaller、Inno Setup
5. 把测试迁移到 `src/tests/`，同步修正导入和路径断言
6. 改写 AGENTS、README、architecture、spec、packaging、inventory 生成方案
7. 重建 `ui/shell` 与 `ui/shared/workers`
8. 重建 `ui/features/training`、`validation`、`settings`、`data`
9. 最后重建 `ui/features/annotation` 与 `services/annotation`
   - 先拆 canvas
   - 再拆 page / persistence / file browser
   - 再拆 AI 预标注链路
10. 重建 `services/models/conversion/training/validation/runtime/settings`
11. 删除旧扁平文件与整个旧 `scr/` 目录
12. 跑完整校验、修补测试、收口文档与结构规则

## 验收标准

必须满足以下全部条件才算完成：

- `pixi run check` 通过
- `pixi run test` 通过
- `pixi run app` 可正常启动
- `python -m src.main` 可正常启动
- 打包流程可运行，`YOLOTool.exe --yolo-train / --yolo-export / --yolo-val` 行为保持可用
- 标注页回归通过：
  - 打开目录
  - 切图
  - 绘制 detect / obb / 多边形
  - 选中 / 拖拽 / 删除 / 撤销
  - 保存 Labelme
  - 保存 YOLO
  - 脏状态提示
  - AI 预标注
- 训练页回归通过：
  - 模型选择
  - 命令预览
  - 开始 / 停止
  - 结果目录打开
  - 曲线读取
- 验证页回归通过：
  - 模型扫描
  - 单图 / 批量 / 摄像头 / 数据集验证
  - 结果展示
  - 标签导出
  - `best.pt / last.pt` 开关
- 设置页回归通过：
  - 默认值
  - 恢复默认
  - 最近项目
  - 帮助图标
  - 程序日志窗口
- 全仓搜索不得再出现业务相关 `scr` 引用
- 架构测试不再出现超阈值页面文件失败
- 文档中的目录树、命令、打包路径、规则全部与 `src` 新结构一致

## 假设与默认决策

- 本次为“一步到位”重构，不保留 `scr` 兼容层
- 页面公开类名保留，模块路径不保留
- 不新增业务功能，只重组结构并稳住现有行为
- `data/runtime/settings.json`、`data/runtime/app_state.json`、`data/models/` 的行为不改
- 训练、验证、AI 预标注继续通过后台隐藏子进程执行
- 若编译或测试连续 5 次失败仍无法解决，必须立即停止并汇报
- 若最后需要提交 git，只能在全部任务完成后做一次总提交

# 架构与维护说明

## 项目概述

本项目是一个独立于 `yolo-weld` 的 Windows 本地可视化 YOLO 训练工作台，使用 **Python + PySide6 / Qt** 开发桌面 GUI。

定位是“通用 YOLO 优先，同时兼容焊缝 OBB 项目”：

- 支持 YOLO `detect` 与 `obb` 两类任务。
- 默认兼容焊缝识别习惯配置，例如类别 `weld`、Labelme 转 YOLO-OBB、直线标注扩展为旋转矩形。
- 使用本项目本地 `pixi` 环境管理依赖，不依赖外部 conda 环境。

## 当前目录结构

```text
yolo_tool/
├── AGENTS.md
├── README.md
├── pixi.toml
├── docs/
│   ├── architecture.md
│   ├── code-inventory.md
│   ├── packaging-windows.md
│   └── spec/
├── installer/
│   ├── YOLOTool.spec
│   ├── build_windows.ps1
│   ├── yolo_tool.iss
│   └── hooks/
└── src/
    ├── main.py
    ├── app.py
    ├── train_cli.py
    ├── open_yolo_tool.pyw
    ├── bootstrap/
    │   ├── app_factory.py
    │   ├── cli_dispatch.py
    │   └── context.py
    ├── shared/
    │   ├── paths.py
    │   ├── qt.py
    │   ├── theme.py
    │   └── types.py
    ├── services/
    │   ├── annotation/
    │   ├── conversion/
    │   ├── data_ops/
    │   ├── models/
    │   ├── runtime/
    │   ├── settings/
    │   ├── training/
    │   └── validation/
    ├── ui/
    │   ├── shell/
    │   ├── shared/
    │   ├── widgets/
    │   └── features/
    ├── runtime/
    ├── assets/
    └── tests/
```

## 分层边界

- `src/main.py` 是唯一桌面可执行入口，同时负责分流 `--yolo-train`、`--yolo-export`、`--yolo-val`、`--yolo-predict`、`--yolo-ai-label` 等隐藏 CLI。
- `src/app.py` 与 `src/bootstrap/app_factory.py` 负责 GUI 应用创建，不承载业务规则。
- `src/bootstrap/cli_dispatch.py` 是唯一 CLI 分发入口；打包后 `YOLOTool.exe --yolo-*` 最终也进入这里。
- `src/shared/` 放跨层共享基础能力，例如路径、Qt 导出、主题和共享类型。
- `src/shared/paths.py` 在开发态必须把 `ROOT` 解析到仓库根目录，而不是 `src/` 子目录；隐藏 CLI 与后台 worker 依赖这个根目录作为 `python -m src.main` 的工作目录。
- `src/shared/paths.py` 同时维护应用图标资源路径；GUI 启动时 `QApplication` 和 `WorkbenchWindow` 都应通过这里的 `ICON_PNG` 读取 `src/assets/app_icon.png`，不要在 UI 层硬编码相对目录，避免开发态或打包态窗口/任务栏图标丢失。
- `src/services/<domain>/` 是唯一业务实现层。这里允许依赖标准库、第三方库、其他服务包和 `src/shared/`，不得依赖 `src/ui/`。
- `src/services/home/` 负责主页的大目录扫描、统计汇总与训练历史整理；这些逻辑必须通过后台 worker 调用，避免主线程同步 I/O 卡住首页。主页切回时若界面上已有上一轮统计值，应优先保留旧值，待新汇总返回后再替换，避免反复闪出“加载中”。
- `src/ui/shell/` 负责主窗口、导航、页面注册、关闭保护、程序日志和整体样式。
- `src/ui/shared/` 负责跨页面 UI 复用能力，例如页面基类、共享表单、共享对话框和后台 worker。
- `src/ui/features/<feature>/` 负责各页面真实实现；`page.py` 只做页面装配，复杂逻辑继续拆到该功能包子模块。
- `src/ui/widgets/` 与 `src/ui/shared/widgets/` 放基础可复用控件与图表组件。
- `src/tests/architecture/` 放结构约束、防退化围栏与文档一致性检查。
- `src/tests/services/` 按领域分目录放服务层测试。
- `src/tests/ui/` 按 feature / shell / shared / data 分目录放页面与交互回归。
- `src/tests/integration/` 放入口和跨层集成回归。

## 服务层说明

### `src/services/settings/`

- `defaults.py` 提供默认设置构造。
- `storage.py` 提供深合并与项目路径序列化 / 反序列化。
- `project_settings.py` 负责项目级设置加载、保存与最近项目状态读写。
- 当前项目配置保存到当前项目目录 `data/runtime/settings.json`。
- 应用级最近项目状态保存到应用根目录 `data/runtime/app_state.json`。
- `src/runtime/settings.json` 仅作为源码内默认配置参考。
- 标注页名称显示由项目设置 `annotation.show_annotation_names` 控制，默认值为 `false`。

### `src/services/runtime/`

- `process_runner.py` 统一后台子进程启动、日志转发、结构化输出和停止流程。
- `windows_spawn.py` 提供 Windows 隐藏窗口参数，确保打包后的后台任务不弹终端。
- `environment_probe.py` 提供 Python、依赖版本、Torch/CUDA 和系统状态检测。
- GUI 日志写入前必须通过这里的终端输出清洗逻辑去掉 ANSI/控制字符。

### `src/services/training/`

- `model_catalog.py` 负责训练模型目录、模型 YAML 与模型路径解析。
- `commands.py` 负责训练 / 导出 / 验证命令构造与 `data.yaml` 的验证路径修复。
- `results_reader.py` 负责 `results.csv` 曲线与指标摘要读取。
- 基础模型目录统一是 `data/models/`。

### `src/services/validation/`

- `model_catalog.py` 负责训练产物模型扫描、输入模式状态和结果计数 / 日志文案。
- `source_collectors.py` 负责图片、视频与数据集来源收集。
- `rendering.py` 负责推理结果对象标准化、结果图渲染与标签输出。
- `runtime_cleanup.py` 负责短生命周期推理运行时释放。
- `prediction_runner.py` 保留为推理总流程装配入口。
- 图片/视频/摄像头推理通过隐藏子进程执行，完成后释放主要推理运行时。
- 摄像头或视频流结果图必须显式以当前帧为底图，避免无目标时黑屏。

### `src/services/annotation/`

- 负责 Labelme/YOLO 标注读写、可编辑标注模型、预览渲染和 AI 预标注业务逻辑。
- 标注页图片列表的大目录扫描、标注存在性判断与首屏批量渲染应尽量拆成“首批同步 + 后台分批补齐”，避免首次进入标注页时阻塞主线程；对大量不可见行不要同步创建整套行内 `QCheckBox`/`QWidget`。
- 标注页首次进入时，应避免在 `AnnotationPage` 构造阶段直接触发整套图片扫描；首轮图片扫描应延后到页面首次显示后启动，先让导航切页完成，再逐步进入标注工作状态。
- 若主窗口已在空闲阶段预热标注页，可提前准备首张图片与首批列表项，减少真正切入标注页时先见空画布的闪动；但后续批量渲染与后台标注状态扫描仍要继续补齐完整列表。
- 标注页图片列表若改用 `setItemWidget(...)` 装配只读勾选框与文件名，底层 `QListWidgetItem` 本身应只保留数据角色，不再重复绘制同名文本，避免出现叠字；只读勾选框保持正常启用样式，不应做成禁用发灰控件。
- AI 预标注结果优先写回页面内部标注对象并保存 Labelme；按设置决定是否同步导出 YOLO。

### `src/services/conversion/`

- `types.py` 定义转换配置与结果模型。
- `class_mapping.py` 负责类别识别、类别映射和映射表解析。
- `labelme_parser.py` 负责 Labelme 形状解析与 Labelme -> YOLO 行转换。
- `dataset_split.py` 负责输入收集、数据集划分和统计汇总。
- `dataset_yaml.py` 负责 `data.yaml` 输出，并只写入本次实际产出的 split 条目。
- `backup.py` 负责旧产物清理与备份；未启用备份时不主动创建 `old/` 目录。
- `formatting.py` 负责转换结果说明文本。
- `execute.py` 保留为转换总流程装配入口。

### `src/services/data_ops/`

- 负责批量重命名、图片压缩和项目内路径显示转换。
- 图片压缩页的“打开结果文件夹”属于页面层轻交互，直接基于当前“输出目录”字段解析后的路径打开目录，不额外下沉到服务层。

## UI 约定

- `src/ui/shell/window.py` 中的 `WorkbenchWindow` 是唯一主窗口实现。
- 页面创建与导航注册统一在 `src/ui/shell/page_registry.py` 与 `src/ui/shell/navigation.py`。
- 主窗口页面采用“首屏懒加载 + 空闲分批预热”：启动时先创建当前页，窗口显示后再按空闲节奏补建其余页面，避免首页打开时连带触发重页面初始化，同时减少用户第一次切到任意页面时再同步吃到建页卡顿。
- 程序级日志缓冲与设置页日志展示统一走 `src/ui/shell/program_log.py`。
- 关闭确认统一由 `src/ui/shell/close_guard.py` 处理，包括未保存标注与训练运行中确认。
- 共享页面基础能力只能放在 `src/ui/shared/page_base.py`，不要回流到页面专属实现。
- worker 真实实现只放在 `src/ui/shared/workers/`，页面持有 worker 时必须在原生 `finished` 信号后再清理对象。
- `src/ui/features/annotation/page.py` 与 `src/ui/features/annotation/canvas/widget.py` 都只保留页面 / 画布装配；交互、保存、菜单、快捷键、AI 与编辑细节继续拆在 feature 子模块。
- 标注画布光标由 `src/ui/features/annotation/canvas/drawing.py` 统一根据交互状态刷新：除编辑模式外选择绘制模式后显示系统十字光标，矩形框模式额外在画布上绘制贯穿鼠标位置的纯黑色实线水平/垂直辅助线，并在短光标热点周围留出原始背景采样空隙，多边形封闭顶点优先显示小手，拖动时显示闭合手。

## 关键运行规则

- 训练与检测都只允许一次启动；运行期间按钮禁用，任务结束后恢复。
- 模型验证、AI 预标注和 Torch/CUDA 摘要读取都优先走短生命周期隐藏子进程，避免主 GUI 长驻推理运行时。
- 对任何会修改用户文件的功能，坚持“先预览，再执行”。
- UI 中项目文件夹显示绝对路径，其他项目内路径优先显示相对路径。
- `data/models/` 是统一基础模型目录；训练与验证模型列表优先使用该目录。

## 打包链路

- PyInstaller 入口是 `src/main.py`，规格文件为 `installer/YOLOTool.spec`。
- 打包脚本 `installer/build_windows.ps1` 负责正式版与开发快包，并在产物目录生成默认 `settings.json` 与 `app_state.json`。
- 安装包脚本 `installer/yolo_tool.iss` 负责把 `dist/YOLOTool/` 封装为安装程序。
- 打包后训练、导出、验证仍通过 `YOLOTool.exe --yolo-train / --yolo-export / --yolo-val` 进入 `src/train_cli.py` 与 `src/bootstrap/cli_dispatch.py`。

## 维护建议

- 新增业务逻辑优先进入 `src/services/`，只有明确依赖 Qt 生命周期的逻辑才放到 `src/ui/`。
- 新增页面逻辑直接放入 `src/ui/features/<feature>/`，不要恢复任何 `views`、`legacy` 或顶层 UI 兼容壳。
- `src/services/<domain>/__init__.py` 只做轻量导出，不塞入业务实现。
- 修改结构后同步更新 `docs/spec/*.md`、`docs/packaging-windows.md` 和 `docs/code-inventory.md`。
- 当前阶段的结构围栏由 `src/tests/architecture/test_structure_boundaries.py` 负责，包含页面 / worker / service 体量阈值、旧路径禁用和 inventory 新鲜度校验。

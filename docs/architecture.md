# 架构与维护说明

## 项目概述

本项目是一个独立于 `yolo-weld` 的 Windows 本地可视化 YOLO 训练工作台，使用 **Python + PySide6 / Qt** 开发桌面 GUI。

定位是"通用 YOLO 优先，同时兼容焊缝 OBB 项目"：

- 支持 YOLO `obb` 与普通 `detect` 两类任务。
- 默认内置焊缝识别项目习惯配置，例如类别 `weld`、Labelme 转 YOLO-OBB、直线标注扩展为旋转矩形。
- 不依赖原项目的 `YL` conda 环境，使用本项目本地 `pixi` 环境管理依赖。

## 当前目录结构

```text
yolo_tool/
├── README.md
├── pixi.toml
├── pixi.lock
├── AGENTS.md
├── 打包程序.bat
├── docs/
│   ├── architecture.md
│   ├── code-inventory.md
│   ├── packaging-windows.md
│   └── spec/
│       ├── annotation.md
│       ├── data-processing.md
│       ├── home.md
│       ├── settings.md
│       ├── training.md
│       └── validation.md
├── installer/
│   ├── yolo_tool.iss
│   ├── YOLOTool.spec
│   ├── build_windows.ps1
│   ├── package_windows.ps1
│   ├── 打包程序.ps1
│   └── hooks/
│       ├── hook-PySide6.scripts.deploy_lib.py
│       ├── hook-torch.py
│       └── hook-torch.utils.tensorboard.py
└── scr/
    ├── __init__.py
    ├── main.py
    ├── app.py
    ├── context.py
    ├── open_yolo_tool.pyw
    ├── paths.py
    ├── theme.py
    ├── train_cli.py
    ├── runtime/
    │   └── settings.json
    ├── assets/
    │   ├── app_icon.png
    │   └── app_icon.ico
    ├── services/
    │   ├── __init__.py
    │   ├── settings_service.py
    │   ├── conversion_service.py
    │   ├── annotation_service.py
    │   ├── rename_service.py
    │   ├── resize_service.py
    │   ├── training_service.py
    │   ├── detection_service.py
    │   ├── runtime_service.py
    │   ├── process_utils.py
    │   └── environment_service.py
    ├── ui/
    │   ├── __init__.py
    │   ├── app.py
    │   ├── forms.py
    │   ├── window.py
    │   ├── qt.py
    │   ├── page_base.py
    │   ├── helpers.py
    │   ├── workers.py
    │   ├── dialogs.py
    │   ├── widgets/
    │   │   ├── __init__.py
    │   │   ├── base.py
    │   │   └── charts.py
    │   └── views/
    │       ├── __init__.py
    │       ├── home.py
    │       ├── data.py
    │       ├── convert.py
    │       ├── preview.py
    │       ├── rename.py
    │       ├── resize.py
    │       ├── training.py
    │       ├── training_form.py
    │       ├── training_runtime.py
    │       ├── training_state.py
    │       ├── validation.py
    │       ├── validation_dataset.py
    │       ├── validation_helpers.py
    │       ├── validation_layout.py
    │       ├── validation_models.py
    │       ├── validation_result_list.py
    │       ├── validation_results.py
    │       ├── validation_runtime.py
    │       ├── validation_sources.py
    │       ├── validation_state.py
    │       └── settings.py
    └── tests/
        ├── conftest.py
        ├── helpers/
        ├── test_app_entry.py
        ├── test_architecture_boundaries.py
        ├── test_services_*.py
        └── test_ui_*.py
```

## 服务层说明

核心服务接口在 `scr/services/`：

- `settings_service.py`：项目级设置文件加载、保存、默认值合并与恢复默认值；默认路径为当前项目目录 `data/runtime/settings.json`，并维护训练、验证、转换、重命名、压缩等页面的持久化默认值。当前包含 `paths.models_dir`、`training.optimizer`、`features.custom_command_dialog`、`features.distribution_multi_class_mode`、`features.show_last_training_models` 等字段。
- `data/runtime/app_state.json`：应用级最近项目状态文件，当前保存 `last_project_root`，仅用于下次启动时恢复最近一次使用的项目目录。
- `conversion_service.py`：Labelme 转 YOLO、已有 YOLO `.txt` 分组、自动识别类别、类别映射、自定义类别名校验、数据集划分、`data.yaml` 生成，以及转换产物备份。
- `annotation_service.py`：YOLO 标注解析与图像预览绘制；预览时按标签内容自动识别 `detect/obb`，并使用更接近 YOLO 官方的框与标签样式。
- `rename_service.py`：批量重命名预览与执行。
- `resize_service.py`：图片备份、缩放、画布归一化。
- `path_service.py`：项目内路径解析、相对路径显示、训练结果模型路径简化等纯路径逻辑。
- `training_service.py`：训练与导出命令生成、模型扫描与解析、模型 YAML 列举、训练开始前自动修复 `data.yaml` 中未还原的 `val` 路径，以及从 `results.csv` 读取训练曲线数据。
- `detection_service.py`：模型扫描、输入源自然排序、单文件/批量检测源收集、检测结果解析、推理流程、检测日志文案，以及结果图片对应 YOLO 标注文件导出。
- 摄像头/视频流的结果图渲染必须显式以当前帧作为底图后再叠加检测结果，不能依赖模型结果对象内部的默认底图回退，避免无目标时出现黑屏。
- `runtime_service.py`：子进程启动、日志转发、结构化事件转发、停止进程；Windows 下优先回收训练进程树，并在日志入队前清洗 ANSI/控制字符，避免 GUI 文本框出现终端转义符残留。
- 模型验证（图片/视频/摄像头推理）与 AI 预标注应通过隐藏子进程执行，避免在 GUI 主进程常驻 `torch` / `ultralytics` 推理运行时，确保任务结束后可随子进程一起回收主要推理内存。
- 验证页图片结果缓存只保留结果路径与轻量元数据，需要回看时再从磁盘重载图片，避免批量检测数百张图片时在 GUI 内存中长期堆积 `PIL.Image` / `QPixmap` 对象。
- `process_utils.py`：Windows 后台子进程隐藏窗口参数，避免 PyInstaller GUI 程序反复弹出终端窗口。
- `environment_service.py`：pixi、模块、GPU/CPU/内存/磁盘状态检测；Torch/CUDA 摘要默认通过短生命周期子进程获取，避免仅因打开系统设置或训练页就把 `torch` 运行时常驻到 GUI 主进程。

## UI 分层约定

- `scr/ui/page_base.py` 只保留跨页面复用的页面基类能力，例如设置保存、状态栏提示、只读日志文本框处理。
- 表单字段构建、帮助提示和通用文件选择集中在 `scr/ui/forms.py`，不要继续把页面专属逻辑塞回 `BasePage`。
- `scr/ui/helpers.py` 只保留轻量 UI 纯函数，不再承接新的 service 转发逻辑。
- 训练页拆分为：
  - `training.py`：页面入口与事件装配
  - `training_form.py`：表单与布局
  - `training_state.py`：设置持久化、命令预览与状态收集
  - `training_runtime.py`：训练启动、停止、日志轮询与恢复
- 验证页拆分为：
  - `validation.py`：页面入口与事件装配
  - `validation_layout.py`：控件布局
  - `validation_state.py`：模型/输入源状态与设置持久化
  - `validation_runtime.py`：检测与数据集验证运行控制
  - 其余 `validation_*` 模块：模型选项、结果展示、数据集流程和辅助逻辑
- `scr/ui/workers.py` 中桥接子进程的 `QThread` 工作器只负责信号转发与停止控制；页面侧若持有 worker 引用，必须在线程原生 `finished` 信号后再清理，避免线程尚未完全结束时对象被销毁而触发 Qt 级异常退出。

## 维护阈值

- `scr/ui/views/` 中的页面文件建议超过 `500-600` 行时优先拆分，不要等到 `800` 行再处理。
- 共享层文件若开始同时承担“页面基类 + 表单组件库 + 业务规则”多重职责，应优先拆分。
- 新增业务逻辑优先进入 `scr/services/`；只有明确依赖 Qt 控件生命周期的逻辑才放在 `scr/ui/`。

设置文件新增字段：

- `paths.models_dir`：统一模型目录，默认指向 `data/models`。
- `training.optimizer`：优化器选择（auto/SGD/Adam/AdamW/RMSProp）。
- `training.hsv_s`、`training.hsv_v`：HSV 饱和度与明度增强参数，和 `training.hsv_h` 一起由训练页 HSV 勾选项控制。
- `features.custom_command_dialog`：训练前是否弹出自定义命令框。
- `features.distribution_multi_class_mode`：主页“各类别图片分布”是否切换为多类别统计模式。
- `features.show_help_icons`：是否显示字段名后的 `ⓘ`；关闭时只隐藏 `ⓘ`，不移除字段名称上的 tooltip。
- `features.show_last_training_models`：模型验证页“选择模型”下拉框是否额外显示训练结果中的 `last.pt`；默认 `False`，关闭时只显示 `best.pt`。
- 系统设置中不再提供“启动自动加载 torch”之类的常驻预热选项；GUI 默认不主动持有推理运行时，只有训练/验证/AI 预标注等实际任务启动后才在对应子进程中按需加载。
- `conversion.use_labelme`：记录标注转换页当前是否启用 Labelme 转 YOLO。
- `conversion.backup_yolo_files`：记录标注转换页是否备份本次转换生成的 YOLO 标注与 `data.yaml`。
- `conversion.class_name_mappings`：记录 Labelme 类别名到 YOLO 类别名的映射关系。
- `rename.prefix`、`rename.start_index`、`rename.padding`、`rename.include_labelme`、`rename.include_yolo`：记录批量重命名页当前配置。
- `image_resize.backup_enabled`：记录图片压缩页是否备份原始图片。
- `features.resize_output_mode`：记录图片压缩页的输出方式。
- `validation.source_scope`：记录模型验证页当前选择的固定输入源/验证源（`全部图片`、`训练图片`、`验证图片`、`测试图片`）。

## 与原 yolo-weld 项目的关系

原项目路径：

```text
D:\ruanjian\User\Python\yolo-weld
```

本项目只参考原项目流程和脚本思想，不直接依赖原项目代码。

原项目关键兼容点：

- Labelme 标注。
- YOLOv8/YOLO11 OBB 训练。
- 焊缝类别 `weld`。
- `line` 标注扩展为窄长 OBB。
- 自定义模型 YAML，例如：

```text
D:\ruanjian\User\Python\yolo-weld\data\yolov8m-obb.yaml
```

## 后续开发建议

- 优先保持服务层可测试，不要把业务逻辑直接写死在 GUI 回调中。
- Qt GUI 可以继续按 `scr/ui/views/`、`scr/ui/widgets/`、`scr/ui/forms.py` 和 `scr/ui/dialogs.py` 这一层次拆分，避免页面文件再次膨胀；主页图表模块保持在 `scr/ui/widgets/charts.py`。
- 训练曲线已从 `results.csv` 读取数据绘制，当前只保留关键曲线与 Epoch 摘要；后续增加指标时不要让标题区重新拥挤。
- GPU 利用率优先通过 `nvidia-smi` 获取；如果不可用，界面显示"待检测"即可。
- 对任何会改文件的功能，继续坚持"先预览，再执行"。

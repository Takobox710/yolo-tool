# AGENTS.md — YOLO 本地训练工作台

## 项目概述

本项目是一个独立于 `yolo-weld` 的 Windows 本地可视化 YOLO 训练工作台，使用 **Python + PySide6 / Qt** 开发桌面 GUI。

定位是"通用 YOLO 优先，同时兼容焊缝 OBB 项目"：

- 支持 YOLO `obb` 与普通 `detect` 两类任务。
- 默认内置焊缝识别项目习惯配置，例如类别 `weld`、Labelme 转 YOLO-OBB、直线标注扩展为旋转矩形。
- 不依赖原项目的 `YL` conda 环境，使用本项目本地 `pixi` 环境管理依赖。

## 重要约束

- 所有项目代码放在 `scr/` 目录下。
- 测试代码放在 `tests/` 目录下。
- 不要把 `.pixi/` 环境目录加入 git。
- 如需提交 git，必须在所有任务完成后进行一次总提交，避免中途多次零散提交。
- 如果编译或测试错误连续出现 5 次仍未解决，必须停止并向人类报告，不要陷入盲猜循环。

## 当前目录结构

```text
yolo_tool/
├── pixi.toml
├── pixi.lock
├── AGENTS.md
├── icon.svg
├── scr/
│   ├── yolo_workbench/
│   │   ├── main.py
│   │   ├── theme.py
│   │   ├── runtime/
│   │   │   └── settings.json
│   │   └── services/
│   │       ├── settings_service.py
│   │       ├── conversion_service.py
│   │       ├── annotation_service.py
│   │       ├── rename_service.py
│   │       ├── resize_service.py
│   │       ├── training_service.py
│   │       ├── detection_service.py
│   │       ├── runtime_service.py
│   │       └── environment_service.py
│   └── yolo_workbench_qt/
│       ├── main.py
│       ├── home_charts.py
│       ├── assets/
│       │   ├── app_icon.png
│       │   └── app_icon.ico
│       └── app.py
└── tests/
```

## 启动与测试

推荐命令：

```powershell
pixi run app
pixi run test
```

等价启动入口：

```powershell
pixi run python -m scr.yolo_workbench.main
```

静态编译检查：

```powershell
pixi run python -m compileall scr tests
```

## Pixi 环境说明

`pixi.toml` 使用 Python 3.12，并配置了：

- `pyside6`
- `Pillow`
- `opencv`
- `ultralytics`
- `matplotlib`
- `pyyaml`
- `scikit-learn`
- `psutil`
- `pytest`
- `torch`
- `torchvision`

PyTorch 已配置 PyPI 额外索引：

```toml
[pypi-options]
extra-index-urls = ["https://download.pytorch.org/whl/cu130"]
```

目标是 CUDA 13.0 版 torch。此前实现时，`pixi install` 同步 CUDA 版 torch 曾因下载/同步耗时超时；如果后续训练需要 GPU，请优先重新完整执行：

```powershell
pixi install
pixi run python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
```

确认 `torch.version.cuda` 为 `13.0` 或符合当前 CUDA 13 系列目标，且 `torch.cuda.is_available()` 为 `True`。

## GUI 功能

主界面采用顶部导航（左侧带图标）：

- 主页
- 数据处理
- 模型训练
- 模型验证
- 系统设置

当前主 GUI 为 `scr/yolo_workbench_qt/app.py` 的 PySide6 / Qt 实现，`scr/yolo_workbench/main.py` 只作为标准启动入口转发到 Qt。

### 主页

主页必须按旧版整体设计重建，展示项目路径、图片数量、标签文件数量、训练曲线、训练结果模型等概览信息。

主页布局约定：

- 主页使用 Qt 两行两列网格布局，行高比例 58:42。
- 主页应放入 `QScrollArea`，最小窗口高度不足时允许滚动，不能压扁卡片内容。
- 主页列宽由代码按可用宽度固定计算，左列约 30%，右列约 70%，避免放大窗口时左列漂移或比例变化。
- 顶部保留欢迎标题和简短环境标签；不要显示标题下方的说明标语。
- 上半区左侧为"项目概览"（标题与"设置项目目录"按钮同行），包含项目文件夹、图片路径、标注路径、结果路径、图片数量、标签数量。
- 项目概览每行保持左侧字段名、右侧数据结构；字段名固定窄宽，右侧长路径使用中间省略显示，完整内容放入 tooltip。
- "设置项目目录"与"打开结果目录"按钮采用紧凑按钮样式，高度约 30px，小字号，不要通过继续加宽按钮解决文字显示问题。
- 上半区右侧为"各类别图片分布"，使用 `scr/yolo_workbench_qt/home_charts.py` 中的独立图表组件渲染柱状图。
- 各类别图片分布显示四根柱：总照片、训练、验证、测试；显示类别、照片总数、各柱数量与占比。柱状图坐标轴左侧留白保持紧凑，当前约定左边距为 30px。
- 下半区左侧为训练曲线卡片，但不显示"训练曲线"标题，以节省空间。
- 训练曲线使用 `scr/yolo_workbench_qt/home_charts.py` 中的独立图表组件，从 `results.csv` 读取数据，顶部只显示 Epoch，不显示 mAP50 或 Box Loss 的数值摘要。
- 训练曲线绘制 mAP50 与 Box Loss 两条关键曲线并保留图例；曲线必须只画线，不得填充折线路径区域，避免出现三角形色块。
- 训练曲线暂无训练记录时显示坐标轴和空状态文字。
- 下半区右侧为"训练历史"（"打开结果目录"按钮与标题同行，排序三角形隐藏），自动扫描 `result/**/weights/*.pt`。
- 训练历史标题行与表格之间固定保留 `3px` 间距。
- 训练历史表格必须支持点击表头排序，但排序三角形隐藏；刷新时先临时关闭排序，填充完整数据后再恢复排序，避免初启动数据错位。
- 训练历史表格列宽必须按当前可见宽度重新计算，初始进入、窗口缩放和刷新数据后都要重算；`Time`、`Recall` 等列不能显示省略号或被右侧滚动条遮挡。
- 主页四张卡片不得保留放大后的固定宽度；窗口横向放大后再缩小时，卡片必须跟随可见区域缩回，并保持 1:2 列宽比例。

不要再添加"最近活动"模块；此前用户明确要求删除该区域。

项目概览中不要显示任务类型。

### 数据处理

左侧子菜单包含：

- 标注转换
- 标注预览
- 批量重命名
- 图片压缩

标注转换支持：

- Labelme -> YOLO
- `obb` 与 `detect`
- `oriented_rectangle` 转 OBB
- `line` 按半宽扩展为 OBB
- 自动划分 `train/val/test`
- 生成 `data.yaml`
- 汇总 `labels`

图片压缩支持：

- 执行前备份原图。
- 按长边等比缩放，默认长边 960。
- 创建默认 960 x 960 白色或黑色画布。
- 将缩放后的图片居中粘贴到画布。

### 模型训练

训练页必须按旧版整体设计重建，并遵循当前交互约定：

- 左侧：基础模型（下拉框，自动读取 `data/models/*.pt`，也可手动输入）、数据集 YAML、模型 YAML（默认空白）、项目输出、数据增强选项。
- 右侧：优化器（auto/SGD/Adam/AdamW/RMSProp 下拉框）、设备、学习率、Epochs、Patience、Workers、Batch、图片尺寸。
- 中部左侧保留训练控制模块（开始训练、停止训练、查看模型报告），但不显示"训练控制"标题。
- 中部右侧保留系统状态模块（GPU/显存/CPU/内存），但不显示"系统状态"标题。
- 训练日志面板不显示标题和进度条，只保留日志文本框。

训练页布局结构：

- 顶部第一行左右两栏，比例接近旧版：左侧更宽用于数据集与增强配置，右侧用于训练参数。
- 中部为两个紧凑模块：左侧训练控制按钮组，右侧 GPU/显存/CPU/内存状态卡片。
- 底部为训练日志面板（无标题、无进度条），日志正文应占满页面主内容宽度。

任务类型不再提供手动选项，应根据模型名称自动推断：

- 模型名称包含 `obb` 时使用 `obb`。
- 其他模型默认使用 `detect`。

不要恢复"任务类型"和"导出格式"这两个训练页选项。

不要显示"自动任务类型""训练控制""系统状态"这三个标题文字。训练控制和系统状态模块本体要保留但高度要紧凑；任务类型状态行本体也不要显示。

训练命令由 `training_service.build_train_command()` 生成，格式类似：

```powershell
pixi run yolo obb train model=... data=... epochs=... imgsz=... batch=... optimizer=...
```

Qt 实现注意事项：

- 基础模型、设备、优化器必须使用 `QComboBox` 等下拉控件。
- 数据增强项必须是真实 `QCheckBox`，勾选状态必须影响训练命令参数。
- 开始训练、停止训练、查看模型报告按钮放在训练控制模块中，不放在训练日志标题栏中。
- 系统状态检测必须后台执行，不得阻塞页面切换或窗口缩放。
- 点击"开始训练"后，若自定义命令框功能开启，先弹出命令编辑对话框，可修改命令后再执行训练；若上一个训练任务未结束则不弹出也不启动新任务。
- 训练和检测均只允许一次启动，按钮在运行期间禁用，任务结束后恢复。

### 模型验证

验证页左右比例为 `3:7`：

- 左侧：模型配置（含下拉框自动扫描模型）、检测源配置、检测控制、检测日志。
- 右侧：源图、检测结果图、检测结果详情表。

支持输入源：

- 图片/视频文件夹
- 摄像头

支持自动扫描 `result/**/weights/*.pt`，也可手动选择模型。

验证页 UI 注意事项：

- 左侧和右侧采用可缩放的 3:7 权重，不要用固定像素宽度锁死，否则小窗口会截断右侧内容。
- 下拉控件使用 Qt 原生 `QComboBox` 并保持与普通输入框一致的边框，不要再用额外白底外壳模拟边框。
- 所有面板顶部边框和圆角必须完整显示，标题栏不能覆盖面板上边框，也不能让顶部圆角变直角。
- 模型路径、检测模式、输入源等左侧控件必须有统一内边距，不能贴面板边缘。
- 置信度与 IoU 放在同一行；置信度输入框左侧要与选择模型输入框左侧对齐，IoU 与右侧输入框距离要自然。
- 源图和检测结果图与面板边框之间要保留内边距，不能贴边。
- 源图和检测结果图上方要有批量检测结果工具栏，包含第一张、上一张、下一张、最后一张、计数、保存结果、清空结果。
- 批量检测时保持右侧显示第一张图片，不随进度切换，后台持续检测，前端维持在第一张。
- 检测和训练均只允许一次启动，按钮在运行期间禁用，任务结束后恢复。

检测源配置约定：

- 检测模式是下拉框，只包含"图片/视频文件夹"和"摄像头"。
- 选择"图片/视频文件夹"时显示输入源路径选择。
- 选择"摄像头"时用摄像头下拉框替换输入源。
- 检测模式右侧不要放路径选择图标。

### 系统设置

系统设置页面显示 Pixi 环境、Torch/CUDA 版本、GPU、显存、CPU、内存、磁盘、模块检测结果。系统信息区域采用白色外框 + 灰色内卡样式（仿照参考图片），2x4 网格排列，每 0.5 秒自动刷新一次。

系统设置页面还包含"训练前显示自定义命令框"开关，控制训练页是否弹出命令编辑对话框。

### 窗口与控件规范

- 程序图标：项目根目录 `icon.svg`，同时在 `scr/yolo_workbench_qt/assets/` 中放置 `app_icon.png` 和 `app_icon.ico`。窗口标题栏和导航栏左侧均显示图标。
- 程序默认启动尺寸为 `1100 x 780`，最小窗口尺寸为 `980 x 720`。关闭窗口时不要持久化用户拉大的窗口尺寸，避免下次启动又变大；应保持配置里的 `window_width=1100`、`window_height=780`。
- 顶部导航按钮文字使用加粗大号字体，当前约定为 `Microsoft YaHei UI 15 bold`。
- 所有应该选择固定选项的字段都应使用下拉框，不要用只读文本框伪装，例如任务类型、设备、输出方式、保存格式、检测模式、摄像头、优化器等。
- 勾选项必须是真交互，不能只是展示状态；训练增强勾选应影响训练命令参数。
- 所有路径显示：项目文件夹显示绝对路径，其他路径（图片路径、标注路径、结果路径、模型训练界面、模型验证界面）显示相对路径。模型路径进一步简化（如 `result\train-12\weights\best.pt` -> `train-12\best.pt`）。
- 所有按钮添加鼠标悬停高亮效果（QPushButton、softButton、QTableWidget::item）。
- 页面级滚动区域和表格不得出现横向滚动条；界面横向宽度应固定在当前窗口可见范围内，通过列宽/布局自适应解决显示问题。
- 训练和检测启动按钮在运行期间禁用，任务结束后恢复。
- 训练控制模块中三个按钮要视觉居中、上下间距一致；"开始训练"按钮为黑字。模型验证页检测控制的"开始检测 / 暂停 / 停止"三个按钮必须等分宽度，不能因为窗口较窄隐藏"停止"。

### 数据处理交互细节

标注预览：

- 选择图片文件夹和标注文件夹。
- 自动读取图片并匹配与图片同名的 `.txt` 标注文件。
- 自动显示当前图片，不需要额外点击"预览"。
- 必须提供上一张、下一张。

批量重命名：

- 选择文件夹或修改参数后自动执行一次预览。
- 可设置标注文件夹。
- 勾选"标注文件一并更改"时，与图片同名的标注文件也改成对应图片名称。
- 图片重命名遇普通目标名冲突时，应通过临时前缀/临时名称中转后再改到目标名称。
- 如果标注文件夹存在干扰项导致目标标注名冲突，例如图片 `2.jpg` 要改成 `1.jpg`，而标注文件夹同时存在 `1.txt` 和 `2.txt`，应告知用户并取消本次重命名。

## 服务层说明

核心服务接口在 `scr/yolo_workbench/services/`：

- `settings_service.py`：设置文件加载、保存、默认值合并。新增 `training.optimizer` 和 `features.custom_command_dialog` 字段。
- `conversion_service.py`：Labelme 转 YOLO、数据集划分、`data.yaml` 生成。
- `annotation_service.py`：YOLO 标注解析与图像预览绘制。
- `rename_service.py`：批量重命名预览与执行。
- `resize_service.py`：图片备份、缩放、画布归一化。
- `training_service.py`：训练与导出命令生成，支持优化器参数及从 `results.csv` 读取训练曲线数据。
- `detection_service.py`：模型扫描、检测结果解析、推理流程。
- `runtime_service.py`：子进程启动、日志转发、停止进程。
- `environment_service.py`：pixi、模块、GPU/CPU/内存/磁盘状态检测。

设置文件新增字段：

- `training.optimizer`：优化器选择（auto/SGD/Adam/AdamW/RMSProp）。
- `features.custom_command_dialog`：训练前是否弹出自定义命令框。

## 测试说明

当前测试覆盖：

- 设置加载与深合并。
- 转换配置校验。
- Labelme OBB 转换。
- Labelme line 转 OBB。
- Detect bbox 转换。
- YOLO 标注读取与预览渲染。
- 批量重命名预览、执行、冲突检测。
- 图片压缩预览、备份、960 x 960 输出。
- 训练命令生成。
- 模型扫描与检测结果归一化。
- Qt 应用入口和核心功能迁移验证。
- 图标资源、主页网格布局与滚动、主页图表模块、相对路径、训练曲线、悬停高亮、防重复启动、自定义命令框、系统信息样式等功能验证。

运行：

```powershell
pixi run test
```

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
- Qt GUI 可以逐步拆分到 `scr/yolo_workbench_qt/views/`，避免 `app.py` 继续变大；主页图表已先拆到 `scr/yolo_workbench_qt/home_charts.py`。
- 训练曲线已从 `results.csv` 读取数据绘制，当前只保留关键曲线与 Epoch 摘要；后续增加指标时不要让标题区重新拥挤。
- GPU 利用率优先通过 `nvidia-smi` 获取；如果不可用，界面显示"待检测"即可。
- 对任何会改文件的功能，继续坚持"先预览，再执行"。

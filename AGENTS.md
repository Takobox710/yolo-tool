# AGENTS.md — YOLO 本地训练工作台

## 项目概述

本项目是一个独立于 `yolo-weld` 的 Windows 本地可视化 YOLO 训练工作台，使用 **Python + PySide6 / Qt** 开发桌面 GUI。

定位是“通用 YOLO 优先，同时兼容焊缝 OBB 项目”：

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
├── scr/
│   ├── yolo_workbench/
│   │   ├── main.py
│   │   ├── runtime/
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

主界面采用顶部导航：

- 主页
- 数据处理
- 模型训练
- 模型验证
- 系统设置

### 主页

展示项目路径、图片数量、标签文件数量、训练曲线、训练结果模型等概览信息。

不要再添加“最近活动”模块；此前用户明确要求删除该区域。

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

训练页布局按最终 UI 原型实现，并遵循当前交互约定：

- 左侧：`data.yaml`、预训练权重、项目输出、模型 YAML、数据增强选项。
- 右侧：基础模型、学习率、Epochs、Patience、Workers、Batch、图片尺寸、设备。
- 中部左侧保留训练控制模块，但不显示“训练控制”标题。
- 中部右侧保留系统状态模块，但不显示“系统状态”标题。
- 训练日志标题栏右侧放短进度条和百分比，不放开始训练、停止训练、查看模型报告按钮；日志正文应占满面板宽度。

任务类型不再提供手动选项，应根据模型名称自动推断：

- 模型名称包含 `obb` 时使用 `obb`。
- 其他模型默认使用 `detect`。

不要恢复“任务类型”和“导出格式”这两个训练页选项。

不要显示“自动任务类型”“训练控制”“系统状态”这三个标题文字。训练控制和系统状态模块本体要保留但高度要紧凑；任务类型状态行本体也不要显示。进度条放在训练日志标题栏右侧，并在右侧显示百分比。

训练命令由 `training_service.build_train_command()` 生成，格式类似：

```powershell
pixi run yolo obb train model=... data=... epochs=... imgsz=... batch=...
```

### 模型验证

验证页左右比例为 `3:7`：

- 左侧：模型配置、检测源配置、检测控制、检测日志。
- 右侧：源图、检测结果图、检测结果详情表。

支持输入源：

- 图片/视频文件夹
- 摄像头

支持自动扫描 `result/**/weights/*.pt`，也可手动选择模型。

验证页 UI 注意事项：

- 左侧和右侧采用可缩放的 3:7 权重，不要用固定像素宽度锁死，否则小窗口会截断右侧内容。
- 下拉控件使用 `CTkComboBox` 并保持与普通输入框一致的边框，不要再用额外白底外壳模拟边框。
- 所有面板顶部边框和圆角必须完整显示，标题栏不能覆盖面板上边框，也不能让顶部圆角变直角。
- 模型路径、检测模式、输入源等左侧控件必须有统一内边距，不能贴面板边缘。
- 置信度与 IoU 放在同一行；置信度输入框左侧要与选择模型输入框左侧对齐，IoU 与右侧输入框距离要自然。
- 源图和检测结果图与面板边框之间要保留内边距，不能贴边。
- 源图和检测结果图上方要有批量检测结果工具栏，包含上一张、下一张、计数、保存结果、清空结果。

检测源配置约定：

- 检测模式是下拉框，只包含“图片/视频文件夹”和“摄像头”。
- 选择“图片/视频文件夹”时显示输入源路径选择。
- 选择“摄像头”时用摄像头下拉框替换输入源。
- 检测模式右侧不要放路径选择图标。

### 窗口与控件规范

程序默认启动和最小窗口尺寸为 `1100 x 780`。关闭窗口时不要持久化用户拉大的窗口尺寸，避免下次启动又变大；应保持配置里的 `window_width=1100`、`window_height=780`。

顶部导航按钮文字使用加粗大号字体，当前约定为 `Microsoft YaHei UI 15 bold`。

所有应该选择固定选项的字段都应使用下拉框，不要用只读文本框伪装，例如任务类型、设备、输出方式、保存格式、检测模式、摄像头等。

勾选项必须是真交互，不能只是展示状态；训练增强勾选应影响训练命令参数。

训练控制模块中三个按钮要视觉居中、上下间距一致；“开始训练”按钮为黑字。模型验证页检测控制的“开始检测 / 暂停 / 停止”三个按钮必须等分宽度，不能因为窗口较窄隐藏“停止”。

### 数据处理交互细节

标注预览：

- 选择图片文件夹和标注文件夹。
- 自动读取图片并匹配与图片同名的 `.txt` 标注文件。
- 自动显示当前图片，不需要额外点击“预览”。
- 必须提供上一张、下一张。

批量重命名：

- 选择文件夹或修改参数后自动执行一次预览。
- 可设置标注文件夹。
- 勾选“标注文件一并更改”时，与图片同名的标注文件也改成对应图片名称。
- 图片重命名遇普通目标名冲突时，应通过临时前缀/临时名称中转后再改到目标名称。
- 如果标注文件夹存在干扰项导致目标标注名冲突，例如图片 `2.jpg` 要改成 `1.jpg`，而标注文件夹同时存在 `1.txt` 和 `2.txt`，应告知用户并取消本次重命名。

## 服务层说明

核心服务接口在 `scr/yolo_workbench/services/`：

- `settings_service.py`：设置文件加载、保存、默认值合并。
- `conversion_service.py`：Labelme 转 YOLO、数据集划分、`data.yaml` 生成。
- `annotation_service.py`：YOLO 标注解析与图像预览绘制。
- `rename_service.py`：批量重命名预览与执行。
- `resize_service.py`：图片备份、缩放、画布归一化。
- `training_service.py`：训练与导出命令生成。
- `detection_service.py`：模型扫描、检测结果解析、推理流程。
- `runtime_service.py`：子进程启动、日志转发、停止进程。
- `environment_service.py`：pixi、模块、GPU/CPU/内存/磁盘状态检测。

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
- Qt GUI 可以逐步拆分到 `scr/yolo_workbench_qt/views/`，避免 `app.py` 继续变大。
- 训练进度条目前可以先基于日志解析，后续可读取 `results.csv` 做更准确进度与曲线。
- GPU 利用率优先通过 `nvidia-smi` 获取；如果不可用，界面显示“待检测”即可。
- 对任何会改文件的功能，继续坚持“先预览，再执行”。

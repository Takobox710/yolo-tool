# yolo_tool

基于 Python + PySide6 / Qt 的本地 YOLO 可视化训练工作台，面向 Windows 桌面环境，主打“通用 YOLO 优先，同时兼容焊缝 OBB 项目”的本地数据处理、训练与验证流程。

项目独立于 `yolo-weld`，使用本仓库自己的 `pixi` 环境管理依赖，不依赖外部 conda 环境。

## 项目特点

- 支持 YOLO `obb` 与普通 `detect` 两类任务。
- 提供完整桌面 GUI，包含主页、数据处理、模型训练、模型验证、系统设置五个主页面。
- 内置焊缝项目常用约定，默认类别可为 `weld`，兼容 Labelme 标注流程。
- 支持 Labelme 转 YOLO，也支持对已存在的 YOLO `.txt` 标注直接分组并生成数据集。
- 支持 `oriented_rectangle` 转 OBB，支持 `line` 标注按半宽扩展为旋转框。
- 训练命令由服务层统一生成，支持优化器、HSV、MixUp、Mosaic 等常见参数。
- 支持扫描 `data/models/*.pt` 与 `result/**/weights/*.pt` 作为模型候选。
- 支持图片/视频文件夹、单图片/视频、摄像头三类验证输入源。
- 主要配置会持久化到当前项目目录的 `data/runtime/settings.json`，切换项目目录后会自动读取该项目自己的配置。
- 支持 PyInstaller `onedir` 绿色版打包，目标 Windows 机器无需安装 Python 或 pixi。
- 服务层与测试已拆分，便于后续继续扩展 GUI 而不把业务逻辑写死在界面回调中。

## 主要功能

### 1. 主页

- 展示项目路径、图片数量、标签数量、训练曲线、训练历史等概览信息。
- 自动读取 `results.csv` 绘制关键训练曲线。
- 自动扫描 `result/**/weights/*.pt` 展示训练历史。

### 2. 数据处理

- 标注转换：支持 Labelme -> YOLO，或已有 YOLO 标签重新分组。
- 标注预览：读取图片与同名 `.txt` 标签进行可视化预览。
- 批量重命名：支持图片、Labelme `.json`、YOLO `.txt` 联动重命名。
- 图片压缩：先备份原图，再按长边缩放并贴到统一画布。

### 3. 模型训练

- 自动从模型名称推断 `obb` 或 `detect`。
- 基础模型优先从 `data/models/` 读取，也允许手动输入。
- 支持训练前弹出命令编辑对话框，便于手动微调最终命令。
- 后台刷新 GPU、显存、CPU、内存状态，避免阻塞页面交互。

训练命令示例：

```powershell
python -m scr.main --yolo-train obb train model=... data=... epochs=... imgsz=... batch=... optimizer=...
```

打包后的程序会通过 `YOLOTool.exe --yolo-train ...` 启动内部训练入口，不依赖目标机器上的 `pixi` 或 `yolo` 命令。

### 4. 模型验证

- 支持图片/视频文件夹、单文件、摄像头三种检测模式。
- 批量检测按自然数字排序处理输入文件。
- 摄像头实时检测时，即使当前帧无目标，也会持续显示摄像头画面，避免黑屏。

### 5. 系统设置

- 查看 Pixi、Torch/CUDA、GPU、CPU、内存、磁盘、模块检测结果。
- 控制“训练前显示自定义命令框”。
- 控制字段名后的 `ⓘ` 解释符号显示，但不会移除 tooltip。

## 技术栈

- Python 3.12
- PySide6 / Qt
- Ultralytics
- Pillow
- OpenCV
- Matplotlib
- PyYAML
- scikit-learn
- psutil
- pytest
- torch / torchvision / torchaudio（目标 CUDA 13.0）

依赖由 `pixi.toml` 管理，PyTorch 相关包通过独立 PyPI 索引拉取 CUDA 13.0 版本。

## 目录结构

```text
yolo_tool/
├── AGENTS.md
├── README.md
├── pixi.toml
├── pixi.lock
├── docs/
│   └── packaging-windows.md
├── packaging/
│   ├── YOLOTool.spec
│   └── build_windows.ps1
└── scr/
    ├── app.py
    ├── main.py
    ├── context.py
    ├── paths.py
    ├── theme.py
    ├── train_cli.py
    ├── runtime/
    │   └── settings.json
    ├── assets/
    ├── services/
    ├── ui/
    │   ├── widgets/
    │   └── views/
    └── tests/
```

项目代码统一放在 `scr/` 目录下，测试代码放在 `scr/tests/`。

## 环境准备

推荐使用 Pixi：

```powershell
pixi install
```

如果需要确认 PyTorch/CUDA 是否正确安装，可执行：

```powershell
pixi run python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
```

目标是 `torch.version.cuda` 对应 CUDA 13 系列，且 `torch.cuda.is_available()` 为 `True`。

## 启动方式

启动 GUI：

```powershell
pixi run app
```

等价入口：

```powershell
pixi run python -m scr.main
```

## Windows 绿色版打包

推荐使用 PyInstaller `onedir` 形式打包：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

打包产物位于：

```text
dist/YOLOTool/
├── YOLOTool.exe
├── _internal/
├── data/
│   ├── models/
│   └── runtime/
│       └── settings.json
├── images/
├── labels/
└── result/
```

把整个 `dist/YOLOTool/` 文件夹复制到其他 Windows 机器即可运行。CUDA 版仍要求目标机器安装兼容的 NVIDIA 驱动。

更多说明见 `docs/packaging-windows.md`。

## 测试与检查

运行测试：

```powershell
pixi run test
```

静态编译检查：

```powershell
pixi run check
```

## 默认目录约定

- 图片目录：`images/`
- 标签目录：`labels/`
- 数据集目录：`data/`
- 基础模型目录：`data/models/`
- 训练结果目录：`result/`
- 运行时设置：`data/runtime/settings.json`

默认窗口尺寸为 `1100 x 770`，最小尺寸为 `800 x 600`。

## 已覆盖测试

当前测试主要覆盖以下内容：

- 设置加载与默认值深合并。
- Labelme OBB / detect / line 转换。
- 已有 YOLO 标注分组与类别自动命名。
- 标注解析与预览渲染。
- 批量重命名预览、执行、冲突处理。
- 图片压缩预览、备份与统一画布输出。
- 训练命令生成与模型路径解析。
- 项目级运行时配置、项目目录切换后配置重载。
- PyInstaller 打包入口与后台子进程隐藏窗口行为。
- 模型扫描、检测结果归一化、输入源自然排序。
- 摄像头实时预览与“无目标不黑屏”回归。
- Qt 应用入口、页面拆分、帮助符号显示、占位提示、日志框只读行为等界面约定。

## 注意事项

- 本项目当前面向 Windows 本地桌面环境。
- `.pixi/` 不应提交到 git。
- `data/`、`images/`、`labels/`、`result/` 属于本地工作数据目录，默认已在 `.gitignore` 中忽略。
- 当前项目的配置文件位于 `data/runtime/settings.json`；`scr/runtime/settings.json` 仅保留为源码内历史/默认配置参考。
- PyInstaller 生成的 `build/`、`dist/` 属于构建产物，默认已在 `.gitignore` 中忽略。
- 如果编译或测试错误连续出现 5 次仍未解决，应停止并由人类介入排查。

## 与 yolo-weld 的关系

原参考项目位于：

```text
D:\ruanjian\User\Python\yolo-weld
```

本项目仅参考其流程与脚本思路，不直接依赖原项目代码或环境。

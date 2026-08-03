# YOLOTool

<p align="center">
  <img src="src/assets/app_icon.png" alt="YOLOTool 图标" width="144">
</p>

<p align="center">
  Windows 本地 YOLO 数据处理、训练与验证工作台
</p>

<p align="center">
  <a href="https://github.com/Takobox710/yolo-tool/releases"><img alt="Release" src="https://img.shields.io/github/v/release/Takobox710/yolo-tool?display_name=tag&label=Release&color=2ea44f"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB">
  <img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-2.13.0%2Bcu130-ee4c2c">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows-0078D4">
</p>

YOLOTool 是一个基于 Python、Qt 和 Ultralytics 的 Windows 桌面 YOLO 训练工作台，覆盖图片标注、数据集整理、模型训练、模型验证和格式转换，支持 YOLO 的 `detect`、`obb` 和 `seg` 任务

## 快速开始

在 Windows 的 PowerShell 7 环境中，从仓库根目录执行：

```powershell
pixi install
pixi run app
```

等价启动入口：

```powershell
pixi run app-qt
pixi run python -m src.main
```

也可以双击 `src/open_yolo_tool.pyw`。程序启动后默认进入主页；项目目录和项目设置在系统设置中管理，当前项目设置保存到 `data/runtime/settings.json`。

## 功能总览

| 页面/模块 | 主要能力 |
| --- | --- |
| 主页 | 项目统计、标注分布、训练曲线和训练历史；大目录统计在后台执行。 |
| 数据标注 | Labelme 标注读写、矩形/圆形/有向矩形/多边形/直线扩展、类别管理、撤销恢复和自动保存。 |
| AI 标注 | YOLO / SAM 预标注，SAM 2/2.1 画布悬停辅助标注，SAM 3 文本提示预标注。 |
| 数据处理 | Labelme 转 YOLO、YOLO 原生数据集划分、标注预览、批量重命名和图片压缩。 |
| 模型训练 | 自动识别任务类型，统一生成训练命令，支持增强参数、命令编辑和中途停止。 |
| 模型验证 | 图片、视频、摄像头和数据集验证；按模式保存图片、标签或视频结果。 |
| 模型转换 | YOLO 支持 ONNX、TorchScript、OpenVINO、TensorRT、NCNN；支持 SAM 模型导出。 |
| 系统设置 | 环境状态、项目设置、默认值恢复、Release 检查和 GPU/CPU 更新资源选择。 |

## 环境与任务

支持的任务和标注链路：

- YOLO `detect`、`obb`、`seg` 三种任务类型。
- Labelme `.json` 与 YOLO `.txt` 互转，支持类别映射和转换产物备份。
- 标注编辑器提供矩形、圆形、有向矩形、多边形和直线等标注形状；这些形状与 YOLO 任务类型是两个不同层次的概念。
- 有向矩形标注可用于构建 OBB 数据集，直线可按半宽扩展为区域后参与数据集转换。
- SAM 2/2.1 画布辅助标注和 SAM 3 文本提示预标注；官方 `sam3.pt` 由用户自行放入 `data/models/`。

模型格式转换能力：

| 环境 | 格式 |
| --- | --- |
| GPU | ONNX、TorchScript、OpenVINO、TensorRT、NCNN |
| CPU | ONNX、TorchScript、OpenVINO、NCNN |

模型转换默认扫描 `result/**/weights/*.pt`；基础模型和 SAM checkpoint 可通过浏览按钮选择，默认输出到 `data/models/model_exports/<模型名>/`。YOLO 转换支持多种精度、动态输入、NMS、校准和转换后验证。

Pixi 环境由 `pixi.toml` 管理：

| 环境 | 用途 |
| --- | --- |
| `default` | GPU 开发、GPU GUI、基础包和附加包构建。 |
| `release-cpu` | CPU 安装包构建，使用 CPU Torch、CPU ONNX Runtime，并内置 CPU 版 OpenVINO、NNCF、NCNN、PNNX。 |

检查 CPU 发布依赖：

```powershell
pixi run -e release-cpu python -m src.devtools.cpu_package_guard
```

## 推荐工作流

1. **创建项目**：在主页或系统设置中选择项目目录，确认基础模型和类别设置。
2. **准备标注**：在数据标注页读写 Labelme 标注；需要 YOLO 输出时，在更多设置中开启自动转换或保存 YOLO 标注。
3. **整理数据集**：在数据处理中选择 Labelme 转换模式或 YOLO 原生划分模式。默认比例为 `train=0.8`、`val=0.2`、`test=0.0`，空 split 不预建目录。
4. **训练模型**：默认基础模型为 `data/models/yolo11s.pt`；训练页根据模型名称自动选择 `detect`、`obb` 或 `seg` 任务，其余训练参数在页面中配置。
5. **验证结果**：模型验证默认显示训练产物中的 `best.pt`；开启“模型验证显示 last”后才显示 `last.pt`。普通图片检测默认输出到 `result/gui_val`，标签位于输出目录的 `labels/` 子目录；视频输出为 MP4。
6. **导出模型**：在数据处理中选择目标格式，按需配置精度、动态轴、NMS、opset、校准和验证参数。

## 项目数据

| 路径 | 用途 |
| --- | --- |
| `images/` | 默认图片目录，同时作为默认 Labelme 标注目录。 |
| `labels/` | 默认 YOLO 标注目录。 |
| `data/` | 数据集和项目数据目录。 |
| `data/models/` | 基础模型、SAM checkpoint 和模型导出目录。 |
| `data/models/model_exports/` | 模型格式转换默认输出目录。 |
| `result/` | 训练结果和验证结果目录。 |
| `result/gui_val/` | 模型验证默认输出目录。 |
| `data/runtime/settings.json` | 当前项目设置。 |
| `data/runtime/app_state.json` | 应用级最近项目状态。 |

项目数据、训练结果、用户模型和运行时设置属于本地工作数据；`.pixi/`、`build/`、`dist/` 和训练产物不应提交到 Git。

## Windows 发布

GPU 发布拆分为程序安装器、基础环境包和可选模型转换附加包；CPU 发布为内嵌完整运行时和模型的一体式安装器。

| 发布物 | 用途 |
| --- | --- |
| `YOLOTool_Setup_<版本>.exe` | GPU 程序安装器和普通程序更新。 |
| `YOLOTool_BaseEnv_<版本>.7z` | GPU 基础运行环境、模型和 SAM 资源。 |
| `YOLOTool_ExtraEnv_<版本>.7z` | GPU OpenVINO、NNCF、NCNN/PNNX、TensorRT 和 GPU ONNX Runtime 覆盖层。 |
| `YOLOTool_CPU_Setup_<版本>.exe` | CPU 一体式安装器，包含 CPU 运行时和模型。 |

常用构建命令：

```powershell
# GPU 完整发布
pwsh -NoProfile -ExecutionPolicy Bypass -File installer/package_windows.ps1 -BuildBaseRuntimeModels -BuildModelExportRuntime

# CPU 完整发布
pwsh -NoProfile -ExecutionPolicy Bypass -File installer/package_windows.ps1 -Variant CPU -Clean

# 普通程序更新，复用已有 GPU 环境包
pwsh -NoProfile -ExecutionPolicy Bypass -File installer/package_windows.ps1

# 本地开发快包
pwsh -NoProfile -ExecutionPolicy Bypass -File installer/build_windows.ps1 -Mode dev
```

根目录双击入口：

- `打包程序.bat`：通过 PowerShell 7 菜单选择 GPU/CPU 全量发布、环境包归档、复用已有 GPU 环境包的程序安装器或开发快包。

安装事务、环境包内容、更新下载和卸载保留规则见 [docs/packaging-windows.md](docs/packaging-windows.md)。

## 开发与测试

完整检查：

```powershell
pixi run check
pixi run test
```

分层回归：

```powershell
pixi run test-fast
pixi run test-ui
pixi run test-integration
pixi run test-full
```

当前测试覆盖服务层、UI、集成入口、隐藏 CLI、PyInstaller、Windows 安装器和分层打包契约，也覆盖设置迁移、任务停止、日志清洗、模型转换和用户文件安全。

开发态入口为 `python -m src.main`；打包后训练、导出和验证由统一 CLI 分发：

```powershell
YOLOTool.exe --yolo-train ...
YOLOTool.exe --yolo-export ...
YOLOTool.exe --yolo-val ...
```

业务逻辑位于 `src/services/`，Qt 页面位于 `src/ui/`，共享上下文和任务协调器负责页面间状态与后台任务；服务层不依赖 UI 层。

## 项目结构

```text
yolo_tool/
├── AGENTS.md
├── README.md
├── pixi.toml
├── docs/
│   ├── architecture.md
│   ├── packaging-windows.md
│   ├── code-inventory.md
│   └── spec/
├── installer/
│   ├── YOLOTool.spec
│   ├── build_windows.ps1
│   ├── package_windows.ps1
│   └── hooks/
└── src/
    ├── main.py
    ├── app.py
    ├── train_cli.py
    ├── bootstrap/
    ├── services/
    ├── shared/
    ├── ui/
    ├── runtime/
    ├── assets/
    └── tests/
```

项目代码统一放在 `src/`，测试代码统一放在 `src/tests/`。

## 详细文档

- [架构与维护说明](docs/architecture.md)
- [主页规格](docs/spec/home.md)
- [数据标注规格](docs/spec/annotation.md)
- [数据处理规格](docs/spec/data-processing.md)
- [模型训练规格](docs/spec/training.md)
- [模型验证规格](docs/spec/validation.md)
- [系统设置规格](docs/spec/settings.md)
- [Windows 发布说明](docs/packaging-windows.md)
- [代码清单](docs/code-inventory.md)

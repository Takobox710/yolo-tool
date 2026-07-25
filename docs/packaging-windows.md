# Windows 程序与运行环境分离发布

Windows 冻结程序使用 PyInstaller `onedir`，正式发布拆成三个独立产物。目标机器不需要安装 Python、Pixi、7-Zip 或开发工具。

| 发布物 | 内容 | 更新时机 |
| --- | --- | --- |
| `YOLOTool_Setup_<程序版本>.exe` | 内嵌图标资源的 `YOLOTool.exe`、程序清单和统一安装逻辑 | 普通功能更新 |
| `YOLOTool_BaseEnv_<基础包版本>.7z` | `_internal/`、基础运行时清单、CPU ONNX Runtime 和官方模型 | 基础依赖或官方模型变化 |
| `YOLOTool_ExtraEnv_<附加包版本>.7z` | 基础包没有的 TensorRT 运行库 | TensorRT 或扩展协议变化 |

`Program Setup` 的硬性体积目标是小于 `100 MB`。基础包使用 Pixi 锁定的 7-Zip CLI 生成非固实 LZMA2 `mx=9` 压缩，以兼容 Inno 按文件随机访问；附加包使用 LZMA2 高压缩生成纯 `.7z`。基础运行环境同时携带 `7z.exe` 和 `7z.dll`，软件内安装附加包时优先使用原生解压与 CRC 校验，避免 `py7zr` 解压后再次逐文件读取大包；没有原生工具时才使用 `py7zr + SHA-256` 回退。两者都不包含 `YOLOTool.exe`，目标机不需要另行安装 7-Zip。程序冻结包额外保留 ONNX、ONNX Runtime、OpenCV、Pillow、psutil 和 Ultralytics 的轻量 `.dist-info` 元数据，用于设置页显示精确版本；运行时仍保留模块版本回退。

当前锁定依赖的实测产物：Program Setup 目标小于 `100 MB`，程序-only EXE 约 `2.76 MB`；基础包约 `1.86 GB`，包含完整 `_internal`、`python_stdlib.zip` 和第三方纯 Python 源码；附加包约 `1.72 GB`，解压内容和构建机磁盘速度会影响首次安装耗时。

## Pixi 环境

- `release-base`：构建主程序和基础包，包含 `onnx`、`onnxslim`、CPU `onnxruntime`、OpenVINO、NCNN、PNNX 及其配套依赖，不包含 TensorRT 和 GPU ONNX Runtime。
- `export-full`：开发态及附加包收集环境，使用 `onnxruntime-gpu`，并在基础后端之外提供 TensorRT CUDA 13。
- 默认开发环境组合完整导出依赖，因此 `pixi run app` 可直接测试五种格式；`onnxruntime` 与 `onnxruntime-gpu` 不进入同一 Pixi 环境。

附加包按 Python distribution 文件清单增量收集，只复制 `tensorrt`、`tensorrt-cu13`、`tensorrt-cu13-libs` 和 `tensorrt-cu13-bindings`，不复制 Python、Torch、CUDA、Ultralytics、ONNX、ONNX Runtime、OpenCV 或 PySide6，也不使用宽泛的 `collect_all(...)`。

## 构建命令

只构建冻结程序和 Program staging：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release -PackageType Program -ProgramOnly -Clean
```

`-ProgramOnly` 使用外置运行时构建路径：不扫描 Torch、Ultralytics、OpenVINO、NCNN、ONNX Runtime 等第三方子模块和动态库，只把应用代码、必要的 PySide6 hook 和外置运行时连接 hook 编译进 `YOLOTool.exe`，运行时复用目标目录已有的 `_internal/`。基础包同时保留 PyInstaller 通常嵌入程序 PYZ 的标准库动态导入模块和第三方纯 Python 源码，避免 `python312.dll`、`typing_extensions` 或 `numpy` 入口缺失。程序更新包构建不会重复分析约 1.7 GB 的基础环境；完整环境构建仍使用完整 spec，确保基础包拥有全部后端和版本元数据。

开发快包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

开发快包输出到 `dist/YOLOTool-dev/`，用于本地验证 GUI 和隐藏 CLI，不作为用户安装发布物。

单独构建两个运行包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_base_runtime_models.ps1 -Clean
powershell -ExecutionPolicy Bypass -File installer\build_model_export_runtime.ps1 -Clean
```

根目录提供两个双击入口：

- `打包更新程序.bat`：直接调用 `package_windows.ps1`，复用 `installer/output/` 中已有的 `YOLOTool_BaseEnv_v1.7z`，只重建程序-only 冻结文件、companion catalog 和程序安装器；已有附加包会登记到 catalog，但不会重建，也不会重新生成基础或附加环境包。
- `打包程序.bat`：调用 `package_windows.ps1 -BuildBaseRuntimeModels -BuildModelExportRuntime`，重新构建程序安装器、基础环境包和附加环境包三个发布物。

两个 BAT 均使用纯 ASCII 内容、CRLF 换行和 Windows PowerShell 的绝对系统路径，避免简体中文代码页把 UTF-8 批处理内容解析成乱码并截断命令。

完整发布对应的 PowerShell 命令为：

```powershell
powershell -ExecutionPolicy Bypass -File installer\打包程序.ps1
```

程序更新入口要求当前版本基础包已经存在，否则会明确报错并停止；附加包不存在时仍可生成程序安装器。PowerShell 下也可单独使用 `-SkipBaseRuntimeModels` 或 `-SkipModelExportRuntime`。旧 `Full`、`AppUpdate`、`RuntimeFull` 参数保留一个过渡周期，输出弃用警告后转发到 `Program`。

`installer/base-runtime-models-version.txt`、`runtime-version.txt` 和 `model-export-runtime-version.txt` 分别控制基础包、运行时兼容协议和附加包版本。当前两个包版本均为 `v1`，运行时协议为 `runtime-1`；只有对应内容变化时才提升版本。

## 安装流程

安装器始终允许编辑目录，默认使用 `{autopf}\YOLOTool`。仅当 `LastInstallPath` 同时包含 `YOLOTool.exe` 和 `_internal` 时才复用；失效的 smoke 路径会被清除。目录已存在或非空时不弹提示，安装器只替换受管文件。Inno 在目录页显示前就会解析内部 `AppId`，因此安装器关闭默认卸载登记，并在目录确定后根据规范化路径生成稳定实例 ID 与独立卸载项。

自定义组件页包含：

- 程序本体：始终安装，并显示新装、升级、修复或降级状态；降级需要二次确认。
- 本体环境和模型：新装、环境缺失或运行时版本不兼容时强制安装；兼容环境默认不选，可主动重装。
- 模型转换附加环境：始终可选且默认不选；缺包不阻止主安装。

安装器先按 companion catalog 在自身目录查找两个 `.7z`，也允许浏览选择其他路径。组件页只比较预期文件名、`.7z` 扩展名和 catalog 记录的压缩大小，不读取压缩包正文；完整 SHA-256 在点击“安装”后只计算一次，通过后才允许解压或调用附加包安装。基础包必选但缺失或损坏时禁止继续；附加包缺失只显示提示。

点击安装后，Inno 会先显示独立的“正在验证安装包”输出页，再执行大型压缩包 SHA-256 校验；校验完成后才进入文件解压进度阶段，避免校验期间出现空白界面。安装成功后，卸载文件统一命名为 `uninstall.exe` 和 `uninstall.dat`，并兼容清理旧版 `unins000.exe/.dat`。

Program 与基础环境先进入 `{app}\.install-staging/`。开始解压基础环境时安装器显示“正在解压本体环境和模型”的平滑进度提示；由于 Inno 的外部归档进度按大文件完成边界更新，百分比不再作为逐字节速度指示。旧程序和环境以同卷原子重命名进入 `.install-backup/`，新文件切换后执行 `YOLOTool.exe --runtime-probe`；任何必选步骤失败都会恢复旧程序、旧环境和被覆盖的官方模型。安装清单统一存放在 `{app}\_internal\yolotool_metadata\`，读取时兼容旧根目录并在升级成功后移除旧副本。官方模型按清单合并更新，`yolo26n.pt` 还会复制一份到应用根目录作为受管兼容副本，用户自行加入 `data/models/` 的其他文件不参与替换。

每个实例的 `install-instance.ini` 写入 `_internal\yolotool_metadata\`。附加环境在主事务成功后通过隐藏 CLI 安装到：

```text
%LOCALAPPDATA%\YOLOTool\instances\<实例ID>\extensions\model-export-runtime\
```

升级旧唯一实例时可把旧全局扩展目录原子迁入实例目录；并行安装不会复用其他实例扩展。附加包失败不撤销已经成功的程序和基础环境更新。

## 卸载与数据

安装提交前的 `YOLOTool.exe --runtime-probe` 只读取程序清单和 `_internal` 基础环境清单，比较 `required_runtime_version` 与 `runtime_version`；不导入 Torch、PySide6、ONNX、ONNX Runtime、Ultralytics 或 OpenCV。附加包后台安装的解压进度范围为 5%-95%。

安装器在压缩包校验页结束后使用普通百分比进度条显示程序和基础环境的实际安装进度，不使用忙碌进度条掩盖解压阶段。附加环境使用原生 7-Zip 的实时百分比输出，并将解压进度映射到附加包安装进度。

卸载单个实例会删除程序、`_internal/`、该实例附加环境，以及 `managed-models.json` 登记的官方模型。以下内容保留：

- `data/runtime/settings.json` 项目设置及同目录的最近项目状态
- 用户自行加入的模型
- `images/`、`labels/`、`result/`

若安装根目录仍含用户数据，卸载器不会删除该根目录，也不会影响其他并行实例。

## 发布验证

- 程序安装器小于 `100 MB`，且不包含 `_internal/`、运行时清单和模型；程序-only EXE 启动时必须能在目标目录找到基础包 `_internal/python312.dll`。
- 两个约 2 GB 伴随包存在时，组件页不执行 SHA-256，必须在 3 秒内完成刷新并保持控件可交互。
- 基础包不包含 `YOLOTool.exe`、TensorRT 和 GPU ONNX Runtime；包含 OpenVINO、NCNN、PNNX。
- 附加包只包含 TensorRT 发行包，清单中的文件和 DLL 目录完整；原生 7-Zip 安装路径使用归档 CRC，并实时把解压百分比映射到安装进度，兼容回退路径使用清单 SHA-256。
- 覆盖首次安装、仅程序升级、强制基础包升级、主动重装、确认降级、并行实例与卸载保留数据。
- 使用 detect 与 OBB 模型完成五格式烟雾导出；TensorRT 仅在兼容 NVIDIA CUDA 13 发布机验证。

Inno Setup 要求 6.4 或更高版本。简体中文语言资源固定在 `installer/languages/ChineseSimplified.isl`，构建机无需额外安装语言包。

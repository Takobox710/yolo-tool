# Windows 程序与运行环境分离发布

Windows 冻结程序使用 PyInstaller `onedir`，正式发布拆成三个独立产物。目标机器不需要安装 Python、Pixi、7-Zip 或开发工具。

| 发布物 | 内容 | 更新时机 |
| --- | --- | --- |
| `YOLOTool_Setup_<程序版本>.exe` | 内嵌图标资源的 `YOLOTool.exe`、程序清单和统一安装逻辑 | 普通功能更新 |
| `YOLOTool_BaseEnv_<基础包版本>.7z` | `_internal/`、CPU ONNX Runtime、SAM 2/2.1 Base+ 代码与 checkpoint、基础运行时清单和官方模型 | 基础依赖或官方模型变化 |
| `YOLOTool_ExtraEnv_<附加包版本>.7z` | OpenVINO、NCNN/PNNX 和 TensorRT 模型转换运行库 | 模型转换后端或扩展协议变化 |

`Program Setup` 的硬性体积目标是小于 `100 MB`。基础包和附加包都使用 Pixi 锁定的原生 7-Zip CLI 生成非固实 LZMA2 `mx=5` 压缩，并启用 `-mmt=on` 多线程；基础包以兼容 Inno 按文件随机访问。基础运行环境构建时，第三方纯 Python 源码在 Windows 优先通过系统 `robocopy /S /MT:16` 目录级复制，缺少该工具时回退 Python 逐文件复制；测试、示例、打包工具、测试框架和未使用的 Windows COM/数据库源码不会进入基础包，ONNX 测试数据也会排除。基础运行环境同时携带 `7z.exe` 和 `7z.dll`，软件内安装附加包时优先使用原生解压与 CRC 校验，避免 `py7zr` 解压后再次逐文件读取大包；没有原生工具时才使用 `py7zr + SHA-256` 回退。两者都不包含 `YOLOTool.exe`，目标机不需要另行安装 7-Zip。程序冻结包额外保留 ONNX、ONNX Runtime、OpenCV、Pillow、psutil 和 Ultralytics 的轻量 `.dist-info` 元数据，用于设置页显示精确版本；运行时仍保留模块版本回退。

上一版 v1 归档的实测大小为：基础包约 `1.86 GB`、附加包约 `1.72 GB`；本次 v2 精简后已验证 staging 未压缩大小约 `3.69 GB`，同一 staging 使用 `mx=5` 的基础包约 `2.10 GB`。内容包含 SAM2 checkpoint、约 `562 KB` 的多架构 CUDA 扩展及新增 OpenVINO/NCNN 运行库；Torch/CUDA、OpenCV、ONNX、PySide6、多媒体和 SAM2 运行组件保留。Program Setup 目标仍小于 `100 MB`，程序-only EXE 约 `2.76 MB`。

## Pixi 环境

- `release-base`：构建主程序和基础包，包含 `onnx`、`onnxslim`、CPU `onnxruntime`、SAM 2/2.1 Base+ 及其基础依赖和预编译 CUDA 后处理扩展，不包含 OpenVINO、NCNN、PNNX、TensorRT 和 GPU ONNX Runtime。
- `export-full`：开发态及附加包收集环境，使用 `onnxruntime-gpu`，并提供 OpenVINO、NCNN、PNNX 和 TensorRT CUDA 13。
- 默认开发环境组合完整导出依赖，因此 `pixi run app` 可直接测试五种格式；`onnxruntime` 与 `onnxruntime-gpu` 不进入同一 Pixi 环境。

附加包按 Python distribution 文件清单增量收集，只复制 `openvino`、`openvino-telemetry`、`ncnn`、`pnnx`、`tensorrt`、`tensorrt-cu13`、`tensorrt-cu13-libs` 和 `tensorrt-cu13-bindings`，不复制 Python、Torch、CUDA、Ultralytics、ONNX、ONNX Runtime、OpenCV 或 PySide6，也不使用宽泛的 `collect_all(...)`。附加包清单支持 `openvino`、`engine` 和 `ncnn` 三种扩展格式。

`installer/` 中的脚本保持按发布层次拆分：`build_windows.ps1` 负责冻结程序，两个 `build_*runtime*.ps1` 分别负责基础包和 OpenVINO/NCNN/TensorRT 附加包，`package_windows.ps1` 负责编排和生成安装器。完整发布直接使用 `-BuildBaseRuntimeModels -BuildModelExportRuntime`，程序更新则省略这两个构建开关并复用已有环境包。基础包和附加包都不生成或读取 `.cache.json`，每次完整发布都会重新构建 staging 和归档。基础包生成基础环境清单时复用同一轮已经计算的 `_internal` 和模型哈希，不重复读取大型运行时文件。版本文本文件分别表达基础包、附加包和运行时协议版本，不能合并为单一版本号。PyInstaller 自定义 hook 只保留 Torch、SAM2 收集 hook 和程序-only 外置运行时 hook。

打包窗口会显示中文阶段提示和每个阶段耗时。PyInstaller 阶段显示构建开始、完成和耗时，但 PyInstaller 本身不提供稳定的总百分比接口；基础包和附加包进入原生 7-Zip 压缩后会显示实时压缩百分比和压缩耗时，使用 `mx=5`、非固实 LZMA2 和 `-mmt=on`。两个环境包每次都会重新压缩。

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

开发快包输出到 `dist/YOLOTool-dev/`，用于本地验证 GUI 和隐藏 CLI，不作为用户安装发布物。完整冻结输出会同时写入根目录 `release-manifest.json` 和 `runtime-manifest.json`，因此可直接启动；运行时清单只用于安装器 `--runtime-probe` 和诊断流程，GUI 启动不再因清单或版本不匹配强制退出。`-ProgramOnly` 输出仍需要已有基础环境才能提供完整功能，但安装器允许在缺少新基础包时保留旧环境完成程序更新。

冻结程序包含系统设置页的 GitHub Release 检查逻辑，不新增运行时依赖；用户需要能访问 `api.github.com` 才能获得版本检查结果。检查失败不会影响程序启动、训练或验证。更新窗口将选中的资源下载到 Windows Shell 解析出的真实 `Downloads` 文件夹；环境包更新通过 Release 文件名版本与本机安装清单或 `package-info.ini` 版本比较，Release 始终携带同版本环境包时不会误报更新。源码开发态使用 `installer/base-runtime-models-version.txt` 和 `installer/model-export-runtime-version.txt` 作为当前环境包版本；基础包缺失按环境缺失处理，附加包缺失只显示可选下载安装提示，不触发“环境包也有更新”；仅当已安装附加包的版本低于 Release 时才触发附加包更新提示。程序与更高版本基础包同时需要更新时默认选择两者，仅程序更新时默认选择程序包，程序-only 场景的同版本提示使用普通文字，手动勾选同版本基础包时显示红色重装提醒，基础包单独留下时在进度条下方显示不可安装的红色提醒。附加环境包在仅勾选附加包、同时勾选程序包或三项全部勾选时，按是否已有附加包显示自动安装、替换或组合状态提示，三项全选时合并确认基础包重装和附加包替换。已有安装但缺少更新基础包时，安装器保留旧环境并警告版本不匹配或环境不完整，继续完成程序更新；首次安装缺少基础包时在组件页直接阻止提交，安装提交阶段不会生成没有运行环境的程序-only 首次安装。附加包可以在程序内热安装或替换。下载按钮右侧可暂停/继续下载或安装器进程。下载期间窗口不允许关闭，安装器启动失败会在窗口中显示为可恢复错误。

单独构建两个运行包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_base_runtime_models.ps1 -Clean
powershell -ExecutionPolicy Bypass -File installer\build_model_export_runtime.ps1 -Clean
```

根目录提供两个双击入口：

- `打包更新程序.bat`：直接调用 `package_windows.ps1`，复用 `installer/output/` 中已有的 `YOLOTool_BaseEnv_v2.7z`，只重建程序-only 冻结文件、companion catalog 和程序安装器；已有附加包会登记到 catalog，但不会重建，也不会重新生成基础或附加环境包。
- `打包程序.bat`：调用 `package_windows.ps1 -BuildBaseRuntimeModels -BuildModelExportRuntime`，重新构建程序安装器、基础环境包和附加环境包三个发布物；两个环境包默认使用原生 7-Zip `mx=5`。

两个 BAT 均使用纯 ASCII 内容、CRLF 换行和 Windows PowerShell 的绝对系统路径，避免简体中文代码页把 UTF-8 批处理内容解析成乱码并截断命令。

完整发布对应的 PowerShell 命令为：

```powershell
powershell -ExecutionPolicy Bypass -File installer\package_windows.ps1 -BuildBaseRuntimeModels -BuildModelExportRuntime
```

程序更新入口要求当前版本基础包已经存在，否则会明确报错并停止；附加包不存在时仍可生成程序安装器。PowerShell 下也可单独使用 `-SkipBaseRuntimeModels` 或 `-SkipModelExportRuntime`。默认完整命令每次重新复制、哈希和压缩两个环境包 staging。`-Clean` 用于强制完整重建，并清理对应的冻结输出、staging 和归档。压缩参数使用基础包和附加包原生 7-Zip `mx=5`、非固实 LZMA2 与 `-mmt=on`。旧 `Full`、`AppUpdate`、`RuntimeFull` 参数保留一个过渡周期，输出弃用警告后转发到 `Program`。

`installer/base-runtime-models-version.txt`、`runtime-version.txt` 和 `model-export-runtime-version.txt` 分别控制基础包、运行时兼容协议和附加包版本。当前两个包版本均为 `v2`，运行时协议为 `runtime-2`；只有对应内容变化时才提升版本。

## 安装流程

安装器始终允许编辑目录，默认使用 `{autopf}\YOLOTool`。仅当 `LastInstallPath` 同时包含 `YOLOTool.exe` 和 `_internal` 时才复用；失效的 smoke 路径会被清除。目录已存在或非空时不弹提示，安装器只替换受管文件。Inno 在目录页显示前就会解析内部 `AppId`，因此安装器关闭默认卸载登记，并在目录确定后根据规范化路径生成稳定实例 ID 与独立卸载项。

自定义组件页包含：

- 程序本体：始终安装，并显示新装、升级、修复或降级状态；降级需要二次确认。
- 本体环境和模型：首次安装、环境缺失或运行时版本不兼容时必须提供并安装；首次安装缺包时阻止提交，已有兼容环境时默认不选，可主动重装或只更新程序。
- 模型转换附加环境：始终可选且默认不选；缺包不阻止主安装。

安装器先按 companion catalog 在自身目录查找两个 `.7z`，也允许浏览选择其他路径。组件页只比较预期文件名、`.7z` 扩展名和 catalog 记录的压缩大小，不读取压缩包正文；完整 SHA-256 在点击“安装”后只计算一次，通过后才允许解压或调用附加包安装。首次安装基础包缺失或损坏时显示红色风险提示并阻止继续，组件页同时显示“进入 GitHub 下载”按钮，点击后打开 YOLOTool Release 页面；已有安装缺少更新基础包时可保留旧环境进行程序更新，并警告版本不匹配或环境不完整；附加包缺失只显示提示。实际安装基础包时仍会校验哈希。

点击安装后，Inno 会先显示独立的“正在验证安装包”输出页，再执行大型压缩包 SHA-256 校验；校验完成后才进入文件解压进度阶段，避免校验期间出现空白界面。安装成功页使用 Inno 原生 `[Run]` 条目提供“安装完成后删除本次使用的安装包和环境包”选项，复选框与“启动 YOLOTool”自动对齐；勾选后由隐藏命令延迟删除当前安装器、基础环境包和已选附加环境包，安装器本体因正在运行会在退出后自动删除。安装成功后，卸载文件统一命名为 `uninstall.exe` 和 `uninstall.dat`，并兼容清理旧版 `unins000.exe/.dat`。

安装进入文件替换前会通过 Inno Setup 的 Windows Restart Manager 注册当前安装目录中的 `YOLOTool.exe`；没有目标进程时直接继续，发现目标实例时由安装器自动关闭，不弹出是否停止应用的询问页，也不使用 PowerShell 或 WMI。其他安装目录的并行实例不会被停止。自动关闭前应由程序自身保存完必要状态，安装器不负责恢复未保存的数据。

Program 与基础环境先进入 `{app}\.install-staging/`。开始解压基础环境时安装器显示“正在解压本体环境和模型”的平滑进度提示；由于 Inno 的外部归档进度按大文件完成边界更新，百分比不再作为逐字节速度指示。旧程序和环境以同卷原子重命名进入 `.install-backup/`，新文件切换后执行 `YOLOTool.exe --runtime-probe`；文件切换、卸载登记等必选安装步骤失败时恢复旧程序、旧环境和被覆盖的官方模型，运行环境版本不一致或自检未通过时只显示警告并继续安装，提示部分功能可能无法使用。安装清单统一存放在 `{app}\_internal\yolotool_metadata\`，读取时兼容旧根目录并在升级成功后移除旧副本。官方模型按清单合并更新，`yolo26n.pt` 还会复制一份到应用根目录作为受管兼容副本，用户自行加入 `data/models/` 的其他文件不参与替换。

每个实例的 `install-instance.ini` 写入 `_internal\yolotool_metadata\`。附加环境在主事务成功后通过隐藏 CLI 安装到当前程序目录；旧版 `%LOCALAPPDATA%` 附加环境同盘时原子迁移，跨盘时复制完成后删除旧目录：

```text
{app}\_internal\extensions\model-export-runtime\
```

升级旧实例时可把 `%LOCALAPPDATA%\YOLOTool\instances\<实例ID>\extensions\` 或旧全局扩展目录原子迁入当前程序目录；基础环境替换 `_internal` 时会临时保留扩展目录。附加包失败不撤销已经成功的程序和基础环境更新。

## 卸载与数据

隐藏 CLI 由 `src/bootstrap/cli_dispatch.py` 的唯一 flag 映射分发到按训练、验证/预测、模型导出、AI 标注和运行时维护划分的 handler；handler 只负责参数、服务调用、结构化输出和退出码。`src/train_cli.py` 保留懒加载 `run_*` 兼容转发，冻结态与开发态继续使用同一命令协议。

安装提交前的 `YOLOTool.exe --runtime-probe` 只读取程序清单和 `_internal` 基础环境清单，比较 `required_runtime_version` 与 `runtime_version`；不导入 Torch、PySide6、ONNX、ONNX Runtime、Ultralytics 或 OpenCV。比较不一致或自检无法完成时只显示“部分功能可能无法使用”的警告，不撤销已经完成的文件切换。附加包后台安装的解压进度范围为 5%-95%。

安装器在压缩包校验页结束后使用普通百分比进度条显示程序和基础环境的实际安装进度，不使用忙碌进度条掩盖解压阶段。附加环境使用原生 7-Zip 的实时百分比输出，并将解压进度映射到附加包安装进度。

卸载单个实例会删除程序、`_internal/`、该实例附加环境，以及 `managed-models.json` 登记的官方模型。以下内容保留：

- `data/runtime/settings.json` 项目设置及同目录的最近项目状态
- 用户自行加入的模型
- `images/`、`labels/`、`result/`

若安装根目录仍含用户数据，卸载器不会删除该根目录，也不会影响其他并行实例。

## 发布验证

- 程序安装器小于 `100 MB`，且不包含 `_internal/`、运行时清单和模型；程序-only EXE 启动时必须能在目标目录找到基础包 `_internal/python312.dll`。
- 两个约 2 GB 伴随包存在时，组件页不执行 SHA-256，必须在 3 秒内完成刷新并保持控件可交互。
- 基础包不包含 `YOLOTool.exe`、OpenVINO、NCNN、PNNX、TensorRT 和 GPU ONNX Runtime；包含 SAM 2/2.1 Base+ 代码、配置和 checkpoint。
- 附加包包含 OpenVINO、NCNN/PNNX 和 TensorRT 发行包，清单中的文件和 DLL 目录完整；原生 7-Zip 安装路径使用归档 CRC，并实时把解压百分比映射到安装进度，兼容回退路径使用清单 SHA-256。
- 覆盖首次安装、仅程序升级、强制基础包升级、主动重装、确认降级、并行实例与卸载保留数据。
- 使用 detect 与 OBB 模型完成五格式烟雾导出；TensorRT 仅在兼容 NVIDIA CUDA 13 发布机验证。

Inno Setup 要求 6.4 或更高版本。简体中文语言资源固定在 `installer/languages/ChineseSimplified.isl`，构建机无需额外安装语言包。

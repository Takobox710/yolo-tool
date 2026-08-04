# Windows 程序与运行环境分离发布

Windows 冻结程序使用 PyInstaller `onedir`，GPU 与 CPU 分别发布。目标机器不需要安装 Python、Pixi、7-Zip 或开发工具。

| 发布物 | 内容 | 更新时机 |
| --- | --- | --- |
| `YOLOTool_Setup_<程序版本>.exe` | 内嵌图标资源的 `YOLOTool.exe`、程序清单和统一安装逻辑 | 普通功能更新 |
| `YOLOTool_BaseEnv_<基础包版本>.7z` | `_internal/`、CPU ONNX Runtime、SAM 2/2.1 Base+ 与 SAM 3 推理代码/依赖、基础运行时清单和官方模型 | 基础依赖或官方模型变化 |
| `YOLOTool_ExtraEnv_<附加包版本>.7z` | OpenVINO、NNCF、NCNN/PNNX 和 TensorRT 模型转换运行库 | 模型转换后端或扩展协议变化 |

CPU 变体只发布 `YOLOTool_CPU_Setup_<版本>.exe` 一体式安装包。CPU 安装包使用 CPU Torch、CPU `onnxruntime`，直接把完整 `dist/CPU/YOLOTool` 冻结目录交给 Inno Setup 内嵌；安装器从完整目录排除根目录 `YOLOTool.exe`，只从程序 staging 安装一份程序本体，避免 EXE 重复携带。不生成 `BaseRuntimeModels-CPU`、CPU BaseEnv/ExtraEnv 压缩包或第二次 `ProgramOnly` 构建，也不携带 CUDA、TensorRT、GPU ONNX Runtime 或 NVIDIA CUDA DLL。CPU 内置 OpenVINO 仅保留 CPU 插件、模型前端和通用 TBB 运行库，排除 GPU/NPU/自动设备插件及开发期库文件。CPU 安装器默认目录为 `YOLOTool_CPU`。

`Program Setup` 的硬性体积目标是小于 `100 MB`。GPU 附加包和基础包默认使用 Pixi 锁定的原生 7-Zip CLI 生成单卷非固实 LZMA2 `mx=5` 压缩；只有显式传入 `-SplitBaseArchive` 时，GPU 基础包才使用 `-v1073700000b` 生成最多两个 `.7z.001/.002` 分卷，每卷严格小于 `1 GiB`。CPU 发布不生成任何运行时压缩包，而是把 CPU 基础运行时 staging 作为 Inno Setup 的内嵌文件直接写入一体式安装器。GPU 安装器和 Release 更新兼容单卷 `.7z` 与特殊分卷基础包；CPU 更新只选择 CPU Setup，不查找或下载 CPU BaseEnv/ExtraEnv。基础运行环境构建时，第三方纯 Python 源码在 Windows 优先通过系统 `robocopy /S /MT:16` 目录级复制，缺少该工具时回退 Python 逐文件复制；测试、示例、打包工具、测试框架和未使用的 Windows COM/数据库源码不会进入基础包，ONNX 测试数据也会排除。GPU 基础运行环境同时携带 `7z.exe` 和 `7z.dll`，软件内安装附加包时优先使用原生解压与 CRC 校验，避免 `py7zr` 解压后再次扫描大包；没有原生工具时回退到 `py7zr` 解压并检查文件集合。GPU 基础包不包含 `YOLOTool.exe`，目标机不需要另行安装 7-Zip；CPU 一体式安装器则由 Inno Setup 一次性安装程序和运行时。程序冻结包额外保留 ONNX、ONNX Runtime、OpenCV、Pillow、psutil 和 Ultralytics 的轻量 `.dist-info` 元数据，用于设置页显示精确版本；运行时仍保留模块版本回退。

上一版 v1 归档的实测大小为：基础包约 `1.86 GB`、附加包约 `1.72 GB`；本次 v2 精简后已验证 staging 未压缩大小约 `3.69 GB`，同一 staging 使用 `mx=5` 的基础包约 `2.10 GB`。内容包含 SAM2 checkpoint、约 `562 KB` 的多架构 CUDA 扩展及新增 OpenVINO/NCNN 运行库；Torch/CUDA、OpenCV、ONNX、PySide6、多媒体和 SAM2 运行组件保留。Program Setup 目标仍小于 `100 MB`，程序-only EXE 约 `2.76 MB`。

冻结程序的训练与验证入口支持 `detect`、`obb`、`seg` 三种任务；Seg 数据集使用与其他任务相同的 `train/val/test/images` 和 `labels` 目录结构，任务类型由模型名称和 CLI 参数传递。

## Pixi 环境

GPU 完整发布先生成完整 `dist/YOLOTool` 供基础环境包提取 `_internal`，基础包归档完成后再生成 `-ProgramOnly` 的程序 staging。CPU 发布只生成一次完整 `dist/CPU/YOLOTool`，Inno Setup 直接从该目录组装一体式安装器。

- `default`：构建 GPU 主程序、基础包和附加包，完整冻结源使用 GPU `onnxruntime-gpu`；GPU BaseEnv 生成时改用 `release-cpu` 中同版本 CPU ONNX Runtime，GPU ORT 作为 ExtraEnv 的隔离覆盖层提供。默认环境同时承担开发和 GPU 发布职责。
- `cpu` / `release-cpu`：构建 CPU 一体式安装器，使用 CPU Torch、CPU `onnxruntime`，并内置 CPU-only OpenVINO、NNCF、NCNN、PNNX；OpenVINO GPU/NPU/自动设备插件不进入冻结目录，CPU 环境的锁定依赖和冻结内容通过 `src.devtools.cpu_package_guard` 检查。
- 默认环境包含完整 GPU 导出依赖，因此 `pixi run app` 可直接测试五种格式、YOLO/SAM2 ONNX 精度转换和 INT8 校准，也可直接用于 GPU 发布；CPU 发布使用 `pixi run -e release-cpu`，两个环境的共享导出与工具链包保持同一锁定版本，只有 Torch wheel 和 ONNX Runtime 按 CPU/GPU 变体隔离。

附加包按共享的 Python distribution 文件清单增量收集，包含 `openvino`、`openvino-telemetry`、`nncf` 及其运行时依赖、`ncnn`、`pnnx`、`tensorrt`、`tensorrt-cu13`、`tensorrt-cu13-libs`、`tensorrt-cu13-bindings`，并将 `onnxruntime-gpu` 放入 `packages/_onnxruntime_gpu/` 隔离覆盖层；不复制 Python、Torch、CUDA、Ultralytics、ONNX、OpenCV 或 PySide6，也不使用宽泛的 `collect_all(...)`。GPU BaseEnv 过滤全部附加发行包和 GPU ORT 后，从 `release-cpu` 覆盖同版本 CPU ONNX Runtime；构建 ExtraEnv 时拒绝普通路径重复文件，运行时覆盖层由启动探测单独选择。附加包清单支持 `openvino`、`engine` 和 `ncnn` 三种扩展格式。

打包实现按职责拆分为 `base_runtime_spec.py`、`base_runtime_dependencies.py`、`base_runtime_staging.py`、`model_export_collector.py`、`model_export_staging.py` 和共享 `archive_builder.py`；`base_runtime_builder.py` 与 `model_export_package.py` 继续保留原有 Python/CLI 入口和兼容导出。

`installer/` 中的脚本保持按发布层次拆分：`build_windows.ps1` 负责冻结程序，`build_base_runtime_models.ps1` 负责 GPU 基础包，`build_model_export_runtime.ps1` 负责 GPU 附加包，`package_windows.ps1` 负责编排和生成安装器。完整 GPU 发布使用 `-BuildBaseRuntimeModels -BuildModelExportRuntime`；CPU 正式发布使用 `-Variant CPU -Clean`，完整冻结目录直接由 Inno Setup 内嵌。CPU 传入 `-BuildModelExportRuntime` 仍会失败。

打包窗口会显示中文阶段提示和每个阶段耗时。PyInstaller 阶段显示构建开始、完成和耗时；GPU 基础包和附加包进入原生 7-Zip 压缩后会显示实时压缩百分比和压缩耗时。CPU 阶段只显示完整冻结和 Inno Setup 构建，不执行运行时 staging 或归档压缩。

## 构建命令

Windows 安装器回归测试位于 `src/tests/integration/`，按安装生命周期、运行时层、CPU/GPU 变体和打包脚本接线拆分；可使用 `pixi run test-installer` 单独筛选。

文档中早期版本的 `2.76 MB` program-only 体积仅作历史参考；当前体积会随应用代码和静态导入模块图变化，发布验证以安装器小于 `100 MB` 且最终 Program staging 不含 `_internal/` 为准。

只构建冻结程序和 Program staging：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release -PackageType Program -ProgramOnly -Clean
```

`-ProgramOnly` 使用外置运行时构建路径：不扫描 Torch、Ultralytics、OpenVINO、NCNN、ONNX Runtime 等第三方子模块和动态库，只把应用代码、必要的 PySide6 hook 和外置运行时连接 hook 编译进 `YOLOTool.exe`，运行时复用目标目录已有的 `_internal/`。Program-only 同时排除 NumPy、SciPy、Pandas、TorchVision、SAM2/SAM3、timm 及其纯 Python 依赖，避免 EXE 的 Python 层与旧 v3 基础包中的原生扩展混用；这些模块统一由 BaseEnv 或 ExtraEnv 提供。基础包同时保留 PyInstaller 通常嵌入程序 PYZ 的标准库动态导入模块，避免 `python312.dll` 入口缺失。程序更新包构建不会重复分析约 1.7 GB 的基础环境；完整环境构建仍使用完整 spec，确保基础包拥有全部后端和版本元数据。

开发快包：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

开发快包输出到 `dist/YOLOTool-dev/`，用于本地验证 GUI 和隐藏 CLI，不作为用户安装发布物。完整冻结输出会同时写入根目录 `release-manifest.json` 和 `runtime-manifest.json`，因此可直接启动；运行时清单只用于安装器 `--runtime-probe` 和诊断流程，GUI 启动不再因清单或版本不匹配强制退出。`-ProgramOnly` 输出仍需要已有基础环境才能提供完整功能，但安装器允许在缺少新基础包时保留旧环境完成程序更新。

SAM 智能辅助标注复用基础包 v3 的 SAM 2/2.1 代码、配置、Torch/CUDA、OpenCV、Pillow；GPU 基础包携带 `data/models/sam2.1_hiera_base_plus.pt`，CPU 一体式运行时携带 `data/models/sam2.1_hiera_tiny.pt`。模型目录会识别全部 `sam` 前缀权重，未知自定义名称只显示、不猜测配置。SAM 3 官方代码固定在提交 `6dbb02bd38288df755dfa1378000a861e65b84f6`，以 Windows 推理专用 vendor wheel 和许可证随基础包发布；同一 runtime 同时提供文本预标注和启用实例交互的 CUDA 画布单点预测。wheel 放宽 NumPy 元数据以兼容项目 NumPy 2.x，并使用 OpenCV fallback 替代 Triton，明确不包含 Flash Attention、Triton 或训练依赖。官方 `sam3.pt` checkpoint 不打包、不进 git，由用户自行放入 `data/models/`；它可在 CUDA 下用于画布点提示辅助标注和 AI 文本预标注。GUI 通过 `YOLOTool.exe --sam-assist-runtime` 与 `YOLOTool.exe --yolo-ai-runtime` 启动交互式隐藏子进程；程序层必须包含对应 CLI 分发代码以及由 `src/assets.qrc` 编译进 `assets_rc.py` 的 `sam_assist.svg`。

冻结程序包含系统设置页的 GitHub Release 检查逻辑，不新增运行时依赖；用户需要能访问 `api.github.com` 才能获得版本检查结果。检查失败不会影响程序启动、训练或验证。更新窗口将选中的资源下载到 Windows Shell 解析出的真实 `Downloads` 文件夹；环境包更新通过 Release 文件名版本与本机安装清单或 `package-info.ini` 版本比较，Release 始终携带同版本环境包时不会误报更新。源码开发态使用 `installer/base-runtime-models-version.txt` 和 `installer/model-export-runtime-version.txt` 作为当前环境包版本；基础包缺失按环境缺失处理，附加包缺失只显示可选下载安装提示，不触发“环境包也有更新”；仅当已安装附加包的版本低于 Release 时才触发附加包更新提示。程序与更高版本基础包同时需要更新时默认选择两者，仅程序更新时默认选择程序包，程序-only 场景的同版本提示使用普通文字，手动勾选同版本基础包时显示红色重装提醒，基础包单独留下时在进度条下方显示不可安装的红色提醒。附加环境包在仅勾选附加包、同时勾选程序包或三项全部勾选时，按是否已有附加包显示自动安装、替换或组合状态提示，三项全选时合并确认基础包重装和附加包替换。已有安装但缺少更新基础包时，安装器保留旧环境并警告版本不匹配或环境不完整，继续完成程序更新；首次安装缺少基础包时在组件页直接阻止提交，安装提交阶段不会生成没有运行环境的程序-only 首次安装。附加包可以在程序内热安装或替换。下载按钮右侧提供暂停和停止，下载期间可隐藏窗口且后台任务继续，重新打开时复用原窗口；安装器启动失败会在窗口中显示为可恢复错误。

单独构建 GPU 运行包：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\build_base_runtime_models.ps1 -Clean
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\build_model_export_runtime.ps1 -Clean
```

根目录仅提供 `打包程序.bat` 一个双击入口。它使用 PowerShell 7 打开 1 至 9 的数字菜单，依次提供 GPU+CPU 全量发布、GPU 全量发布、GPU BaseEnv 单卷/分卷、GPU ExtraEnv 单卷/分卷、GPU 程序安装器、CPU 全量发布和本地开发快包。第 7 项复用 `installer/output/` 中已有的 GPU 基础环境包，只重建程序-only 冻结文件、companion catalog 和程序安装器；已有附加包会登记到 catalog，但不会重建环境包。按数字后立即启动流程；全量发布与环境归档使用 `-Clean`，程序安装器和开发快包保持现有默认行为。CPU 不生成 BaseEnv/ExtraEnv 压缩包。

`打包程序.bat` 是纯 ASCII 的 PowerShell 7 启动包装，中文菜单由 `installer/packaging_menu.ps1` 输出并通过按键读取，避免让 `cmd.exe` 直接解析中文和括号；菜单调用子脚本前会将参数数组转换为命名参数，确保开关不会被误绑定为 `Variant` 等位置参数。菜单脚本使用 UTF-8 编码，并通过 PowerShell 7 的 `pwsh.exe` 执行，避免调用 Windows PowerShell 5.1。

完整发布对应的 PowerShell 命令为：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\package_windows.ps1 -BuildBaseRuntimeModels -BuildModelExportRuntime
```

CPU 正式发布命令为：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\package_windows.ps1 -Variant CPU -Clean
```

GPU 程序更新入口要求当前版本基础包已经存在，否则会明确报错并停止；附加包不存在时仍可生成程序安装器。CPU 程序更新可复用已有 CPU 安装目录中的一体式运行时，不下载或生成外部环境包。PowerShell 下也可单独使用 `-SkipBaseRuntimeModels` 或 `-SkipModelExportRuntime`。默认完整命令每次重新复制、生成清单并压缩 GPU 环境包 staging；CPU 只重新生成 staging 并由 Inno Setup 内嵌。`-Clean` 用于强制完整重建，并清理对应的冻结输出、staging 和归档。GPU 压缩参数使用基础包和附加包原生 7-Zip `mx=5`、非固实 LZMA2 与 `-mmt=on`；基础包和附加包分别通过 `-SplitBaseArchive`、`-SplitArchive` 启用分卷，统一使用 `-v1073700000b`，每卷严格小于 `1 GiB`，最多生成 `.001/.002`。旧 `Full`、`AppUpdate`、`RuntimeFull` 参数保留一个过渡周期，输出弃用警告后转发到 `Program`。

完整 GPU 发布在基础归档构建完成后会按本次 `-SplitBaseArchive` 参数重新解析归档路径；即使输出目录残留旧的 `.7z.001` 分卷文件，单卷构建也会继续使用新生成的 `.7z` 基础包。单卷与分卷现在可以同时保留：重建单卷只替换 `.7z`，重建分卷只替换 `.7z.001/.002`，安装器编排按当前命令选择对应格式。

`installer/base-runtime-models-version.txt`、`runtime-version.txt` 和 `model-export-runtime-version.txt` 分别控制基础包、运行时兼容协议和附加包版本。当前基础包为 `v3`、附加包为 `v3`，运行时协议仍为 `runtime-2`；默认两个 GPU 环境包均为单个 `.7z`，分卷模式下要求同一目录、同一版本和连续的 `.001/.002` 后缀，只有对应内容变化时才提升版本。

## 安装流程

安装器始终允许编辑目录，默认使用 `{autopf}\YOLOTool`。仅当 `LastInstallPath` 同时包含 `YOLOTool.exe` 和 `_internal` 时才复用；失效的 smoke 路径会被清除。目录已存在或非空时不弹提示，安装器只替换受管文件。Inno 在目录页显示前就会解析内部 `AppId`，因此安装器关闭默认卸载登记，并在目录确定后根据规范化路径生成稳定实例 ID 与独立卸载项。

自定义组件页包含：

- 程序本体：始终安装，并显示新装、升级、修复或降级状态；降级需要二次确认。
- 本体环境和模型：首次安装、环境缺失或运行时版本不兼容时必须提供并安装；首次安装缺包时阻止提交，已有兼容环境时默认不选，可主动重装或只更新程序。
- 模型转换附加环境：始终可选且默认不选；缺包不阻止主安装。

安装器先按 companion catalog 中的版本化文件名在自身目录查找基础包 `.7z` 或特殊分卷首卷 `.7z.001`，以及附加包 `.7z`，也允许浏览选择其他路径。组件页只比较预期文件名和分卷扩展名，不读取压缩包正文；分卷基础包最多接受 `.001/.002`，运行时协议版本仍由包内 manifest 和安装后的运行时清单约束。首次安装基础包缺失或损坏时显示红色风险提示并阻止继续，组件页同时显示“进入 GitHub 下载”按钮，点击后打开 YOLOTool Release 页面；已有安装缺少更新基础包时可保留旧环境进行程序更新，并警告版本不匹配或环境不完整；附加包缺失只显示提示。归档损坏或无法解压时由安装事务失败并回滚。

安装成功页使用 Inno 原生 `[Run]` 条目提供“安装完成后删除本次使用的安装包和环境包”选项，复选框与“启动 YOLOTool”自动对齐；勾选后由隐藏命令延迟删除当前安装器、基础环境包和已选附加环境包，安装器本体因正在运行会在退出后自动删除。安装成功后，卸载文件统一命名为 `uninstall.exe` 和 `uninstall.dat`，并兼容清理旧版 `unins000.exe/.dat`。

安装进入文件替换前会通过 Inno Setup 的 Windows Restart Manager 注册当前安装目录中的 `YOLOTool.exe`；没有目标进程时直接继续，发现目标实例时由安装器自动关闭，不弹出是否停止应用的询问页，也不使用 PowerShell 或 WMI。其他安装目录的并行实例不会被停止。自动关闭前应由程序自身保存完必要状态，安装器不负责恢复未保存的数据。

Program 与基础环境先进入 `{app}\.install-staging/`。开始解压基础环境时安装器显示“正在解压本体环境和模型”的平滑进度提示；由于 Inno 的外部归档进度按大文件完成边界更新，百分比不再作为逐字节速度指示。旧程序和环境以同卷原子重命名进入 `.install-backup/`，新文件切换后执行 `YOLOTool.exe --runtime-probe`；文件切换、卸载登记等必选安装步骤失败时恢复旧程序、旧环境和被覆盖的官方模型，运行环境版本不一致或自检未通过时只显示警告并继续安装，提示部分功能可能无法使用。安装清单统一存放在 `{app}\_internal\yolotool_metadata\`，读取时兼容旧根目录并在升级成功后移除旧副本。官方模型按清单合并更新，`yolo26n.pt` 还会复制一份到应用根目录作为受管兼容副本，用户自行加入 `data/models/` 的其他文件不参与替换。

每个实例的 `install-instance.ini` 写入 `_internal\yolotool_metadata\`。附加环境在主事务成功后通过隐藏 CLI 安装到当前程序目录；旧版 `%LOCALAPPDATA%` 附加环境同盘时原子迁移，跨盘时复制完成后删除旧目录：

```text
{app}\_internal\extensions\model-export-runtime\
```

升级旧实例时可把 `%LOCALAPPDATA%\YOLOTool\instances\<实例ID>\extensions\` 或旧全局扩展目录原子迁入当前程序目录；基础环境替换 `_internal` 时会临时保留扩展目录。附加包失败不撤销已经成功的程序和基础环境更新。

## 卸载与数据

隐藏 CLI 由 `src/bootstrap/cli_dispatch.py` 的唯一 flag 映射分发到按训练、验证/预测、模型导出、AI 标注、SAM 辅助标注和运行时维护划分的 handler；`cli_validation.py` 与 `cli_annotation.py` 保留兼容转发，具体实现分别拆入 `cli_val.py`/`cli_predict.py` 和 `cli_annotation_labels.py`/`cli_annotation_batch.py`/`cli_annotation_runtime.py`/`cli_sam_runtime.py`，`src/train_cli.py` 只保留 `run_*_cli` 兼容转发。冻结态与开发态继续使用同一命令协议。`--sam-assist-runtime` 从标准输入逐行接收 `load_model`、`set_image`、`predict_point`、`shutdown` JSON 命令，并以结构化行返回请求 ID、状态、错误或几何，不输出完整 mask。

安装提交前的 `YOLOTool.exe --runtime-probe` 只读取程序清单和 `_internal` 基础环境清单，比较 `required_runtime_version` 与 `runtime_version`；不导入 Torch、PySide6、ONNX、ONNX Runtime、Ultralytics 或 OpenCV。比较不一致或自检无法完成时只显示“部分功能可能无法使用”的警告，不撤销已经完成的文件切换。附加包后台安装不显示解压百分比进度条。

GPU 安装器在压缩包校验页结束后使用普通百分比进度条显示程序和基础环境的实际安装进度，不使用忙碌进度条掩盖解压阶段；CPU 安装器直接显示一体式文件安装进度。附加环境仍使用原生 7-Zip 校验归档，但界面不显示解压百分比进度条。

卸载单个实例会删除程序、`_internal/`、该实例附加环境，以及 `managed-models.json` 登记的官方模型。以下内容保留：

- `data/runtime/settings.json` 项目设置及同目录的最近项目状态
- 用户自行加入的模型
- `images/`、`labels/`、`result/`

若安装根目录仍含用户数据，卸载器不会删除该根目录，也不会影响其他并行实例。

## 发布验证

- 应验证首次进入系统设置页时在 Release 检查完成前打开更新窗口，结果返回后窗口会原地刷新；“检测更新”按钮可再次发起检查，并在后台任务完成后恢复可用。
- 系统设置更新窗口的汇总下载进度从 `0%` 开始；程序与一个环境包按 `20%/80%` 分配，程序、基础环境和附加环境三项同时下载时按 `10%/45%/45%` 分配。
- 应验证更新窗口进度条上方右侧显示下载速度和已下载/总大小；无 `Content-Length` 时总大小显示为 `--`。
- 应验证下载期间关闭更新窗口后任务仍继续，重新打开时复用原进度；点击暂停后的“停止”按钮应取消下载并允许重新开始。
- 应验证从系统设置打开更新窗口时由主工作台窗口拥有对话框，首次显示前已完成样式初始化，不出现瞬态白色小窗口。

- GPU 完整发布完成后必须检查 `dist/packages/Program/YOLOTool.exe` 来自最后一次 `-ProgramOnly` 构建，且 `dist/packages/Program/` 不含 `_internal/`；CPU 直嵌模式还必须确认 Inno Setup 的完整目录输入排除了根目录 `YOLOTool.exe`，避免程序本体被携带两份。

- 程序安装器小于 `100 MB`，且不包含 `_internal/`、运行时清单和模型；程序-only EXE 启动时必须能在目标目录找到基础包 `_internal/python312.dll`。
- 两个约 2 GB 伴随包存在时，组件页不读取压缩包正文，必须在 3 秒内完成刷新并保持控件可交互。
- GPU 基础包不包含 `YOLOTool.exe`、OpenVINO、NCNN、PNNX、TensorRT 或 GPU ONNX Runtime，只包含 CPU ONNX Runtime；GPU 附加包 v3 额外携带隔离的 GPU ONNX Runtime，启动前验证 `CUDAExecutionProvider` 后才优先加载，否则继续使用基础包 CPU Runtime。CPU 一体式安装器同时安装 `YOLOTool.exe`、CPU Torch、CPU ONNX Runtime、CPU-only OpenVINO、NCNN、PNNX 和模型，不包含 TensorRT、GPU ONNX Runtime、CUDA 或 OpenVINO GPU/NPU/自动设备插件。两种运行时内容都包含 SAM 2/2.1 Base+ 代码、配置和 checkpoint，以及 SAM 3 交互代码和依赖。
- 开发快包或 Program-only 产物应能显示内嵌 SAM 图标，并可启动 `YOLOTool.exe --sam-assist-runtime`；在具备 CUDA 的发布机分别使用 Base+ 与用户提供的官方 `sam3.pt` 完成加载、图片编码、单点几何推理和 `shutdown` 冒烟，验证高级参数协议及退出后不残留子进程。
- 附加包包含 OpenVINO、NCNN/PNNX、TensorRT 发行包和 `_onnxruntime_gpu` 隔离覆盖层，清单中的文件和 DLL 目录完整；原生 7-Zip 安装路径使用归档 CRC，兼容回退路径检查文件集合，界面仅保留安装状态日志。
- 覆盖首次安装、仅程序升级、强制基础包升级、主动重装、确认降级、并行实例与卸载保留数据。
- 使用 detect 与 OBB 模型完成五格式烟雾导出，并使用 SAM2.1 Base+ 完成双文件 ONNX 烟雾导出；GPU 版 TensorRT 仅在兼容 NVIDIA CUDA 13 发布机验证，CPU 版验证 ONNX、TorchScript、OpenVINO 和 NCNN，并确认 TensorRT 不可用。

Inno Setup 要求 7.0.2 或更高版本。`installer/package_windows.ps1` 会搜索 Inno Setup 7 的标准/自定义安装目录和注册表路径；不再使用 Inno Setup 6 编译器。简体中文语言资源固定在 `installer/languages/ChineseSimplified.isl`，构建机无需额外安装语言包。

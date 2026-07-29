# 架构与维护说明

## 项目概述

本项目是一个独立于 `yolo-weld` 的 Windows 本地可视化 YOLO 训练工作台，使用 **Python + PySide6 / Qt** 开发桌面 GUI。

定位是“通用 YOLO 优先，同时兼容焊缝 OBB 项目”：

- 支持 YOLO `detect`、`obb` 与 `seg` 三类任务。
- 兼容焊缝识别习惯配置，例如类别 `weld`、Labelme 转 YOLO-OBB、直线标注扩展为旋转矩形；新项目不预置具体类别名称。
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
    │   └── handlers.py
    ├── shared/
    │   ├── paths.py
    │   ├── qt.py
    │   └── theme.py
    ├── services/
    │   ├── annotation/
    │   ├── conversion/
    │   ├── data_ops/
    │   ├── model_export/
    │   ├── models/
    │   ├── runtime/
    │   ├── settings/
    │   ├── training/
    │   └── validation/
    ├── ui/
    │   ├── shell/
    │   ├── shared/
    │   └── features/
    ├── runtime/
    ├── assets/
    └── tests/
```

## 分层边界

- `src/main.py` 是唯一桌面可执行入口，同时负责分流 `--yolo-train`、`--yolo-export`、`--yolo-export-probe`、`--yolo-val`、`--yolo-predict`、`--yolo-ai-label`、`--sam-assist-runtime` 等隐藏 CLI。
- `src/app.py` 与 `src/bootstrap/app_factory.py` 负责 GUI 应用创建，不承载业务规则。
- `src/bootstrap/cli_dispatch.py` 是唯一 CLI 分发入口；打包后 `YOLOTool.exe --yolo-*` 最终也进入这里。
- `src/shared/` 只放跨层共享基础能力，例如路径、Qt 导出和主题；设置模型与任务模型分别归属设置服务和 UI 上下文，不再放入通用类型文件。
- `src/shared/paths.py` 在开发态必须把 `ROOT` 解析到仓库根目录，而不是 `src/` 子目录；隐藏 CLI 与后台 worker 依赖这个根目录作为 `python -m src.main` 的工作目录。
- `src/shared/paths.py` 同时维护应用数据根目录和资源路径常量；`src/assets.qrc` 与生成的 `src/assets_rc.py` 将 PNG/ICO 编译为 Qt 内嵌资源，冻结态不再依赖 EXE 同级的 `app_assets/`，而 `data/` 仍从 EXE 所在目录读取。GUI 启动时通过 `src/ui/shared/assets.py` 读取内嵌图标；安装器只在升级旧版本时清理历史 `app_assets` 目录。顶部导航图标由 `src/ui/shared/widgets/base.py` 按当前屏幕设备像素比生成物理 pixmap 并设置对应 DPR；主窗口屏幕变化时重新取样，保持 `28 x 28` 逻辑尺寸下的清晰度。
- `src/services/<domain>/` 是唯一业务实现层。这里允许依赖标准库、第三方库、其他服务包和 `src/shared/`，不得依赖 `src/ui/`。
- `src/services/home/` 负责主页的大目录扫描、统计汇总与训练历史整理；这些逻辑必须通过后台 worker 调用，避免主线程同步 I/O 卡住首页。主页切回时若界面上已有上一轮统计值，应优先保留旧值，待新汇总返回后再替换，避免反复闪出“加载中”。
- 主页类别分布优先读取数据集 `data.yaml` 的 `names`，关闭多类别模式时使用普通图片分布，开启多类别模式时按总标注和各类别标注对象数量展示；数据集与设置均无类别名称时使用“目标名称”作为兜底。
- 主页标注数量按 Labelme `shapes` 数量或 YOLO 非空标签行数统计，不按标注文件数统计；普通分布图固定显示总图片、训练、验证、测试、未标注五项，总图片固定在最左侧，其余项目按数量降序排列，未标注为 0 时隐藏。普通模式仅在只有一个标注类型时显示上方类型名称，多类别时隐藏名称并扩展绘图区；无标题模式下 Y 轴顶部间距为 15px，柱顶数值标签和柱状图位置保持独立。
- 主页没有有效的 `data/train|val|test/labels` 标签时，分布统计回退到当前图片目录及同名 Labelme/YOLO 标签；多类别模式下按每个类别的标注对象数量统计，第一项为总标注数并按类别数量降序排列。
- `src/ui/shell/` 负责主窗口、导航、页面注册、关闭保护、程序日志和整体样式。
- `src/ui/shared/` 负责跨页面 UI 复用能力，例如页面基类、共享表单、共享对话框、后台 worker、`WorkbenchContext` 和 `TaskCoordinator`。
- `src/ui/features/<feature>/` 负责各页面真实实现；`page.py` 只做页面装配，复杂逻辑继续拆到该功能包子模块。
- 数据标注页的目标类型联动由 `src/ui/features/annotation/selection.py` 统一维护：选中画布或列表标注时同步右侧下拉框，选中标注时修改下拉框会回写该标注类别；未选中标注时下拉框仍只控制新建标注的默认类别。
- `src/services/annotation/class_names.py` 扫描当前项目 Labelme 标注目录中的非空类别名并追加到项目设置；`ClassManagerDialog` 负责类别编辑、删除依赖保护和转换按钮，`ClassConversionDialog` 作为独立窗口选择源/目标类别；确认后由标注页统一保存设置和标注，取消不产生转换。
- `src/ui/shared/widgets/` 放基础控件与图表组件，旧的 `src/ui/widgets/` 已删除。主页 `DatasetDistributionWidget` 和 `TrainingCurveWidget` 使用当前控件 DPR 创建物理 pixmap、以逻辑坐标绘制，并通过 `refresh_for_device_pixel_ratio()` 响应主窗口跨屏切换，避免高 DPI 下图表文字、坐标轴和曲线被放大模糊；图表内框在 pixmap 内部绘制，与训练历史表格统一使用 `1 px #CFD9E3` 边框和 `5 px` 圆角，避免 QLabel 内容覆盖圆角造成断开空隙；各类别图片分布坐标轴保持 `20 px` 左边距、`38 px` 顶部位置和 `33 px` 底部留白；训练曲线横轴使用 `results.csv` 的 `epoch` 列。
- `src/tests/architecture/` 只保留依赖方向、旧入口、模块体量和 Qt 生命周期四类结构围栏，不扫描文档措辞或代码清单内容。
- `src/tests/services/` 按领域保护文件读写、转换、设置、命令构造和运行时安全等业务规则。
- `src/tests/ui/` 按业务域和 shell 分目录保留关键页面工作流与服务接线；数据处理 UI 测试使用 `data_processing/`，避免与项目级 `data/` 忽略规则冲突；精确布局、颜色、尺寸与提示文本改由发布前人工检查。
- `src/tests/integration/` 放开发/冻结入口、隐藏 CLI 和 Windows 打包契约回归。
- `pixi run test` 是完整测试入口，当前通过 162 项测试；`pixi run test-fast` 提供服务层、架构围栏和入口的快速回归，`pixi run test-ui`、`pixi run test-integration` 和 `pixi run test-full` 保留分层/兼容入口。
- pytest 缓存由 Pixi 测试任务写入 `.pixi/pytest-cache`，避免在项目根目录生成 `.pytest_cache`；该目录随本地 Pixi 环境一起被忽略。

## 服务层说明

### `src/services/settings/`

- `model.py` 使用嵌套 `slots=True` dataclass 定义 `AppSettings` 及各设置分区，并提供字典编解码和字段级类型回退。
- `defaults.py` 提供默认设置构造；`project_settings.py` 负责 schema v0 迁移、字段级校验、损坏配置备份、项目路径序列化/反序列化与最近项目状态读写。
- `SettingsService.load()` 返回 `SettingsLoadResult`，携带设置、迁移状态和问题列表；`save()` 只接受类型化 `AppSettings`，未知字段忽略并报告，保存前再次校验。
- 当前项目配置保存到当前项目目录 `data/runtime/settings.json`。
- 应用级最近项目状态保存到应用根目录 `data/runtime/app_state.json`。
- `src/runtime/settings.json` 仅作为源码内默认配置参考。
- 设置文件写入 `schema_version: 1`；旧版本或无版本文件按 v0 迁移，保持原有字段含义、相对路径存储、外部绝对路径和裸模型名规则。
- `model_export` 节点保存 `model_path`、`output_dir`、`format`、`imgsz` 和 `simplify`；扩展安装状态从当前安装目录 `_internal/extensions/` 下的活动清单读取，不写入项目设置。旧版本位于 `%LOCALAPPDATA%/YOLOTool/instances/<实例ID>/extensions/` 或 `%LOCALAPPDATA%/YOLOTool/extensions/` 的扩展会在升级时迁移，同盘使用原子移动，跨盘复制完成后删除旧目录。
- 标注页名称显示由项目设置 `annotation.show_annotation_names` 控制，默认值为 `false`。
- 标注页未配置 `dataset.class_names` 时类别下拉框保持为空，不再自动添加 `weld`；进入项目标注目录时会按文件顺序读取所有 Labelme JSON 的非空 `label`，将缺少的类别追加到当前项目 `data/runtime/settings.json`。

### `src/services/runtime/`

- `process_runner.py` 统一后台子进程启动、日志转发、结构化输出和停止流程。
- `windows_spawn.py` 提供 Windows 隐藏窗口参数，确保打包后的后台任务不弹终端。
- `environment_probe.py` 提供 Python、依赖版本、Torch/CUDA 和系统状态检测；依赖版本优先读取 `importlib.metadata`，冻结态缺少发行版元数据时回退读取模块的 `__version__`。GUI 启动不强制比较运行环境版本；安装器调用的 `--runtime-probe` 仍不加载这些模块，只比较程序清单要求的运行时版本与 `_internal` 基础环境清单中的版本。
- `release_updates.py` 通过标准库 HTTPS 请求读取 `Takobox710/yolo-tool` 的最新稳定 GitHub Release，负责程序与环境包版本号规范化、比较、发布说明和安装器/环境包资源解析、Release 资源顺序下载、Windows Shell 已知 Downloads 路径解析、安装包启动及失败结果封装；环境包版本来自 `YOLOTool_BaseEnv_<版本>.7z` / `YOLOTool_ExtraEnv_<版本>.7z` 文件名，并与 `install-instance.ini` / `package-info.ini` 的包版本比较；基础包缺失按环境缺失处理，附加包缺失只作为可选资源，不触发更新判定；源码开发态缺少安装清单时回退读取 `installer/*-version.txt`，网络请求和文件下载必须放入后台 worker，不能在 Qt 主线程直接执行。
- `installer/YOLOTool.spec` 在 `YOLO_TOOL_PROGRAM_ONLY=1` 时只分析应用代码，第三方运行时模块由基础包 `_internal/` 提供；程序本体明确收集 `ctypes.util` 和 `ctypes.wintypes`，兼容 Cryptodome 在 Python 3.12 Windows 下从 CFFI 回退到 ctypes 的导入链。打包链路只保留实际需要的 `installer/hooks/hook-torch.py` 与 `installer/hooks/program_external_runtime.py`：前者收集完整环境所需的 Torch 源码、动态库和隐藏导入，后者只在程序-only 模式注册固定的后端 DLL 目录和基础包路径，不递归扫描运行时目录；已排除的 PySide6 deploy_lib 和 tensorboard 模块不再配置空 hook。基础环境构建时，`src/devtools/release_package.py` 将 PyInstaller 通常嵌入 PYZ 的动态导入标准库打入 `python_stdlib.zip`，并只补齐运行所需的第三方纯 Python 源码，过滤测试、示例、打包工具、测试框架和未使用的 Windows COM/数据库源码，避免程序-only 启动时出现 Python DLL 或动态导入模块缺失。
- GUI 日志写入前必须通过这里的终端输出清洗逻辑去掉 ANSI/控制字符。

### `src/services/training/`

- `model_catalog.py` 负责训练模型目录、模型 YAML 与模型路径解析。
- `commands.py` 负责训练 / 导出 / 验证命令构造与 `data.yaml` 的验证路径修复。
- `results_reader.py` 负责 `results.csv` 曲线与指标摘要读取。
- 基础模型目录统一是 `data/models/`。

### `src/services/model_export/`

- `formats.py` 定义五种显示名称到 Ultralytics 参数 `onnx`、`torchscript`、`openvino`、`engine`、`ncnn` 的固定映射、产物路径和模型扫描规则。
- `commands.py` 构建统一的 `YOLOTool.exe --yolo-export` 命令；训练服务保留 `build_export_command` 转发以兼容旧导入。
- `execute.py` 在输出目录的临时工作区导出，成功后替换最终产物；失败或停止时清理临时文件并保留旧结果。
- `runtime.py` 区分内置 ONNX/TorchScript、开发态 Pixi 后端和冻结态增量扩展；冻结态 OpenVINO、TensorRT、NCNN 都通过增量扩展提供，并单独判断 TensorRT 的 NVIDIA GPU 能力。
- `package.py` 导入纯 `.7z` 或兼容 `.zip` 附加包，校验扩展 schema、协议、平台、安全相对路径、符号链接、文件清单和解压结果，管理候选安装、原子活动指针、失败回滚和“当前 + 上一版本”保留策略；`manifest.py` 集中维护清单协议、路径校验、指纹和 7z 清单读取，避免 `package.py` 与 `inspection.py` 循环依赖。`.7z` 优先调用基础环境随附的原生 `7z.exe`，利用解压过程的 CRC 校验发现归档损坏，没有原生工具时回退到 `py7zr` 解压并检查文件集合。原生 7-Zip 的百分比输出会通过进度回调映射到附加包安装的解压区间，`inspection.py` 的快速入口只读取清单并按压缩包指纹缓存，安装阶段再报告检查、解压、探测和切换。
- `activation.py` 在隐藏导出子进程启动早期追加活动扩展的 `packages/` 到 `sys.path`，并通过清单注册 DLL 目录；主程序本体与扩展共用同一个 Python、Torch、CUDA、Ultralytics、ONNX 和 ONNX Runtime，不复制这些基础库。
- `src/devtools/model_export_package.py` 依据 `importlib.metadata` 的 distribution 文件清单收集 OpenVINO、NCNN、PNNX 和 TensorRT 发行包，不使用 PyInstaller `collect_all(...)` 或复制完整运行环境；tqdm 和 portalocker 随基础环境发布。基础环境同时携带 SAM 2.1 Base+ 代码、配置、checkpoint 和针对 Python 3.12/PyTorch 2.13/CUDA 13.0 构建的多架构 CUDA 后处理扩展，用户安装时不编译。附加产物使用原生 7-Zip 的多线程非固实 LZMA2 极限压缩生成纯 `.7z`，不包含安装程序。基础包构建复制第三方纯 Python 源码时，Windows 优先使用 `robocopy /S /MT:16`，并排除测试、示例和开发工具；其他平台或缺少命令时保留逐文件回退。

### `src/services/validation/`

- `model_catalog.py` 负责训练产物模型扫描、输入模式状态和结果计数 / 日志文案。
- `source_collectors.py` 负责图片、视频与数据集来源收集。
- `rendering.py` 负责推理结果对象标准化、结果图渲染与标签输出。
- `runtime_cleanup.py` 负责短生命周期推理运行时释放。
- `prediction_runner.py` 保留为推理总流程装配入口。
- 图片检测/视频检测/摄像头检测推理通过隐藏子进程执行，完成后释放主要推理运行时。
- 摄像头检测或视频流结果图必须显式以当前帧为底图，避免无目标时黑屏。
- 摄像头检测模式由 `state.py` 隐藏批量结果工具栏，避免无效工具栏占用右侧实时预览区顶部间距。
- 摄像头检测模式仍由 `state.py` 保留左侧启动/停止按钮，按钮可见性与右侧批量导航工具栏独立控制。
- 视频文件检测按输入后缀自动进入视频进度模式，后台每秒发送一次进度事件并写出 MP4 结果；视频检测不生成帧级 YOLO TXT 标注。
- 验证页视频模式由 `src/ui/features/validation/video_player.py` 管理源视频与结果视频的 Qt 播放器，页面加载时暂停在当前视频第一帧；源视频作为播放时钟，顶部滑块同步拖动两侧视频，播放按钮与检测按钮状态分离，两个视频面板使用等权横向伸缩，后续批量视频事件不得替换当前预览。
- 验证页在图片检测与视频检测间切换时，由 `src/ui/features/validation/state.py` 暂停页面绘制，完成所有模式控件和播放器状态更新后再统一刷新，避免视频切换为图片时出现中间画面闪动。
- 验证页源视频播放器监听 `playbackStateChanged` 和 `mediaStatusChanged`；视频自然结束时由页面统一恢复播放按钮状态并暂停结果视频。
- 验证页拖放由 `ValidationPageActionsMixin` 识别本地图片/视频文件并更新模式与输入源；输入源选项通过 `source_selection` 区分批量目录和单文件选择，`collect_prediction_sources()` 对图片检测/视频检测模式同时支持目录和单文件路径，复用同一检测 worker。
- 验证页检测前预览由 `results.show_source_preview()` 负责加载图片源或暂停视频首帧；检测会话开始后由 `detection_started_for_source` 切回原有结果缓存与列表逻辑。
- 验证页源图和检测结果图使用无视觉容器承载图片/视频切换，容器零内边距；`ImageView` 自身边框直接占据原图片区外框位置，避免出现大框套小框。

验证页左侧布局将普通检测日志控件设为纵向伸缩项，使日志区域填满左侧面板的剩余高度；数据集验证模式则切换为顶部对齐和固定表单高度，避免右侧验证日志面板把左侧控件均匀拉开，并通过 `source_scope` 支持按钮选择自定义验证目录后临时覆盖 `data.yaml` 的 `val:`。验证页外层保持标准页面内边距，右侧内部装配布局清除默认 margin，避免右侧模块边缘间距被重复计算。页面专属布局代码位于 `src/ui/features/validation/layout.py`。

### `src/services/annotation/`

- 负责 Labelme/YOLO 标注读写、可编辑标注模型、预览渲染和 AI 预标注业务逻辑。
- `editable_document.py` 将镜像有向矩形和直线扩展统一保存为内部 `obb_mirror`；Labelme 仍写标准 `oriented_rectangle`，通过 shape 级 `flags.yolo_tool_shape` 恢复内部形状，旧的无 flags 文件继续按普通 `obb` 兼容读取。Seg 标签显式按任务类型读取为 polygon，矩形、OBB、圆形和 line 在导出时转换为多边形。
- `sam3_text.py` 提供官方 `sam3.pt` 识别、项目优先模型发现、文本提示词规范化、mask IoU 去重和三种 mask 几何转换；SAM3 运行时不依赖 Qt，仅在 CUDA 上加载官方图片模型。`ai_labeling.py` 复用一次图片编码、多提示词推理、面积过滤、稳定去重和 Labelme/YOLO 写入。
- 标注页图片列表的大目录扫描、标注存在性判断与首屏批量渲染应尽量拆成“首批同步 + 后台分批补齐”，避免首次进入标注页时阻塞主线程；对大量不可见行不要同步创建整套行内 `QCheckBox`/`QWidget`。
- 标注页首次进入时，应避免在 `AnnotationPage` 构造阶段直接触发整套图片扫描；首轮图片扫描应延后到页面首次显示后启动，先让导航切页完成，再逐步进入标注工作状态。
- 若主窗口已在空闲阶段预热标注页，可提前准备首张图片与首批列表项，减少真正切入标注页时先见空画布的闪动；但后续批量渲染与后台标注状态扫描仍要继续补齐完整列表。
- 标注页图片列表若改用 `setItemWidget(...)` 装配只读勾选框与文件名，底层 `QListWidgetItem` 本身应只保留数据角色，不再重复绘制同名文本，避免出现叠字；只读勾选框保持正常启用样式，不应做成禁用发灰控件。
- AI 预标注结果优先写回页面内部标注对象并保存 Labelme；按设置决定是否同步导出 YOLO。
- `AiPrelabelDialog` 顶部“范围与模式”卡片使用底部伸缩空间承接额外高度，标题、范围选择和处理模式保持紧凑排列，避免窗口变高时控件行间出现过大空隙。
- SAM 3 类别映射表的文本提示词表格行高为 `38 px`，单元格上下左右均保留 `5 px` 内边距，编辑框使用 `0` 内边距并保持至少 `28 px` 高，避免全局输入框内边距导致文字被裁切。
- `AiPrelabelDialog` 根据模型后端切换参数布局：YOLO 显示置信度与 NMS IoU，SAM 3 隐藏这组普通模型控件，并将高级参数开关放在标注形状选择右侧；SAM 3 的模型文件与标注形状下拉框文本左边缘对齐，轮廓简化比例数值框隐藏上下箭头；SAM 3 的内部置信度与 mask 去重 IoU 仍由已保存值承接推理协议。
- AI 预标注模型选择使用显示名到绝对路径的映射；SAM 3 的显示名固定为 checkpoint 文件名，避免将项目目录结构暴露在下拉框中。
- `sam_assist.py` 是不依赖 Qt 的 SAM 模型目录与几何服务：按项目优先级扫描所有 `sam` 前缀 checkpoint，识别 SAM 1 ViT、SAM 2/2.1 各架构和官方 SAM 3，生成简化显示名称及运行后端标识；未知自定义名称保留原文件名并不猜测配置，将最大外轮廓转换为简化多边形、轴对齐矩形及角点顺序稳定的普通 OBB。
- `sam_runtime.py` 延迟导入 Torch、SAM2、SAM3、OpenCV 与 Pillow，长期保留当前模型及图片 embedding；SAM 2/2.1 使用点提示 predictor，SAM 3 使用启用实例交互的 `predict_inst`，CUDA 使用 `torch.inference_mode()` 与 bfloat16 autocast，SAM 2/2.1 可回退 CPU。点预测统一按项目参数决定单结果/三候选，选择最高质量候选后执行最低质量、最小面积和轮廓简化过滤。模型切换和页面生命周期结束时清理 predictor/model、执行垃圾回收并释放 CUDA cache；关闭 SAM 开关只停止预览和推理，不终止页面运行时。

### `src/services/conversion/`

- `types.py` 定义转换配置与结果模型。
- `class_mapping.py` 负责类别识别、类别映射和映射表解析。
- `labelme_parser.py` 负责 Labelme 形状解析与 Labelme -> YOLO detect/OBB/Seg 行转换。
- `dataset_split.py` 负责输入收集、数据集划分和统计汇总。
- `dataset_yaml.py` 负责 `data.yaml` 输出，并只写入本次实际产出的 split 条目。
- 数据处理页的数据集划分配置直接读取当前项目 `dataset.class_names`；该字段由数据标注页“管理类别”维护，自定义类别映射窗口也使用这组类别作为来源。
- 数据集划分页的“模式选择”用 `conversion.use_labelme` 兼容保存 Labelme 转换模式或 YOLO 原生划分模式；模式选择独占转换参数区首行，线标注转换宽度继续读取 `dataset.line_to_obb.half_width`。
- `backup.py` 负责旧产物清理与备份；未启用备份时不主动创建 `old/` 目录。
- `formatting.py` 负责转换结果说明文本。
- `execute.py` 保留为转换总流程装配入口。

### `src/services/data_ops/`

- 负责批量重命名、图片压缩和项目内路径显示转换。
- `relative_path_from_project()` 用于验证页自定义输入源的相对路径显示；路径解析仍由 `resolve_project_path()` 统一处理，项目外路径使用 `..` 表示。
- 图片压缩页的“打开结果文件夹”属于页面层轻交互，直接基于当前“输出目录”字段解析后的路径打开目录，不额外下沉到服务层。

## UI 约定

- `src/ui/shell/window.py` 中的 `WorkbenchWindow` 是唯一主窗口实现。
- 页面统一接收 `src/ui/shared/context.py` 的 `WorkbenchContext`，页面不再持有窗口对象、访问 `page.app` 或探测宿主任意属性。上下文集中提供当前 `AppSettings`、设置服务、日志、后台调用、项目切换和页面刷新回调。
- 设置修改先更新类型化模型，再由 `WorkbenchContext.save_settings()` 比较快照、持久化并广播实际变化字段；项目切换和恢复默认设置通过上下文替换设置并递增 generation。
- `src/ui/shared/tasks.py` 的 `TaskCoordinator` 为训练、验证、模型转换、AI 预标注和普通后台任务提供唯一任务租约；重复启动被拒绝，停止/完成按 token 校验，页面销毁或项目 generation 变化后的回调不得污染新页面。
- UI 中使用 `QTimer.singleShot` 延迟调用页面或窗口方法时，必须传入所属 `QObject` 作为上下文；对象销毁后 Qt 会自动取消未执行回调，避免跨页面或退出阶段访问已删除控件。
- 页面创建与导航注册统一在 `src/ui/shell/page_registry.py` 与 `src/ui/shell/navigation.py`。
- 主窗口页面采用“首屏懒加载 + 空闲分批预热”：启动时先创建当前页，窗口显示后再按空闲节奏补建其余页面，避免首页打开时连带触发重页面初始化，同时减少用户第一次切到任意页面时再同步吃到建页卡顿。
- 程序级日志缓冲与设置页日志展示统一走 `src/ui/shell/program_log.py`。
- 关闭确认统一由 `src/ui/shell/close_guard.py` 处理，包括未保存标注与训练运行中确认；环境状态、主页摘要、训练状态和 GitHub Release 检查等短生命周期后台任务不阻止关闭，也不触发确认弹窗。
- `WorkbenchWindow` 默认尺寸为 `1100 x 740`，最小尺寸为 `800 x 600`；项目内路径在 UI 中优先显示为相对路径，写入文件时由设置存储层解析/序列化。
- 页面通过上下文提交设置变更并接收字段路径通知；控件刷新期间阻断信号，避免通知回写造成重复保存。
- 项目路径字段分为三组共享路径：`paths.images_dir`（数据集划分、标注预览、批量重命名、数据标注）、`paths.annotations_dir`（数据标注、数据集划分、批量重命名）和 `paths.labels_dir`（标注预览、数据集划分）；图片压缩源目录单独使用 `image_resize.source_dir`。
- 数据处理页的 `ModelExportTab` 只负责控件状态、预览、确认和结构化日志；格式、路径、依赖、进程命令和扩展安装规则均由 `src/services/model_export/` 提供。模型转换页与系统设置页共用附加包拖放处理，识别 `.7z/.zip` 清单并确认后再在后台安装。
- 标注页“更多设置”使用等权垂直伸缩项承接窗口额外高度，保证各设置行之间的间隔一致；复合设置内部（如直线扩展像素标题与数值框）不参与外层间隔分配。
- 共享页面基础能力只能放在 `src/ui/shared/page_base.py`，不要回流到页面专属实现。
- 通用短任务 worker 实现放在 `src/ui/shared/workers/`；需要维护交互式子进程协议的功能专属 worker 可留在对应 feature 包，例如 `annotation/sam/runtime.py`。页面持有 QThread 时必须在原生 `finished` 信号后再清理对象。
- `src/ui/features/annotation/page.py` 与 `src/ui/features/annotation/canvas/widget.py` 都只保留页面 / 画布装配；交互、保存、菜单、快捷键、AI 与编辑细节继续拆在 feature 子模块。
- `src/ui/features/annotation/sam/controller.py` 负责模型发现、项目级模型与高级参数保存、首帧立即提交与 `50~120 ms` 自适应移动调度（同一形状下小于 `2 px` 的微小移动过滤）、模型/图片编码状态及页面生命周期；参数保存只使旧悬停请求失效，不重载模型或图片 embedding。移动期间保留最近完成的预览帧，并使用失效代次隔离离开、命中标注、确认、切图和切模式前的结果。`sam/runtime.py` 通过隐藏子进程维持一个在途预测，只保留一个最新待发送坐标。
- 标注画布只持有 SAM 启用状态、预览几何和输入回调，不导入 Torch、SAM2、OpenCV 或子进程实现。SAM 预览为独立绿色图层，复刻 LabelPaw 的纯绿色不透明边缘与低透明度填充，边框使用较粗、较长且 `cosmetic` 的固定像素虚线，确认时创建正式 `EditableAnnotation` 并复用 `_finish_annotation()`；命中已有标注的悬停不发起请求。
- `DrawShapeDialog` 与画布右键菜单共用 `AnimatedToggleSwitch`；`240 px` 宽的窗口在模型框右侧提供 `50 x 36 px` 的紧凑`高级`按钮，SAM 标题行距窗口顶部 `12 px`，模型下拉框允许横向压缩并省略过长名称，由 `sam/settings_dialog.py` 承载独立参数窗口。高级窗口顶部通过模型下拉框切换候选 checkpoint，并可直接打开当前模型目录；取消不提交模型切换，保存后由标注窗口同步选择。最小掩码面积与轮廓简化比例共用对齐滑块/数值列，前者使用对数刻度覆盖 `1~100000000 px²`；最低预测质量、最小掩码面积和轮廓简化比例的数值框均关闭上下调按钮，保留直接输入和滑块联动。SAM 图标只保留在“画标注框”窗口，右键菜单的 SAM 行置于菜单底部、与标注形状之间使用分隔线并使用普通自定义菜单行间距，后者只负责同步开关；SAM 开启时只允许矩形、普通有向矩形、镜像有向矩形、多边形和编辑模式。
- 标注页快捷键由 `src/ui/features/annotation/shortcuts.py` 集中注册；`W` 与左侧 `画标注框(W)` 按钮共用 `enable_draw_mode()`，`V/R/O/M/P/C/L` 持续切换对应画布模式，`L` 仅在直线扩展启用时生效。
- `DrawShapeDialog` 的“编辑”选项与下方形状列表共用一个连续外框，中间使用固定 `2 px` 高的较粗分隔线，不额外保留垂直布局间距。
- 标注画布右键菜单的“取消当前绘制”仅由未完成的临时绘制状态（起点、旋转矩形步骤或多边形顶点）触发；单纯切换到绘制形状不会显示该菜单项。
- 标注画布光标由 `src/ui/features/annotation/canvas/drawing.py` 统一根据交互状态刷新：除编辑模式外选择绘制模式后显示系统十字光标，矩形框模式额外在画布上绘制贯穿鼠标位置、依据热点下图片亮度在黑色与深灰色（`#000000` 至 `#484848`）之间变化的水平/垂直辅助线；三通道始终相等，不会显示彩色，并在短光标热点周围留出原始背景采样空隙，多边形封闭顶点优先显示小手，拖动时显示闭合手。
- 数据标注页底部状态栏由 `src/ui/features/annotation/layout.py` 装配并由 `src/ui/features/annotation/page.py` 管理；`annotation.show_canvas_status` 控制其显示，绘制模式变化通过画布状态回调同步“当前状态：{模式}”文字，离开数据标注页时隐藏。
- 页面导航在切换 `QStackedWidget` 当前页前调用目标页的 `prepare_for_show()`，预先完成标注页状态栏和底部边距布局，避免页面首次显示时发生一次可见重排。
- `src/ui/shared/widgets/base.py` 的 `PageScrollArea` 在窗口尺寸变化时同步滚动内容页的最小/最大宽度到视口宽度，确保页面从普通窗口切换到全屏后仍横向铺满，滚动区域只承担纵向滚动。
- `src/ui/features/annotation/canvas/status.py` 仅提供模式文字映射和状态变化通知，不再在画布内容上绘制黑底状态文字；验证页不再调用主窗口级 `set_status_text()`。
- 数据标注页采用“模块区 + 页面状态栏”的纵向布局，模块区与状态栏之间保持 `3 px` 间距；状态栏隐藏时恢复原有 `12 px` 页面底部边距，左侧栏、画布和右侧栏的底边保持对齐。
- 标注画布离开时清除悬停状态和辅助线；重新进入时由 `src/ui/features/annotation/canvas/interaction.py` 依据 `QEnterEvent` 坐标恢复当前绘制模式的光标和手动矩形框辅助线，避免短十字光标丢失；SAM 智能标注开启时不记录或绘制贯穿画布的长十字位置。
- 标注画布渲染由 `src/ui/features/annotation/canvas/render.py` 负责：已完成标注保持类别颜色显示；编辑模式下选中标注持续显示半透明背景，未选中时仅在悬停填充；绘制中的矩形、圆形和 OBB 使用半透明纯绿色轮廓，多边形在至少三个顶点确定后以半透明纯绿色背景标识区域，使颜色随图片底色混合变化，且不显示类别名称。
- 标注画布控制点由同一渲染模块按状态区分形状：绘制预览使用直径 `7 px` 的不透明纯绿色实心圆点，已完成标注默认使用直径 `7 px` 的实心圆点；圆形标注绘制预览中的半径控制点随鼠标确定方向，完成后使用 JSON 中保存的半径点位置，只有主动拖动该点才会改变；编辑模式悬浮时当前控制点显示直径 `9 px` 的空心方块，其余控制点显示直径 `9 px` 的空心圆点并允许直接拖动；普通有向矩形在四条边中心追加旋转控制点，拖动时以四角点平均位置为中心旋转全部角点，保持中心、尺寸和点顺序；开启 `annotation.optimize_mirror_edit` 后，镜像有向矩形改为绘制中心线并只显示中心线两端、两条长边中心四个控制点，端点拖动重建中心线，宽度点拖动按中心线对称重建两侧；绘制模式只渲染控制点，不开放选中或拖动；编辑模式未选中标注在整体悬浮时显示与选中态相同深度的背景，移开后恢复无背景，选中标注继续显示同等深度的半透明背景；编辑模式控制点命中范围为最大可视尺寸的 `2.0` 倍。

## 关键运行规则

- 训练与检测都只允许一次启动；运行期间按钮禁用，任务结束后恢复。
- 项目切换、恢复默认设置和关闭程序遇到写入/推理任务时，统一由任务协调器执行确认、停止和回收；过期结果按任务 token 与项目 generation 丢弃。
- 模型验证、AI 预标注和 Torch/CUDA 摘要读取都优先走短生命周期隐藏子进程，避免主 GUI 长驻推理运行时。
- `--yolo-ai-runtime` 按 payload 的 `backend` 延迟加载 YOLO 或 SAM3；相同模型会话复用实例，切换模型或关闭时释放旧模型与 CUDA cache。SAM3 payload 额外携带提示词映射、启用类别、输出形状、置信度、去重 IoU、最小面积和轮廓简化参数；旧 YOLO payload 保持兼容。
- SAM 辅助标注使用长期但按页面会话限定的隐藏 `--sam-assist-runtime`：协议包含 `load_model`、`set_image`、`predict_point` 和 `shutdown`，`load_model` 携带 `runtime_kind`，点预测携带四项高级参数，响应只传请求元数据与几何结果，不通过 JSON 传输完整 mask。悬停调度由页面控制器完成，首个点立即提交，最多一个推理在途并保留一个最新坐标，后续间隔根据最近推理耗时在 `50~120 ms` 内自适应；响应必须通过请求、模型、图片和形状代次过滤。关闭开关时仅异步取消预览与待处理请求并保留运行时，页面导航、项目重载和主窗口退出时才异步结束子进程；AI 预标注开始前则同步关闭该运行时释放显存，任务结束不自动重启。清理钩子保持幂等并等待残留 QThread。
- 每次启动后首次进入系统设置页时，GitHub Release 检查通过 `WorkbenchWindow.run_background()` 非阻塞执行；检查标志由 `WorkbenchContext` 持有，后续切换页面不重复检查，设置页顶部通知不使用模态对话框。
- 系统设置程序版本号或升级图标点击后打开 `ReleaseUpdateDialog`；该对话框展示版本、发布说明、资源勾选项、环境包更新信息模块、进度条下方的选择规则提示和汇总进度，环境更新信息和基础包默认勾选只在 Release 包版本高于本机版本时生效，首次安装缺少本机版本时视为需要环境包；冻结版优先读取安装清单/包信息，源码版使用当前环境包版本文本文件；同版本环境包仍可手动下载但不作为更新提示，程序-only 场景的同版本提示使用普通文字，手动勾选同版本基础包时使用红字提醒将执行一次重装；基础包被单独留下时显示红色不可安装提示；附加包可单独下载，并在仅勾选附加包、同时勾选程序包或三项全部勾选时根据是否已有附加包分别显示自动安装、替换或组合状态提示，三项全选时合并确认基础包重装和附加包替换；按钮显示“下载并安装所选资源”并在程序包未选中时热安装；勾选安装器时下载完成后启动，启动失败会转为可见错误状态；下载按钮支持通过事件暂停/继续下载或通过进程挂起/恢复暂停/继续安装器；已有安装但未提供新基础包时程序-only 下载保留旧环境并警告版本不匹配或环境不完整，首次安装缺少基础包时安装器阻止提交；下载期间拦截更新窗口关闭请求。
- 安装器在进入文件事务前通过 Inno Setup 的 Windows Restart Manager 注册安装目录中的目标 `YOLOTool.exe`；没有目标进程时直接继续，发现目标进程后由安装器自动关闭，不使用 PowerShell 或 WMI；自动关闭不负责恢复程序中的未保存状态。
- 安装器完成页的安装包清理选项挂在右侧运行选项下方，勾选后延迟删除本次使用的安装器、基础环境包和附加环境包。
- 系统设置页的八个环境状态卡固定为四列等宽网格，避免长内容把最后一列异常拉宽。
- 对任何会修改用户文件的功能，坚持“先预览，再执行”。
- UI 中项目文件夹显示绝对路径，其他项目内路径优先显示相对路径。
- `data/models/` 是统一基础模型目录；训练与验证模型列表优先使用该目录。

## 打包链路

- 完整发布先用完整冻结目录构建基础运行环境，再清理并重建 program-only 程序 staging；Inno Setup 的程序层只允许使用后一次 staging，避免完整冻结 EXE 将 `_internal` 运行库重复带入安装器。

- PyInstaller 入口是 `src/main.py`，规格文件为 `installer/YOLOTool.spec`。
- 打包脚本 `installer/build_windows.ps1` 负责正式版与开发快包，并在产物目录生成默认 `settings.json`、`app_state.json`；完整冻结输出还会写入根目录兼容清单，使 `dist/YOLOTool` 可直接启动，程序-only 输出仍依赖已安装基础环境；应用图标和 `sam_assist.svg` 由 PyInstaller/Qt 资源模块随程序本体提供。
- 基础包模型来源固定为 `data/models/yolo11s.pt`、`data/models/yolo26n.pt`、`data/models/yolov8n.pt` 和 `data/models/sam2.1_hiera_base_plus.pt`；由 PowerShell 复制到产物根目录的 `data/models/`，spec 不收集用户 checkpoint。SAM3 代码与推理依赖随基础包 v3 提供，但官方 `sam3.pt` 不进入源码、基础包或程序包，用户需自行接受条款并放入项目或程序根目录 `data/models/`。
- `src/services/runtime/metadata.py` 统一解析 `_internal/yolotool_metadata/`，并为旧安装保留根目录清单回退；`release_manifest.py` 负责环境兼容，`install_instance.py` 将附加环境放入 `_internal/extensions/` 并迁移旧 `%LOCALAPPDATA%` 目录，`managed_models.py` 只清理清单登记的官方模型路径。
- `src/devtools/release_package.py` 分别生成 `Program` staging 和 `BaseRuntimeModels` staging/`.7z`；基础包清单登记 `_internal` 与模型文件路径及解压体积，不读取大型运行时文件内容；`companion_catalog.py` 固定伴随包的名称、标识、版本、平台、运行时协议和解压体积，不把一次性压缩产物哈希作为版本身份。
- 基础包和模型转换附加包都不生成或读取 `.cache.json`，完整发布时每次重新构建 staging 和归档。基础包和附加包都通过原生 7-Zip `-mmt=on` 压缩；`-Clean` 仍可清理并强制重建输出。
- `installer/yolo_tool.iss` 生成统一的小型 `YOLOTool_Setup_<版本>.exe`。组件页只按版本化文件名和 `.7z` 扩展名识别候选包，不绑定压缩大小或归档哈希；程序与必选基础环境在 staging/backup 事务中切换并执行冻结启动探测。文件事务失败时回滚，运行时版本自检不匹配或未通过时只警告并继续完成安装。
- 每个实例的 `install-instance.ini` 与其他安装清单存放在 `_internal/yolotool_metadata/`；基础包维护规范模型 `data/models/yolo26n.pt` 和受管的根目录兼容副本。
- 打包后训练、导出、验证仍通过 `YOLOTool.exe --yolo-train / --yolo-export / --yolo-val` 进入 `src/train_cli.py` 与 `src/bootstrap/cli_dispatch.py`。

## 维护建议

- 新增业务逻辑优先进入 `src/services/`，只有明确依赖 Qt 生命周期的逻辑才放到 `src/ui/`。
- 新增页面逻辑直接放入 `src/ui/features/<feature>/`，不要恢复任何 `views`、`legacy` 或顶层 UI 兼容壳。
- `src/services/<domain>/__init__.py` 只做轻量导出，不塞入业务实现。
- 修改结构后同步更新 `docs/spec/*.md`、`docs/packaging-windows.md` 和 `docs/code-inventory.md`。
- 当前阶段的结构围栏由 `src/tests/architecture/test_structure_boundaries.py` 的 4 项场景负责：分层依赖、旧路径与导入禁用、页面/worker/service 体量阈值，以及 Qt 延迟回调上下文和通配导入限制。模块体量采用“建议拆分线 + 硬安全线”：`page.py` 与标注画布模块建议在 250 行附近审查职责、硬上限 350 行，共享 worker 建议线 220 行、硬上限 300 行，服务实现建议线 300 行、硬上限 400 行；服务包 `__init__.py` 仍不得超过 80 行。超过建议线本身不导致测试失败，只有越过硬安全线才要求按职责拆分，禁止为满足行数而压缩排版或删除合理空白。代码清单在结构变化后由生成器更新并通过 diff 审查，不再占用 pytest 时间。

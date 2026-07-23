# 架构与维护说明

## 项目概述

本项目是一个独立于 `yolo-weld` 的 Windows 本地可视化 YOLO 训练工作台，使用 **Python + PySide6 / Qt** 开发桌面 GUI。

定位是“通用 YOLO 优先，同时兼容焊缝 OBB 项目”：

- 支持 YOLO `detect` 与 `obb` 两类任务。
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
- `src/shared/paths.py` 同时维护应用数据根目录和静态资源根目录；开发态资源从仓库 `src/assets/` 读取，PyInstaller 冻结态资源从 EXE 同级的 `app_assets/` 读取，而 `data/` 仍从 EXE 所在目录读取。GUI 启动时 `QApplication` 和 `WorkbenchWindow` 都应通过这里的 `ICON_PNG` 加载图标，不要在 UI 层硬编码相对目录。顶部导航图标由 `src/ui/shared/widgets/base.py` 按当前屏幕设备像素比生成物理 pixmap 并设置对应 DPR；主窗口屏幕变化时重新取样，保持 `28 x 28` 逻辑尺寸下的清晰度。
- `src/services/<domain>/` 是唯一业务实现层。这里允许依赖标准库、第三方库、其他服务包和 `src/shared/`，不得依赖 `src/ui/`。
- `src/services/home/` 负责主页的大目录扫描、统计汇总与训练历史整理；这些逻辑必须通过后台 worker 调用，避免主线程同步 I/O 卡住首页。主页切回时若界面上已有上一轮统计值，应优先保留旧值，待新汇总返回后再替换，避免反复闪出“加载中”。
- 主页类别分布优先读取数据集 `data.yaml` 的 `names`，关闭多类别模式时使用普通图片分布，开启多类别模式时按总标注和各类别标注对象数量展示；数据集与设置均无类别名称时使用“目标名称”作为兜底。
- 主页标注数量按 Labelme `shapes` 数量或 YOLO 非空标签行数统计，不按标注文件数统计；普通分布图固定显示总图片、训练、验证、测试、未标注五项，总图片固定在最左侧，其余项目按数量降序排列，未标注为 0 时隐藏。普通模式仅在只有一个标注类型时显示上方类型名称，多类别时隐藏名称并扩展绘图区；无标题模式下 Y 轴顶部间距为 15px，柱顶数值标签和柱状图位置保持独立。
- 主页没有有效的 `data/train|val|test/labels` 标签时，分布统计回退到当前图片目录及同名 Labelme/YOLO 标签；多类别模式下按每个类别的标注对象数量统计，第一项为总标注数并按类别数量降序排列。
- `src/ui/shell/` 负责主窗口、导航、页面注册、关闭保护、程序日志和整体样式。
- `src/ui/shared/` 负责跨页面 UI 复用能力，例如页面基类、共享表单、共享对话框和后台 worker。
- `src/ui/features/<feature>/` 负责各页面真实实现；`page.py` 只做页面装配，复杂逻辑继续拆到该功能包子模块。
- 数据标注页的目标类型联动由 `src/ui/features/annotation/selection.py` 统一维护：选中画布或列表标注时同步右侧下拉框，选中标注时修改下拉框会回写该标注类别；未选中标注时下拉框仍只控制新建标注的默认类别。
- `src/services/annotation/class_names.py` 扫描当前项目 Labelme 标注目录中的非空类别名并追加到项目设置；`ClassManagerDialog` 负责类别编辑、删除依赖保护和转换按钮，`ClassConversionDialog` 作为独立窗口选择源/目标类别；确认后由标注页统一保存设置和标注，取消不产生转换。
- `src/ui/widgets/` 与 `src/ui/shared/widgets/` 放基础可复用控件与图表组件。主页 `DatasetDistributionWidget` 和 `TrainingCurveWidget` 使用当前控件 DPR 创建物理 pixmap、以逻辑坐标绘制，并通过 `refresh_for_device_pixel_ratio()` 响应主窗口跨屏切换，避免高 DPI 下图表文字、坐标轴和曲线被放大模糊；图表内框在 pixmap 内部绘制，与训练历史表格统一使用 `1 px #CFD9E3` 边框和 `5 px` 圆角，避免 QLabel 内容覆盖圆角造成断开空隙；各类别图片分布坐标轴保持 `20 px` 左边距、`38 px` 顶部位置和 `33 px` 底部留白，类别标题上方留 `7 px`、标题到坐标轴顶部留 `9 px`，最高柱数字与坐标轴顶部间距为 `0 px`；训练曲线坐标轴左边距保持为 `34 px`，顶部 `Epoch` 摘要按纵轴 `1.0` 刻度的实际字体宽度计算起点以保持左对齐。
- `src/tests/architecture/` 只保留依赖方向、旧入口、模块体量和 Qt 生命周期四类结构围栏，不扫描文档措辞或代码清单内容。
- `src/tests/services/` 按领域保护文件读写、转换、设置、命令构造和运行时安全等业务规则。
- `src/tests/ui/` 按业务域和 shell 分目录保留关键页面工作流与服务接线；数据处理 UI 测试使用 `data_processing/`，避免与项目级 `data/` 忽略规则冲突；精确布局、颜色、尺寸与提示文本改由发布前人工检查。
- `src/tests/integration/` 放开发/冻结入口、隐藏 CLI 和 Windows 打包契约回归。
- 默认 `pixi run test` 固定收集 88 项核心测试，不另设隐藏的慢速或完整测试套件。

## 服务层说明

### `src/services/settings/`

- `defaults.py` 提供默认设置构造。
- `storage.py` 提供深合并与项目路径序列化 / 反序列化。
- `project_settings.py` 负责项目级设置加载、保存与最近项目状态读写。
- 当前项目配置保存到当前项目目录 `data/runtime/settings.json`。
- 应用级最近项目状态保存到应用根目录 `data/runtime/app_state.json`。
- `src/runtime/settings.json` 仅作为源码内默认配置参考。
- 标注页名称显示由项目设置 `annotation.show_annotation_names` 控制，默认值为 `false`。
- 标注页未配置 `dataset.class_names` 时类别下拉框保持为空，不再自动添加 `weld`；进入项目标注目录时会按文件顺序读取所有 Labelme JSON 的非空 `label`，将缺少的类别追加到当前项目 `data/runtime/settings.json`。

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
- 数据处理页的数据集划分配置直接读取当前项目 `dataset.class_names`；该字段由数据标注页“管理类别”维护，自定义类别映射窗口也使用这组类别作为来源。
- `backup.py` 负责旧产物清理与备份；未启用备份时不主动创建 `old/` 目录。
- `formatting.py` 负责转换结果说明文本。
- `execute.py` 保留为转换总流程装配入口。

### `src/services/data_ops/`

- 负责批量重命名、图片压缩和项目内路径显示转换。
- `relative_path_from_project()` 用于验证页自定义输入源的相对路径显示；路径解析仍由 `resolve_project_path()` 统一处理，项目外路径使用 `..` 表示。
- 图片压缩页的“打开结果文件夹”属于页面层轻交互，直接基于当前“输出目录”字段解析后的路径打开目录，不额外下沉到服务层。

## UI 约定

- `src/ui/shell/window.py` 中的 `WorkbenchWindow` 是唯一主窗口实现。
- UI 中使用 `QTimer.singleShot` 延迟调用页面或窗口方法时，必须传入所属 `QObject` 作为上下文；对象销毁后 Qt 会自动取消未执行回调，避免跨页面或退出阶段访问已删除控件。
- 页面创建与导航注册统一在 `src/ui/shell/page_registry.py` 与 `src/ui/shell/navigation.py`。
- 主窗口页面采用“首屏懒加载 + 空闲分批预热”：启动时先创建当前页，窗口显示后再按空闲节奏补建其余页面，避免首页打开时连带触发重页面初始化，同时减少用户第一次切到任意页面时再同步吃到建页卡顿。
- 程序级日志缓冲与设置页日志展示统一走 `src/ui/shell/program_log.py`。
- 关闭确认统一由 `src/ui/shell/close_guard.py` 处理，包括未保存标注与训练运行中确认。
- `WorkbenchWindow` 默认尺寸为 `1100 x 740`，最小尺寸为 `800 x 600`；项目内路径在 UI 中优先显示为相对路径，写入文件时由设置存储层解析/序列化。
- `BasePage.update_setting()` 保存项目设置后，通过 `WorkbenchWindow.notify_setting_changed()` 广播设置键路径；已创建页面必须立即刷新镜像路径控件，控件刷新期间阻断信号，避免重复保存。
- 项目路径字段分为三组共享路径：`paths.images_dir`（数据集划分、标注预览、批量重命名、数据标注）、`paths.annotations_dir`（数据标注、数据集划分、批量重命名）和 `paths.labels_dir`（标注预览、数据集划分）；图片压缩源目录单独使用 `image_resize.source_dir`。
- 标注页“更多设置”使用等权垂直伸缩项承接窗口额外高度，保证各设置行之间的间隔一致；复合设置内部（如直线扩展像素标题与数值框）不参与外层间隔分配。
- 共享页面基础能力只能放在 `src/ui/shared/page_base.py`，不要回流到页面专属实现。
- worker 真实实现只放在 `src/ui/shared/workers/`，页面持有 worker 时必须在原生 `finished` 信号后再清理对象。
- `src/ui/features/annotation/page.py` 与 `src/ui/features/annotation/canvas/widget.py` 都只保留页面 / 画布装配；交互、保存、菜单、快捷键、AI 与编辑细节继续拆在 feature 子模块。
- 标注页快捷键由 `src/ui/features/annotation/shortcuts.py` 集中注册；`W` 与左侧 `画标注框(W)` 按钮共用 `enable_draw_mode()`，`V/R/O/M/P/C/L` 持续切换对应画布模式，`L` 仅在直线扩展启用时生效。
- `DrawShapeDialog` 的“编辑”选项与下方形状列表共用一个连续外框，中间使用固定 `2 px` 高的较粗分隔线，不额外保留垂直布局间距。
- 标注画布右键菜单的“取消当前绘制”仅由未完成的临时绘制状态（起点、旋转矩形步骤或多边形顶点）触发；单纯切换到绘制形状不会显示该菜单项。
- 标注画布光标由 `src/ui/features/annotation/canvas/drawing.py` 统一根据交互状态刷新：除编辑模式外选择绘制模式后显示系统十字光标，矩形框模式额外在画布上绘制贯穿鼠标位置、依据热点下图片亮度在黑色与深灰色（`#000000` 至 `#484848`）之间变化的水平/垂直辅助线；三通道始终相等，不会显示彩色，并在短光标热点周围留出原始背景采样空隙，多边形封闭顶点优先显示小手，拖动时显示闭合手。
- 数据标注页底部状态栏由 `src/ui/features/annotation/layout.py` 装配并由 `src/ui/features/annotation/page.py` 管理；`annotation.show_canvas_status` 控制其显示，绘制模式变化通过画布状态回调同步“当前状态：{模式}”文字，离开数据标注页时隐藏。
- 页面导航在切换 `QStackedWidget` 当前页前调用目标页的 `prepare_for_show()`，预先完成标注页状态栏和底部边距布局，避免页面首次显示时发生一次可见重排。
- `src/ui/features/annotation/canvas/status.py` 仅提供模式文字映射和状态变化通知，不再在画布内容上绘制黑底状态文字；验证页不再调用主窗口级 `set_status_text()`。
- 数据标注页采用“模块区 + 页面状态栏”的纵向布局，模块区与状态栏之间保持 `3 px` 间距；状态栏隐藏时恢复原有 `12 px` 页面底部边距，左侧栏、画布和右侧栏的底边保持对齐。
- 标注画布离开时清除悬停状态和辅助线；重新进入时由 `src/ui/features/annotation/canvas/interaction.py` 依据 `QEnterEvent` 坐标恢复当前绘制模式的光标和矩形框辅助线，避免短十字光标丢失。
- 标注画布渲染由 `src/ui/features/annotation/canvas/render.py` 负责：已完成标注保持类别颜色显示；编辑模式下选中标注持续显示半透明背景，未选中时仅在悬停填充；绘制中的矩形、圆形和 OBB 使用半透明纯绿色轮廓，多边形在至少三个顶点确定后以半透明纯绿色背景标识区域，使颜色随图片底色混合变化，且不显示类别名称。
- 标注画布控制点由同一渲染模块按状态区分形状：绘制预览使用直径 `7 px` 的不透明纯绿色实心圆点，已完成标注默认使用直径 `7 px` 的实心圆点；圆形标注绘制预览中的半径控制点随鼠标确定方向，完成后使用 JSON 中保存的半径点位置，只有主动拖动该点才会改变；编辑模式悬浮时当前控制点显示直径 `9 px` 的空心方块，其余控制点显示直径 `9 px` 的空心圆点并允许直接拖动；绘制模式只渲染控制点，不开放选中或拖动；编辑模式未选中标注在整体悬浮时显示与选中态相同深度的背景，移开后恢复无背景，选中标注继续显示同等深度的半透明背景；编辑模式控制点命中范围为最大可视尺寸的 `2.0` 倍。

## 关键运行规则

- 训练与检测都只允许一次启动；运行期间按钮禁用，任务结束后恢复。
- 模型验证、AI 预标注和 Torch/CUDA 摘要读取都优先走短生命周期隐藏子进程，避免主 GUI 长驻推理运行时。
- 对任何会修改用户文件的功能，坚持“先预览，再执行”。
- UI 中项目文件夹显示绝对路径，其他项目内路径优先显示相对路径。
- `data/models/` 是统一基础模型目录；训练与验证模型列表优先使用该目录。

## 打包链路

- PyInstaller 入口是 `src/main.py`，规格文件为 `installer/YOLOTool.spec`。
- 打包脚本 `installer/build_windows.ps1` 负责正式版与开发快包，并在产物目录生成默认 `settings.json`、`app_state.json` 和 `app_assets/`。
- 打包模型来源统一为 `data/models/*.pt`；由 PowerShell 复制到产物根目录的 `data/models/`，spec 不收集模型文件，项目根目录 `.pt` 也不再复制，避免模型落入 `_internal/` 或形成重复副本。
- `src/services/runtime/release_manifest.py` 负责发布清单、环境版本校验和 SHA-256 校验；`src/devtools/release_package.py` 按 `Full`、`AppUpdate`、`RuntimeFull` 生成 staging。
- 安装包脚本 `installer/yolo_tool.iss` 通过 `PackageType` 编译参数封装三种安装程序。更新包在临时目录完成文件准备后再切换程序层或程序加环境层，用户数据层不参与更新。
- 打包后训练、导出、验证仍通过 `YOLOTool.exe --yolo-train / --yolo-export / --yolo-val` 进入 `src/train_cli.py` 与 `src/bootstrap/cli_dispatch.py`。

## 维护建议

- 新增业务逻辑优先进入 `src/services/`，只有明确依赖 Qt 生命周期的逻辑才放到 `src/ui/`。
- 新增页面逻辑直接放入 `src/ui/features/<feature>/`，不要恢复任何 `views`、`legacy` 或顶层 UI 兼容壳。
- `src/services/<domain>/__init__.py` 只做轻量导出，不塞入业务实现。
- 修改结构后同步更新 `docs/spec/*.md`、`docs/packaging-windows.md` 和 `docs/code-inventory.md`。
- 当前阶段的结构围栏由 `src/tests/architecture/test_structure_boundaries.py` 的 4 项场景负责：分层依赖、旧路径与导入禁用、页面/worker/service 体量阈值，以及 Qt 延迟回调上下文和通配导入限制。代码清单在结构变化后由生成器更新并通过 diff 审查，不再占用 pytest 时间。

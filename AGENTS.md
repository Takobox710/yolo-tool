# AGENTS.md — YOLO 本地训练工作台

## 项目概述

本项目是一个独立于 `yolo-weld` 的 Windows 本地可视化 YOLO 训练工作台，使用 **Python + PySide6 / Qt** 开发桌面 GUI。

定位是"通用 YOLO 优先，同时兼容焊缝 OBB 项目"：

- 支持 YOLO `obb` 与普通 `detect` 两类任务。
- 默认内置焊缝识别项目习惯配置，例如类别 `weld`、Labelme 转 YOLO-OBB、直线标注扩展为旋转矩形。
- 不依赖原项目的 `YL` conda 环境，使用本项目本地 `pixi` 环境管理依赖。

## 重要约束

- 所有项目代码放在 `scr/` 目录下，UI、服务、入口、资源都从 `scr/` 根组织。
- 测试代码放在 `scr/tests/` 目录下。
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
├── 打包程序.bat
├── docs/
│   └── packaging-windows.md
├── installer/
│   ├── yolo_tool.iss
│   ├── YOLOTool.spec
│   ├── build_windows.ps1
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
    │       ├── validation.py
    │       └── settings.py
    └── tests/
        ├── conftest.py
        ├── test_core_services.py
        └── test_direct_app_entry.py
```

## 启动与测试

推荐命令：

```powershell
pixi run app
pixi run test
```

等价启动入口：

```powershell
pixi run python -m scr.main
```

如需双击启动，可使用 `scr/open_yolo_tool.pyw`。

静态编译检查：

```powershell
pixi run check
```

Windows 绿色版打包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release
```

开发快速打包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File installer\打包程序.ps1
```

如需直接双击一键打包，可使用项目根目录的 `打包程序.bat`。

Inno Setup 安装包脚本位于 `installer/yolo_tool.iss`，与统一的 PyInstaller spec、hooks、PowerShell 打包脚本统一放在 `installer/` 目录维护。

正式版产物位于 `dist/YOLOTool/`，开发快包位于 `dist/YOLOTool-dev/`。

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

PyTorch 相关依赖当前通过 `pixi.toml` 的 `[pypi-dependencies]` 单独指定索引：

```toml
torch = { version = "*", index = "https://download.pytorch.org/whl/cu130" }
torchvision = { version = "*", index = "https://download.pytorch.org/whl/cu130" }
torchaudio = { version = "*", index = "https://download.pytorch.org/whl/cu130" }
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

当前主 GUI 入口为 `scr/main.py`，应用装配层位于 `scr/app.py`，窗口与页面拆分到 `scr/ui/` 下；服务层保持在 `scr/services/` 下。

除主页默认显示外，用户在训练、验证、标注转换、批量重命名、图片压缩等界面修改过的主要配置项，应持久化到当前项目目录的 `data/runtime/settings.json`，下次启动或切回该项目后继续保留。

主页点击"设置项目目录"切换项目时，必须重新加载目标项目的 `data/runtime/settings.json`；若不存在则按目标项目目录创建默认配置。`scr/runtime/settings.json` 只作为历史/源码内默认配置参考，不再作为当前项目配置的唯一落点。

程序最近一次打开的项目根目录应单独持久化到应用根目录 `data/runtime/app_state.json` 的 `last_project_root`；它只用于恢复最近项目，不得覆盖当前项目自己的 `data/runtime/settings.json`，测试中也不得误写真实工作区的该文件。

程序启动时默认进入"主页"，不再根据上次关闭前的 `last_page` 自动恢复页面。

### 主页

主页必须按旧版整体设计重建，展示项目路径、图片数量、标注数量、训练曲线、训练结果模型等概览信息。

主页布局约定：

- 主页使用 Qt 两行两列网格布局，行高比例 58:42。
- 主页应放入 `QScrollArea`，最小窗口高度不足时允许滚动，不能压扁卡片内容。
- 主页页面本体当前最小高度为 `650`；默认窗口下应尽量避免轻微溢出导致刚启动就出现竖向滚动条。
- 主页列宽由代码按可用宽度固定计算，左列约 30%，右列约 70%，避免放大窗口时左列漂移或比例变化。
- 顶部保留欢迎标题和简短环境标签；不要显示标题下方的说明标语。
- 上半区左侧为"项目概览"（标题与"设置项目目录"按钮同行），包含项目文件夹、图片路径、标注路径、结果路径、图片数量、标注数量。
- 项目概览每行保持左侧字段名、右侧数据结构；字段名固定窄宽，右侧长路径使用中间省略显示，完整内容放入 tooltip。
- "设置项目目录"与"打开结果目录"按钮采用紧凑按钮样式，高度约 30px，小字号，不要通过继续加宽按钮解决文字显示问题。
- 上半区右侧为"各类别图片分布"，使用 `scr/ui/widgets/charts.py` 中的独立图表组件渲染柱状图。
- 各类别图片分布显示四根柱：总照片、训练、验证、测试。单类别模式下顶部显示当前类别名，不显示“总计 xx 张图片”；训练、验证、测试三项之间单独计算占比，总照片不参与这三项百分比分母。柱状图坐标轴左侧留白保持紧凑，当前约定左边距为 30px。
- 当项目存在多个类别且系统设置开启多类别分布模式时，顶部只显示“总计 xx 张照片”，不显示类别名；柱状图改为按类别展示，各柱名称为各类别名称。
- 下半区左侧为训练曲线卡片，但不显示"训练曲线"标题，以节省空间。
- 训练曲线使用 `scr/ui/widgets/charts.py` 中的独立图表组件，从 `results.csv` 读取数据，顶部只显示 Epoch，不显示 mAP50 或 Box Loss 的数值摘要。
- 训练曲线绘制 mAP50 与 Box Loss 两条关键曲线并保留图例；曲线必须只画线，不得填充折线路径区域，避免出现三角形色块。
- 训练曲线暂无训练记录时显示坐标轴和空状态文字。
- 下半区右侧为"训练历史"（"打开结果目录"按钮与标题同行，排序三角形隐藏），自动扫描 `result/**/weights/*.pt`。
- 训练历史默认按模型 ID 自然含义排序，编号靠后的训练目录优先显示，例如 `train-2` 在 `train` 前；同一训练目录内 `best` 优先于 `last`。
- 训练历史标题行与表格之间固定保留 `3px` 间距。
- 训练历史表格必须支持点击表头排序，但排序三角形隐藏；刷新时先临时关闭排序，填充完整数据后再恢复排序，避免初启动数据错位。
- 训练历史表格列宽必须按当前可见宽度重新计算，初始进入、窗口缩放和刷新数据后都要重算；`Time`、`Recall` 等列不能显示省略号或被右侧滚动条遮挡。
- 主页首次布局后，训练历史列宽延迟重算使用 `50ms`，不要恢复为更长的 `80ms`。
- 主页四张卡片不得保留放大后的固定宽度；窗口横向放大后再缩小时，卡片必须跟随可见区域缩回，并保持 1:2 列宽比例。
- 主页底部内容区外边距当前为 `16, 16, 16, 4`；不要再把底部留白恢复为更大的默认值。
- 主页"训练历史"卡片里的"打开结果目录"按钮当前固定宽度为 `110px`。

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
- 可关闭 Labelme 转换开关，对已经转换好的 YOLO `.txt` 标注只执行 train/val/test 分组、图片与标签复制、`data.yaml` 生成和 labels 汇总。
- `obb` 与 `detect`
- `oriented_rectangle` 转 OBB
- `line` 按半宽扩展为 OBB
- 自动划分 `train/val/test`
- 生成 `data.yaml`
- 汇总 `labels`
- 类别名称不再由界面手动输入。Labelme 模式下从 `.json` 的 `label` 自动识别类别，按首次出现顺序生成 class id；YOLO `.txt` 分组模式下若没有类别名称来源，则按数字 id 自动显示为 `class_0`、`class_1` 等。
- 支持“备份标注文件”开关；开启后，每次转换生成的 YOLO 标注文件和 `data.yaml` 都会备份到 `data/old/backup-时间戳/` 下独立文件夹，支持多次共存。
- 支持“自定义类别名称”窗口，可把多个 Labelme 类别通过英文逗号映射到同一个 YOLO 类别，并在保存时校验是否引用了不存在或重复的 Labelme 类别。

标注转换页面布局与交互约定：

- 页面顶部采用类似模型训练页的左右两张卡片布局。
- 左侧卡片标题为"数据集与转换配置"，上方 2x2 放置图片目录、Labelme 标注目录、YOLO 标注目录、输出目录；下方放置"Labelme 转 YOLO"、"备份标注文件"和"自定义类别名称"。
- 右侧卡片标题为"转换参数"，按从左到右、从上到下排列为：任务类型、训练、验证、测试、随机种子、直线拓展宽度。
- 任务类型下拉框默认值为 `detect`，下拉顺序固定为 `detect` 在前、`obb` 在后。
- 默认数据集划分比例为 `train=0.8`、`val=0.2`、`test=0.0`。
- 解释方式固定采用方案 B：直接在字段名称后追加 `ⓘ`，tooltip 继续挂在对应名称控件本身，不要再实现独立解释图标控件、悬浮说明层或自定义气泡。
- 图片目录、Labelme 标注目录、YOLO 标注目录、输出目录这四个路径字段不要显示 `ⓘ`。
- 标注转换页仅以下项目显示 `ⓘ`：`Labelme 转 YOLO`、`备份标注文件`、任务类型、训练、验证、测试、随机种子、直线拓展宽度。
- 解释只通过鼠标悬停 tooltip 显示，不要在界面上额外显示说明段落。
- 不要显示"开启时读取同名 json 并转换..."、比例合计提示、"OBB + Labelme 直线标注..."等常驻说明文字；这些内容如需保留，只能放入 tooltip。
- Tooltip 应关闭动画或采用更快的显示方式，避免鼠标悬停后等待过久。
- 直线拓展宽度只在 `任务类型=obb` 且 Labelme 转 YOLO 开启时启用。
- 转换结果输出需直观展示数据集划分、总体统计、类别统计、跳过/未知标签和输出路径；类别相关数据只在结果输出中展示。

图片压缩支持：

- 可选是否备份原始图片，默认不备份。
- 以“画布尺寸”作为长边对齐目标，按长边等比缩放。
- 默认创建 `960 x 960` 白色或黑色画布。
- 将缩放后的图片居中粘贴到画布。
- 递归扫描图片目录及其子目录中的图片，并按自然数字顺序预览与处理。
- 输出目录与备份目录都应保持与原图片目录一致的相对目录结构。

### 模型训练

训练页必须按旧版整体设计重建，并遵循当前交互约定：

- 左侧：基础模型（下拉框，自动读取 `data/models/*.pt`，也可手动输入）、数据集 YAML、模型 YAML（默认空白）、项目输出、数据增强选项。
- 右侧：优化器（auto/SGD/Adam/AdamW/RMSProp 下拉框）、设备、学习率、训练轮数、早停轮数、线程数、批次大小、图片尺寸。
- 默认基础模型为 `yolov8s.pt`，默认训练参数为：优化器 `auto`、学习率 `0.001`、`训练轮数=500`、`早停轮数=100`、`线程数=2`、`批次大小=16`、`图片尺寸=640`、`设备=0`。
- 训练页“图片尺寸”使用可编辑下拉框，内置 `640`、`960`、`1280` 三个候选值，同时允许手动输入其他尺寸。
- 默认增强勾选状态与当前界面一致：随机拼图、缩放、平移、调色、左右翻转默认开启；上下翻转、旋转、混合默认关闭。
- 中部左侧保留训练控制模块（开始训练、停止训练、查看模型报告），但不显示"训练控制"标题。
- 中部右侧保留系统状态模块（GPU/显存/CPU/内存），但不显示"系统状态"标题。
- 训练日志面板不显示标题和进度条，只保留日志文本框。
- 基础模型、数据集 YAML、模型 YAML、项目输出四个输入区域应保留灰色占位提示。
- 数据增强勾选项按从左到右、从上到下顺序排列为：随机拼图、缩放、平移、调色、左右翻转、上下翻转、旋转、混合。
- 训练页解释方式同样固定为方案 B：不要再使用独立解释图标；tooltip 直接挂在字段名或勾选项文本上。
- 训练页 tooltip 文案当前统一采用“中文全称（命令参数名）；说明”的格式，例如：`随机缩放增强（scale）；随机缩放目标与画面，提升对尺寸变化的适应能力。`
- 训练页仅以下项目显示 `ⓘ`：
  - `训练参数` 卡片中的全部项：优化器、学习率、训练轮数、早停轮数、线程数、批次大小、图片尺寸、设备。
  - `数据集与增强配置` 下方 8 个增强项：随机拼图、缩放、平移、调色、左右翻转、上下翻转、旋转、混合。
- 基础模型、数据集 YAML、模型 YAML、项目输出这四项不要显示 `ⓘ`，但保留占位提示。
- `线程数` 与 `图片尺寸` 的 tooltip 必须明确说明提高后会占用更多系统内存。
- 8 个增强项的 tooltip 中必须写出对应训练命令参数名，便于用户在命令中查找与修改，例如 `mosaic`、`scale`、`translate`、`hsv_h / hsv_s / hsv_v`、`fliplr`、`flipud`、`degrees`、`mixup`。

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
python -m scr.main --yolo-train obb train model=... data=... epochs=... imgsz=... batch=... optimizer=...
```

打包后训练/导出命令通过 `YOLOTool.exe --yolo-train ...` 或 `YOLOTool.exe --yolo-export ...` 进入 `scr/train_cli.py`，目标机器不需要安装 Python、pixi 或 Ultralytics CLI。不要把训练命令恢复为依赖 `pixi run yolo ...` 的形式。

模型目录约定：

- `data/models/` 是统一的基础模型目录。
- 训练页基础模型下拉框默认从 `data/models/*.pt` 读取，不再优先扫描项目根目录下的 `.pt`。
- 当基础模型输入的是模型文件名，例如 `yolo11n.pt`、`yolov8m-obb.pt`，训练命令中的 `model=` 与 `pretrained=` 都应解析为 `data/models/` 下的绝对路径。
- 若本地不存在该模型，Ultralytics 触发自动下载时，也应下载到 `data/models/`，不要落到项目根目录或其他默认目录。

Qt 实现注意事项：

- 基础模型、设备、优化器必须使用 `QComboBox` 等下拉控件。
- 数据增强项必须是真实 `QCheckBox`，勾选状态必须影响训练命令参数。
- HSV 勾选项必须同时控制 `hsv_h`、`hsv_s`、`hsv_v` 三个训练参数；取消勾选时三者都传 `0`。
- 开始训练、停止训练、查看模型报告按钮放在训练控制模块中，不放在训练日志标题栏中。
- 系统状态检测必须后台执行，不得阻塞页面切换或窗口缩放，并且训练页 GPU/显存/CPU/内存状态需每 `0.5s` 自动刷新一次。
- Windows 打包后的后台子进程不得弹出终端窗口；调用 `nvidia-smi`、训练/导出等后台进程时应通过 `scr/services/process_utils.py` 提供的隐藏窗口参数。
- 点击"开始训练"后，若自定义命令框功能开启，先弹出命令编辑对话框，可修改命令后再执行训练；若上一个训练任务未结束则不弹出也不启动新任务。
- 训练命令编辑对话框当前默认尺寸为 `700 x 200`，最小尺寸为 `350 x 100`。
- 训练和检测均只允许一次启动，按钮在运行期间禁用，任务结束后恢复。
- 点击"停止训练"后，训练页应立即进入"停止中"状态，禁用停止按钮，待训练进程真正退出后再统一恢复"开始训练"按钮，避免出现已停止但开始按钮仍为灰色的状态不同步问题。
- 训练停止后，若后台的 Windows `multiprocessing` dataloader 子进程继续抛出 `WinError 5` 等停止期噪声，不应继续污染 GUI 日志；训练页应优先呈现"已请求停止训练"和最终停止结果。
- GUI 训练日志不得直接显示终端 ANSI 控制序列；像 `ESC[K`、`ESC[34m`、`ESC[1m` 这类进度刷新和颜色控制符必须在写入文本框前清洗掉，避免日志出现 `[K`、`[34m` 等乱码残留。

### 模型验证

验证页左右比例当前为 `1:3`，左侧保持紧凑，右侧图片区和详情表纵向占位比例为 `2:1`：

- 左侧：模型配置（含下拉框自动扫描模型）、置信度/IoU/图片尺寸、检测模式与输入源、检测按钮区、日志文本框（不显示"检测日志"标题）。
- 右侧：源图、检测结果图、检测结果详情表。

支持输入源：

- 图片/视频文件夹
- 图片/视频（单张图片或单段视频）
- 摄像头
- 数据集验证

支持自动扫描 `data/models/*.pt` 与 `result/**/weights/*.pt`，也可手动选择模型；列表中优先显示 `data/models` 下的基础模型。

- 模型验证页的“选择模型”下拉框默认只显示各训练目录下的 `best.pt`。
- 当系统设置开启“训练模型显示 last”时，模型验证页的“选择模型”下拉框才额外显示各训练目录下的 `last.pt`。
- 若当前已选中某个训练目录的 `last.pt`，随后关闭“训练模型显示 last”，模型验证页应自动回退到同一训练目录下的 `best.pt`。

验证页 UI 注意事项：

- 左侧和右侧采用可缩放的 `1:3` 权重，不要用固定像素宽度锁死，否则小窗口会截断右侧内容。
- 下拉控件使用 Qt 原生 `QComboBox` 并保持与普通输入框一致的边框，不要再用额外白底外壳模拟边框。
- 所有面板顶部边框和圆角必须完整显示，标题栏不能覆盖面板上边框，也不能让顶部圆角变直角。
- 选择模型使用上方标签、下方可编辑下拉框，右侧带"选择"按钮，可手动选择 `.pt` 模型。
- 验证页“图片尺寸”放在 `IoU` 后面，使用可编辑下拉框，内置 `640`、`960`、`1280` 三个候选值，同时允许手动输入其他尺寸；该值必须实际传递给检测推理的 `imgsz` 参数。
- 不显示"检测源配置"标题；模型路径、检测模式、输入源等左侧控件必须有统一内边距，不能贴面板边缘。
- 置信度与 IoU 放在同一行；置信度输入框左侧要与选择模型输入框左侧对齐，IoU 与右侧输入框距离要自然。
- 源图和检测结果图与面板边框之间要保留内边距，不能贴边。
- 源图和检测结果图上方要有批量检测结果工具栏，按钮顺序为：上一张、下一张、第一张、最后一张、列表、打开保存文件夹，并显示计数。
- 检测结果详情表不显示"序号"列，只显示类别、置信度、坐标、尺寸、角度。
- 批量检测时保持右侧显示第一张图片，不随进度切换，后台持续检测，前端维持在第一张；上一张/下一张只在已经检测完成的结果中切换显示，不得触发重新检测。
- 选择"图片/视频文件夹"时，检测按钮文字为"批量检测"；选择"图片/视频"时，检测按钮文字为"开始检测"。
- 选择"摄像头"时，右侧结果区改为实时预览语义，不进入批量结果列表；上一张、下一张、第一张、最后一张和列表按钮都不应用于摄像头历史帧切换，计数区域显示"实时预览"。
- 选择"数据集验证"时，开始按钮文字为"开始验证"，左侧显示 `数据集 YAML`、`选择验证源`、`输出文件夹` 和 `打开保存目录`；右侧图片区/结果表隐藏，仅显示"验证日志"。
- 摄像头检测日志需持续显示实时帧率（FPS）。
- 摄像头在无检测目标时，检测结果图仍必须继续显示当前摄像头画面，只是不叠加检测框，严禁出现黑屏或空白结果图。
- 批量检测顺序必须使用自然数字排序，例如 `1.jpg, 2.jpg, 3.jpg, 10.jpg, 100.jpg`。
- 点击"列表"应直接读取当前输入源文件夹或单文件，列表只显示文件名，不显示序号；列表窗口初始尺寸为 `320 x 520`，最小尺寸为 `200 x 200`，底部带"搜索文件名"输入框。
- 列表选择已检测完成的图片/视频时，应立即跳转显示对应缓存结果；选择未检测文件只更新当前选择，不自动触发检测。
- 检测和训练均只允许一次启动，按钮在运行期间禁用，任务结束后恢复。

检测源配置约定：

- 检测模式是下拉框，包含"图片/视频文件夹"、"图片/视频"、"摄像头"和"数据集验证"，默认仍为"图片/视频文件夹"。
- 选择"图片/视频文件夹"时，`输入源` 使用可编辑下拉框，直接提供 `全部图片`、`训练图片`、`验证图片`、`测试图片` 四个选项，右侧保留"选择"按钮可改为自定义图片文件夹。
- 选择"图片/视频文件夹"时，若输入源选择 `全部图片`，读取软件设置中的图片路径（默认项目根目录 `images/`）；若选择 `训练图片`、`验证图片`、`测试图片`，分别读取 `data/train/images`、`data/val/images`、`data/test/images`；若用户手动选择了自定义图片文件夹，则优先使用该自定义目录。
- 选择"图片/视频"时显示单个图片或视频文件选择。
- 选择"摄像头"时用摄像头下拉框替换输入源。
- 选择"数据集验证"时显示 `数据集 YAML` 与 `选择验证源`，开始验证时仅临时改写 `data.yaml` 中的 `val:` 指向；待验证进程退出后必须恢复原文件。
- 检测模式右侧不要放路径选择图标。
- 不显示"检测控制"标题。
- 检测按钮区仅保留"开始检测 / 批量检测"与"暂停"，不要恢复"停止"按钮。

### 系统设置

系统设置页面显示 Pixi 环境、Torch/CUDA 版本、GPU、显存、CPU、内存、磁盘、模块检测结果。系统信息区域采用白色外框 + 灰色内卡样式（仿照参考图片），2x4 网格排列，每 0.5 秒自动刷新一次。

系统设置页面还包含：

- 系统信息区域放在页面最上方。
- 系统信息下方使用同一行放置以下控件：`训练前显示自定义命令框`、`显示配置解释符号`、`训练模型显示 last`、`恢复默认设置`。
- "训练前显示自定义命令框"开关，控制训练页是否弹出命令编辑对话框。
- "显示配置解释符号"开关，控制是否显示字段名后的 `ⓘ`。
- "训练模型显示 last"开关，控制模型验证页“选择模型”下拉框是否显示训练结果中的 `last.pt`；默认关闭，关闭时只显示 `best.pt`。
- "恢复默认设置"按钮，点击后将当前项目的设置恢复到代码默认值，但保留当前项目目录不变。

关于"显示配置解释符号"开关：

- 关闭时只隐藏 `ⓘ`，不要清空 tooltip。
- 关闭后鼠标悬停在字段名称本身，仍应能通过默认 Qt tooltip 延迟看到解释。
- 不要再实现"关闭后完全无解释"或需要额外自定义浮层的方案。

### 窗口与控件规范

- 程序图标：项目根目录 `icon.svg`，同时在 `scr/assets/` 中放置 `app_icon.png` 和 `app_icon.ico`。窗口标题栏和导航栏左侧均显示图标。
- 程序默认启动尺寸为 `1100 x 770`，最小窗口尺寸为 `800 x 600`。关闭窗口时不要持久化用户拉大的窗口尺寸，避免下次启动又变大；应保持配置里的 `window_width=1100`、`window_height=770`。
- 五个主页面当前约定在启动时预创建，以减少首次切换到数据处理、模型训练等页面时的卡顿；不要恢复为点击后才懒加载创建。
- 顶部导航按钮文字使用加粗大号字体，当前约定为 `Microsoft YaHei UI 15 bold`。
- 所有应该选择固定选项的字段都应使用下拉框，不要用只读文本框伪装，例如任务类型、设备、输出方式、保存格式、检测模式、摄像头、优化器等。
- 对需要兼顾常用候选值与自定义输入的字段，应优先使用可编辑下拉框；当前训练页与验证页的“图片尺寸”均采用此方案。
- 勾选项必须是真交互，不能只是展示状态；训练增强勾选应影响训练命令参数。
- 所有路径显示：项目文件夹显示绝对路径，其他路径（图片路径、标注路径、结果路径、模型训练界面、模型验证界面）显示相对路径。模型路径进一步简化（如 `result\train-12\weights\best.pt` -> `train-12\best.pt`）。
- `data/models` 下的模型路径也应显示为项目内相对路径，例如 `data\models\yolo11n.pt`，不要显示绝对路径。
- 所有按钮添加鼠标悬停高亮效果（QPushButton、softButton、QTableWidget::item）。
- 页面级滚动区域和表格不得出现横向滚动条；界面横向宽度应固定在当前窗口可见范围内，通过列宽/布局自适应解决显示问题。
- 训练和检测启动按钮在运行期间禁用，任务结束后恢复。
- 训练控制模块中三个按钮要视觉居中、上下间距一致；"开始训练"按钮为黑字。模型验证页检测按钮区当前只保留"开始检测 / 批量检测"与"暂停"，按钮需保持整齐对齐，不要恢复"停止"按钮。
- 所有只读日志/输出文本框应视为展示控件而不是编辑控件：必须 `readOnly`、`NoFocus`、隐藏文本光标，并保留鼠标选中文本与 `Ctrl+C` 复制能力，避免切页或初始加载时出现输入光标样式残留。
- 模型验证的默认输出目录当前为 `result/gui_val`。
- 模型验证在保存结果图片时，应同时把同名标注保存到本次输出目录下新建的 `labels/` 子目录中；普通框使用 YOLO detect 格式，OBB 使用 8 点格式。

### 数据处理交互细节

标注预览：

- 选择图片文件夹和标注文件夹。
- 自动读取图片并匹配与图片同名的 `.txt` 标注文件。
- 自动显示当前图片，不需要额外点击"预览"。
- 必须提供上一张、下一张。
- 提供与模型验证同款的"列表"按钮；弹窗只显示文件名，支持搜索并可直接跳转到当前图片。
- 预览时应根据标签内容自动识别 `detect` 或 `obb` 格式，不得完全依赖当前全局任务类型。
- 标注框样式应接近 YOLO 官方预览风格：彩色框线、实心标签底色、白色文字；标签位置需尽量贴近无方向框或旋转框本体。

批量重命名：

- 选择文件夹或修改参数后自动执行一次预览。
- 不再提供单独的"预览"按钮，界面保持自动预览。
- 配置区按三列排列，顺序为：图片文件夹、Labelme 标注文件夹、YOLO 标注文件夹；命名前缀、起始编号、编号位数。
- 编号位数使用下拉框，可选 `1-4`，默认 `1`。
- 提供"Labelme 标注文件一并更改"和"YOLO 标注文件一并更改"两个独立勾选项，默认都关闭。
- 勾选对应开关时，与图片同名的 Labelme `.json` 或 YOLO `.txt` 标注文件也改成对应图片名称。
- 预览结果表不显示“原文件名”“新文件名”“图片冲突”“序号”列，而是显示三列：`图片文件状态`、`Labelme 标注状态`、`YOLO 标注状态`。
- 批量重命名预览表的状态单元格内容居中显示；列表弹窗保持普通显示，不做居中对齐。
- 图片重命名遇普通目标名冲突时，应通过临时前缀/临时名称中转后再改到目标名称。
- 如果标注文件夹存在干扰项导致目标标注名冲突，例如图片 `2.jpg` 要改成 `1.jpg`，而标注文件夹同时存在 `1.txt` 和 `2.txt`，应告知用户并取消本次重命名。

## 服务层说明

核心服务接口在 `scr/services/`：

- `settings_service.py`：项目级设置文件加载、保存、默认值合并与恢复默认值；默认路径为当前项目目录 `data/runtime/settings.json`，并维护训练、验证、转换、重命名、压缩等页面的持久化默认值。当前包含 `paths.models_dir`、`training.optimizer`、`features.custom_command_dialog`、`features.distribution_multi_class_mode`、`features.show_last_training_models` 等字段。
- `data/runtime/app_state.json`：应用级最近项目状态文件，当前保存 `last_project_root`，仅用于下次启动时恢复最近一次使用的项目目录。
- `conversion_service.py`：Labelme 转 YOLO、已有 YOLO `.txt` 分组、自动识别类别、类别映射、自定义类别名校验、数据集划分、`data.yaml` 生成，以及转换产物备份。
- `annotation_service.py`：YOLO 标注解析与图像预览绘制；预览时按标签内容自动识别 `detect/obb`，并使用更接近 YOLO 官方的框与标签样式。
- `rename_service.py`：批量重命名预览与执行。
- `resize_service.py`：图片备份、缩放、画布归一化。
- `training_service.py`：训练与导出命令生成，支持优化器参数、HSV 三参数、训练开始前自动修复 `data.yaml` 中未还原的 `val` 路径，以及从 `results.csv` 读取训练曲线数据。
- `detection_service.py`：模型扫描、输入源自然排序、单文件/批量检测源收集、检测结果解析、推理流程，以及结果图片对应 YOLO 标注文件导出。
- 摄像头/视频流的结果图渲染必须显式以当前帧作为底图后再叠加检测结果，不能依赖模型结果对象内部的默认底图回退，避免无目标时出现黑屏。
- `runtime_service.py`：子进程启动、日志转发、停止进程。
- `runtime_service.py`：子进程启动、日志转发、停止进程；Windows 下优先回收训练进程树，并在日志入队前清洗 ANSI/控制字符，避免 GUI 文本框出现终端转义符残留。
- `process_utils.py`：Windows 后台子进程隐藏窗口参数，避免 PyInstaller GUI 程序反复弹出终端窗口。
- `environment_service.py`：pixi、模块、GPU/CPU/内存/磁盘状态检测。

设置文件新增字段：

- `paths.models_dir`：统一模型目录，默认指向 `data/models`。
- `training.optimizer`：优化器选择（auto/SGD/Adam/AdamW/RMSProp）。
- `training.hsv_s`、`training.hsv_v`：HSV 饱和度与明度增强参数，和 `training.hsv_h` 一起由训练页 HSV 勾选项控制。
- `features.custom_command_dialog`：训练前是否弹出自定义命令框。
- `features.distribution_multi_class_mode`：主页“各类别图片分布”是否切换为多类别统计模式。
- `features.show_help_icons`：是否显示字段名后的 `ⓘ`；关闭时只隐藏 `ⓘ`，不移除字段名称上的 tooltip。
- `features.show_last_training_models`：模型验证页“选择模型”下拉框是否额外显示训练结果中的 `last.pt`；默认 `False`，关闭时只显示 `best.pt`。
- `conversion.use_labelme`：记录标注转换页当前是否启用 Labelme 转 YOLO。
- `conversion.backup_yolo_files`：记录标注转换页是否备份本次转换生成的 YOLO 标注与 `data.yaml`。
- `conversion.class_name_mappings`：记录 Labelme 类别名到 YOLO 类别名的映射关系。
- `rename.prefix`、`rename.start_index`、`rename.padding`、`rename.include_labelme`、`rename.include_yolo`：记录批量重命名页当前配置。
- `image_resize.backup_enabled`：记录图片压缩页是否备份原始图片。
- `features.resize_output_mode`：记录图片压缩页的输出方式。
- `validation.source_scope`：记录模型验证页当前选择的固定输入源/验证源（`全部图片`、`训练图片`、`验证图片`、`测试图片`）。

## 打包说明

推荐分发形式为 PyInstaller `onedir` 绿色版，不建议优先制作单文件 exe。原因是本项目包含 PySide6、OpenCV、Ultralytics、Torch/CUDA 等大体量依赖，单文件模式启动慢且更容易遇到临时目录和杀毒误报问题。

打包命令：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release -Clean
```

开发联调时可使用更快的开发快包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File installer\打包程序.ps1
```

如需继续生成 Inno Setup 安装包，可在完成 `dist/YOLOTool/` 构建后使用：

```powershell
ISCC installer\yolo_tool.iss
```

当前 `installer/打包程序.ps1` 不再生成 `build_log.txt`。

打包后的目录结构约定：

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

开发快包输出到 `dist/YOLOTool-dev/`，用于本地快速验证 GUI 启动、训练入口和检测入口，不覆盖正式版目录。

当前打包体系约定：

- `installer/yolo_tool.iss`：Inno Setup 安装包脚本。
- `installer/YOLOTool.spec`：统一的 PyInstaller spec，通过环境变量区分正式版与开发快包。
- `installer/build_windows.ps1`：仅负责 PyInstaller 打包，支持 `release/dev` 两种模式。
- `installer/打包程序.ps1`：一键串联 PyInstaller 与 Inno Setup。
- `installer/hooks/`：用于压制无关 PyInstaller 探测噪声的自定义 hooks。

当前不再使用对 `torch`、`PySide6` 等大包的 `collect_all(...)` 全量扫描；原因是它会显著拖慢打包，并制造大量与本项目无关的误报。

已知仍可能出现但当前可接受的打包日志噪声包括：

- `triton not found`
- `Hidden import "tzdata" not found`
- `Hidden import "scipy.special._cdflib" not found`
- `Ignoring /usr/lib64/libgomp.so.1 ... only basenames are supported with ctypes imports`

这些日志目前不影响 GUI 启动、训练入口或检测入口；若后续出现真正的运行时缺模块，再按实际功能回补依赖，不要为了“清空所有 warning”恢复全量扫描。

`data/models/`、`data/runtime/`、`images/`、`labels/`、`result/` 都是 exe 同级的项目工作目录。CUDA 版打包后目标机器不需要 Python/pixi，但仍需要兼容的 NVIDIA 驱动。

## 测试说明

当前测试覆盖：

- 设置加载与深合并。
- 当前项目配置恢复默认值。
- 转换配置校验。
- Labelme OBB 转换。
- Labelme line 转 OBB。
- Detect bbox 转换。
- 已有 YOLO `.txt` 标注分组。
- Labelme 类别自动识别与 YOLO 数字类别自动命名。
- YOLO 标注读取与预览渲染。
- 批量重命名预览、执行、冲突检测。
- 图片压缩递归扫描、自然排序、可选备份与保持目录结构的 960 x 960 输出。
- 训练命令生成。
- 训练命令编辑弹窗尺寸与命令编辑行为。
- 模型扫描与检测结果归一化。
- `data/models` 统一模型目录、训练命令模型路径解析、配置持久化与重启恢复。
- 模型验证页“选择模型”下拉框对 `best.pt / last.pt` 的显示开关与自动回退行为。
- 项目级 `data/runtime/settings.json`、`data/runtime/app_state.json` 最近项目恢复、项目目录切换后配置重载、PyInstaller 脚本入口、隐藏后台子进程窗口。
- 训练停止后按钮状态恢复、停止期日志噪声抑制，以及 GUI 日志 ANSI 控制符清洗。
- 摄像头实时预览、FPS 日志与“无目标时不黑屏”回归。
- Qt 应用入口和核心功能迁移验证。
- 图标资源、主页网格布局与滚动、主页图表模块、主页标注数量统计、多类别图片分布模式、相对路径、训练曲线、悬停高亮、防重复启动、自定义命令框、系统信息样式、训练页系统状态自动刷新、检测列表与批量检测行为等功能验证。
- 转换页默认任务类型与下拉顺序、训练页默认基础模型与训练参数、系统设置页系统信息与控制区布局等默认界面行为验证。
- 配置项占位文本、方案 B 的 `ⓘ + tooltip` 解释方式、解释符号显示开关、只读日志框无焦点且支持 `Ctrl+C` 复制、主页面预创建减少首切卡顿等交互验证。

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
- Qt GUI 可以继续按 `scr/ui/views/`、`scr/ui/widgets/` 和 `scr/ui/dialogs.py` 这一层次拆分，避免页面文件再次膨胀；主页图表模块保持在 `scr/ui/widgets/charts.py`。
- 训练曲线已从 `results.csv` 读取数据绘制，当前只保留关键曲线与 Epoch 摘要；后续增加指标时不要让标题区重新拥挤。
- GPU 利用率优先通过 `nvidia-smi` 获取；如果不可用，界面显示"待检测"即可。
- 对任何会改文件的功能，继续坚持"先预览，再执行"。

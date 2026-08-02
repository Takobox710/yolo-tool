# 数据处理规格

左侧子菜单包含：

- `🔄 数据集划分`
- `🖼 标注预览`
- `🏷 批量重命名`
- `📦 图片压缩`
- `🗂️ 模型格式转换`

数据处理页左侧导航当前界面约定：

- `数据集划分`、`标注预览`、`批量重命名` 和 `数据标注` 的图片目录/图片文件夹共用 `paths.images_dir`；`数据标注`、`数据集划分` 和 `批量重命名` 的 Labelme 标注目录共用 `paths.annotations_dir`；`标注预览` 与 `数据集划分` 的 YOLO 标注目录共用 `paths.labels_dir`。任一共享字段修改后，其他页面必须立即同步，不需要重启程序。

- 左侧栏标题显示为 `数据处理`，标题居中显示。
- 左侧栏整体宽度、外边距、内边距、标题与分隔线位置应尽量与数据标注页左侧栏对齐，视觉边缘保持重合。
- 左侧导航按钮采用“图标 + 文本”形式；当前使用与按钮文字直接组合显示的 emoji 图标，不改为 Qt 原生标准图标。
- 左侧五个入口的文字起始位置应尽量保持整齐一致，不要因图标方案变化造成明显参差。
- 左侧导航按钮保持与数据标注页相近的深色 hover / 选中高亮样式。

数据集划分支持（包含标注转换）：

- `Labelme 转 YOLO 并划分数据集`：读取 Labelme `.json`，转换为 YOLO 标签并执行 train/val/test 分组。
- `YOLO 原生数据集划分`：读取已有 YOLO `.txt` 标注，只执行 train/val/test 分组、图片与标签复制、`data.yaml` 生成和 labels 汇总。
- `detect`、`obb` 与 `seg`
- `seg` 输出每个实例一行的 YOLO 多边形标签：类别 ID 后跟至少三个归一化坐标点。
- `oriented_rectangle` 转 OBB
- `rectangle`、`oriented_rectangle`、`circle` 和 `polygon` 均可转换为 Seg 多边形；`line` 在开启线宽时按半宽扩展为区域。
- 自动划分 `train/val/test`
- 生成 `data.yaml`
- 汇总 `labels`
- 类别名称不再由界面手动输入。Labelme 模式下从 `.json` 的 `label` 自动识别类别，按首次出现顺序生成 class id；YOLO `.txt` 分组模式下若没有类别名称来源，则按数字 id 自动显示为 `class_0`、`class_1` 等。
- 支持“备份标注文件”开关；开启后，每次转换生成的 YOLO 标注文件和 `data.yaml` 都会备份到 `data/old/backup-时间戳/` 下独立文件夹，支持多次共存。
- “备份标注文件”在 Labelme 和 YOLO 原生两种模式下均可使用。
- 标注转换仅在对应位置实际产生新文件时才创建目录：未开启“备份标注文件”时不创建 `old/`；某个 split 本次没有图片与标签输出时不创建对应的 `train/`、`val/` 或 `test/` 目录，`data.yaml` 也不应保留指向该空 split 的条目。
- 支持“自定义类别名称”窗口，可把多个 Labelme 类别通过英文逗号映射到同一个 YOLO 类别，并在保存时校验是否引用了不存在或重复的 Labelme 类别。
- YOLO 原生模式下隐藏“自定义类别名称”按钮；Labelme 模式下可打开并保存类别映射。

数据集划分页面布局与交互约定：

- 页面顶部采用类似模型训练页的左右两张卡片布局。
- 左侧卡片标题为"数据集划分配置"，上方 2x2 放置图片目录、Labelme 标注目录、YOLO 标注目录、数据集输出目录；下方放置"备份标注文件"和"自定义类别名称"。
- 右侧卡片标题为"转换参数"；"模式选择"独占一行并位于"任务类型"之前，随后按从左到右、从上到下排列任务类型、训练、验证和测试。
- "模式选择"下拉框固定包含"Labelme 转 YOLO 并划分数据集"和"YOLO 原生数据集划分"两项。
- 任务类型下拉框默认值为 `detect`，下拉顺序固定为 `detect`、`obb`、`seg`。
- YOLO 原生模式下任务类型字段显示为禁用态，文字变灰且不可选择；Labelme 模式下恢复可选。
- 默认数据集划分比例为 `train=0.8`、`val=0.2`、`test=0.0`。
- 解释方式固定采用方案 B：直接在字段名称后追加 `ⓘ`，tooltip 继续挂在对应名称控件本身，不要再实现独立解释图标控件、悬浮说明层或自定义气泡。
- 图片目录、Labelme 标注目录、YOLO 标注目录、数据集输出目录这四个路径字段不要显示 `ⓘ`。
- 数据集划分页仅以下项目显示 `ⓘ`：模式选择、`备份标注文件`、任务类型、训练、验证、测试。
- 解释只通过鼠标悬停 tooltip 显示，不要在界面上额外显示说明段落。
- 不要显示"开启时读取同名 json 并转换..."、比例合计提示、"OBB + Labelme 直线标注..."等常驻说明文字；这些内容如需保留，只能放入 tooltip。
- Tooltip 应关闭动画或采用更快的显示方式，避免鼠标悬停后等待过久。
- Labelme 的 `line` 标注转换继续使用项目数据集设置中的线宽，不在数据集划分参数区单独编辑。
- 随机种子暂不在数据集划分页面显示，划分时继续读取项目设置中的 `dataset.random_seed`。
- 转换结果输出需直观展示数据集划分、总体统计、类别统计、跳过/未知标签和输出路径；类别相关数据只在结果输出中展示。

图片压缩支持：

- 图片压缩的源图片目录使用独立的 `image_resize.source_dir`，修改后不改变上述共享图片目录。

- 可选是否备份原始图片，默认不备份。
- 以“画布尺寸”作为长边对齐目标，按长边等比缩放。
- 默认创建 `960 x 960` 白色或黑色画布。
- 将缩放后的图片居中粘贴到画布。
- 递归扫描图片目录及其子目录中的图片，并按自然数字顺序预览与处理。
- 输出目录与备份目录都应保持与原图片目录一致的相对目录结构。
- 动作区至少提供 `预览压缩`、`执行压缩` 与 `打开结果文件夹` 三个按钮；`打开结果文件夹` 固定打开当前“输出目录”字段对应的位置，不依赖是否刚执行过压缩。

## 数据集划分补充

- 类别名称直接读取当前项目数据标注页“管理类别”保存的 `dataset.class_names`，不以当前标注目录扫描结果替代已管理类别。
- “自定义类别名称”映射表左侧行号从 `0` 开始；映射设置仍保存到当前项目设置。
- 预览和执行前均按训练、验证、测试比例划分数据，并在日志中显示类别统计和输出信息。
- 数据处理页面内容区随窗口和全屏后的可用宽度自动扩展，滚动仅用于承载超出高度的内容。

## 模型格式转换

- 数据处理页新增“模型格式转换”工具，保留 ONNX、TorchScript、OpenVINO、TensorRT 和 NCNN 五种格式入口；不再显示独立的 `SAM2 ONNX` 格式项，选择 ONNX 后按文件名识别 YOLO 或 SAM2/SAM2.1 checkpoint。
- 默认只扫描当前项目 `result/**/weights/*.pt`；`data/models/` 中的基础模型和 SAM checkpoint 不主动出现在转换列表中，仍可通过浏览选择其他 `.pt` 文件。
- ONNX + YOLO 支持 FP32/FP16/INT8、图简化、动态 Batch/高度/宽度、NMS、opset、INT8 校准和量化后验证；ONNX + SAM2/SAM2.1 支持三种精度、图简化、校准和验证，但固定 batch=1、输入 1024、单点提示并隐藏动态轴和 NMS。
- TorchScript 支持 FP32/FP16、batch、统一动态输入、NMS 和 TorchScript 优化；OpenVINO 支持 FP32/FP16/INT8、batch、统一动态输入、NMS 和 NNCF 校准；TensorRT 支持三种精度、batch、统一动态输入、NMS、中间 ONNX 简化、workspace 和校准；NCNN 仅支持 FP32/FP16 与 batch。
- TorchScript 优化要求 CPU，不能与 FP16 GPU 导出同时启用；TensorRT 动态输入或动态输入加 NMS 时 batch 必须大于 1，避免触发 Ultralytics 导出器的形状约束。
- INT8 配置区只在选择 INT8 后显示，校准数据统一接受 `dataset.yaml` 或图片目录，并按校准样本上限取样；页面可按需下载并缓存 COCO128 通用校准集，也可继续选择项目自定义图片。SAM2/SAM2.1 ONNX 当前只提供 FP32/FP16，因 ORT 静态 INT8 在真实点提示下会破坏掩膜质量而不显示 INT8；YOLO、OpenVINO 和 TensorRT 仍按各自后端提供 INT8。
- 默认值为 FP32、batch=1、图简化开启、动态轴关闭、NMS 关闭、校准样本 300、验证样本 16，NMS 默认 `conf=0.25`、`iou=0.45`、`max_det=300`。
- 默认输出根目录为 `data/models/model_exports/`，每个模型使用独立子目录。YOLO 精度产物名为 `model_fp32.onnx`、`model_fp16.onnx`、`model_int8.onnx` 等；SAM2 产物目录名为 `model_sam2_onnx_fp32/`、`model_sam2_onnx_fp16/` 或 `model_sam2_onnx_int8/`。
- 模型格式转换页默认采用 ONNX 基线的 `3:2` 等高双卡片布局；当基础配置第三行的格式选项空间不足时，左侧基础配置卡片自适应扩大，最大不超过 `2:1`。`基础配置` 固定放置源模型、输出目录、目标格式和导出精度；`推理参数` 固定放置输入尺寸、Batch、Conf、IoU 和最大检测数。所有格式复用同一组固定控件，不支持的公共字段保留位置并禁用，最终不会传入导出命令。两卡片等高排列，`基础配置` 被较高卡片拉伸时，额外纵向空间按标题、各配置行与上下边框之间的空隙平均分配，而不是全部堆在卡片底部。
- 两张公共配置卡片的固定字段下方直接承载按格式变化的专属配置。基础配置卡片继续放置格式选项、NMS、类别无关和动态输入；ONNX 下简化、导出 NMS、类别无关位于同一行，TorchScript 下导出 NMS、类别无关、TorchScript 优化、动态输入位于同一行，TensorRT 下导出 NMS、简化 ONNX、类别无关、动态输入位于同一行。OpenVINO 的动态输入也放在该基础配置行；推理参数卡片在最大检测数右侧放置 ONNX opset 或 TensorRT workspace，ONNX 和 NCNN 的动态输入保留原位置，并继续放置 INT8 校准与验证等选项。ONNX、TorchScript、OpenVINO、TensorRT 按各自能力显示对应字段，NCNN 没有专属项时只保留两张公共卡片。配置区统一滚动，预览、转换、停止、打开目录和附加包操作保持独立可达；切换格式时在当前会话内保留各格式专属字段。
- “预览转换”显示源模型、目标产物、运行环境、能力状态和覆盖风险；目标已存在时必须在执行前确认，只有新产物完整生成后才替换旧结果。
- 转换过程提供结构化实时日志、停止和打开结果文件夹；运行期间禁用模型、格式、参数、环境安装和开始操作，程序退出时复用 `export_handle` 停止子进程。
- YOLO 的 ONNX、TorchScript 与 SAM2 ONNX 使用基础安装环境；SAM2 ONNX 导出依赖 PyTorch、SAM2、ONNX、ONNXSlim、ONNXScript 和 ONNX Runtime。OpenVINO INT8 额外依赖 NNCF。GPU 发布版由 `release-gpu` 提供 GPU ONNX Runtime，OpenVINO、NNCF、TensorRT 和 NCNN 通过模型转换附加包提供；CPU 一体式安装器直接内置 OpenVINO、NNCF、NCNN、PNNX，TensorRT 始终不可用；开发态默认环境复用 `release-gpu` 的完整能力。
- GPU 模型转换附加包发布名为 `YOLOTool_ExtraEnv_<版本>.7z`，包含 OpenVINO、NNCF、NCNN/PNNX 和 TensorRT 运行库，同时兼容同结构 `.zip`，不执行第三方安装器；CPU 发布不生成或安装 ExtraEnv，已安装旧版本时 GPU 必须先确认替换。
- 附加包安装显示阶段进度，拒绝路径穿越、绝对路径、符号链接、错误平台、协议不匹配、缺失文件和未登记文件；7-Zip/Zip 解压错误会使安装失败并继续使用旧版本，成功后只保留当前版本和一个上一版本。
- 附加环境安装到当前程序目录的 `_internal/extensions/model-export-runtime/`，基础环境升级时保留该目录；旧版本位于 `%LOCALAPPDATA%/YOLOTool/` 时在升级过程中迁移到新位置。
- GPU 未安装扩展时选择 OpenVINO、TensorRT 或 NCNN 会明确提示缺少模型转换环境包；无 NVIDIA GPU 时 OpenVINO 和 NCNN 仍可用，TensorRT 显示硬件不可用。CPU 冻结环境检测到内置 OpenVINO/NCNN/PNNX 时直接显示内置能力，TensorRT 明确提示 CPU 版不包含该后端。
- TensorRT `.engine` 受 GPU、驱动和 TensorRT 版本约束，不保证跨机器通用；TorchScript FP16 在无 GPU 时不可用，TensorRT 在无 NVIDIA GPU 时不可用。

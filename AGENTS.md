# AGENTS.md — YOLO 本地训练工作台

## 项目定位

本项目是一个 Windows 本地可视化 YOLO 训练工作台，使用 **Python 3.12 + PySide6 / Qt** 开发桌面 GUI。

定位是“通用 YOLO 优先，同时兼容焊缝 OBB 项目”：

- 支持 YOLO `detect` 与 `obb`。
- 默认兼容焊缝识别习惯配置，例如类别 `weld`、Labelme 转 YOLO-OBB、直线标注扩展为旋转矩形。
- 使用本项目本地 `pixi` 环境，不依赖外部 `yolo-weld` conda 环境。

## 不可违反约束

- 所有项目代码放在 `src/` 目录下。
- 测试代码放在 `src/tests/` 目录下。
- UI 测试按 `src/tests/ui/<domain>/` 分目录维护；服务层测试按 `src/tests/services/<domain>/` 分目录维护；结构围栏测试放在 `src/tests/architecture/`。
- 不要把 `.pixi/`、`dist/`、`build/`、缓存目录、模型训练产物加入 git。
- 需要提交 git 时，必须完成所有任务后再做一次总提交，不要中途零散提交。
- 修改任何会影响行为、结构、入口、打包方式、设置字段、测试组织、页面布局或用户操作流程的代码后，必须同步检查并更新受影响文档；至少包括 `docs/spec/*.md`、`docs/architecture.md`、`docs/packaging-windows.md`、`README.md` 与 `docs/code-inventory.md` 中相关文件。禁止只改代码不更新文档。
- 每次完成一批可感知改动后，必须同步更新根目录 `CHANGELOG.md`；日常开发阶段只允许在文件最上方的 `# [Unreleased] > ## 待提交改动` 顶部追加简短记录，格式固定为 `- YYYY/MM/DD HH:mm：本次改动`，最新记录必须放最前面。后续任何 AI 在准备 git 提交说明、GitHub 提交说明或版本更新说明前，必须先阅读该文件，再结合当前 `git diff` 生成总结，不能只依赖当前对话上下文。
- 如果编译或测试错误连续出现 5 次仍未解决，必须立即停止并向人类报告，严禁盲猜死循环。
- 不改变公开入口：`pixi run app`、`pixi run test`、`pixi run check`、`python -m src.main`。
- 打包后训练/导出/验证仍通过 `YOLOTool.exe --yolo-train / --yolo-export / --yolo-val` 进入 `src/train_cli.py`。

## 目录职责地图

```text
yolo_tool/
├── AGENTS.md                  # AI 维护入口文档
├── pixi.toml                  # 环境和任务命令
├── docs/
│   ├── architecture.md        # 架构、服务层、设置字段、维护建议
│   ├── packaging-windows.md   # Windows 打包说明
│   └── spec/                  # 页面与功能规格
├── installer/                 # PyInstaller / Inno Setup 打包脚本
└── src/
    ├── main.py                # GUI 与隐藏 CLI 统一入口
    ├── train_cli.py           # 打包后训练、导出、验证入口
    ├── services/              # 可测试业务逻辑
    ├── ui/                    # Qt UI、页面、控件和 worker
    ├── runtime/               # 源码内默认配置参考
    ├── assets/                # 应用图标资源
    └── tests/                 # pytest 测试（architecture / services / ui / integration）
```

## 文档索引

- 架构与服务边界：`docs/architecture.md`
- 主页规格：`docs/spec/home.md`
- 数据标注规格：`docs/spec/annotation.md`
- 数据处理规格：`docs/spec/data-processing.md`
- 模型训练规格：`docs/spec/training.md`
- 模型验证规格：`docs/spec/validation.md`
- 系统设置规格：`docs/spec/settings.md`
- Windows 打包：`docs/packaging-windows.md`
- 版本更新与改动记录：`CHANGELOG.md`

改功能前先读对应 spec；改共享逻辑前先读 `docs/architecture.md`。

## AI 修改流程

1. 先用 `rg` / `rg --files` 找相关代码、测试和规格文档。
2. 读对应 `docs/spec/*.md` 与现有测试，确认用户请求是否改变既有约定。
3. 优先修改服务层中的可测试逻辑，再让 UI 调用服务层。
4. 保持公开类名与入口兼容，例如 `AnnotationPage`、`ValidatePage`、`TrainPage`、`HomePage`。
5. 修改后同步更新受影响文档；如果改动会影响用户可见行为、维护结构、入口、打包、设置字段或测试组织，必须同时更新根目录 `CHANGELOG.md` 的 `Unreleased > 待提交改动`，并把最新记录插到最上方。
6. 修改后至少运行 `pixi run check`；涉及行为变化时运行相关测试，收尾前优先运行 `pixi run test`。
7. 如果连续 5 次编译或测试失败仍无法解决，停止并报告失败命令、错误摘要和已尝试方案。

## 分层规则

- `src/services/` 不得导入 `src/ui/`。服务层只能依赖标准库、第三方库、其他服务或独立模型模块。
- UI 页面负责布局、控件状态和用户交互；复杂业务规则、文件读写、数据转换应放到服务层。
- `src/ui/features/*/page.py` 只做页面装配；页面专属复杂逻辑继续拆到对应功能包子模块。
- `src/ui/features/annotation/canvas/widget.py` 只保留 Qt 入口、信号与状态挂接；交互、渲染、几何、编辑、右键菜单继续拆到 `canvas/` 子模块。
- `src/ui/shared/page_base.py` 只保留真正跨页面复用的基础能力，不要塞入页面专属逻辑。
- 后台子进程必须通过 `src/services/runtime/` 中的统一入口与隐藏窗口参数启动，避免 Windows GUI 程序弹出终端窗口。
- 训练与检测只允许一次启动，运行期间按钮禁用，任务结束后恢复。
- GUI 日志写入前必须清洗 ANSI/控制字符。
- `src/services/<domain>/__init__.py` 只能做轻量导出，不得塞实现。

## 设置与路径规则

- 当前项目配置保存到当前项目目录 `data/runtime/settings.json`。
- 应用级最近项目状态保存到应用根目录 `data/runtime/app_state.json`。
- `src/runtime/settings.json` 只作为源码内默认配置参考，不作为当前项目唯一落点。
- 程序启动默认进入主页，不按 `last_page` 自动恢复页面。
- `data/models/` 是统一基础模型目录；训练和验证模型列表优先使用该目录。
- UI 中项目文件夹显示绝对路径，其他项目内路径尽量显示相对路径。

## 常用命令

```powershell
pixi run app
pixi run test
pixi run check
pixi run python -m src.main
```

Windows 绿色版打包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release
```

开发快速打包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

一键打包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\打包程序.ps1
```

## 测试重点

- 设置加载、深合并、恢复默认值、最近项目恢复。
- Labelme/YOLO 转换、类别识别、类别映射、数据集划分、备份。
- 数据标注的 Labelme 读写、YOLO 同步导出、画布绘制与选择、AI 预标注。
- 训练命令生成、模型目录解析、停止流程、日志清洗。
- 验证页模型扫描、单文件/批量/摄像头/数据集验证、结果保存、`best.pt / last.pt` 开关。
- Windows 打包入口、隐藏后台子进程、图标资源。

## 维护建议

- 对任何会改用户文件的功能，坚持“先预览，再执行”。
- 重构时保持导入兼容，优先做小步移动和 re-export，再逐步收紧边界。
- 不为了清空 PyInstaller warning 恢复大包 `collect_all(...)` 全量扫描；只按真实运行缺失补依赖。
- 新增功能先补服务层测试，再接 UI。
- 需要准备 git 提交说明、GitHub 提交说明或软件版本更新说明时，先阅读根目录 `CHANGELOG.md`，再结合 `git diff` 汇总；不要只根据当前对话记忆生成说明。
- `CHANGELOG.md` 的使用方式固定为：文件最上方始终保留 `# [Unreleased]`，其中 `## 待提交改动` 只维护当前尚未提交的日常记录，按时间倒序排列；准备 git 提交时，先检查最近一批待提交改动里是否存在同一主题的连续修订或覆盖关系，若后面的记录已经覆盖前面的记录，必须先归并成最终有效的 1 条或若干条结果，不能机械逐条照抄中间过程；然后再整理成一个提交标题，并将这批归并后、去除时间前缀的改动列表直接写入 `git commit` 的提交描述（body）；提交完成后从 `## 待提交改动` 删除这些项，并追加到 `# [Unreleased] > ## 提交记录` 中，格式为 `## 提交标题（commit_hash）` 加去除时间前缀后的原始改动列表，也就是直接保留每条改动描述本身；准备软件版本更新时，在 `# [Unreleased]` 下方新增 `# [版本号] - YYYY-MM-DD` 版本块，先写该版本的高层总结，再写 `## 本版本提交记录`，并把本次版本包含的全部 Git 提交记录整体归档到这里；发版后新的未提交改动继续追加到最上方的 `# [Unreleased] > ## 待提交改动`。


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
- 需要提交或推送改动时使用 `github-push-workflow` skill；普通改动完成一批任务后只做一次总提交，不要中途零散提交；版本归档按 skill 明确的预提交例外执行。
- 修改任何会影响行为、结构、入口、打包方式、设置字段、测试组织、页面布局或用户操作流程的代码后，必须同步检查并更新受影响文档；至少包括 `docs/spec/*.md`、`docs/architecture.md`、`docs/packaging-windows.md`、`README.md` 与 `docs/code-inventory.md` 中相关文件。禁止只改代码不更新文档。
- 每次对话产生改动后都必须检查根目录 `CHANGELOG.md`；用户可见行为、维护结构、入口、打包、设置字段、测试组织或版本结果变化必须记录。`# [Unreleased] > ## 待提交改动` 的每条记录必须使用实际本地时间，严格采用 `- yyyy/MM/dd HH:mm：改动说明`，最新记录置顶；移入 `## 提交记录` 时删除时间前缀。
- 如果编译或测试错误连续出现 5 次仍未解决，必须立即停止并向人类报告，严禁盲猜死循环。
- 不改变公开入口：`pixi run app`、`pixi run test`、`pixi run check`、`python -m src.main`；`pixi run app-qt` 只是同一 GUI 入口的兼容别名。
- 打包后训练/导出/验证仍通过 `YOLOTool.exe --yolo-train / --yolo-export / --yolo-val`，由 `src/bootstrap/cli_dispatch.py` 转发到 `src/train_cli.py`。

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
    ├── app.py                # GUI 应用装配
    ├── main.py                # GUI 与隐藏 CLI 统一入口
    ├── train_cli.py           # 打包后训练、导出、验证入口
    ├── bootstrap/             # CLI 分发与运行上下文
    ├── devtools/              # 发布包、伴随包与开发工具
    ├── services/              # 可测试业务逻辑
    ├── ui/                    # Qt UI、页面、控件和 worker
    ├── runtime/               # 源码内默认配置参考
    ├── shared/                # 跨服务和 UI 的共享类型与路径
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

## GitHub 推送流程 Skill

- 本项目使用 `github-push-workflow` skill 处理 Git 提交、GitHub 推送、CHANGELOG 归并、普通提交哈希回填和 `X.Y.Z` 版本归档；准备提交前必须先阅读根目录 `CHANGELOG.md`，再结合当前 `git diff` 汇总，不能只依赖对话记忆。
- 完成一批普通改动后只创建一次总提交，只纳入当前任务相关文件；已有用户改动、无关文件、缓存、构建产物和训练产物不得擅自纳入。版本归档需要预提交时，以 skill 的版本归档流程为例外。
- 每次对话产生改动后都要检查 `CHANGELOG.md`。用户可见行为、维护结构、入口、打包、设置字段、测试组织或版本结果变化必须记录；只运行测试/检查、阅读分析、格式修正、空白或注释调整，以及不改变行为的内部整理通常不单独记录。
- CHANGELOG 与提交说明只写具体的最终行为、修复、维护规则或发布结果；禁止单独写“同步更新架构、规格、README、代码清单”“补充回归测试”“测试通过”等泛化清单，除非该条目同时说明了具体且有维护价值的变化。
- 普通 Git 提交的 body 必须逐字等于归并后 CHANGELOG 提交条目下的正文，包含相同的项目符号、顺序和具体内容；不得为了提交而额外压缩、改写或补充摘要。提交前后必须核对两者一致；不一致时必须停止提交并修正。
- 普通提交默认推送当前分支的远程跟踪分支；用户明确禁止推送、远程分叉或无法确认改动归属时必须停止，不得强制推送、自动创建 tag/Release 或修改远程设置。
- 用户明确调用该 skill 后，可以直接要求“提交改动”或“更新项目版本为 `X.Y.Z`”；不要求先执行初始化对话。第一次在项目中使用时，skill 负责补齐本节规则和 `CHANGELOG.md` 初始结构。
- 普通提交的稳定哈希只允许直接回填到本地工作树，不为回填创建第二次提交或推送；版本归档提交自身不写入 `CHANGELOG.md`，也不回填该提交哈希。
- skill 保留完整执行顺序和命令细节；本文件必须保留时间格式、CHANGELOG 与 Git body 一致性、低价值总结过滤、普通提交推送安全边界和版本归档例外等关键项目约束。

## 版本发布适配

- 用户要求“更新项目版本为 `X.Y.Z`”时，除更新 `CHANGELOG.md` 版本块外，必须同步更新程序版本源 `src/__init__.py` 的 `APP_VERSION` 与安装器版本源 `installer/yolo_tool.iss` 的 `MyAppVersion`。
- 同步检查并更新受影响的版本断言、发布脚本、安装器配置和文档；`installer/package_windows.ps1` 会从 `APP_VERSION` 传递安装器版本，但 `yolo_tool.iss` 的默认兜底值仍必须保持一致。
- 版本归档提交前必须执行完整正式打包：`pwsh -NoProfile -ExecutionPolicy Bypass -File installer\package_windows.ps1 -Clean -BuildBaseRuntimeModels -BuildModelExportRuntime`。该命令生成程序安装器、基础环境包和附加环境包；打包失败时停止版本归档，不提交、不推送，并报告失败原因。
- 基础环境、运行时协议和附加环境包版本只有在对应内容或协议实际变化时才更新，不因程序版本变更机械递增。

## AI 修改流程

1. 先用 `rg` / `rg --files` 找相关代码、测试和规格文档。
2. 读对应 `docs/spec/*.md` 与现有测试，确认用户请求是否改变既有约定。
3. 优先修改服务层中的可测试逻辑，再让 UI 调用服务层。
4. 保持公开类名与入口兼容，例如 `AnnotationPage`、`ValidatePage`、`TrainPage`、`HomePage`。
5. 修改后同步更新受影响文档；如果改动会影响用户可见行为、维护结构、入口、打包、设置字段或测试组织，按 `github-push-workflow` skill 更新根目录 `CHANGELOG.md` 的 `Unreleased > 待提交改动`。
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
- 模块行数围栏只用于阻止明显膨胀：`page.py` 与标注画布模块硬上限 350 行，共享 worker 硬上限 300 行，服务实现硬上限 400 行，服务包 `__init__.py` 硬上限 80 行。原 250/220/300 行阈值仅作为职责审查建议线，超过建议线时先判断内聚性和可读性；禁止为通过测试压缩排版、删除合理空白或进行没有职责收益的拆文件。

## 设置与路径规则

- 当前项目配置保存到当前项目目录 `data/runtime/settings.json`。
- 应用级最近项目状态保存到应用根目录 `data/runtime/app_state.json`。
- `src/runtime/settings.json` 只作为源码内默认配置参考，不作为当前项目唯一落点。
- 程序启动默认进入主页，不按 `last_page` 自动恢复页面。
- `data/models/` 是统一基础模型目录；训练和验证模型列表优先使用该目录。
- UI 中项目文件夹显示绝对路径，其他项目内路径尽量显示相对路径。

## 常用命令

开发 GUI：

```powershell
pixi run app
```

等价的直接入口：

```powershell
pixi run python -m src.main
```

运行测试和静态检查：

```powershell
pixi run test
pixi run check
```

构建程序更新用的冻结程序和 `Program` staging：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release -PackageType Program -ProgramOnly -Clean
```

本地开发快包（输出到 `dist/YOLOTool-dev/`，不作为用户发布物）：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

普通程序更新（复用已有基础环境包）：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\package_windows.ps1
```

完整发布（程序安装器、基础环境包和附加环境包）：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File installer\package_windows.ps1 -BuildBaseRuntimeModels -BuildModelExportRuntime
```

## 测试重点

- 设置加载、深合并、恢复默认值、最近项目恢复。
- Labelme/YOLO 转换、类别识别、类别映射、数据集划分、备份。
- 数据标注的 Labelme 读写、YOLO 同步导出、画布绘制与选择、AI 预标注。
- 模型格式转换、导出能力探测、附加运行时包安装与失败回滚。
- 训练命令生成、模型目录解析、停止流程、日志清洗。
- 验证页模型扫描、单文件/批量/摄像头检测/数据集验证、结果保存、`best.pt / last.pt` 开关。
- Windows 打包入口、隐藏后台子进程、图标资源。

## 维护建议

- 对任何会改用户文件的功能，坚持“先预览，再执行”。
- 重构时保持导入兼容，优先做小步移动和 re-export，再逐步收紧边界。
- 不为了清空 PyInstaller warning 恢复大包 `collect_all(...)` 全量扫描；只按真实运行缺失补依赖。
- 新增功能先补服务层测试，再接 UI。
- 使用 `QTimer.singleShot` 延迟调用 UI 页面或窗口方法时，必须传入所属 `QObject` 作为上下文，避免对象销毁后回调继续访问旧控件；Qt UI 测试必须在测试结束时清理顶层窗口并保持 `QApplication` 生命周期覆盖整个测试会话。
- Git 提交、推送、CHANGELOG 归并、哈希回填和版本归档统一按 `github-push-workflow` skill 执行；本项目的公开入口、文档同步范围、测试命令和产物排除规则以本文件其他章节为准。


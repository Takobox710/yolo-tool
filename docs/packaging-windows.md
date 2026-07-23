# Windows 打包与分层更新

项目继续使用 PyInstaller `onedir`，目标机器不需要安装 Python 或 pixi。打包产物分为程序层、环境层、模型层和用户数据层：

```text
YOLOTool/
├── YOLOTool.exe
├── app_assets/
├── release-manifest.json
├── runtime-manifest.json
├── runtime-version.txt
├── _internal/
└── data/models/
```

`_internal/` 包含 Python、PySide6、Torch、CUDA、OpenCV 等环境；`app_assets/` 只包含可随程序更新的图标资源。冻结态路径由 `src/shared/paths.py` 从 EXE 同级目录读取，开发态仍从 `src/assets/` 读取。

## 构建命令

正式完整产物：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release -PackageType Full -Clean
```

开发快包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

开发快包输出到 `dist/YOLOTool-dev/`，其中可执行文件名为 `YOLOTool-dev.exe`。

三类安装包由 `installer/package_windows.ps1` 或 `installer/打包程序.ps1` 生成：

```powershell
powershell -File installer\package_windows.ps1 -PackageType Full
powershell -File installer\package_windows.ps1 -PackageType AppUpdate
powershell -File installer\package_windows.ps1 -PackageType RuntimeFull -RuntimeVersion runtime-2
```

`Full` 首次安装包含程序、全部环境和基础模型；`AppUpdate` 只包含 EXE、程序资源和清单；`RuntimeFull` 同时更新程序和完整 `_internal` 环境，但不包含模型和用户数据。环境升级不再制作增量包，因此不需要维护基础环境版本和文件删除兼容规则。

## 更新规则

首次迁移需要安装一次新的 `Full` 包，之后普通程序改动只安装 `AppUpdate`。程序更新包要求当前运行环境与清单匹配；依赖变化时安装 `RuntimeFull`，该包会同时带上兼容的程序层。更新包会自动定位已有安装目录、要求关闭程序，并先写入临时目录再切换，失败时尝试恢复旧文件。

配置、模型、图片、标签和训练结果不会被更新包覆盖。`data/runtime/settings.json` 与 `data/runtime/app_state.json` 只在完整首次安装时使用 `onlyifdoesntexist` 写入。

打包入口统一来自 `src/main.py`，GUI 与 `--yolo-train`、`--yolo-export`、`--yolo-val` 等隐藏 CLI 都会执行运行环境版本校验。运行时清单缺失或版本不匹配时，GUI 显示错误，CLI 返回非零状态。

完整包输出到 `installer/output/YOLOTool_Setup_<version>.exe`；程序包输出为 `YOLOTool_AppUpdate_<version>.exe`；环境升级包输出为 `YOLOTool_RuntimeFull_<version>.exe`。

验证页视频预览使用 PySide6 的 `QtMultimedia` 与 `QtMultimediaWidgets`；发布前需确认 `_internal/` 中包含对应 Qt 多媒体插件。

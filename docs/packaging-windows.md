# Windows 打包说明

推荐使用 `onedir` 绿色版打包，避免单文件模式带来的启动慢和大依赖解包问题。

## 命令

正式版：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode release
```

开发快包：

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_windows.ps1 -Mode dev
```

如需一键完成 `PyInstaller + Inno Setup`，可执行：

```powershell
powershell -ExecutionPolicy Bypass -File installer\打包程序.ps1
```

## 输出目录

- 正式版输出到 `dist/YOLOTool/`
- 开发版输出到 `dist/YOLOTool-dev/`

打包入口统一来自 `src/main.py`，GUI 与 `--yolo-train`、`--yolo-export`、`--yolo-val` 等隐藏 CLI 子命令都通过同一可执行文件进入 `src/bootstrap/cli_dispatch.py`。

运行时配置使用打包目录内的 `data/runtime/settings.json` 与 `data/runtime/app_state.json`。

程序图标资源统一来自 `src/assets/app_icon.ico` 与 `src/assets/app_icon.png`：`.ico` 用于 PyInstaller/Inno Setup 的 EXE 与安装器图标，GUI 运行时窗口图标通过 `src/shared/paths.py` 中的 `ICON_PNG` 加载，避免目录结构调整后出现窗口或任务栏图标缺失。

Inno Setup 安装脚本位于 `installer/yolo_tool.iss`，与单一的 PyInstaller spec、hooks、PowerShell 打包脚本放在同一目录下统一维护。

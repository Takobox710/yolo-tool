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

Inno Setup 安装脚本位于 `installer/yolo_tool.iss`，与单一的 PyInstaller spec、hooks、PowerShell 打包脚本放在同一目录下统一维护。

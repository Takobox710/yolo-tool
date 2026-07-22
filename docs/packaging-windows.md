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

基础模型由 `installer/build_windows.ps1` 从项目的 `data/models/*.pt` 复制到打包产物的 `data/models/`；模型不会作为 PyInstaller 数据文件写入 `_internal/`，项目根目录下的 `.pt` 文件也不会复制到产物根目录。

程序图标资源统一来自 `src/assets/app_icon.ico` 与 `src/assets/app_icon.png`：`.ico` 用于 PyInstaller/Inno Setup 的 EXE 与安装器图标，GUI 运行时窗口图标通过 `src/shared/paths.py` 中的 `ICON_PNG` 加载。冻结态下 `ICON_PNG` 从 PyInstaller 的 `_MEIPASS/src/assets/` 读取，数据文件仍从 EXE 所在目录读取。顶部导航图标以及主页两张图表按当前屏幕设备像素比生成高 DPI pixmap，并在窗口跨屏切换时刷新，打包后无需额外图标或图表资源文件。

Inno Setup 安装脚本位于 `installer/yolo_tool.iss`，与单一的 PyInstaller spec、hooks、PowerShell 打包脚本放在同一目录下统一维护。

验证页视频预览使用 PySide6 的 `QtMultimedia` 与 `QtMultimediaWidgets`；打包验证时需确认 `dist/YOLOTool/` 中包含对应 Qt 多媒体插件，Windows 播放后端才能正常打开源视频和 MP4 检测结果。

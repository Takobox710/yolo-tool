# Windows 打包说明

推荐使用 `onedir` 绿色版打包，避免单文件模式带来的启动慢和大依赖解包问题。

## 命令

正式版：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -Mode release
```

开发快包：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -Mode dev
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows_dev.ps1
```

## 输出目录

- 正式版输出到 `dist/YOLOTool/`
- 开发版输出到 `dist/YOLOTool-dev/`

运行时配置使用项目内的 `data/runtime/settings.json`。

# Windows Packaging

The recommended distribution format is PyInstaller onedir. The build output is a folder, not a single exe, because this app bundles PySide6, OpenCV, Ultralytics, and Torch. Keeping the runtime unpacked makes startup faster and avoids temporary-path issues during training and detection.

Build from the project root:

```powershell
.\packaging\build_windows.ps1 -Clean
```

The generated app folder is:

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

`data/runtime/settings.json` is project-local. When the user changes the project directory in the Home page, the app loads that selected project's `data/runtime/settings.json`; if it does not exist, the app creates it with defaults for that project root.

Training and export do not rely on `pixi` on the target machine. The GUI starts a child process through the packaged executable itself, using the hidden `--yolo-train` or `--yolo-export` entrypoint.

For CUDA builds, the target Windows machine still needs a compatible NVIDIA driver even though it does not need Python, pixi, or a conda environment.

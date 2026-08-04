"""Record native top-level window lifecycle events on Windows.

This diagnostic is intentionally dependency-free so it can be used against a
frozen YOLOTool build as well as a Pixi development session.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from ctypes import wintypes
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import Timer
from typing import Callable


EVENT_OBJECT_CREATE = 0x8000
EVENT_OBJECT_DESTROY = 0x8001
EVENT_OBJECT_SHOW = 0x8002
EVENT_OBJECT_HIDE = 0x8003
EVENT_OBJECT_LOCATIONCHANGE = 0x800B
EVENT_OBJECT_NAMECHANGE = 0x800C
OBJID_WINDOW = 0
WINEVENT_OUTOFCONTEXT = 0
WM_QUIT = 0x0012
GW_OWNER = 4
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

EVENT_NAMES = {
    EVENT_OBJECT_CREATE: "created",
    EVENT_OBJECT_DESTROY: "destroyed",
    EVENT_OBJECT_SHOW: "shown",
    EVENT_OBJECT_HIDE: "hidden",
    EVENT_OBJECT_LOCATIONCHANGE: "geometry_changed",
    EVENT_OBJECT_NAMECHANGE: "title_changed",
}


@dataclass(frozen=True, slots=True)
class WindowSnapshot:
    hwnd: int
    title: str
    class_name: str
    pid: int
    process_path: str
    owner_hwnd: int
    visible: bool
    left: int
    top: int
    width: int
    height: int


def event_name(event: int) -> str:
    return EVENT_NAMES.get(event, f"event_0x{event:04X}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="记录 Windows 顶层窗口的创建、显示、尺寸变化和销毁事件。"
    )
    parser.add_argument("--duration", type=float, default=30.0, help="监测秒数，默认 30。")
    parser.add_argument("--pid", type=int, help="只记录指定进程 ID 的窗口。")
    parser.add_argument("--title", help="只记录标题包含此文本的窗口，不区分大小写。")
    parser.add_argument("--process-name", help="只记录指定进程文件名的窗口。")
    parser.add_argument(
        "--visible-only", action="store_true", help="忽略从未显示的原生窗口。"
    )
    parser.add_argument("--jsonl", type=Path, help="同时写入 UTF-8 JSONL 文件。")
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error("--duration 必须大于 0")
    return args


class _Win32Api:
    """Small ctypes wrapper kept here so importing --help works off Windows."""

    def __init__(self) -> None:
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_functions()

    def _configure_functions(self) -> None:
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClassNameW.restype = ctypes.c_int
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.GetWindowRect.restype = wintypes.BOOL
        self.user32.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
        self.user32.GetWindow.restype = wintypes.HWND
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

    def text(self, hwnd: int) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(max(length + 1, 1))
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value

    def class_name(self, hwnd: int) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value

    def process_path(self, pid: int) -> str:
        handle = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if self.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                return buffer.value
        finally:
            self.kernel32.CloseHandle(handle)
        return ""

    def snapshot(self, hwnd: int) -> WindowSnapshot | None:
        if not self.user32.IsWindow(hwnd):
            return None
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        rect = wintypes.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        return WindowSnapshot(
            hwnd=int(hwnd),
            title=self.text(hwnd),
            class_name=self.class_name(hwnd),
            pid=int(pid.value),
            process_path=self.process_path(int(pid.value)),
            owner_hwnd=int(self.user32.GetWindow(hwnd, GW_OWNER) or 0),
            visible=bool(self.user32.IsWindowVisible(hwnd)),
            left=rect.left,
            top=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
        )


def snapshot_matches(snapshot: WindowSnapshot, args: argparse.Namespace) -> bool:
    if args.pid is not None and snapshot.pid != args.pid:
        return False
    if args.title and args.title.casefold() not in snapshot.title.casefold():
        return False
    if args.process_name:
        expected = args.process_name.casefold()
        if Path(snapshot.process_path).name.casefold() != expected:
            return False
    return not args.visible_only or snapshot.visible


class WindowLifecycleMonitor:
    def __init__(self, api: _Win32Api, args: argparse.Namespace, write: Callable[[str], None]) -> None:
        self.api = api
        self.args = args
        self.write = write
        self.snapshots: dict[int, WindowSnapshot] = {}

    def observe(self, event: int, hwnd: int) -> None:
        previous = self.snapshots.get(hwnd)
        current = self.api.snapshot(hwnd)
        if event == EVENT_OBJECT_DESTROY:
            if previous is not None:
                self._emit(event, previous)
                self.snapshots.pop(hwnd, None)
            return
        if current is None or not snapshot_matches(current, self.args):
            return
        self.snapshots[hwnd] = current
        if event != EVENT_OBJECT_LOCATIONCHANGE or current != previous:
            self._emit(event, current)

    def _emit(self, event: int, snapshot: WindowSnapshot) -> None:
        record = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "event": event_name(event),
            **asdict(snapshot),
        }
        self.write(json.dumps(record, ensure_ascii=False))


def run_monitor(args: argparse.Namespace) -> None:
    if os.name != "nt":
        raise RuntimeError("窗口生命周期监测器仅支持 Windows。")
    api = _Win32Api()
    output = args.jsonl.open("a", encoding="utf-8") if args.jsonl else None

    def write(line: str) -> None:
        print(line, flush=True)
        if output is not None:
            output.write(line + "\n")
            output.flush()

    monitor = WindowLifecycleMonitor(api, args, write)
    callback_type = ctypes.WINFUNCTYPE(
        None,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.HWND,
        wintypes.LONG,
        wintypes.LONG,
        wintypes.DWORD,
        wintypes.DWORD,
    )

    @callback_type
    def on_window_event(_hook, event, hwnd, object_id, child_id, _thread_id, _event_time):
        if event in EVENT_NAMES and object_id == OBJID_WINDOW and child_id == 0:
            monitor.observe(int(event), int(hwnd or 0))

    user32 = api.user32
    user32.SetWinEventHook.argtypes = [
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        callback_type,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    user32.SetWinEventHook.restype = ctypes.c_void_p
    user32.UnhookWinEvent.argtypes = [ctypes.c_void_p]
    user32.UnhookWinEvent.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, ctypes.c_uint, ctypes.c_uint]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

    hook = user32.SetWinEventHook(
        EVENT_OBJECT_CREATE,
        EVENT_OBJECT_NAMECHANGE,
        None,
        on_window_event,
        0,
        0,
        WINEVENT_OUTOFCONTEXT,
    )
    if not hook:
        raise ctypes.WinError(ctypes.get_last_error())
    thread_id = api.kernel32.GetCurrentThreadId()
    timer = Timer(args.duration, lambda: user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0))
    timer.daemon = True
    timer.start()
    print(f"正在监测 {args.duration:g} 秒；按 Ctrl+C 可提前结束。", flush=True)
    try:
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel()
        user32.UnhookWinEvent(hook)
        if output is not None:
            output.close()


def main(argv: list[str] | None = None) -> int:
    try:
        run_monitor(parse_args(argv))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

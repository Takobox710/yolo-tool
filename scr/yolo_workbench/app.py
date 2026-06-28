from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from pathlib import Path
from queue import Empty, Queue

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scr.yolo_workbench.services.annotation_service import load_yolo_annotations, render_annotation_preview
    from scr.yolo_workbench.services.conversion_service import ConversionConfig, preview_conversion, run_conversion
    from scr.yolo_workbench.services.detection_service import run_prediction, scan_candidate_models
    from scr.yolo_workbench.services.environment_service import detect_modules, pixi_available, system_status, torch_cuda_summary
    from scr.yolo_workbench.services.rename_service import execute_rename, preview_rename
    from scr.yolo_workbench.services.resize_service import ResizeConfig, preview_resize, run_resize
    from scr.yolo_workbench.services.runtime_service import spawn_logged_process, stop_process
    from scr.yolo_workbench.services.settings_service import ROOT, SettingsService
    from scr.yolo_workbench.services.training_service import build_export_command, build_train_command, infer_task_mode_from_model
    from scr.yolo_workbench.theme import COLORS, FONTS
else:
    from .services.annotation_service import load_yolo_annotations, render_annotation_preview
    from .services.conversion_service import ConversionConfig, preview_conversion, run_conversion
    from .services.detection_service import run_prediction, scan_candidate_models
    from .services.environment_service import detect_modules, pixi_available, system_status, torch_cuda_summary
    from .services.rename_service import execute_rename, preview_rename
    from .services.resize_service import ResizeConfig, preview_resize, run_resize
    from .services.runtime_service import spawn_logged_process, stop_process
    from .services.settings_service import ROOT, SettingsService
    from .services.training_service import build_export_command, build_train_command, infer_task_mode_from_model
    from .theme import COLORS, FONTS


def run_app() -> None:
    try:
        import customtkinter as ctk
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        from PIL import Image, ImageTk
    except ModuleNotFoundError as exc:
        raise SystemExit(f"缺少运行依赖：{exc.name}。请先执行 pixi install 或 pixi run app。") from exc

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    class WorkbenchApp(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.settings_service = SettingsService()
            self.settings = self.settings_service.load()
            self.command_queue: Queue = Queue()
            self.training_handle = None
            self.export_handle = None
            self.detect_stop = threading.Event()
            self.detect_thread = None
            self.tk_module = tk
            self.ttk_module = ttk
            self.filedialog = filedialog
            self.messagebox = messagebox
            self.Image = Image
            self.ImageTk = ImageTk
            self.image_refs: dict[str, object] = {}
            self._page_save_job = None

            width = min(int(self.settings["ui"].get("window_width", 1100)), 1100)
            height = min(int(self.settings["ui"].get("window_height", 780)), 780)
            self.title("YOLO 本地训练工作台")
            self.geometry(f"{width}x{height}")
            self.minsize(1100, 780)
            self.configure(fg_color=COLORS["bg"])
            self.protocol("WM_DELETE_WINDOW", self.on_close)

            self._build_shell()
            self.after(150, self._poll_queue)

        def _build_shell(self):
            self.grid_rowconfigure(1, weight=1)
            self.grid_columnconfigure(0, weight=1)

            self.navbar = ctk.CTkFrame(self, height=80, fg_color=COLORS["nav"], corner_radius=0)
            self.navbar.grid(row=0, column=0, sticky="ew")
            self.navbar.grid_columnconfigure(1, weight=1)

            brand = ctk.CTkFrame(self.navbar, fg_color="transparent")
            brand.grid(row=0, column=0, padx=22, pady=14, sticky="w")
            logo = ctk.CTkFrame(brand, width=42, height=42, fg_color=COLORS["blue"], corner_radius=14)
            logo.pack(side="left", padx=(0, 12))
            logo.pack_propagate(False)
            ctk.CTkLabel(logo, text="YOLO", font=("Microsoft YaHei UI", 8, "bold"), text_color="white").pack(expand=True)
            brand_text = ctk.CTkFrame(brand, fg_color="transparent")
            brand_text.pack(side="left")
            ctk.CTkLabel(brand_text, text="YOLO 本地训练工作台", font=FONTS["brand"], text_color="white").pack(anchor="w")
            ctk.CTkLabel(
                brand_text,
                text="通用 YOLO + 焊缝 OBB 模板 · Pixi Python 3.12 · Torch CUDA 13.0",
                font=FONTS["small"],
                text_color="#BED2E2",
            ).pack(anchor="w")

            nav = ctk.CTkFrame(self.navbar, fg_color="transparent")
            nav.grid(row=0, column=1, sticky="e", padx=20)
            self.nav_buttons = {}
            for key, label in [
                ("home", "主页"),
                ("data", "数据处理"),
                ("train", "模型训练"),
                ("validate", "模型验证"),
                ("settings", "系统设置"),
            ]:
                button = ctk.CTkButton(
                    nav,
                    text=label,
                    width=92,
                    height=44,
                    font=FONTS["nav"],
                    fg_color="transparent",
                    hover_color=COLORS["nav_hover"],
                    command=lambda page=key: self.show_page(page),
                )
                button.pack(side="left", padx=4)
                self.nav_buttons[key] = button

            self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
            self.content.grid(row=1, column=0, sticky="nsew", padx=14, pady=14)
            self.content.grid_rowconfigure(0, weight=1)
            self.content.grid_columnconfigure(0, weight=1)

            self.statusbar = ctk.CTkLabel(self, text="就绪 - 请选择模型和检测源", anchor="w", fg_color="#F7FAFC", text_color=COLORS["muted"])
            self.statusbar.grid(row=2, column=0, sticky="ew")

            self.page_factories = {
                "home": HomePage,
                "data": DataPage,
                "train": TrainPage,
                "validate": ValidatePage,
                "settings": SettingsPage,
            }
            self.pages = {}
            self.current_page_key = None
            self.show_page(self.settings["ui"].get("last_page", "home"))

        def show_page(self, key: str):
            if key not in self.page_factories:
                key = "home"
            if self.current_page_key == key and key in self.pages:
                return
            if self.current_page_key in self.pages:
                self.pages[self.current_page_key].grid_forget()
            if key not in self.pages:
                self.pages[key] = self.page_factories[key](self.content, self)
            for name, button in self.nav_buttons.items():
                button.configure(fg_color=COLORS["nav_hover"] if name == key else "transparent")
            self.pages[key].grid(row=0, column=0, sticky="nsew")
            self.current_page_key = key
            self.pages[key].on_show()
            self.settings["ui"]["last_page"] = key
            self.schedule_settings_save()

        def run_background(self, kind: str, work):
            def worker():
                try:
                    self.command_queue.put((kind, work()))
                except Exception:
                    self.command_queue.put(("background_error", traceback.format_exc()))

            threading.Thread(target=worker, daemon=True).start()

        def schedule_settings_save(self):
            if self._page_save_job is not None:
                self.after_cancel(self._page_save_job)
            self._page_save_job = self.after(700, self._save_settings)

        def _save_settings(self):
            self._page_save_job = None
            self.settings_service.save(self.settings)

        def set_status(self, text: str):
            self.statusbar.configure(text=text)

        def _poll_queue(self):
            try:
                while True:
                    kind, payload = self.command_queue.get_nowait()
                    if kind == "train_log":
                        if "train" in self.pages:
                            self.pages["train"].append_log(payload)
                    elif kind == "train_exit":
                        if "train" in self.pages:
                            self.pages["train"].append_log(f"训练进程结束，退出码：{payload}")
                            self.pages["train"].set_progress(1.0)
                        self.set_status("训练结束")
                    elif kind == "detect_log":
                        if "validate" in self.pages:
                            self.pages["validate"].append_log(payload)
                    elif kind == "detect_result":
                        if "validate" in self.pages:
                            self.pages["validate"].handle_result(payload)
                    elif kind == "detect_done":
                        if "validate" in self.pages:
                            self.pages["validate"].append_log("检测任务结束。")
                        self.set_status("检测结束")
                    elif kind == "train_status":
                        if "train" in self.pages:
                            self.pages["train"].apply_status(payload)
                    elif kind == "settings_status":
                        if "settings" in self.pages:
                            self.pages["settings"].apply_status(payload)
                    elif kind == "validate_models":
                        if "validate" in self.pages:
                            self.pages["validate"].apply_model_candidates(payload)
                    elif kind == "background_error":
                        self.set_status("后台任务异常，详情见终端或日志")
                        print(payload)
            except Empty:
                pass
            self.after(150, self._poll_queue)

        def on_close(self):
            if self._page_save_job is not None:
                self.after_cancel(self._page_save_job)
                self._page_save_job = None
            self.settings["ui"]["window_width"] = 1100
            self.settings["ui"]["window_height"] = 780
            self.settings_service.save(self.settings)
            stop_process(self.training_handle)
            stop_process(self.export_handle)
            self.detect_stop.set()
            self.destroy()

    class BasePage(ctk.CTkFrame):
        def __init__(self, master, app: WorkbenchApp):
            super().__init__(master, fg_color="transparent")
            self.app = app

        def panel(self, parent, title: str = "", actions=None, header_builder=None):
            frame = ctk.CTkFrame(parent, fg_color=COLORS["panel"], border_width=1, border_color=COLORS["line"], corner_radius=8)
            if title or actions or header_builder:
                header = ctk.CTkFrame(frame, fg_color=COLORS["panel"], height=40, corner_radius=6)
                header.pack(fill="x", padx=8, pady=(8, 0))
                header.pack_propagate(False)
                header.grid_columnconfigure(0, weight=1)
                if title:
                    ctk.CTkLabel(header, text=title, font=FONTS["section"], text_color=COLORS["heading"], anchor="w").grid(row=0, column=0, sticky="w", padx=16)
                if actions:
                    action_bar = ctk.CTkFrame(header, fg_color="transparent")
                    action_bar.grid(row=0, column=1, sticky="e", padx=12)
                    for action in actions:
                        ctk.CTkButton(
                            action_bar,
                            text=action["text"],
                            height=32,
                            width=action.get("width", 112),
                            fg_color=action.get("fg_color", COLORS["soft"]),
                            hover_color=action.get("hover_color", COLORS["nav_hover"]),
                            text_color=action.get("text_color", COLORS["text"]),
                            command=action.get("command"),
                        ).pack(side="left", padx=4)
                if header_builder:
                    custom = ctk.CTkFrame(header, fg_color="transparent")
                    custom.grid(row=0, column=2, sticky="e", padx=12)
                    header_builder(custom)
            return frame

        def field(self, parent, label: str, value: str, browse=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=120, anchor="w", font=FONTS["body"], text_color=COLORS["text"]).pack(side="left")
            var = self.app.tk_module.StringVar(value=str(value))
            entry = ctk.CTkEntry(row, textvariable=var, height=36, fg_color="#FFFFFF", border_color="#CFD9E3", corner_radius=5)
            entry.pack(side="left", fill="x", expand=True)
            if browse:
                ctk.CTkButton(row, text="📂", width=38, height=36, fg_color=COLORS["blue"], command=lambda: browse(var)).pack(side="left", padx=(8, 0))
            return var

        def path_field(self, parent, label: str, value: str, browse=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=120, anchor="w", font=FONTS["body"], text_color=COLORS["text"]).pack(side="left")
            var = self.app.tk_module.StringVar(value=str(value))
            display_var = self.app.tk_module.StringVar(value=self.compact_path(value, 4))
            entry = ctk.CTkEntry(row, textvariable=display_var, height=36, fg_color="#FFFFFF", border_color="#CFD9E3", corner_radius=5)
            entry.pack(side="left", fill="x", expand=True)
            entry.configure(state="readonly")
            if browse:
                ctk.CTkButton(row, text="📂", width=38, height=36, fg_color=COLORS["blue"], command=lambda: browse(var, display_var)).pack(side="left", padx=(8, 0))
            var.display_var = display_var  # type: ignore[attr-defined]
            return var

        def compact_field(self, parent, label: str, value: str):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=72, anchor="w", font=FONTS["body"], text_color=COLORS["text"]).pack(side="left")
            var = self.app.tk_module.StringVar(value=str(value))
            entry = ctk.CTkEntry(row, textvariable=var, height=36, fg_color="#FFFFFF", border_color="#CFD9E3", corner_radius=5)
            entry.pack(side="left", fill="x", expand=True)
            return var

        def compact_path_field(self, parent, label: str, value: str, browse=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=72, anchor="w", font=FONTS["body"], text_color=COLORS["text"]).pack(side="left")
            var = self.app.tk_module.StringVar(value=str(value))
            display_var = self.app.tk_module.StringVar(value=self.compact_path(value, 4))
            entry = ctk.CTkEntry(row, textvariable=display_var, height=36, fg_color="#FFFFFF", border_color="#CFD9E3", corner_radius=5)
            entry.pack(side="left", fill="x", expand=True)
            entry.configure(state="readonly")
            if browse:
                ctk.CTkButton(row, text="📂", width=38, height=36, fg_color=COLORS["blue"], command=lambda: browse(var, display_var)).pack(side="left", padx=(8, 0))
            var.display_var = display_var  # type: ignore[attr-defined]
            return var

        def compact_option_field(self, parent, label: str, value: str, values: list[str], command=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=72, anchor="w", font=FONTS["body"], text_color=COLORS["text"]).pack(side="left")
            var = self.app.tk_module.StringVar(value=str(value))
            option = ctk.CTkComboBox(
                row,
                variable=var,
                values=values,
                height=36,
                border_width=1,
                border_color="#CFD9E3",
                corner_radius=5,
                fg_color="#FFFFFF",
                button_color=COLORS["blue"],
                button_hover_color=COLORS["nav_hover"],
                text_color=COLORS["text"],
                dropdown_fg_color="#FFFFFF",
                dropdown_text_color=COLORS["text"],
                command=command,
            )
            option.pack(side="left", fill="x", expand=True)
            return var

        def option_field(self, parent, label: str, value: str, values: list[str], command=None):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=120, anchor="w", font=FONTS["body"], text_color=COLORS["text"]).pack(side="left")
            var = self.app.tk_module.StringVar(value=str(value))
            option = ctk.CTkComboBox(
                row,
                variable=var,
                values=values,
                height=36,
                border_width=1,
                border_color="#CFD9E3",
                corner_radius=5,
                fg_color="#FFFFFF",
                button_color=COLORS["blue"],
                button_hover_color=COLORS["nav_hover"],
                text_color=COLORS["text"],
                dropdown_fg_color="#FFFFFF",
                dropdown_text_color=COLORS["text"],
                command=command,
            )
            option.pack(side="left", fill="x", expand=True)
            return var

        def stat_card(self, parent, label: str, value: str):
            card = ctk.CTkFrame(parent, fg_color="#F1F4F8", corner_radius=4)
            card.pack(fill="x", pady=4)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=label, font=FONTS["body"], text_color=COLORS["muted"], anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=8)
            value_label = ctk.CTkLabel(card, text=value, font=FONTS["stat"], text_color=COLORS["deep"], anchor="e")
            value_label.grid(row=0, column=1, sticky="e", padx=12, pady=8)
            return value_label

        def metric_card(self, parent, label: str, value: str):
            card = ctk.CTkFrame(parent, fg_color="#F7FAFC", border_width=1, border_color="#DFE8F0", corner_radius=6)
            ctk.CTkLabel(card, text=label, font=FONTS["small"], text_color=COLORS["muted"], anchor="w").pack(fill="x", padx=12, pady=(10, 0))
            value_label = ctk.CTkLabel(card, text=value, font=FONTS["metric"], text_color=COLORS["deep"], anchor="w")
            value_label.pack(fill="x", padx=12, pady=(2, 10))
            return card, value_label

        def check_card(self, parent, label: str, enabled: bool = True):
            card = ctk.CTkFrame(parent, fg_color="#F1F6FA", border_width=1, border_color="#D9E4EE", corner_radius=5)
            state = self.app.tk_module.BooleanVar(value=enabled)
            box_color = COLORS["blue"] if enabled else "#FFFFFF"
            box = ctk.CTkFrame(card, fg_color=box_color, border_width=0 if enabled else 2, border_color="#AEBDCA", width=16, height=16, corner_radius=3)
            box.pack(side="left", padx=(10, 8), pady=10)
            box.pack_propagate(False)
            ctk.CTkLabel(card, text=label, font=FONTS["body"], text_color=COLORS["text"], anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 10))

            def toggle(_event=None):
                state.set(not state.get())
                box.configure(fg_color=COLORS["blue"] if state.get() else "#FFFFFF", border_width=0 if state.get() else 2)

            card.bind("<Button-1>", toggle)
            box.bind("<Button-1>", toggle)
            for child in card.winfo_children():
                child.bind("<Button-1>", toggle)
            card.value = state  # type: ignore[attr-defined]
            return card

        def placeholder_canvas(self, parent, text: str, height: int = 330):
            canvas = self.app.tk_module.Canvas(parent, bg="#F8FBFD", highlightthickness=2, highlightbackground="#B8DCF6", height=height)
            canvas.create_text(10, 10, anchor="nw", text=text, fill="#7B8B99", font=("Microsoft YaHei UI", 12, "bold"))
            return canvas

        def compact_path(self, value: str | Path, max_parts: int = 2):
            path = Path(str(value))
            parts = path.parts
            if len(parts) <= max_parts + 1:
                return str(value)
            return ".../" + "/".join(parts[-max_parts:]).replace("\\", "/")

        def on_show(self):
            pass

    class HomePage(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(2, weight=1)
            self._build()

        def _build(self):
            hero = ctk.CTkFrame(self, fg_color="transparent")
            hero.grid(row=0, column=0, sticky="ew", pady=(0, 16))
            hero.grid_columnconfigure(0, weight=1)
            copy = ctk.CTkFrame(hero, fg_color="transparent")
            copy.grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(copy, text="欢迎使用 YOLO 本地训练工作台", font=FONTS["title"], text_color="#1A3857").pack(anchor="w")
            ctk.CTkLabel(copy, text="配置项目路径、检查数据状态、查看训练结果。", font=FONTS["body"], text_color=COLORS["muted"]).pack(anchor="w")
            env = ctk.CTkFrame(hero, fg_color="transparent")
            env.grid(row=0, column=1, sticky="e")
            for text in ["pixi env: local", "Python 3.12", "CUDA 13.0"]:
                pill = ctk.CTkFrame(env, fg_color="#FFFFFF", border_width=1, border_color=COLORS["line"], corner_radius=14)
                pill.pack(side="left", padx=5)
                ctk.CTkLabel(pill, text=text, font=FONTS["small"], text_color="#345").pack(padx=12, pady=7)

            top = ctk.CTkFrame(self, fg_color="transparent")
            top.grid(row=1, column=0, sticky="nsew")
            top.grid_columnconfigure(0, weight=0, minsize=400)
            top.grid_columnconfigure(1, weight=1)

            overview = self.panel(top, "项目概览", actions=[{"text": "设置项目目录", "fg_color": COLORS["nav"], "text_color": "white", "command": self.pick_project_root}])
            overview.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            overview_body = ctk.CTkFrame(overview, fg_color="transparent")
            overview_body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            self.overview_stats = {
                "project": self.stat_card(overview_body, "项目文件夹", "-"),
                "images": self.stat_card(overview_body, "图片路径", "-"),
                "annotations": self.stat_card(overview_body, "标注路径", "-"),
                "result": self.stat_card(overview_body, "结果路径", "-"),
                "counts": self.stat_card(overview_body, "已标注 / 图片", "-"),
            }

            chart = self.panel(top, "各类别图片分布", actions=[{"text": "刷新统计", "command": self.on_show}])
            chart.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            self.chart_canvas = self.app.tk_module.Canvas(chart, bg="#FBFDFF", highlightthickness=1, highlightbackground="#E4EAF0", height=270)
            self.chart_canvas.pack(fill="both", expand=True, padx=16, pady=(0, 16))

            lower = ctk.CTkFrame(self, fg_color="transparent")
            lower.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
            lower.grid_columnconfigure(0, weight=0, minsize=400)
            lower.grid_columnconfigure(1, weight=1)
            curve = self.panel(lower, "训练曲线")
            curve.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            self.curve_canvas = self.app.tk_module.Canvas(curve, bg="#FBFDFF", highlightthickness=1, highlightbackground="#E4EAF0", height=220)
            self.curve_canvas.pack(fill="both", expand=True, padx=16, pady=(0, 16))

            history = self.panel(lower, "训练历史", actions=[{"text": "打开结果目录", "command": self.open_result_dir}])
            history.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            self.history_table = self.app.ttk_module.Treeview(history, columns=("训练ID", "任务", "模型", "Epochs", "mAP@0.5", "训练时长"), show="headings", height=5)
            for column in self.history_table["columns"]:
                self.history_table.heading(column, text=column)
                self.history_table.column(column, anchor="center", width=110)
            self.history_table.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        def on_show(self):
            settings = self.app.settings
            paths = settings["paths"]
            images = Path(paths["images_dir"])
            labels = Path(paths["labels_dir"])
            result = Path(paths["result_dir"])
            image_count = len([p for p in images.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}]) if images.exists() else 0
            label_count = len(list(labels.glob("*.txt"))) if labels.exists() else 0
            self.overview_stats["project"].configure(text=Path(settings["project"]["root"]).name)
            self.overview_stats["images"].configure(text=self.compact_path(images, 2))
            self.overview_stats["annotations"].configure(text=self.compact_path(paths["annotations_dir"], 2))
            self.overview_stats["result"].configure(text=self.compact_path(result, 2))
            self.overview_stats["counts"].configure(text=f"{label_count} / {image_count}")
            self.draw_distribution(label_count)
            self.draw_empty_curve()
            self.history_table.delete(*self.history_table.get_children())
            candidates = scan_candidate_models(result)
            for candidate in candidates[:8]:
                train_id = candidate.parent.parent.name
                self.history_table.insert("", "end", values=(train_id, settings["task"]["mode"], candidate.name, "-", "-", "-"))

        def draw_distribution(self, label_count: int):
            canvas = self.chart_canvas
            canvas.delete("all")
            canvas.update_idletasks()
            width = max(canvas.winfo_width(), 640)
            height = max(canvas.winfo_height(), 240)
            canvas.create_text(width / 2, 28, text=f"{', '.join(self.app.settings['dataset']['class_names'])} / images", fill=COLORS["text"], font=("Microsoft YaHei UI", 12, "bold"))
            canvas.create_line(50, height - 46, width - 26, height - 46, fill="#111", width=2)
            bar_height = min(max(label_count, 1), 500) / 500 * (height - 110)
            x1, x2 = width / 2 - 55, width / 2 + 55
            canvas.create_rectangle(x1, height - 46 - bar_height, x2, height - 46, fill="#5AAEE3", outline="")
            canvas.create_text(width / 2, height - 56 - bar_height, text=str(label_count), fill=COLORS["deep"], font=("Microsoft YaHei UI", 12, "bold"))

        def draw_empty_curve(self):
            canvas = self.curve_canvas
            canvas.delete("all")
            canvas.update_idletasks()
            width = max(canvas.winfo_width(), 360)
            height = max(canvas.winfo_height(), 200)
            canvas.create_line(36, 28, 36, height - 36, fill="#222", width=2)
            canvas.create_line(36, height - 36, width - 28, height - 36, fill="#222", width=2)
            canvas.create_text(width / 2, height / 2, text="暂无训练记录\n请进行模型训练", fill="#94A2AD", font=("Microsoft YaHei UI", 12, "bold"), justify="center")

        def pick_project_root(self):
            path = self.app.filedialog.askdirectory()
            if path:
                self.app.settings["project"]["root"] = path
                self.app.settings_service.save(self.app.settings)
                self.on_show()

        def open_result_dir(self):
            path = Path(self.app.settings["paths"]["result_dir"])
            if path.exists():
                os.startfile(path)  # type: ignore[attr-defined]

    class DataPage(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(0, weight=1)
            self._build()

        def _build(self):
            sidebar = ctk.CTkFrame(self, fg_color=COLORS["nav"], corner_radius=8, width=220)
            sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 16))
            ctk.CTkLabel(sidebar, text="数据处理", font=FONTS["section"], text_color="white").pack(pady=(22, 16))
            self.sub_pages = {}
            self.sub_buttons = {}
            for key, label in [("convert", "标注转换"), ("preview", "标注预览"), ("rename", "批量重命名"), ("resize", "图片压缩")]:
                button = ctk.CTkButton(sidebar, text=label, fg_color="transparent", hover_color=COLORS["nav_hover"], command=lambda k=key: self.show_tool(k))
                button.pack(fill="x", padx=12, pady=6)
                self.sub_buttons[key] = button

            self.tool_area = ctk.CTkFrame(self, fg_color="transparent")
            self.tool_area.grid(row=0, column=1, sticky="nsew")
            self.tool_area.grid_rowconfigure(0, weight=1)
            self.tool_area.grid_columnconfigure(0, weight=1)
            self.sub_page_factories = {
                "convert": ConvertTool,
                "preview": PreviewTool,
                "rename": RenameTool,
                "resize": ResizeTool,
            }
            self.current_tool_key = None
            self.show_tool("convert")

        def show_tool(self, key):
            if key not in self.sub_page_factories:
                key = "convert"
            if self.current_tool_key == key and key in self.sub_pages:
                return
            if self.current_tool_key in self.sub_pages:
                self.sub_pages[self.current_tool_key].grid_forget()
            if key not in self.sub_pages:
                self.sub_pages[key] = self.sub_page_factories[key](self.tool_area, self.app)
            for name, button in self.sub_buttons.items():
                button.configure(fg_color=COLORS["nav_hover"] if name == key else "transparent")
            self.sub_pages[key].grid(row=0, column=0, sticky="nsew")
            self.current_tool_key = key

    class ConvertTool(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self._build()

        def _build(self):
            panel = self.panel(
                self,
                "标注转换配置",
                actions=[
                    {"text": "预览转换", "command": self.preview},
                    {"text": "执行转换", "fg_color": COLORS["green"], "text_color": "white", "command": self.run},
                ],
            )
            panel.pack(fill="both", expand=True)
            body = ctk.CTkFrame(panel, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            paths = self.app.settings["paths"]
            dataset = self.app.settings["dataset"]
            form = ctk.CTkFrame(body, fg_color="transparent")
            form.pack(fill="x")
            form.grid_columnconfigure((0, 1), weight=1)
            left = ctk.CTkFrame(form, fg_color="transparent")
            right = ctk.CTkFrame(form, fg_color="transparent")
            left.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            right.grid(row=0, column=1, sticky="ew", padx=(10, 0))
            self.images_var = self.field(left, "图片目录", paths["images_dir"], self.pick_dir)
            self.annotations_var = self.field(left, "Labelme目录", paths["annotations_dir"], self.pick_dir)
            self.output_var = self.field(left, "输出目录", paths["dataset_dir"], self.pick_dir)
            self.classes_var = self.field(left, "类别名称", ",".join(dataset["class_names"]))
            self.task_var = self.option_field(right, "任务类型", self.app.settings["task"]["mode"], ["obb", "detect"])
            ratios = dataset["split_ratios"]
            self.ratio_var = self.field(right, "划分比例", f"{ratios['train']},{ratios['val']},{ratios['test']}")
            self.seed_var = self.field(right, "随机种子", str(dataset["random_seed"]))
            self.line_width_var = self.field(right, "线宽半径", str(dataset["line_to_obb"]["half_width"]))

            checks = ctk.CTkFrame(body, fg_color="transparent")
            checks.pack(fill="x", pady=(10, 0))
            checks.grid_columnconfigure((0, 1, 2, 3), weight=1)
            for index, (label, enabled) in enumerate([("Labelme 转换", True), ("直线转 OBB", True), ("生成 data.yaml", True), ("执行前备份", False)]):
                self.check_card(checks, label, enabled).grid(row=0, column=index, sticky="ew", padx=5)

            self.log = ctk.CTkTextbox(body, height=230, fg_color="#FBFCFD", border_width=1, border_color="#E4EBF2", font=FONTS["mono"])
            self.log.pack(fill="both", expand=True, pady=(14, 0))
            self.log.insert("end", "预览结果：\n- 请选择预览转换以扫描图片和 Labelme 标注\n- 未执行任何写入")

        def pick_dir(self, var):
            path = self.app.filedialog.askdirectory()
            if path:
                var.set(path)

        def config(self):
            train, val, test = [float(item.strip()) for item in self.ratio_var.get().split(",")]
            return ConversionConfig(
                task_mode=self.task_var.get() or self.app.settings["task"]["mode"],
                images_dir=Path(self.images_var.get()),
                annotations_dir=Path(self.annotations_var.get()),
                output_dir=Path(self.output_var.get()),
                labels_dir=Path(self.app.settings["paths"]["labels_dir"]),
                class_names=[item.strip() for item in self.classes_var.get().split(",") if item.strip()],
                train_ratio=train,
                val_ratio=val,
                test_ratio=test,
                line_to_obb=True,
                line_half_width=float(self.line_width_var.get()),
            )

        def preview(self):
            try:
                result = preview_conversion(self.config())
                self.log.delete("1.0", "end")
                self.log.insert("end", f"有标注图片: {result.labeled_count}\n无标注图片: {result.unlabeled_count}\n计划划分: {result.planned_splits}\n未执行任何写入。")
            except Exception as exc:
                self.log.insert("end", f"\n错误: {exc}")

        def run(self):
            try:
                result = run_conversion(self.config())
                self.log.insert("end", f"\n转换完成: train={result.labeled_train_count}, val={result.labeled_val_count}, test={result.labeled_test_count}, boxes={result.total_boxes}")
            except Exception:
                self.log.insert("end", "\n" + traceback.format_exc())

    class PreviewTool(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self.preview_ref = None
            self.preview_items: list[Path] = []
            self.preview_index = 0
            self._build()

        def _build(self):
            panel = self.panel(
                self,
                "标注预览",
                actions=[
                    {"text": "上一张", "command": self.prev_image},
                    {"text": "下一张", "command": self.next_image},
                ],
            )
            panel.pack(fill="both", expand=True)
            body = ctk.CTkFrame(panel, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            form = ctk.CTkFrame(body, fg_color="transparent")
            form.pack(fill="x")
            form.grid_columnconfigure((0, 1), weight=1)
            left_form = ctk.CTkFrame(form, fg_color="transparent")
            right_form = ctk.CTkFrame(form, fg_color="transparent")
            left_form.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            right_form.grid(row=0, column=1, sticky="ew", padx=(10, 0))
            self.image_dir_var = self.field(left_form, "图片文件夹", self.app.settings["paths"]["images_dir"], self.pick_image_dir)
            self.label_dir_var = self.field(right_form, "标注文件夹", self.app.settings["paths"]["labels_dir"], self.pick_label_dir)
            self.current_preview_label = ctk.CTkLabel(body, text="等待扫描图片", anchor="w", text_color=COLORS["muted"], font=FONTS["small"])
            self.current_preview_label.pack(fill="x", pady=(6, 0))

            preview = ctk.CTkFrame(body, fg_color="transparent")
            preview.pack(fill="both", expand=True, pady=(10, 0))
            preview.grid_columnconfigure((0, 1), weight=1)
            preview.grid_rowconfigure(0, weight=1)
            source_panel = self.panel(preview, "原始图片")
            source_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            result_panel = self.panel(preview, "YOLO 标注框 / OBB 四点框")
            result_panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            self.source_canvas = self.app.tk_module.Canvas(source_panel, bg="#F8FBFD", highlightthickness=2, highlightbackground="#B8DCF6", height=360)
            self.source_canvas.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            self.canvas = self.app.tk_module.Canvas(result_panel, bg="#F8FBFD", highlightthickness=2, highlightbackground="#B8DCF6", height=360)
            self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        def pick_image_dir(self, var):
            path = self.app.filedialog.askdirectory()
            if path:
                var.set(path)
                self.load_preview_items()

        def pick_label_dir(self, var):
            path = self.app.filedialog.askdirectory()
            if path:
                var.set(path)
                self.load_preview_items()

        def load_preview_items(self):
            image_dir = Path(self.image_dir_var.get())
            self.preview_items = sorted(path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}) if image_dir.exists() else []
            self.preview_index = 0
            self.render_current()

        def prev_image(self):
            if not self.preview_items:
                self.load_preview_items()
                return
            self.preview_index = (self.preview_index - 1) % len(self.preview_items)
            self.render_current()

        def next_image(self):
            if not self.preview_items:
                self.load_preview_items()
                return
            self.preview_index = (self.preview_index + 1) % len(self.preview_items)
            self.render_current()

        def render_current(self):
            if not self.preview_items:
                self.current_preview_label.configure(text="未找到图片")
                return
            image_path = self.preview_items[self.preview_index]
            label_path = Path(self.label_dir_var.get()) / f"{image_path.stem}.txt"
            self.current_preview_label.configure(text=f"{self.preview_index + 1}/{len(self.preview_items)}  {image_path.name}  ->  {label_path.name if label_path.exists() else '未找到同名标注'}")
            self.render(image_path, label_path)

        def render(self, image_path=None, label_path=None):
            image_path = Path(image_path) if image_path else (self.preview_items[self.preview_index] if self.preview_items else Path(""))
            label_path = Path(label_path) if label_path else Path(self.label_dir_var.get()) / f"{image_path.stem}.txt"
            if not image_path.exists():
                return
            image = self.app.Image.open(image_path)
            annotations = load_yolo_annotations(image.size, label_path, self.app.settings["task"]["mode"], self.app.settings["dataset"]["class_names"])
            preview = render_annotation_preview(image_path, annotations)
            self._display_on(self.source_canvas, image, "preview_source")
            self._display(preview)

        def _display(self, image):
            self._display_on(self.canvas, image, "preview_result")

        def _display_on(self, canvas, image, key):
            canvas.update_idletasks()
            preview = image.copy()
            preview.thumbnail((max(canvas.winfo_width(), 600) - 20, max(canvas.winfo_height(), 360) - 20))
            photo = self.app.ImageTk.PhotoImage(preview)
            canvas.delete("all")
            canvas.create_image(canvas.winfo_width() / 2, canvas.winfo_height() / 2, image=photo)
            self.app.image_refs[key] = photo

        def on_show(self):
            if not self.preview_items:
                self.load_preview_items()

    class RenameTool(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self.plan = []
            self._preview_job = None
            self._build()

        def _build(self):
            panel = self.panel(
                self,
                "批量重命名",
                actions=[
                    {"text": "预览", "command": self.preview},
                    {"text": "执行重命名", "fg_color": COLORS["green"], "text_color": "white", "command": self.run},
                ],
            )
            panel.pack(fill="both", expand=True)
            body = ctk.CTkFrame(panel, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            form = ctk.CTkFrame(body, fg_color="transparent")
            form.pack(fill="x")
            form.grid_columnconfigure((0, 1), weight=1)
            left = ctk.CTkFrame(form, fg_color="transparent")
            right = ctk.CTkFrame(form, fg_color="transparent")
            left.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            right.grid(row=0, column=1, sticky="ew", padx=(10, 0))
            self.folder_var = self.field(left, "文件夹", self.app.settings["paths"]["images_dir"], self.pick_dir)
            self.label_folder_var = self.field(left, "标注文件夹", self.app.settings["paths"]["labels_dir"], self.pick_label_dir)
            self.prefix_var = self.field(left, "命名前缀", "A")
            self.start_var = self.field(right, "起始编号", "1")
            self.padding_var = self.field(right, "编号位数", "3")
            self.rename_labels_card = self.check_card(right, "标注文件一并更改", True)
            self.rename_labels_card.pack(fill="x", pady=5)
            for var in (self.folder_var, self.label_folder_var, self.prefix_var, self.start_var, self.padding_var):
                var.trace_add("write", lambda *_: self.schedule_preview())
            self.rename_labels_card.value.trace_add("write", lambda *_: self.schedule_preview())  # type: ignore[attr-defined]
            self.table = self._table(body, ("序号", "原文件名", "新文件名", "图片冲突", "标注状态"))
            self.after(100, self.schedule_preview)

        def _table(self, parent, columns):
            table = self.app.ttk_module.Treeview(parent, columns=columns, show="headings")
            for column in columns:
                table.heading(column, text=column)
                table.column(column, anchor="center", width=140)
            table.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            return table

        def pick_dir(self, var):
            path = self.app.filedialog.askdirectory()
            if path:
                var.set(path)

        def pick_label_dir(self, var):
            path = self.app.filedialog.askdirectory()
            if path:
                var.set(path)

        def schedule_preview(self):
            if self._preview_job is not None:
                self.after_cancel(self._preview_job)
            self._preview_job = self.after(250, self.preview)

        def preview(self):
            self._preview_job = None
            try:
                self.plan = preview_rename(
                    Path(self.folder_var.get()),
                    self.prefix_var.get(),
                    int(self.start_var.get()),
                    int(self.padding_var.get()),
                    labels_dir=Path(self.label_folder_var.get()),
                    include_labels=self.rename_labels_card.value.get(),  # type: ignore[attr-defined]
                )
            except Exception:
                return
            self.table.delete(*self.table.get_children())
            for item in self.plan:
                label_status = item.note or (f"{item.label_source.name} -> {item.label_target.name}" if item.label_source and item.label_target else "不处理")
                self.table.insert("", "end", values=(item.index, item.old_name, item.new_name, "是" if item.conflict else "无", label_status))

        def run(self):
            result = execute_rename(self.plan)
            if result.renamed_count == 0 and result.skipped_count:
                self.app.messagebox.showwarning("发现冲突", "检测到标注文件目标名称冲突，已取消本次重命名。")
            else:
                self.app.messagebox.showinfo("重命名完成", f"已重命名图片 {result.renamed_count} 个，标注 {result.label_renamed_count} 个。")
            self.preview()

    class ResizeTool(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self._build()

        def _build(self):
            panel = self.panel(
                self,
                "图片压缩 / 画布归一化",
                actions=[
                    {"text": "预览压缩", "command": self.preview},
                    {"text": "执行压缩", "fg_color": COLORS["green"], "text_color": "white", "command": self.run},
                ],
            )
            panel.pack(fill="both", expand=True)
            body = ctk.CTkFrame(panel, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            resize = self.app.settings["image_resize"]
            form = ctk.CTkFrame(body, fg_color="transparent")
            form.pack(fill="x")
            form.grid_columnconfigure((0, 1), weight=1)
            left = ctk.CTkFrame(form, fg_color="transparent")
            right = ctk.CTkFrame(form, fg_color="transparent")
            left.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            right.grid(row=0, column=1, sticky="ew", padx=(10, 0))
            self.source_var = self.field(left, "图片目录", self.app.settings["paths"]["images_dir"], self.pick_dir)
            self.backup_var = self.field(left, "备份目录", resize["backup_dir"], self.pick_dir)
            self.output_var = self.field(left, "输出目录", resize["output_dir"], self.pick_dir)
            self.mode_var = self.option_field(left, "输出方式", "输出到新文件夹", ["输出到新文件夹", "覆盖原文件"])
            self.long_var = self.field(right, "长边缩放", str(resize["long_edge"]))
            self.canvas_var = self.field(right, "画布尺寸", str(resize["canvas_size"]))
            self.bg_var = self.option_field(right, "背景颜色", resize["background"], ["white", "black"])
            self.format_var = self.option_field(right, "保存格式", "保持原格式", ["保持原格式", "jpg", "png"])
            checks = ctk.CTkFrame(body, fg_color="transparent")
            checks.pack(fill="x", pady=(10, 0))
            checks.grid_columnconfigure((0, 1, 2, 3), weight=1)
            for index, (label, enabled) in enumerate([("执行前备份原图", True), ("长边等比缩放", True), ("居中贴入画布", True), ("黑色背景", resize["background"] == "black")]):
                self.check_card(checks, label, enabled).grid(row=0, column=index, sticky="ew", padx=5)
            self.log = ctk.CTkTextbox(body, height=210, fg_color="#FBFCFD", border_width=1, border_color="#E4EBF2", font=FONTS["mono"])
            self.log.pack(fill="both", expand=True, pady=(14, 0))

        def pick_dir(self, var):
            path = self.app.filedialog.askdirectory()
            if path:
                var.set(path)

        def config(self):
            return ResizeConfig(
                source_dir=Path(self.source_var.get()),
                output_dir=Path(self.output_var.get()),
                backup_dir=Path(self.backup_var.get()),
                long_edge=int(self.long_var.get()),
                canvas_size=int(self.canvas_var.get()),
                background=self.bg_var.get(),
            )

        def preview(self):
            result = preview_resize(self.config())
            self.log.delete("1.0", "end")
            self.log.insert("end", f"将备份到: {result.backup_dir}\n")
            for item in result.items[:20]:
                self.log.insert("end", f"{item.source.name}: {item.original_size} -> {item.resized_size}, scale={item.scale:.3f}\n")

        def run(self):
            result = run_resize(self.config())
            self.log.insert("end", f"\n压缩完成: {result.processed_count} 张，输出目录: {result.output_dir}")

    class TrainPage(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self._status_loading = False
            self._build()

        def _build(self):
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(2, weight=1)
            top = ctk.CTkFrame(self, fg_color="transparent")
            top.grid(row=0, column=0, sticky="nsew")
            top.grid_columnconfigure(0, weight=115)
            top.grid_columnconfigure(1, weight=85)
            left = self.panel(top, "数据集与增强配置")
            left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            right = self.panel(top, "训练参数")
            right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            training = self.app.settings["training"]
            self.train_vars = {}
            left_body = ctk.CTkFrame(left, fg_color="transparent")
            left_body.pack(fill="both", expand=True, padx=16, pady=(0, 8))
            form = ctk.CTkFrame(left_body, fg_color="transparent")
            form.pack(fill="x")
            form.grid_columnconfigure((0, 1), weight=1)
            form_left = ctk.CTkFrame(form, fg_color="transparent")
            form_right = ctk.CTkFrame(form, fg_color="transparent")
            form_left.grid(row=0, column=0, sticky="ew", padx=(0, 10))
            form_right.grid(row=0, column=1, sticky="ew", padx=(10, 0))
            for key, label, parent in [
                ("data", "data.yaml", form_left),
                ("pretrained", "预训练权重", form_left),
                ("project", "项目输出", form_right),
                ("model_yaml", "模型 YAML", form_right),
            ]:
                self.train_vars[key] = self.field(parent, label, training.get(key, ""))
            checks = ctk.CTkFrame(left_body, fg_color="transparent")
            checks.pack(fill="x", pady=(4, 0))
            checks.grid_columnconfigure((0, 1, 2, 3), weight=1)
            self.augment_cards = {}
            augmentations = [
                ("mosaic", "马赛克", training.get("mosaic", 0) > 0),
                ("fliplr", "水平翻转", training.get("fliplr", 0) > 0),
                ("scale", "随机缩放", training.get("scale", 0) > 0),
                ("translate", "随机平移", training.get("translate", 0) > 0),
                ("flipud", "垂直翻转", training.get("flipud", 0) > 0),
                ("degrees", "随机旋转", training.get("degrees", 0) > 0),
                ("hsv", "色域扰动", training.get("hsv", 0) > 0),
                ("mixup", "MixUp", training.get("mixup", 0) > 0),
            ]
            for index, (key, label, enabled) in enumerate(augmentations):
                card = self.check_card(checks, label, enabled)
                card.grid(row=index // 4, column=index % 4, sticky="ew", padx=5, pady=5)
                self.augment_cards[key] = card

            right_body = ctk.CTkFrame(right, fg_color="transparent")
            right_body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            params = ctk.CTkFrame(right_body, fg_color="transparent")
            params.pack(fill="x")
            params.grid_columnconfigure((0, 1), weight=1)
            for index, (key, label) in enumerate([("base_model", "基础模型"), ("lr", "学习率"), ("epochs", "Epochs"), ("patience", "Patience"), ("workers", "Workers"), ("batch", "Batch"), ("imgsz", "图片尺寸")]):
                holder = ctk.CTkFrame(params, fg_color="transparent")
                holder.grid(row=index // 2, column=index % 2, sticky="ew", padx=5, pady=0)
                if key == "base_model":
                    self.train_vars[key] = self.option_field(holder, label, str(training.get(key, "")), ["yolo11n-obb", "yolo11s-obb", "yolo11m-obb", "yolo11n", "yolo11s", "yolo11m"])
                else:
                    self.train_vars[key] = self.field(holder, label, str(training.get(key, "")))
            device_holder = ctk.CTkFrame(params, fg_color="transparent")
            device_holder.grid(row=3, column=1, sticky="ew", padx=5, pady=0)
            self.train_vars["device"] = self.option_field(device_holder, "设备", str(training.get("device", "")), ["0", "cpu", "0,1"])

            action = ctk.CTkFrame(self, fg_color="transparent")
            action.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
            action.grid_columnconfigure(0, weight=1)
            action.grid_columnconfigure(1, weight=2)
            control = self.panel(action)
            control.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            control_body = ctk.CTkFrame(control, fg_color="transparent")
            control_body.pack(fill="both", expand=True, padx=14, pady=14)
            control_body.grid_columnconfigure((0, 1), weight=1, uniform="train_buttons")
            ctk.CTkButton(control_body, text="开始训练", height=34, fg_color=COLORS["green"], text_color=COLORS["text"], command=self.start).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
            row = ctk.CTkFrame(control_body, fg_color="transparent")
            row.grid(row=1, column=0, columnspan=2, sticky="ew")
            row.grid_columnconfigure((0, 1), weight=1, uniform="train_buttons")
            ctk.CTkButton(row, text="停止训练", height=34, fg_color=COLORS["soft"], text_color=COLORS["text"], command=self.stop).grid(row=0, column=0, sticky="ew", padx=(0, 7))
            ctk.CTkButton(row, text="查看模型报告", height=34, fg_color=COLORS["yellow"], text_color=COLORS["text"], command=self.open_result).grid(row=0, column=1, sticky="ew", padx=(7, 0))

            status = self.panel(action)
            status.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            status_body = ctk.CTkFrame(status, fg_color="transparent")
            status_body.pack(fill="both", expand=True, padx=12, pady=10)
            status_body.grid_columnconfigure((0, 1, 2, 3), weight=1)
            self.metric_labels = {}
            for index, key_label in enumerate([("gpu", "GPU"), ("vram", "显存占用"), ("cpu", "CPU占用"), ("memory", "内存占用")]):
                card, label = self.metric_card(status_body, key_label[1], "待检测")
                card.grid(row=0, column=index, sticky="nsew", padx=6, pady=6)
                self.metric_labels[key_label[0]] = label

            def build_progress_header(parent):
                self.progress = ctk.CTkProgressBar(parent, width=220)
                self.progress.pack(side="left", padx=(0, 10))
                self.progress.set(0)
                self.progress_label = ctk.CTkLabel(parent, text="0%", width=44, anchor="e", font=FONTS["stat"], text_color=COLORS["deep"])
                self.progress_label.pack(side="left")

            log_panel = self.panel(self, "训练日志", header_builder=build_progress_header)
            log_panel.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
            log_body = ctk.CTkFrame(log_panel, fg_color="transparent")
            log_body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            log_body.grid_columnconfigure(0, weight=1)
            log_body.grid_rowconfigure(0, weight=1)
            self.log = ctk.CTkTextbox(log_body, height=300, fg_color="#FBFCFD", border_width=1, border_color="#E4EBF2", font=FONTS["mono"])
            self.log.grid(row=0, column=0, sticky="nsew")
            self.log.insert("end", "pixi run yolo obb train model=data/yolov8m-obb.yaml data=data/data.yaml epochs=800 imgsz=640 batch=16 device=0\n等待开始训练...")

        def on_show(self):
            self.refresh_status_async()

        def refresh_status_async(self):
            if self._status_loading:
                return
            self._status_loading = True
            for label in self.metric_labels.values():
                label.configure(text="检测中...")
            self.app.run_background(
                "train_status",
                lambda: {"status": system_status(), "cuda": torch_cuda_summary()},
            )

        def apply_status(self, payload):
            self._status_loading = False
            status = payload["status"]
            cuda = payload["cuda"]
            values = {
                "gpu": f"{self.short_gpu_name(status.get('gpu') or cuda.get('gpu', '待检测'))} · {status.get('gpu_usage', '待检测')}",
                "vram": status.get("vram", "待检测"),
                "cpu": status.get("cpu", "待检测"),
                "memory": status.get("memory", "待检测"),
            }
            for key, value in values.items():
                self.metric_labels[key].configure(text=value)

        def short_gpu_name(self, name: str):
            cleaned = name.replace("NVIDIA GeForce ", "").replace(" Laptop GPU", "").replace("NVIDIA ", "")
            return cleaned or "待检测"

        def collect_config(self):
            config = {key: var.get() for key, var in self.train_vars.items()}
            config["task_mode"] = infer_task_mode_from_model(config.get("model_yaml") or config.get("base_model") or config.get("pretrained"))
            for key in ("epochs", "patience", "workers", "batch", "imgsz"):
                config[key] = int(config[key])
            config["lr"] = float(config["lr"])
            for key, card in self.augment_cards.items():
                default_value = self.app.settings["training"].get(key, 0)
                config[key] = default_value if card.value.get() else 0  # type: ignore[attr-defined]
            return config

        def start(self):
            config = self.collect_config()
            command = build_train_command(config)
            self.log.delete("1.0", "end")
            self.log.insert("end", " ".join(command) + "\n")
            self.set_progress(0.0)
            queue = Queue()
            self.app.training_handle = spawn_logged_process(command, str(ROOT), queue)
            self.app.set_status("训练中")

            def forward():
                while True:
                    event, payload = queue.get()
                    if event == "log":
                        self.app.command_queue.put(("train_log", payload))
                    elif event == "exit":
                        self.app.command_queue.put(("train_exit", payload))
                        break

            threading.Thread(target=forward, daemon=True).start()

        def stop(self):
            stop_process(self.app.training_handle)
            self.append_log("已请求停止训练。")

        def open_result(self):
            path = Path(self.train_vars["project"].get())
            if path.exists():
                os.startfile(path)  # type: ignore[attr-defined]

        def append_log(self, text):
            self.log.insert("end", text + "\n")
            self.log.see("end")

        def set_progress(self, value: float):
            value = max(0.0, min(1.0, value))
            self.progress.set(value)
            self.progress_label.configure(text=f"{round(value * 100)}%")

    class ValidatePage(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self.source_ref = None
            self.result_ref = None
            self.detect_results = []
            self.detect_index = -1
            self._model_scan_started = False
            self._build()

        def _build(self):
            self.validate_layout = "30/70"
            self.grid_columnconfigure(0, weight=3, uniform="validate")
            self.grid_columnconfigure(1, weight=7, uniform="validate")
            self.grid_rowconfigure(0, weight=1)
            left = ctk.CTkFrame(self, fg_color="transparent")
            left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            right = ctk.CTkFrame(self, fg_color="transparent")
            right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            right.grid_columnconfigure((0, 1), weight=1)
            right.grid_rowconfigure(1, weight=1)
            right.grid_rowconfigure(2, weight=0)

            cfg = self.panel(left, "模型配置")
            cfg.pack(fill="x", pady=(0, 12))
            validation = self.app.settings["validation"]
            cfg_body = ctk.CTkFrame(cfg, fg_color="transparent")
            cfg_body.pack(fill="x", padx=16, pady=(0, 12))
            self.model_var = self.compact_path_field(cfg_body, "选择模型", validation["model_path"], self.pick_model)
            conf_row = ctk.CTkFrame(cfg, fg_color="transparent")
            conf_row.pack(fill="x", padx=16, pady=(0, 10))
            conf_row.grid_columnconfigure((0, 1), weight=1)
            conf_holder = ctk.CTkFrame(conf_row, fg_color="transparent")
            iou_holder = ctk.CTkFrame(conf_row, fg_color="transparent")
            conf_holder.grid(row=0, column=0, sticky="ew", padx=(0, 12))
            iou_holder.grid(row=0, column=1, sticky="ew", padx=(12, 0))
            self.conf_var = self.compact_field(conf_holder, "置信度", str(validation["confidence"]))
            self.iou_var = self.compact_field(iou_holder, "IoU", str(validation["iou"]))

            src = self.panel(left, "检测源配置")
            src.pack(fill="x", pady=(0, 12))
            src_body = ctk.CTkFrame(src, fg_color="transparent")
            src_body.pack(fill="x", padx=16, pady=(0, 12))
            self.mode_var = self.compact_option_field(src_body, "检测模式", "图片/视频文件夹", ["图片/视频文件夹", "摄像头"], self.on_source_mode_change)
            self.source_row = ctk.CTkFrame(src_body, fg_color="transparent")
            self.source_row.pack(fill="x", padx=0, pady=0)
            self.source_var = self.compact_path_field(self.source_row, "输入源", validation["source_path"], self.pick_source)
            self.camera_row = ctk.CTkFrame(src_body, fg_color="transparent")
            self.camera_var = self.compact_option_field(self.camera_row, "摄像头", str(validation["camera_index"]), ["0", "1", "2", "3"])
            self.on_source_mode_change(self.mode_var.get())

            control = self.panel(left, "检测控制")
            control.pack(fill="both", expand=True)
            row = ctk.CTkFrame(control, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(0, 8))
            row.grid_columnconfigure((0, 1, 2), weight=1, uniform="detect_buttons")
            ctk.CTkButton(row, text="开始检测", height=34, fg_color=COLORS["green"], text_color=COLORS["text"], command=self.start).grid(row=0, column=0, sticky="ew", padx=(0, 4))
            ctk.CTkButton(row, text="暂停", height=34, fg_color=COLORS["soft"], text_color=COLORS["text"]).grid(row=0, column=1, sticky="ew", padx=4)
            ctk.CTkButton(row, text="停止", height=34, fg_color=COLORS["soft"], text_color=COLORS["text"], command=self.stop).grid(row=0, column=2, sticky="ew", padx=(4, 0))
            self.detect_progress = ctk.CTkProgressBar(control)
            self.detect_progress.pack(fill="x", padx=16, pady=(0, 8))
            self.detect_progress.set(0)
            self.detect_log = ctk.CTkTextbox(control, height=170, font=FONTS["mono"])
            self.detect_log.pack(fill="both", expand=True, padx=16, pady=(0, 16))

            viewer_bar = ctk.CTkFrame(right, fg_color="transparent")
            viewer_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            viewer_bar.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(viewer_bar, text="批量检测结果:", font=FONTS["body"], text_color=COLORS["text"], anchor="w").grid(row=0, column=0, sticky="w")
            controls = ctk.CTkFrame(viewer_bar, fg_color="transparent")
            controls.grid(row=0, column=1, sticky="e")
            ctk.CTkButton(controls, text="⬅ 上一个", width=92, height=30, fg_color=COLORS["soft"], text_color=COLORS["text"], command=self.prev_result).pack(side="left", padx=4)
            self.result_counter = ctk.CTkLabel(controls, text="0/0", width=52, anchor="center", font=FONTS["stat"], text_color=COLORS["deep"])
            self.result_counter.pack(side="left", padx=6)
            ctk.CTkButton(controls, text="下一个 ➡", width=92, height=30, fg_color=COLORS["soft"], text_color=COLORS["text"], command=self.next_result).pack(side="left", padx=4)
            ctk.CTkButton(controls, text="💾 保存结果", width=104, height=30, fg_color=COLORS["soft"], text_color=COLORS["text"], command=self.save_current_result).pack(side="left", padx=4)
            ctk.CTkButton(controls, text="🗑 清空结果", width=104, height=30, fg_color=COLORS["soft"], text_color=COLORS["text"], command=self.clear_results).pack(side="left", padx=4)

            source_panel = self.panel(right, "源")
            source_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
            result_panel = self.panel(right, "检测结果")
            result_panel.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
            self.source_canvas = self.app.tk_module.Canvas(source_panel, bg="#F8FBFD", highlightthickness=0)
            self.source_canvas.pack(fill="both", expand=True, padx=18, pady=(8, 18))
            self.result_canvas = self.app.tk_module.Canvas(result_panel, bg="#F8FBFD", highlightthickness=0)
            self.result_canvas.pack(fill="both", expand=True, padx=18, pady=(8, 18))

            table_panel = self.panel(right, "检测结果详情表")
            table_panel.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            columns = ("序号", "类别", "置信度", "坐标(x,y)", "尺寸(w×h)", "角度")
            self.table = self.app.ttk_module.Treeview(table_panel, columns=columns, show="headings", height=7)
            for column in columns:
                self.table.heading(column, text=column)
                self.table.column(column, anchor="center", width=110)
            self.table.pack(fill="x", padx=16, pady=(0, 16))

        def on_show(self):
            if not self.model_var.get() and not self._model_scan_started:
                self._model_scan_started = True
                self.app.run_background(
                    "validate_models",
                    lambda: scan_candidate_models(Path(self.app.settings["paths"]["result_dir"])),
                )

        def apply_model_candidates(self, candidates):
            self._model_scan_started = False
            if self.model_var.get() or not candidates:
                return
            self.model_var.set(str(candidates[0]))
            self.model_var.display_var.set(self.compact_path(candidates[0], 4))  # type: ignore[attr-defined]

        def pick_model(self, var, display_var=None):
            path = self.app.filedialog.askopenfilename(filetypes=[("PyTorch 模型", "*.pt"), ("所有文件", "*.*")])
            if path:
                var.set(path)
                if display_var is not None:
                    display_var.set(self.compact_path(path, 4))

        def pick_source(self, var, display_var=None):
            path = self.app.filedialog.askdirectory()
            if path:
                self.source_var.set(path)
                if display_var is not None:
                    display_var.set(self.compact_path(path, 4))

        def on_source_mode_change(self, value):
            if value == "摄像头":
                self.source_row.pack_forget()
                self.camera_row.pack(fill="x", padx=0, pady=0)
            else:
                self.camera_row.pack_forget()
                self.source_row.pack(fill="x", padx=0, pady=0)

        def start(self):
            self.detect_log.delete("1.0", "end")
            self.app.detect_stop.clear()
            config = {
                "model_path": self.model_var.get(),
                "source_mode": "摄像头" if self.mode_var.get() == "摄像头" else "图片文件夹",
                "source_path": self.source_var.get(),
                "camera_index": int(self.camera_var.get() or 0),
                "confidence": float(self.conf_var.get()),
                "iou": float(self.iou_var.get()),
                "save_dir": self.app.settings["validation"]["save_dir"],
            }

            def worker():
                try:
                    run_prediction(config, self.app.detect_stop, lambda payload: self.app.command_queue.put(("detect_result", payload)))
                except Exception:
                    self.app.command_queue.put(("detect_log", traceback.format_exc()))
                self.app.command_queue.put(("detect_done", None))

            self.app.detect_thread = threading.Thread(target=worker, daemon=True)
            self.app.detect_thread.start()
            self.app.set_status("检测中")

        def stop(self):
            self.app.detect_stop.set()
            self.append_log("已请求停止检测。")

        def append_log(self, text):
            self.detect_log.insert("end", text + "\n")
            self.detect_log.see("end")

        def handle_result(self, payload):
            self.detect_results.append(payload)
            self.detect_index = len(self.detect_results) - 1
            self.show_detection_payload(payload)

        def show_detection_payload(self, payload):
            self._display(self.source_canvas, payload["source_image"], "source")
            self._display(self.result_canvas, payload["result_image"], "result")
            self.table.delete(*self.table.get_children())
            for index, item in enumerate(payload["items"], start=1):
                self.table.insert("", "end", values=(index, item.label, f"{item.confidence:.3f}", f"({item.center_x:.1f}, {item.center_y:.1f})", f"{item.width:.1f}×{item.height:.1f}", f"{item.angle:.1f}"))
            elapsed = payload.get("elapsed", 0.0)
            fps = (1 / elapsed) if elapsed else 0
            self.result_counter.configure(text=f"{self.detect_index + 1}/{len(self.detect_results)}")
            self.append_log(f"{payload.get('status')} | 单张耗时: {elapsed * 1000:.1f}ms | FPS: {fps:.1f} | 结果: {len(payload['items'])} 个")

        def prev_result(self):
            if not self.detect_results:
                return
            self.detect_index = (self.detect_index - 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def next_result(self):
            if not self.detect_results:
                return
            self.detect_index = (self.detect_index + 1) % len(self.detect_results)
            self.show_detection_payload(self.detect_results[self.detect_index])

        def save_current_result(self):
            if not self.detect_results or self.detect_index < 0:
                return
            payload = self.detect_results[self.detect_index]
            save_dir = Path(self.app.settings["validation"]["save_dir"])
            save_dir.mkdir(parents=True, exist_ok=True)
            filename = f"gui_result_{self.detect_index + 1:04d}.png"
            payload["result_image"].save(save_dir / filename)
            self.append_log(f"已保存结果: {save_dir / filename}")

        def clear_results(self):
            self.detect_results.clear()
            self.detect_index = -1
            self.result_counter.configure(text="0/0")
            self.source_canvas.delete("all")
            self.result_canvas.delete("all")
            self.table.delete(*self.table.get_children())
            self.append_log("已清空检测结果。")

        def _display(self, canvas, image, key):
            canvas.update_idletasks()
            preview = image.copy()
            preview.thumbnail((max(canvas.winfo_width(), 500) - 20, max(canvas.winfo_height(), 360) - 20))
            photo = self.app.ImageTk.PhotoImage(preview)
            canvas.delete("all")
            canvas.create_image(canvas.winfo_width() / 2, canvas.winfo_height() / 2, image=photo)
            self.app.image_refs[key] = photo

    class SettingsPage(BasePage):
        def __init__(self, master, app):
            super().__init__(master, app)
            self._status_loading = False
            self.grid_columnconfigure(0, weight=1)
            self._build()

        def _build(self):
            hero = ctk.CTkFrame(self, fg_color="transparent")
            hero.grid(row=0, column=0, sticky="ew", pady=(0, 16))
            ctk.CTkLabel(hero, text="系统设置", font=FONTS["title"], text_color="#1A3857").pack(anchor="w")
            ctk.CTkLabel(hero, text="本地环境、pixi 命令、缓存与默认模板。", font=FONTS["body"], text_color=COLORS["muted"]).pack(anchor="w")

            grid = ctk.CTkFrame(self, fg_color="transparent")
            grid.grid(row=1, column=0, sticky="nsew")
            grid.grid_columnconfigure((0, 1), weight=1)

            env_panel = self.panel(grid, "Pixi 环境")
            env_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            env_body = ctk.CTkFrame(env_panel, fg_color="transparent")
            env_body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            self.pixi_stat = self.stat_card(env_body, "Pixi", "待检测")
            self.python_stat = self.stat_card(env_body, "Python", "3.12")
            self.torch_stat = self.stat_card(env_body, "Torch", "待检测")
            self.command_stat = self.stat_card(env_body, "运行命令", "pixi run")
            self.env_log = ctk.CTkTextbox(env_body, height=150, fg_color="#FBFCFD", border_width=1, border_color="#E4EBF2", font=FONTS["mono"])
            self.env_log.pack(fill="both", expand=True, pady=(12, 0))

            template_panel = self.panel(grid, "默认项目模板")
            template_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            template_body = ctk.CTkFrame(template_panel, fg_color="transparent")
            template_body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            self.generic_stat = self.stat_card(template_body, "通用优先", "开启")
            self.weld_stat = self.stat_card(template_body, "焊缝 OBB 预设", "weld")
            self.preview_stat = self.stat_card(template_body, "危险操作", "预览后执行")
            self.settings_log = ctk.CTkTextbox(template_body, height=235, fg_color="#FBFCFD", border_width=1, border_color="#E4EBF2", font=FONTS["mono"])
            self.settings_log.pack(fill="both", expand=True, pady=(12, 0))

        def on_show(self):
            self.settings_log.delete("1.0", "end")
            self.settings_log.insert("end", json.dumps(self.app.settings, ensure_ascii=False, indent=2))
            if self._status_loading:
                return
            self._status_loading = True
            self.pixi_stat.configure(text="检测中...")
            self.torch_stat.configure(text="检测中...")
            self.env_log.delete("1.0", "end")
            self.env_log.insert("end", "正在后台检测本地环境...\n")
            self.weld_stat.configure(text=", ".join(self.app.settings["dataset"]["class_names"]))
            self.app.run_background(
                "settings_status",
                lambda: {
                    "cuda": torch_cuda_summary(),
                    "modules": detect_modules(),
                    "pixi": pixi_available(),
                },
            )

        def apply_status(self, payload):
            self._status_loading = False
            cuda = payload["cuda"]
            modules = payload["modules"]
            self.pixi_stat.configure(text="可用" if payload["pixi"] else "不可用")
            self.torch_stat.configure(text=f"CUDA {cuda['cuda']}")
            self.env_log.delete("1.0", "end")
            self.env_log.insert("end", "计划：使用 pixi.toml 管理依赖，不依赖 conda YL。\n")
            self.env_log.insert("end", json.dumps(modules, ensure_ascii=False, indent=2))

    app = WorkbenchApp()
    app.mainloop()

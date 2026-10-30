# -*- coding: utf-8 -*-
"""app.py —— 随机数生成器界面层"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from param_utils import (
    DEFAULT_COUNT,
    DEFAULT_DUPLICATE,
    DEFAULT_MAX,
    DEFAULT_MIN,
    ParamError,
    Params,
    build_params,
    generate_numbers,
)

# --------------------------------------------------------------------------
# 视觉常量
# --------------------------------------------------------------------------
FONT_FAMILY = "Microsoft YaHei UI"
FONT_TITLE = (FONT_FAMILY, 28, "bold")
FONT_AUTHOR = (FONT_FAMILY, 10)
FONT_RESULT = ("Consolas", 13)
FONT_STATUS = (FONT_FAMILY, 9)

COLOR_TITLE = "#000000"
COLOR_AUTHOR = "#009688"        # 蓝绿色
COLOR_RESULT_BG = "#fbfbfb"
COLOR_RESULT_FG = "#1f2937"
COLOR_MUTED = "#6b7280"


# ==========================================================================
# 主窗口
# ==========================================================================
class RandomApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("随机数生成器")
        self.geometry("720x640")
        self.minsize(620, 540)
        self.configure(bg="white")

        self.params: Params = Params()
        self.records: list[dict] = []      # 历史记录（内存中）

        self._init_style()
        self._build_ui()
        self._refresh_status()

    # ------------------------------------------------------------------
    def _init_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("App.TButton", font=(FONT_FAMILY, 11), padding=(14, 6))
        style.configure("Accent.TButton", font=(FONT_FAMILY, 11, "bold"),
                        padding=(18, 7))
        style.configure("White.TLabel", background="white",
                        foreground="#374151", font=(FONT_FAMILY, 10))
        style.configure("Hint.TLabel", background="white",
                        foreground=COLOR_MUTED, font=(FONT_FAMILY, 9))
        style.configure("White.TCheckbutton", background="white",
                        foreground="#374151", font=(FONT_FAMILY, 10))

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = tk.Frame(self, bg="white", padx=20, pady=16)
        outer.pack(fill="both", expand=True)

        # ---------- 标题区 ----------
        header = tk.Frame(outer, bg="white")
        header.pack(fill="x")
        tk.Label(header, text="随机数生成器", font=FONT_TITLE,
                 fg=COLOR_TITLE, bg="white").pack()
        tk.Label(header, text="作者：hand_jun", font=FONT_AUTHOR,
                 fg=COLOR_AUTHOR, bg="white").pack(pady=(2, 0))

        # ---------- 按钮区 ----------
        bar = tk.Frame(outer, bg="white")
        bar.pack(fill="x", pady=(16, 10))

        ttk.Button(bar, text="开始生成", style="Accent.TButton",
                   command=self.on_generate).pack(side="left")
        ttk.Button(bar, text="设置", style="App.TButton",
                   command=self.on_settings).pack(side="left", padx=(10, 0))
        ttk.Button(bar, text="查看历史记录", style="App.TButton",
                   command=self.on_history).pack(side="left", padx=(10, 0))

        # ---------- 结果区 ----------
        result_box = tk.LabelFrame(
            outer, text=" 生成结果 ", font=(FONT_FAMILY, 10),
            bg="white", fg="#374151", bd=1, relief="solid",
            labelanchor="nw", padx=8, pady=8,
        )
        result_box.pack(fill="both", expand=True)

        self.result_text = tk.Text(
            result_box, wrap="word", height=12,
            font=FONT_RESULT, bd=0, relief="flat",
            bg=COLOR_RESULT_BG, fg=COLOR_RESULT_FG,
            insertbackground=COLOR_RESULT_FG,
            padx=10, pady=8, state="disabled",
        )
        scroll = ttk.Scrollbar(result_box, orient="vertical",
                               command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scroll.set)
        self.result_text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        result_box.rowconfigure(0, weight=1)
        result_box.columnconfigure(0, weight=1)

        # 鼠标滚轮：无论指针是否在文本框上，都能滚动查看结果
        self.result_text.bind("<MouseWheel>", self._on_result_wheel)
        self.result_text.bind("<Button-4>", self._on_result_wheel)
        self.result_text.bind("<Button-5>", self._on_result_wheel)

        self._show_placeholder()

        # ---------- 状态栏 ----------
        self.status_label = tk.Label(
            outer, text="", anchor="w", justify="left",
            font=FONT_STATUS, fg=COLOR_MUTED, bg="white",
        )
        self.status_label.pack(fill="x", pady=(8, 0))

    # ------------------------------------------------------------------
    def _show_placeholder(self):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert(
            "1.0",
            "点击上方「开始生成」按钮，结果会显示在这里。\n\n"
            "提示：结果区域支持鼠标滚轮滚动查看。",
        )
        self.result_text.configure(state="disabled")

    # ------------------------------------------------------------------
    def _on_result_wheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.result_text.yview_scroll(delta * 3, "units")
        return "break"

    # ------------------------------------------------------------------
    def _refresh_status(self):
        p = self.params
        dup = "允许重复" if p.allow_duplicate else "不允许重复"
        self.status_label.configure(
            text=f"当前参数：范围 [{p.min_value}, {p.max_value}]　|　"
                 f"每次生成 {p.count} 个　|　{dup}　|　"
                 f"已生成 {len(self.records)} 次"
        )

    # ------------------------------------------------------------------
    def _render_numbers(self, numbers: list[int]):
        per_line = 10
        rows = []
        for start in range(0, len(numbers), per_line):
            chunk = numbers[start:start + per_line]
            rows.append("   ".join(f"{n:>6}" for n in chunk))

        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", "\n".join(rows))
        self.result_text.configure(state="disabled")
        self.result_text.yview_moveto(0.0)

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
    def on_generate(self):
        try:
            numbers = generate_numbers(self.params)
        except ParamError as exc:
            messagebox.showerror(exc.title, exc.message, parent=self)
            return
        except Exception as exc:      # 兜底，绝不让界面崩掉
            messagebox.showerror(
                "生成失败",
                f"生成时遇到了意料之外的错误：\n{exc}\n\n"
                f"【请这样处理】\n"
                f"1. 检查「设置」里的参数是否正常\n"
                f"2. 重新打开软件后再试一次",
                parent=self,
            )
            return

        self._render_numbers(numbers)
        self.records.append({
            "time": datetime.now(),
            "params": self.params.copy(),
            "numbers": numbers,
        })
        self._refresh_status()

    # ------------------------------------------------------------------
    def on_settings(self):
        SettingsDialog(self, self.params, self._apply_params)

    def _apply_params(self, params: Params):
        self.params = params
        self._refresh_status()

    # ------------------------------------------------------------------
    def on_history(self):
        HistoryWindow(self, self.records)


# ==========================================================================
# 设置窗口
# ==========================================================================
class SettingsDialog(tk.Toplevel):
    def __init__(self, master, params: Params, on_apply):
        super().__init__(master)
        self.title("设置")
        self.resizable(False, False)
        self.configure(bg="white")
        self.transient(master)
        self.on_apply = on_apply

        self.var_min = tk.StringVar(value=str(params.min_value))
        self.var_max = tk.StringVar(value=str(params.max_value))
        self.var_count = tk.StringVar(value=str(params.count))
        self.var_dup = tk.BooleanVar(value=params.allow_duplicate)

        self._build_ui()
        self._sync_dup_text()
        self._center_on(master)

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.destroy())

        self.wait_visibility()
        self.grab_set()
        self.focus_set()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = tk.Frame(self, bg="white", padx=20, pady=16)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="参数设置", font=(FONT_FAMILY, 13, "bold"),
                 fg="#111827", bg="white").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        ttk.Label(
            outer,
            text="小问题会自动纠正（小数取整 / 越界钳制 / 大小值互换）",
            style="Hint.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        self.entry_min = self._add_field(
            outer, 2, "范围 · 最小值", "整数，-10000 ~ 10000", self.var_min)
        self.entry_max = self._add_field(
            outer, 3, "范围 · 最大值", "整数，-10000 ~ 10000", self.var_max)
        self.entry_count = self._add_field(
            outer, 4, "每次生成个数", "整数，1 ~ 50", self.var_count)

        ttk.Label(outer, text="是否重复生成",
                  style="White.TLabel").grid(row=5, column=0, sticky="w", pady=6)
        self.chk_dup = ttk.Checkbutton(
            outer, variable=self.var_dup, style="White.TCheckbutton",
            command=self._sync_dup_text,
        )
        self.chk_dup.grid(row=5, column=1, columnspan=2, sticky="w", pady=6)

        buttons = tk.Frame(outer, bg="white")
        buttons.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(18, 0))
        ttk.Button(buttons, text="恢复默认", style="App.TButton",
                   command=self.on_reset).pack(side="left")
        ttk.Button(buttons, text="确定", style="Accent.TButton",
                   command=self.on_ok).pack(side="right")
        ttk.Button(buttons, text="取消", style="App.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))

    # ------------------------------------------------------------------
    def _add_field(self, parent, row, label_text, hint, variable):
        ttk.Label(parent, text=label_text,
                  style="White.TLabel").grid(row=row, column=0, sticky="w", pady=6)
        entry = tk.Entry(
            parent, textvariable=variable, width=12,
            font=(FONT_FAMILY, 11), justify="right",
            relief="solid", bd=1, bg="#ffffff",
        )
        entry.grid(row=row, column=1, sticky="e", padx=(12, 10), pady=6, ipady=3)
        ttk.Label(parent, text=hint, style="Hint.TLabel").grid(
            row=row, column=2, sticky="w", pady=6)
        return entry

    # ------------------------------------------------------------------
    def _sync_dup_text(self):
        if self.var_dup.get():
            self.chk_dup.configure(text="√ 允许重复")
        else:
            self.chk_dup.configure(text="× 不允许重复")

    # ------------------------------------------------------------------
    def on_reset(self):
        self.var_min.set(str(DEFAULT_MIN))
        self.var_max.set(str(DEFAULT_MAX))
        self.var_count.set(str(DEFAULT_COUNT))
        self.var_dup.set(DEFAULT_DUPLICATE)
        self._sync_dup_text()

    # ------------------------------------------------------------------
    def on_ok(self):
        try:
            params, corrections = build_params(
                self.var_min.get(),
                self.var_max.get(),
                self.var_count.get(),
                self.var_dup.get(),
            )
        except ParamError as exc:
            messagebox.showerror(exc.title, exc.message, parent=self)
            self._focus_field(exc.field)
            return

        if corrections:
            messagebox.showinfo(
                "参数已自动纠正",
                "为了让程序正常运行，以下参数已被自动调整：\n\n"
                + "\n".join(f"· {item}" for item in corrections)
                + "\n\n如果这不是你想要的，请修改后重新点击「确定」。",
                parent=self,
            )

        self.on_apply(params)
        self.destroy()

    # ------------------------------------------------------------------
    def _focus_field(self, field_name: str):
        mapping = {
            "最小值": self.entry_min,
            "最大值": self.entry_max,
            "每次生成个数": self.entry_count,
        }
        entry = mapping.get(field_name)
        if entry is not None:
            entry.focus_set()
            entry.select_range(0, "end")

    # ------------------------------------------------------------------
    def _center_on(self, master):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        mw, mh = master.winfo_width(), master.winfo_height()
        x = mx + max((mw - w) // 2, 0)
        y = my + max((mh - h) // 3, 0)
        self.geometry(f"+{x}+{y}")


# ==========================================================================
# 历史记录窗口（控制台风格）
# ==========================================================================
class HistoryWindow(tk.Toplevel):
    def __init__(self, master, records: list):
        super().__init__(master)
        self.title("历史记录")
        self.geometry("780x540")
        self.minsize(560, 380)
        self.transient(master)
        self.configure(bg="#1e1e1e")

        self.records = records          # 直接引用，方便清空后同步刷新
        self._build_ui()
        self._render()
        self._center_on(master)

    # ------------------------------------------------------------------
    def _build_ui(self):
        top = tk.Frame(self, bg="#252526", padx=12, pady=8)
        top.pack(fill="x")

        tk.Label(top, text="历史记录", bg="#252526", fg="#e5e7eb",
                 font=(FONT_FAMILY, 12, "bold")).pack(side="left")
        tk.Label(top, text="（时间 + 参数 + 结果）", bg="#252526",
                 fg="#7f8c8d", font=(FONT_FAMILY, 9)).pack(side="left", padx=(8, 0))

        ttk.Button(top, text="清空历史", style="App.TButton",
                   command=self.on_clear).pack(side="right")
        ttk.Button(top, text="关闭", style="App.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))

        body = tk.Frame(self, bg="#1e1e1e")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.text = tk.Text(
            body, wrap="none", bg="#1e1e1e", fg="#d4d4d4",
            font=("Consolas", 11), bd=0, relief="flat",
            insertbackground="#d4d4d4", padx=12, pady=10,
            selectbackground="#264f78", state="disabled",
        )
        yscroll = ttk.Scrollbar(body, orient="vertical",
                                command=self.text.yview)
        xscroll = ttk.Scrollbar(body, orient="horizontal",
                                command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set,
                            xscrollcommand=xscroll.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        # 控制台风格配色
        self.text.tag_configure("time", foreground="#7f8c8d")
        self.text.tag_configure("index", foreground="#dcdcaa")
        self.text.tag_configure("param", foreground="#569cd6")
        self.text.tag_configure("arrow", foreground="#6a9955")
        self.text.tag_configure("number", foreground="#4ec9b0")
        self.text.tag_configure("empty", foreground="#7f8c8d")

    # ------------------------------------------------------------------
    def _render(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")

        if not self.records:
            self.text.insert(
                "end",
                "还没有任何生成记录。\n回到主窗口点击「开始生成」试试。\n",
                "empty",
            )
            self.text.configure(state="disabled")
            return

        for i, rec in enumerate(self.records, 1):
            stamp = rec["time"].strftime("%Y-%m-%d %H:%M:%S")
            p: Params = rec["params"]

            self.text.insert("end", f"#{i:03d}  ", "index")
            self.text.insert("end", f"[{stamp}]  ", "time")
            self.text.insert("end",
                             f"范围[{p.min_value}, {p.max_value}]  ", "param")
            self.text.insert("end", f"个数:{p.count}  ", "param")
            self.text.insert(
                "end",
                ("允许重复" if p.allow_duplicate else "不重复") + "\n",
                "param",
            )
            self.text.insert("end", "      → ", "arrow")
            nums = ", ".join(str(n) for n in rec["numbers"])
            self.text.insert("end", nums + "\n\n", "number")

        self.text.configure(state="disabled")
        self.text.yview_moveto(1.0)     # 自动滚到最新一条

    # ------------------------------------------------------------------
    def on_clear(self):
        if not self.records:
            return
        if not messagebox.askyesno(
            "清空历史记录",
            f"确定要删除全部 {len(self.records)} 条记录吗？\n此操作无法撤销。",
            parent=self,
        ):
            return
        self.records.clear()
        self._render()

    # ------------------------------------------------------------------
    def _center_on(self, master):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        mw, mh = master.winfo_width(), master.winfo_height()
        x = mx + max((mw - w) // 2, 0)
        y = my + max((mh - h) // 3, 0)
        self.geometry(f"+{x}+{y}")
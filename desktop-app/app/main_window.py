from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import io
import os

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageTk


# ========== 颜色主题 ==========
COLORS = {
    "bg": "#f1f5f9",
    "white": "#ffffff",
    "primary": "#4a90d9",
    "primary_hover": "#2563eb",
    "text_dark": "#0f172a",
    "text_muted": "#64748b",
    "text_light": "#94a3b8",
    "border": "#e2e8f0",
    "user_bubble": "#eff6ff",
    "ai_bubble": "#f0fdf4",
    "code_bg": "#1e293b",
    "code_text": "#e2e8f0",
    "success": "#10b981",
    "error": "#ef4444",
    "warning": "#f59e0b",
}

FONTS = {
    "title": ("Microsoft YaHei", 18, "bold"),
    "subtitle": ("Microsoft YaHei", 14, "bold"),
    "body": ("Microsoft YaHei", 11),
    "small": ("Microsoft YaHei", 10),
    "code": ("Consolas", 11),
    "emoji": ("Segoe UI Emoji", 14),
}


class MainWindow(tk.Tk):
    """主窗口"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("📊 DeepSeek 数据分析助手")
        self.configure(bg=COLORS["bg"])

        self.geometry("1400x900")
        self.minsize(1100, 700)

        self._msg_counter = 0
        # 存储图表数据用于下载
        self._chart_data_list = []  # [(figure_bytes, chart_index), ...]

        self._build_ui()
        self._setup_menu()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开 CSV 文件 (Ctrl+O)", command=self._on_open_file)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="文件", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.bind("<Control-o>", lambda e: self._on_open_file())

    def _show_about(self):
        messagebox.showinfo(
            "关于",
            "📊 DeepSeek 数据分析助手\n\n"
            "上传 CSV 文件，用自然语言提问，\n"
            "AI 自动生成代码并执行分析绘图。\n\n"
            "基于 DeepSeek API + Python Tkinter",
            parent=self
        )

    def _on_open_file(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="选择 CSV 文件",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")]
        )
        if file_path:
            self.controller.on_file_selected(file_path)

    def _build_ui(self):
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部标题栏
        header = tk.Frame(main_container, bg=COLORS["white"], highlightthickness=0)
        header.pack(fill=tk.X, pady=(0, 8))

        title_label = tk.Label(
            header, text="📊 DeepSeek 数据分析助手",
            font=FONTS["title"], bg=COLORS["white"], fg=COLORS["text_dark"],
            anchor="w", padx=16, pady=10
        )
        title_label.pack(side=tk.LEFT)

        self.status_label = tk.Label(
            header, text="就绪 ✅",
            font=FONTS["body"], bg=COLORS["white"], fg=COLORS["text_muted"],
            padx=16
        )
        self.status_label.pack(side=tk.RIGHT)

        # PanedWindow 分割面板
        self.paned = tk.PanedWindow(
            main_container, orient=tk.HORIZONTAL,
            bg=COLORS["border"], sashwidth=4, sashrelief=tk.RAISED
        )
        self.paned.pack(fill=tk.BOTH, expand=True)

        left_panel = tk.Frame(self.paned, bg=COLORS["bg"])
        self._build_left_panel(left_panel)

        right_panel = tk.Frame(self.paned, bg=COLORS["bg"])
        self._build_right_panel(right_panel)

        self.paned.add(left_panel, minsize=300, width=500)
        self.paned.add(right_panel, minsize=400, width=700)

    def _build_left_panel(self, parent):
        # 文件选择区域
        file_frame = tk.Frame(parent, bg=COLORS["white"], highlightthickness=0)
        file_frame.pack(fill=tk.X, pady=(0, 8))

        file_icon = tk.Label(file_frame, text="📂", font=("Segoe UI Emoji", 28), bg=COLORS["white"])
        file_icon.pack(pady=(8, 4))

        file_text = tk.Label(file_frame, text="选择 CSV 文件开始分析",
                             font=FONTS["body"], bg=COLORS["white"], fg=COLORS["text_muted"])
        file_text.pack()

        select_btn = tk.Button(
            file_frame, text="📁 选择 CSV 文件",
            font=FONTS["body"], bg=COLORS["primary"], fg="white",
            activebackground=COLORS["primary_hover"], activeforeground="white",
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
            command=self._on_open_file
        )
        select_btn.pack(pady=(8, 4))
        self._bind_hover(select_btn, COLORS["primary"], COLORS["primary_hover"])

        # 数据预览区域
        preview_frame = tk.Frame(parent, bg=COLORS["white"], highlightthickness=0)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        preview_title = tk.Label(preview_frame, text="📊 数据预览",
                                 font=FONTS["subtitle"], bg=COLORS["white"],
                                 fg=COLORS["text_dark"], anchor="w")
        preview_title.pack(fill=tk.X, padx=12, pady=(12, 0))

        self.data_info = tk.Label(preview_frame, text="尚未加载数据",
                                  font=FONTS["small"], bg=COLORS["white"],
                                  fg=COLORS["text_muted"], anchor="w")
        self.data_info.pack(fill=tk.X, padx=12, pady=(2, 6))

        # 表格容器
        table_container = tk.Frame(preview_frame, bg=COLORS["white"])
        table_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.data_tree = ttk.Treeview(table_container, show="headings", height=12)

        v_scroll = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.data_tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.data_tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Treeview", font=FONTS["small"], rowheight=26)
        style.configure("Treeview.Heading", font=FONTS["small"])

    def _build_right_panel(self, parent):
        # 标题
        chat_title = tk.Label(parent, text="💬 自然语言提问",
                              font=FONTS["subtitle"], bg=COLORS["bg"],
                              fg=COLORS["text_dark"], anchor="w")
        chat_title.pack(fill=tk.X)

        # 聊天消息区域
        chat_container = tk.Frame(parent, bg=COLORS["white"])
        chat_container.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        self.chat_text = tk.Text(
            chat_container,
            font=FONTS["body"],
            bg=COLORS["white"],
            fg=COLORS["text_dark"],
            relief=tk.FLAT,
            wrap=tk.WORD,
            padx=12,
            pady=8,
            state=tk.DISABLED,
            highlightthickness=0
        )

        chat_scrollbar = ttk.Scrollbar(chat_container, orient=tk.VERTICAL, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)

        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 欢迎消息
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, "👋 选择 CSV 文件后，在这里输入你的问题，AI 会自动生成代码并分析数据！\n\n")
        self.chat_text.config(state=tk.DISABLED)

        # 输入区域
        input_frame = tk.Frame(parent, bg=COLORS["bg"])
        input_frame.pack(fill=tk.X)

        input_container = tk.Frame(input_frame, bg=COLORS["white"])
        input_container.pack(fill=tk.X, padx=0, pady=0)

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_container, textvariable=self.input_var,
            font=FONTS["body"], bg=COLORS["white"],
            fg=COLORS["text_dark"], relief=tk.FLAT,
            highlightthickness=2, highlightcolor=COLORS["primary"],
            highlightbackground=COLORS["border"]
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(8, 4), pady=8)

        send_btn = tk.Button(
            input_container, text="🚀 发送",
            font=FONTS["body"], bg=COLORS["primary"], fg="white",
            activebackground=COLORS["primary_hover"], activeforeground="white",
            relief=tk.FLAT, padx=16, pady=6, cursor="hand2",
            command=self._on_send
        )
        send_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=8)
        self._bind_hover(send_btn, COLORS["primary"], COLORS["primary_hover"])

        self.input_entry.bind("<Return>", lambda e: self._on_send())

    def _on_send(self):
        text = self.input_var.get().strip()
        if text:
            self.input_var.set("")
            self.controller.on_question_submitted(text)

    def _bind_hover(self, button, normal_color, hover_color):
        def on_enter(e):
            button.config(bg=hover_color)
        def on_leave(e):
            button.config(bg=normal_color)
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    # ========== 公共方法 ==========

    def update_status(self, message: str):
        self.status_label.config(text=message)

    def show_data_preview(self, df: pd.DataFrame, encoding: str):
        self.data_info.config(text=f"📋 {df.shape[0]} 行 × {df.shape[1]} 列 | 编码: {encoding}")

        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        columns = list(df.columns)
        self.data_tree["columns"] = columns
        for col in columns:
            self.data_tree.heading(col, text=col)
            col_width = max(80, min(150, len(str(col)) * 15))
            self.data_tree.column(col, width=col_width, minwidth=50)

        for i in range(min(len(df), 100)):
            values = [str(df.iloc[i, j]) if pd.notna(df.iloc[i, j]) else ""
                      for j in range(len(columns))]
            self.data_tree.insert("", tk.END, values=values)

    def add_chat_message(self, role: str, content: str) -> int:
        """添加聊天消息，返回消息 ID"""
        self._msg_counter += 1
        msg_id = self._msg_counter

        # 移除欢迎消息
        if msg_id == 1:
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete("1.0", tk.END)
            self.chat_text.config(state=tk.DISABLED)

        # 角色标签
        role_text = "👤 你" if role == "user" else "🤖 AI 助手"

        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"\n{role_text}\n", ("role",))
        self.chat_text.insert(tk.END, f"{content}\n", ("content",))
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

        # 配置标签样式
        self.chat_text.tag_config("role", font=("Microsoft YaHei", 11, "bold"),
                                   foreground=COLORS["primary"] if role == "user" else COLORS["success"],
                                   spacing1=8, spacing3=2)
        self.chat_text.tag_config("content", font=FONTS["body"],
                                   foreground=COLORS["text_dark"],
                                   spacing1=2, spacing3=4,
                                   lmargin1=8, lmargin2=8)

        return msg_id

    def update_chat_message(self, msg_id: int, content: str):
        """更新最后一条 AI 消息"""
        self.chat_text.config(state=tk.NORMAL)
        last_role = self.chat_text.search("🤖 AI 助手", "1.0", tk.END, backwards=True)
        if last_role:
            line_end = self.chat_text.index(f"{last_role} lineend")
            self.chat_text.delete(f"{line_end}+1c", tk.END)
            self.chat_text.insert(tk.END, f"{content}\n", ("content",))
        else:
            self.chat_text.insert(tk.END, f"{content}\n", ("content",))
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

    def add_chart(self, figure):
        """添加图表到聊天区域，附带下载按钮"""
        # 多重布局优化
        try:
            figure.set_size_inches(12, 7, forward=True)
            figure.tight_layout(pad=3.0, h_pad=2.0, w_pad=2.0)
        except Exception:
            try:
                figure.set_layout_engine('constrained', compress=True)
            except Exception:
                pass

        # 保存图片到内存（用于显示）
        buf = io.BytesIO()
        figure.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
        buf.seek(0)

        img = Image.open(buf)

        max_width = 680
        if img.width > max_width:
            ratio = max_width / img.width
            new_width = max_width
            new_height = int(img.height * ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)

        photo = ImageTk.PhotoImage(img)

        # 记录图表索引
        chart_index = len(self._chart_data_list)

        # 在 Text 中插入图片
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.image_create(tk.END, image=photo)
        self.chat_text.insert(tk.END, "\n")

        # 插入下载按钮（用可点击的文本链接）
        download_tag = f"download_{chart_index}"
        self.chat_text.insert(tk.END, "💾 下载图表  ", ("download_hint",))
        self.chat_text.insert(tk.END, "[PNG]  [JPEG]  [PDF]  [SVG]", (download_tag,))
        self.chat_text.insert(tk.END, "\n")

        # 配置标签样式
        self.chat_text.tag_config("download_hint", font=FONTS["small"],
                                   foreground=COLORS["text_muted"])
        self.chat_text.tag_config(download_tag, font=FONTS["small"],
                                   foreground=COLORS["primary"],
                                   underline=True)
        # 绑定点击事件
        self.chat_text.tag_bind(download_tag, "<Button-1>",
                                 lambda e, idx=chart_index: self._on_download_click(e, idx))
        self.chat_text.tag_bind(download_tag, "<Enter>",
                                 lambda e: self.chat_text.config(cursor="hand2"))
        self.chat_text.tag_bind(download_tag, "<Leave>",
                                 lambda e: self.chat_text.config(cursor=""))

        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)

        # 保存图表数据（用于下载）- 多种格式
        chart_data = {}
        for fmt in ['png', 'jpeg', 'pdf', 'svg']:
            try:
                b = io.BytesIO()
                if fmt == 'jpeg':
                    # JPEG 需要用 pil_kwargs 传递 quality 参数
                    figure.savefig(b, format=fmt, dpi=200, bbox_inches='tight',
                                   facecolor='white', edgecolor='none',
                                   pil_kwargs={'quality': 95})
                else:
                    figure.savefig(b, format=fmt, dpi=200, bbox_inches='tight',
                                   facecolor='white', edgecolor='none')
                b.seek(0)
                chart_data[fmt] = b
            except Exception:
                # 如果某种格式保存失败，跳过（不影响其他格式）
                pass
        self._chart_data_list.append(chart_data)

        # 保持图片引用
        if not hasattr(self, "_chart_images"):
            self._chart_images = []
        self._chart_images.append(photo)

        # 关闭 figure 释放内存
        plt.close(figure)

    def _on_download_click(self, event, chart_index):
        """点击下载链接时弹出格式选择"""
        if chart_index >= len(self._chart_data_list):
            return

        # 弹出菜单选择格式
        popup = tk.Menu(self, tearoff=0)
        popup.add_command(label="PNG 图片", command=lambda: self._download_chart(chart_index, 'png'))
        popup.add_command(label="JPEG 图片", command=lambda: self._download_chart(chart_index, 'jpeg'))
        popup.add_separator()
        popup.add_command(label="PDF 文档", command=lambda: self._download_chart(chart_index, 'pdf'))
        popup.add_command(label="SVG 矢量图", command=lambda: self._download_chart(chart_index, 'svg'))

        # 在鼠标位置弹出
        try:
            popup.tk_popup(event.x_root, event.y_root)
        finally:
            popup.grab_release()

    def _download_chart(self, chart_index: int, fmt: str):
        """下载图表到本地文件"""
        if chart_index >= len(self._chart_data_list):
            return

        chart_data = self._chart_data_list[chart_index]
        if fmt not in chart_data:
            return

        # 文件扩展名映射
        ext_map = {'png': 'png', 'jpeg': 'jpg', 'pdf': 'pdf', 'svg': 'svg'}
        ext = ext_map.get(fmt, fmt)

        # 弹出保存对话框
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title=f"保存图表为 {fmt.upper()} 格式",
            defaultextension=f".{ext}",
            filetypes=[
                (f"{fmt.upper()} 文件", f"*.{ext}"),
                ("所有文件", "*.*")
            ]
        )
        if not file_path:
            return

        try:
            # 写入文件
            data = chart_data[fmt]
            data.seek(0)
            with open(file_path, 'wb') as f:
                f.write(data.read())
            self.update_status(f"✅ 图表已保存: {Path(file_path).name}")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存图表时出错:\n{str(e)}", parent=self)
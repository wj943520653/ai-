from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import threading
import traceback
import io
import re
from contextlib import redirect_stdout

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from app.csv_reader import read_csv_with_encoding
from app.deepseek_client import DeepSeekClient
from app.main_window import MainWindow


# ========== 安全限制 ==========
BLOCKED_KEYWORDS = [
    "__import__",
    "open(",       # 文件操作
    "os.",         # 系统操作
    "subprocess",  # 子进程
    "sys.",        # 系统参数
    "eval(",       # 代码执行
    "exec(",       # 代码执行（除了我们自己的 exec）
    "compile(",    # 编译代码
    "globals()",   # 全局变量
    "locals()",    # 局部变量
    "del ",        # 删除变量
    "__builtins__",
]


class MainController:
    """主控制器，协调数据和 UI"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.df = None
        self.df_head_str = ""
        self.df_info_str = ""

        self.api_client = DeepSeekClient()
        self.window = MainWindow(self)

    def run(self):
        self.window.center_window()
        self.window.mainloop()

    def on_file_selected(self, file_path: str):
        try:
            df, encoding = read_csv_with_encoding(file_path)
            self.df = df
            self.df_head_str = df.head(5).to_string()
            self.df_info_str = str(df.dtypes)

            self.window.show_data_preview(df, encoding)
            self.window.update_status(f"✅ 已加载: {Path(file_path).name} ({df.shape[0]}行, {df.shape[1]}列)")
        except FileNotFoundError as e:
            self.window.update_status("❌ 文件不存在")
            messagebox.showerror("文件错误", str(e), parent=self.window)
        except ValueError as e:
            self.window.update_status("❌ 文件读取失败")
            messagebox.showerror("文件错误", str(e), parent=self.window)
        except Exception as e:
            self.window.update_status("❌ 加载失败")
            messagebox.showerror("加载失败", f"读取文件时发生未知错误，请重试。\n\n错误: {str(e)}", parent=self.window)

    def on_question_submitted(self, question: str):
        if self.df is None:
            self.window.update_status("⚠️ 请先加载 CSV 文件")
            messagebox.showwarning("提示", "请先选择 CSV 文件", parent=self.window)
            return

        self.window.add_chat_message("user", question)
        thinking_id = self.window.add_chat_message("assistant", "🤔 AI 正在思考并生成代码...")

        def api_worker():
            def on_response(content, error):
                if error:
                    self.window.after(0, lambda: self.window.update_chat_message(
                        thinking_id, f"❌ {error}"
                    ))
                    self.window.after(0, lambda: self.window.update_status("❌ 分析失败"))
                    return

                def update_ui():
                    # 判断返回的是代码还是对话文本
                    if self._is_code(content):
                        # 是代码 -> 执行
                        self.window.update_chat_message(thinking_id, "📊 正在分析数据...")
                        result, exec_error = self._execute_code(content)
                        if exec_error:
                            self.window.update_chat_message(thinking_id, f"❌ {exec_error}")
                            self.window.update_status("❌ 分析失败")
                        else:
                            if result is not None:
                                if isinstance(result, plt.Figure):
                                    self.window.update_chat_message(thinking_id, "📊 分析结果：")
                                    self.window.add_chart(result)
                                else:
                                    self.window.update_chat_message(thinking_id, f"📊 分析结果:\n{str(result)}")
                            else:
                                self.window.update_chat_message(thinking_id, "✅ 分析完成（无返回结果）")
                            self.window.update_status("✅ 分析完成")
                    else:
                        # 是对话文本 -> 直接显示
                        self.window.update_chat_message(thinking_id, content)
                        self.window.update_status("✅ 回答完成")

                self.window.after(0, update_ui)

            self.api_client.generate_code(question, self.df_head_str, self.df_info_str, on_response)

        thread = threading.Thread(target=api_worker, daemon=True)
        thread.start()

    def _is_code(self, content: str) -> bool:
        """判断 AI 返回的是代码还是对话文本"""
        # 如果包含 import、plt.、pd.、def 等代码特征，视为代码
        code_patterns = [
            r'^import\s+',
            r'^from\s+\w+\s+import',
            r'plt\.',
            r'pd\.',
            r'^def\s+',
            r'^result\s*=',
            r'^fig\s*=\s*plt',
            r'^ax\s*=',
        ]
        for pattern in code_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _validate_code_safety(self, code: str) -> str | None:
        """检查代码安全性"""
        for keyword in BLOCKED_KEYWORDS:
            if keyword in code:
                return (
                    f"生成的代码包含被禁止的操作（{keyword}），已阻止执行。\n"
                    f"请尝试换个问法，让 AI 使用更安全的分析方法。"
                )
        return None

    def _fix_common_code_errors(self, code: str) -> str:
        """自动修复 AI 生成代码中的常见错误"""
        fixed = code

        # 修复1: plt.xticks(rotation=45, ha='right') -> ha 不是有效参数
        fixed = re.sub(
            r'plt\.xticks\(([^)]*?),\s*ha\s*=\s*[\'\"](right|left|center)[\'\"]\s*\)',
            r'plt.xticks(\1)\nplt.gca().set_xticklabels(plt.gca().get_xticklabels(), ha="\2")',
            fixed
        )

        # 修复2: 移除 for 循环外对循环变量的引用
        lines = fixed.split('\n')
        cleaned_lines = []
        in_loop = False
        loop_vars = set()

        for line in lines:
            stripped = line.strip()
            for_match = re.match(r'for\s+(\w+(?:\s*,\s*\w+)*)\s+in\s+', stripped)
            if for_match:
                in_loop = True
                vars_str = for_match.group(1)
                loop_vars = set(v.strip() for v in vars_str.split(','))
                cleaned_lines.append(line)
                continue

            if in_loop and stripped and not stripped.startswith((' ', '\t')):
                in_loop = False
                loop_vars = set()

            if in_loop:
                cleaned_lines.append(line)
                continue

            if loop_vars and stripped:
                used_vars = {v for v in loop_vars if v in stripped}
                if used_vars:
                    continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _execute_code(self, code: str):
        import pandas as pd
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import traceback
        import io
        from contextlib import redirect_stdout

        # === 安全校验 ===
        safety_error = self._validate_code_safety(code)
        if safety_error:
            return None, safety_error

        exec_globals = {
            "pd": pd,
            "plt": plt,
            "df": self.df.copy() if self.df is not None else pd.DataFrame(),
            "result": None,
        }

        def try_exec(code_to_run):
            f = io.StringIO()
            with redirect_stdout(f):
                exec(code_to_run, exec_globals)
            result = exec_globals.get("result")
            output = f.getvalue()
            if result is None and output.strip():
                result = output.strip()
            return result

        # 第一次尝试：直接执行
        try:
            result = try_exec(code)
            return result, None
        except Exception as e:
            first_error = str(e)

        # 第二次尝试：自动修复常见错误后重试
        try:
            fixed_code = self._fix_common_code_errors(code)
            if fixed_code != code:
                result = try_exec(fixed_code)
                return result, None
        except Exception:
            pass

        # 第三次尝试：移除所有可能出问题的标注/样式行
        try:
            fallback_lines = []
            for line in code.split('\n'):
                stripped = line.strip()
                if 'xticks' in stripped or 'yticks' in stripped:
                    continue
                if '.text(' in stripped or '.annotate(' in stripped:
                    continue
                fallback_lines.append(line)
            fallback_code = '\n'.join(fallback_lines)
            if fallback_code != code:
                result = try_exec(fallback_code)
                return result, None
        except Exception:
            pass

        return None, f"代码执行时遇到错误，请尝试换个问法。\n提示: {first_error}"
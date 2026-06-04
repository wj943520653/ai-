from __future__ import annotations

import json
import os
import requests
import threading
import time
from typing import Callable


class DeepSeekClient:
    """DeepSeek API 客户端（带超时和自动重试，支持对话与代码生成）"""

    # 从环境变量读取 API Key，避免硬编码
    DEFAULT_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    MAX_RETRIES = 2
    TIMEOUT = 60
    RETRY_DELAY = 2.0

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or self.DEFAULT_API_KEY
        if not self.api_key:
            raise ValueError(
                "未配置 API Key！\n"
                "请创建 .env 文件并写入：DEEPSEEK_API_KEY=你的Key\n"
                "或设置环境变量 DEEPSEEK_API_KEY"
            )

    def generate_code(
        self,
        question: str,
        df_head: str,
        df_info: str,
        callback: Callable[[str | None, str | None], None],
    ):
        """在后台线程中调用 API，通过回调返回结果"""
        thread = threading.Thread(
            target=self._do_request_with_retry,
            args=(question, df_head, df_info, callback),
            daemon=True
        )
        thread.start()

    def _do_request_with_retry(
        self,
        question: str,
        df_head: str,
        df_info: str,
        callback: Callable[[str | None, str | None], None],
    ):
        """带重试机制的 API 请求"""
        last_error = ""

        for attempt in range(1 + self.MAX_RETRIES):
            try:
                if attempt > 0:
                    time.sleep(self.RETRY_DELAY)

                result = self._do_request(question, df_head, df_info)
                callback(result, None)
                return

            except requests.exceptions.Timeout:
                last_error = "API 请求超时，请检查网络连接后重试。"
                if attempt < self.MAX_RETRIES:
                    continue
            except requests.exceptions.ConnectionError:
                last_error = "网络连接失败，请检查网络后重试。"
                if attempt < self.MAX_RETRIES:
                    continue
            except Exception as e:
                last_error = f"请求失败: {str(e)}"
                break

        callback(None, last_error)

    def _do_request(self, question: str, df_head: str, df_info: str) -> str:
        """执行单次 API 请求，返回结果"""
        prompt = self._build_prompt(question, df_head, df_info)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1500,
        }

        resp = requests.post(
            self.API_URL,
            headers=headers,
            json=payload,
            timeout=self.TIMEOUT,
        )

        if resp.status_code != 200:
            raise Exception(f"API 错误 (HTTP {resp.status_code})")

        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip()

        # 清理 markdown 标记
        if content.startswith("```python"):
            content = content[9:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    def _build_prompt(self, question: str, df_head: str, df_info: str) -> str:
        """构建 prompt：根据问题类型决定是对话回答还是生成代码"""
        return f"""你是一个智能数据分析助手。用户上传了一个 CSV 文件，以下是文件的前5行：
{df_head}

列信息（列名及数据类型）：
{df_info}

用户的问题是：{question}

请根据问题类型选择回答方式：

【情况1 - 对话/咨询类问题】
如果用户的问题是关于"你能做什么"、"你是谁"、"有什么功能"、"你好"等对话类问题，或者是询问数据概况、列含义等不需要生成代码就能回答的问题，请直接用中文文字回答，不要生成代码。回答要简洁友好。

【情况2 - 数据分析/绘图类问题】
如果用户的问题是需要分析数据、计算统计量、生成图表等，请生成 Python 代码来完成。要求：
1. 代码必须将结果赋给一个变量名为 `result` 的变量（如果是图表，则 `result` 应为 matplotlib 的 figure 对象；如果是文本，则为字符串）。
2. 只输出代码，不要输出任何额外的解释或标记（不要用```python```包围）。
3. 可以使用 pandas、matplotlib 等常见库。数据已经读取为变量 `df`。
4. 如果是绘图，代码最后一行应该是 `result = plt.gcf()` 或者直接是 `result = fig`。
5. 确保中文正常显示（添加 plt.rcParams 设置）：
   plt.rcParams['font.sans-serif'] = ['SimHei']
   plt.rcParams['axes.unicode_minus'] = False
6. 图片尺寸设置为 (12, 7)（比默认更大，防止文字拥挤）。
7. 【重要】防止文字堆叠重叠的严格要求：
   - 如果 x 轴标签是文本且数量较多（超过8个），必须使用 `plt.xticks(rotation=45)` 旋转45度，然后使用 `ax.set_xticklabels(labels, ha='right')` 右对齐
   - 如果 x 轴标签数量非常多（超过15个），必须使用 `plt.xticks(rotation=60, fontsize=9)` 并缩小字体，然后使用 `ax.set_xticklabels(labels, ha='right')` 右对齐
   - 对于柱状图/条形图，如果类别超过10个，使用 `plt.subplots(figsize=(14, 7))` 加宽图表
   - 对于饼图，如果扇区超过6个，将小扇区合并为"其他"类别
   - 对于折线图，如果数据点超过20个，x轴标签只显示部分刻度（每隔N个显示一个）
   - 图例如果条目过多（超过8个），将图例放在图外：`plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')`
   - 始终在绘图后调用 `plt.tight_layout()` 自动调整布局
8. 确保代码简洁、正确。注意：`plt.xticks()` 不支持 `ha` 参数，不要使用 `ha=` 在 `plt.xticks()` 中。"""
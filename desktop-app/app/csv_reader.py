from __future__ import annotations

import os
import pandas as pd
import chardet


# 最大文件大小：20MB
MAX_FILE_SIZE = 20 * 1024 * 1024


def read_csv_with_encoding(file_path: str) -> tuple[pd.DataFrame, str]:
    """自动检测编码并读取 CSV 文件（带文件大小校验和编码回退）"""

    # === 1. 文件存在性检查 ===
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # === 2. 文件大小检查 ===
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise ValueError("文件为空，请选择非空 CSV 文件。")
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"文件过大（{size_mb:.1f}MB），请选择小于 20MB 的 CSV 文件。"
        )

    # === 3. 编码检测 ===
    with open(file_path, "rb") as f:
        raw_data = f.read(10000)  # 只读取前 10KB 用于编码检测

    detected = chardet.detect(raw_data)
    detected_encoding = detected.get("encoding", None)

    # 构建编码回退列表：chardet 结果优先，然后尝试常见编码
    encodings = []
    if detected_encoding:
        encodings.append(detected_encoding)
    encodings.extend(["utf-8", "gbk", "gb2312", "gb18030", "latin1", "utf-16", "cp1252"])

    # 去重（保留顺序）
    seen = set()
    unique_encodings = []
    for enc in encodings:
        if enc and enc.lower() not in seen:
            seen.add(enc.lower())
            unique_encodings.append(enc)

    # === 4. 尝试读取 ===
    last_error = ""
    for enc in unique_encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc, nrows=None)
            # === 5. 空数据检查 ===
            if df.empty:
                raise ValueError(
                    "文件读取成功但数据为空，请检查 CSV 文件是否包含有效数据。"
                )
            return df, enc
        except ValueError as ve:
            # 空数据等明确错误直接抛出
            raise ve
        except Exception as e:
            last_error = str(e)
            continue

    raise ValueError(
        f"无法识别文件编码，请确保是 CSV 格式。\n"
        f"已尝试编码: {', '.join(unique_encodings)}\n"
        f"最后错误: {last_error}"
    )
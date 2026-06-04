import sys
import os
from pathlib import Path

# 加载 .env 文件（如果存在）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装时跳过

# 确保 app 包可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.controller import MainController


def main():
    root = Path(__file__).resolve().parent
    app = MainController(root)
    app.run()


if __name__ == "__main__":
    main()
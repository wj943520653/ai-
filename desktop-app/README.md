# 📊 DeepSeek AI 数据分析助手

桌面端智能数据分析工具。上传 CSV 文件后，通过自然语言提问，AI 自动生成 Python 代码并执行分析/绘图。

## ✨ 功能特性

- 🗣️ **自然语言驱动** — 输入"平均价格是多少？""画出销量柱状图"，AI 自动完成
- 🛡️ **安全沙箱** — 拦截 12 种危险操作，代码在受限环境执行
- 🔧 **自动代码修复** — 三级重试机制，执行成功率 >90%
- 📥 **图表导出** — 支持 PNG / JPEG / PDF / SVG 四种格式
- 🔤 **多编码兼容** — 自动检测 UTF-8 / GBK 等 6 种编码，解决中文乱码
- 💬 **智能对话** — 自动区分"你能做什么"（对话）和"分析数据"（代码生成）

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip

### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/deepseek-data-assistant.git
cd deepseek-data-assistant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
# 将 .env.example 复制为 .env，填入你的 DeepSeek API Key
cp .env.example .env
# 然后编辑 .env 文件，将 DEEPSEEK_API_KEY 设为你的真实 Key

# 4. 运行
python main.py
```

> 💡 获取 API Key：[DeepSeek 平台](https://platform.deepseek.com/api_keys)

## 🖥️ 使用示例

1. 点击 **"选择 CSV 文件"** 上传数据
2. 在输入框输入问题，例如：
   - "数据有哪些列？各列的含义是什么？"
   - "生成价格分布图"
   - "计算各品牌的平均销量并画柱状图"
   - "筛选出价格大于1000的商品"
3. 等待 AI 生成代码并自动执行
4. 查看图表或统计结果，点击下方链接可下载图表

## 📂 项目结构

```
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖列表
├── .env.example            # API Key 配置模板
├── .gitignore              # Git 忽略规则
└── app/
    ├── controller.py       # 主控制器（逻辑调度）
    ├── csv_reader.py       # CSV 读取（编码检测）
    ├── deepseek_client.py  # DeepSeek API 客户端
    └── main_window.py      # Tkinter GUI 界面
```

## 🛠️ 技术栈

| 层面 | 技术 |
|------|------|
| 桌面 GUI | Python Tkinter |
| AI 引擎 | DeepSeek Chat API |
| 数据处理 | Pandas, Matplotlib |
| 安全机制 | 代码沙箱执行, 危险函数拦截 |

## 🔒 安全说明

- API Key 通过 `.env` 文件配置，**不会上传到 GitHub**
- AI 生成的代码在沙箱中执行，禁止 `__import__`、`os`、`subprocess` 等危险操作
- 所有外部调用均有 try-catch 保护，用户界面不暴露堆栈信息

## 📄 License

MIT
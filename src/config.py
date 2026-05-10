"""
配置文件 - 集中管理所有可配置参数
换 AI Provider 只需改这里
"""

import os

# ── AI 模型配置 ──────────────────────────────────────────
# 可选: "deepseek", "zhipu", "siliconflow"
AI_PROVIDER = "zhipu"          # ✅ 已在用智谱 GLM-4-Flash（国内稳定，有免费额度）

# DeepSeek (platform.deepseek.com)
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# 智谱 GLM-4-Flash (open.bigmodel.cn) ✅ 推荐，国内访问稳定
# 从环境变量读取，如果没有则使用默认值（本地开发）
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "YOUR_ZHIPU_API_KEY")
ZHIPU_MODEL = "glm-4-flash"

# SiliconFlow (聚合多家模型)
SILICONFLOW_API_KEY = "YOUR_SILICONFLOW_API_KEY"
SILICONFLOW_MODEL = "deepseek-ai/DeepSeek-V3"

# ── 股票监控配置 ──────────────────────────────────────────
# 默认监控的股票代码列表（格式：沪深=6位数字，sh/6开头沪，sz/0或3开头深）
DEFAULT_STOCKS = [
    "000001",  # 平安银行
    "600519",  # 贵州茅台
    "000858",  # 五粮液
    "601318",  # 中国平安
    "600036",  # 招商银行
]

# 行情刷新间隔（秒）
REFRESH_INTERVAL_SECONDS = 30

# ── 东方财富 API 配置 ────────────────────────────────────
EASTMONEY_BASE = "https://push2.eastmoney.com/api/qt/ulist.np/get"

# ── 分析参数 ─────────────────────────────────────────────
LOOKBACK_DAYS = 60          # 技术分析回看天数
TOP_STOCKS_LIMIT = 10       # 涨幅榜/跌幅榜展示数量
NEWS_LIMIT = 10             # 最新新闻条数

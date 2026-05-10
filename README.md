# 📈 A股股票监控分析系统

基于 Streamlit + akshare + 大模型 API 的本地网页版股票监控与分析工具。

---

## 功能特性

| 模块 | 说明 |
|------|------|
| 📡 实时行情 | 东方财富接口，秒级刷新，支持自定义股票列表 |
| 📊 涨跌榜 | 全市场涨幅榜 / 跌幅榜 / 成交额榜 TOP10 |
| 📉 技术指标 | MA / MACD / RSI / BOLL / 量比 / 量能分析 |
| 📋 基本面 | 行业 / 概念题材 / ROE / 毛利率 / 资产负债率 |
| 🤖 AI 分析 | DeepSeek / 智谱 GLM-4-Flash / SiliconFlow 自动生成研判报告 |

---

## 快速启动

### 1. 安装依赖

```bash
cd stock-monitor
pip install streamlit akshare pandas pyecharts requests schedule openai
```

### 2. 配置 API Key（启用 AI 分析必读）

编辑 `src/config.py`，选择并填写你的 AI Provider：

```python
AI_PROVIDER = "deepseek"          # 可选: "deepseek" / "zhipu" / "siliconflow"
DEEPSEEK_API_KEY = "sk-xxxxxx"   # platform.deepseek.com 注册获取
```

- **DeepSeek**：https://platform.deepseek.com（推荐，有免费额度）
- **智谱 GLM-4-Flash**：https://open.bigmodel.cn（免费额度充足）
- **SiliconFlow**：https://siliconflow.cn（聚合多模型）

不填 API Key 也可以正常使用行情和技术指标功能，只是没有 AI 分析。

### 3. 启动

```bash
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`

---

## 使用说明

1. **添加股票**：在左侧边栏输入框输入 6 位股票代码，每行一个
2. **调整刷新频率**：滑动条设置行情自动刷新间隔（10-300秒）
3. **切换股票**：在"个股深度分析"中选择要查看的股票
4. **查看分析**：切换 行情 / 技术指标 / 基本面 / AI 分析 四个标签页

---

## 项目结构

```
stock-monitor/
├── app.py               # Streamlit 主程序
├── src/
│   ├── config.py        # 配置文件（API / 股票列表 / 参数）
│   ├── data_source.py   # 数据获取模块（akshare / 东方财富）
│   └── ai_client.py     # AI 客户端（多 Provider 统一接口）
├── README.md
└── run.bat              # Windows 一键启动脚本
```

---

## ⚠️ 免责声明

本工具仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。

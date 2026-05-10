# -*- coding: utf-8 -*-
"""
AI Client - Supports DeepSeek / Zhipu GLM-4 / SiliconFlow
"""

from typing import Optional
import config

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


SYSTEM_PROMPT = (
    "You are a professional A-share (Chinese stock) analyst. "
    "Your analysis must:\n"
    "1. Base all statements on data provided - never fabricate\n"
    "2. Give clear probability assessment (HIGH/MEDIUM/LOW) with reasons\n"
    "3. Combine technical analysis (MA, MACD, RSI, KDJ, BOLL, volume) AND fundamentals (earnings, valuation, sector)\n"
    "4. Provide 1-3 actionable suggestions (short-term 1-5d / mid-term 5-30d / long-term 30d+)\n"
    "5. Include explicit risk warnings - be direct, not vague\n"
    "6. Use Markdown format, Chinese language preferred, professional tone for mainland China investors"
)


class AIClient:
    def __init__(self):
        self.provider = config.AI_PROVIDER
        self._client = None
        self._model = None
        self._init_client()

    def _init_client(self):
        if self.provider == "deepseek":
            key = getattr(config, "DEEPSEEK_API_KEY", "")
            if not key or key.startswith("YOUR_"):
                raise ValueError("Configure DeepSeek API Key in src/config.py")
            self._client = OpenAI(api_key=key, base_url=config.DEEPSEEK_BASE_URL)
            self._model  = config.DEEPSEEK_MODEL

        elif self.provider == "zhipu":
            key = getattr(config, "ZHIPU_API_KEY", "")
            if not key or key.startswith("YOUR_"):
                raise ValueError("Configure Zhipu API Key in src/config.py")
            self._client = OpenAI(api_key=key, base_url="https://open.bigmodel.cn/api/paas/v4")
            self._model  = config.ZHIPU_MODEL

        elif self.provider == "siliconflow":
            key = getattr(config, "SILICONFLOW_API_KEY", "")
            if not key or key.startswith("YOUR_"):
                raise ValueError("Configure SiliconFlow API Key in src/config.py")
            self._client = OpenAI(api_key=key, base_url="https://api.siliconflow.cn/v1")
            self._model  = config.SILICONFLOW_MODEL
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def analyze_stock(self, code, name, realtime, background, technical):
        prompt = self._build_prompt(code, name, realtime, background, technical)
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1500,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"AI Error ({self.provider}): {str(e)}\n\nPlease try again or check API configuration."

    def _build_prompt(self, code, name, rt, bg, tech):
        parts = []

        # Realtime quote
        parts.append(f"[Real-time Quote] {name} ({code})")
        if rt:
            fields = [
                ("Current Price", rt.get("current"), "CNY"),
                ("Prev Close", rt.get("prev_close"), "CNY"),
                ("Change", rt.get("change"), "CNY"),
                ("Change%", rt.get("pct"), "%"),
                ("Open", rt.get("open"), "CNY"),
                ("High", rt.get("high"), "CNY"),
                ("Low", rt.get("low"), "CNY"),
                ("Volume", rt.get("vol"), "shares"),
                ("Amount", rt.get("amount"), "CNY"),
            ]
            for label, val, unit in fields:
                if val is not None:
                    parts.append(f"  {label}: {val} {unit}")

        # Fundamentals
        if bg:
            parts.append("")
            parts.append("[Fundamentals]")
            if bg.get("industry"):
                parts.append(f"  Industry: {bg['industry']}")
            if bg.get("financial"):
                fin = bg["financial"]
                for k, v in fin.items():
                    if v is not None:
                        parts.append(f"  {k}: {v}")
            if bg.get("total_shares"):
                parts.append(f"  Total Shares: {bg['total_shares']}")

        # Technical
        if tech:
            parts.append("")
            parts.append("[Technical Indicators]")

            if tech.get("ma"):
                ma = tech["ma"]
                parts.append("  Moving Averages:")
                for k, v in ma.items():
                    if v is not None:
                        parts.append(f"    {k}: {v}")

            if tech.get("rsi"):
                rsi = tech["rsi"]
                parts.append("  RSI:")
                for k, v in rsi.items():
                    if v is not None:
                        parts.append(f"    RSI({k}): {v}")

            if tech.get("macd"):
                macd = tech["macd"]
                parts.append("  MACD:")
                for k, v in macd.items():
                    if v is not None:
                        parts.append(f"    {k}: {v}")

            if tech.get("kdj"):
                kdj = tech["kdj"]
                parts.append("  KDJ:")
                for k, v in kdj.items():
                    if v is not None:
                        parts.append(f"    {k}: {v}")

            if tech.get("boll"):
                boll = tech["boll"]
                parts.append("  BOLL:")
                for k, v in boll.items():
                    if v is not None:
                        parts.append(f"    {k}: {v}")

            if tech.get("volume"):
                vol = tech["volume"]
                parts.append("  Volume:")
                for k, v in vol.items():
                    if v is not None:
                        parts.append(f"    {k}: {v}")

            if tech.get("trend"):
                trend = tech["trend"]
                parts.append("  Trend:")
                for k, v in trend.items():
                    if v is not None:
                        parts.append(f"    {k}: {v}")

        parts.append("")
        parts.append(f"Please analyze {name} ({code}) based on the data above and output:")
        parts.append("1. Market sentiment & fund flow analysis")
        parts.append("2. Technical analysis & key price levels")
        parts.append("3. Fundamental valuation analysis")
        parts.append("4. Overall assessment (Bullish/Neutral/Bearish with probability)")
        parts.append("5. Actionable suggestions (short/mid/long term)")
        parts.append("6. Risk warning")

        return "\n".join(parts)


_ai_client = None


def get_ai_client():
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client

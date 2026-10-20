# -*- coding: utf-8 -*-
"""
LLM 只做两件事：
1. 看图，把询价单抽成结构化 JSON（有提议权）
2. 根据 Python 算好的事实，写一段中文摘要（不改数字）

所有价格、合计、同比，全部在 pricing.py 里算，不经过模型。
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from models import ExtractionResult, Item, OrderInfo
from storage import BOXES

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"

# 没有 key 时自动进入演示模式：别人 clone 下来不配环境也能跑完整流程
DEMO_MODE = os.getenv("DEMO_MODE", "0").strip() == "1" or not os.getenv(
    "DEEPSEEK_API_KEY", ""
).strip()

EXTRACTION_PROMPT = """你是制造业询价单解析器。请仔细阅读这张中文询价单图片，提取抬头信息和所有零件行，只输出一个 JSON 对象。

JSON 结构：
{
  "order": {
    "customer": "发出询价单的采购方公司名",
    "inquiry_no": "询价单号",
    "date": "YYYY-MM-DD",
    "urgent": true
  },
  "items": [
    {
      "part_name": "零件名称",
      "material": "材质",
      "weight_kg": 0.85,
      "quantity": 120,
      "unit": "件",
      "process": "CNC车削、去毛刺",
      "delivery_days": 7
    }
  ]
}

规则：
1. 只提取图片里真实存在的内容，不要编造。
2. weight_kg、quantity 必须是数字；delivery_days 必须是整数天数。
3. process 保留原文的工序组合，用顿号分隔。
4. urgent 根据备注判断：出现「急单」「加急」为 true。
5. customer 是发出询价单的采购方（页面左上角的公司名），不是「致：」后面那家公司；「致：」后面的是收件的报价方/供应商，不要填进 customer。
6. 缺失字段用 null。
7. 不要输出 Markdown 代码块或任何解释文字。"""

SUMMARY_PROMPT = """你是制造业报价助手。下面是一次报价的确定性计算结果（JSON）。请写一段 2-3 句的中文摘要，给业务员看。

要求：
- 只使用 JSON 里的数字和事实，不要编造原因、价格或交期。
- 必须提到总价、是否急单，以及与历史同材料报价的对比（如果 items 里有 change_pct）。
- 语气专业、克制，不要用感叹号，不要 Markdown，不要分点。
- 不超过 120 个汉字。

事实：
{facts}"""


def _api_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "没有找到 DEEPSEEK_API_KEY。请复制 .env.example 为 .env 并填入 key；"
            "或者设置 DEMO_MODE=1 使用内置演示数据。"
        )
    return key


def _client() -> OpenAI:
    return OpenAI(api_key=_api_key(), base_url=BASE_URL)


def _parse_json_loose(text: str) -> dict:
    """模型偶尔会用 ```json 包裹或在前后加解释，这里做一次兜底。"""
    s = (text or "").strip()
    if not s:
        raise ValueError("模型返回了空内容")
    if s.startswith("```"):
        s = s[3:].strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("模型输出里没有找到 JSON 对象")
    return json.loads(s[start : end + 1])


def _call_json(messages: list[dict], max_tokens: int = 2200) -> dict:
    client = _client()

    def once(msgs):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=msgs,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=max_tokens,
            extra_body={"thinking": {"type": "disabled"}},
        )
        return resp.choices[0].message.content or ""

    content = once(messages)
    try:
        return _parse_json_loose(content)
    except (ValueError, json.JSONDecodeError):
        # 把上一次的错误输出附回去，只重试一次
        retry_messages = messages + [
            {"role": "assistant", "content": content},
            {
                "role": "user",
                "content": "你上次的输出不是合法 JSON。请只输出一个 JSON 对象，不要代码块、不要解释。",
            },
        ]
        return _parse_json_loose(once(retry_messages))


def _to_data_url(image_base64: str) -> str:
    if image_base64.startswith("data:image/"):
        return image_base64
    # 没有前缀时按文件头猜 MIME
    mime = "image/png" if image_base64.startswith("iVBOR") else "image/jpeg"
    return f"data:{mime};base64,{image_base64}"


def extract_inquiry(image_base64: str = "") -> dict:
    """图片 -> 结构化询价单。演示模式直接读固定数据。"""
    if DEMO_MODE:
        raw = json.loads(
            (BACKEND_DIR / "data" / "demo_extraction.json").read_text(encoding="utf-8")
        )
        result = ExtractionResult(**raw)
        return {**result.model_dump(), "boxes": BOXES, "mode": "demo"}

    messages = [
        {"role": "system", "content": EXTRACTION_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请解析这张询价单，输出 JSON。"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": _to_data_url(image_base64),
                        "detail": "high",
                    },
                },
            ],
        },
    ]

    data = _call_json(messages)
    try:
        parsed = ExtractionResult(
            order=OrderInfo(**(data.get("order") or {})),
            items=[Item(**row) for row in (data.get("items") or [])],
        )
    except Exception as exc:  # Pydantic 校验失败时，带着错误重试一次
        retry = messages + [
            {"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
            {
                "role": "user",
                "content": (
                    "上一版 JSON 结构不符合要求，校验错误是："
                    f"{exc}。请严格按给定结构重新输出，只输出 JSON。"
                ),
            },
        ]
        data = _call_json(retry)
        parsed = ExtractionResult(
            order=OrderInfo(**(data.get("order") or {})),
            items=[Item(**row) for row in (data.get("items") or [])],
        )

    if not parsed.items:
        raise ValueError("模型没有从图片里识别出任何零件行")

    return {**parsed.model_dump(), "boxes": BOXES, "mode": "live"}


def template_summary(facts: dict) -> str:
    """LLM 不可用时的兜底摘要：只拼事实，不编原因。"""
    items = facts.get("items", [])
    compared = [row for row in items if row.get("change_pct") is not None]
    if compared:
        row = max(compared, key=lambda r: abs(r["change_pct"]))
        compare_text = (
            f"与历史同材料报价相比，{row['part_name']}单件价变化 "
            f"{row['change_pct']:+.1f}%"
        )
    else:
        compare_text = "暂无可对比的历史同材料报价"

    return (
        f"本次共 {facts.get('item_count', 0)} 个零件、"
        f"{facts.get('total_quantity', 0):g} 件，报价合计 ¥{facts.get('total', 0):,.2f}"
        f"（含开机费 ¥{facts.get('setup_fee', 0):,.2f}，"
        f"急单系数 {facts.get('expedite_multiplier', 1)}）。"
        f"{compare_text}。建议在报价单中保留「含税含运费、有效期 30 天」的条款。"
    )


def generate_summary(facts: dict) -> str:
    if DEMO_MODE:
        return (BACKEND_DIR / "data" / "demo_summary.txt").read_text(
            encoding="utf-8"
        ).strip()

    try:
        client = _client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARY_PROMPT.format(
                        facts=json.dumps(facts, ensure_ascii=False, indent=2)
                    ),
                }
            ],
            temperature=0.3,
            max_tokens=320,
            extra_body={"thinking": {"type": "disabled"}},
        )
        text = (resp.choices[0].message.content or "").strip()
        text = re.sub(r"^```.*?\n|```$", "", text, flags=re.S).strip()
        return text or template_summary(facts)
    except Exception:
        # 演示不能因为摘要失败而断掉
        return template_summary(facts)

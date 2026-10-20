# -*- coding: utf-8 -*-
"""本地自检：计价、历史对比、中文 PDF、LLM 看图。"""

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from models import Item, OrderInfo
from pdf_generator import build_pdf, rmb_upper
from pricing import calculate_quote

raw = json.loads((ROOT / "backend" / "data" / "demo_extraction.json").read_text("utf-8"))
order = OrderInfo(**raw["order"])
items = [Item(**row) for row in raw["items"]]

quote = calculate_quote(order, items)
print("quote_id:", quote["quote_id"])
for row in quote["line_items"]:
    print(
        f"  {row['part_name']}: 材料 {row['material_cost']:.2f} + 工序 {row['process_cost']:.2f}"
        f" = 单件 {row['unit_price']:.2f} x {row['quantity']:g} = {row['line_total']:.2f}"
        f"  上次 {row['previous']['unit_price'] if row['previous'] else '-'}"
        f"  变化 {row['change_pct']}%"
    )
print("setup:", quote["setup_fee"], "subtotal:", quote["subtotal"], "total:", quote["total"])
print("biggest:", quote["biggest_change"])
print("rmb:", rmb_upper(quote["total"]))

summary = (ROOT / "backend" / "data" / "demo_summary.txt").read_text("utf-8").strip()
pdf_bytes = build_pdf(order, quote, summary)
out = ROOT / "screenshots" / "quotation_preview.pdf"
out.write_bytes(pdf_bytes)
print("pdf:", out, len(pdf_bytes), "bytes")

# LLM 看图（真实调用一次，验证 deepseek-flash 的图片 + JSON 模式）
if "--llm" in sys.argv:
    from llm import extract_inquiry

    img = (ROOT / "backend" / "static" / "inquiry.png").read_bytes()
    b64 = base64.b64encode(img).decode("utf-8")
    got = extract_inquiry(b64)
    print("llm mode:", got["mode"])
    (ROOT / "screenshots" / "llm_result.json").write_text(
        json.dumps(got, ensure_ascii=False, indent=2), encoding="utf-8"
    )

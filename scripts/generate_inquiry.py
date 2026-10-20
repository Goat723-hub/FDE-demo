# -*- coding: utf-8 -*-
"""
生成一张「询价单」示例图片，并输出每个字段的归一化坐标。
坐标会被前端用来在图片上画高亮框。

用法：
    python scripts/generate_inquiry.py
输出：
    backend/static/inquiry.png
    backend/data/inquiry_boxes.json
"""

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_IMAGE = ROOT / "backend" / "static" / "inquiry.png"
OUT_BOXES = ROOT / "backend" / "data" / "inquiry_boxes.json"

W, H = 1240, 1754
MARGIN = 90
TABLE_W = W - MARGIN * 2

PAPER = (251, 250, 245)
INK = (31, 31, 31)
MUTED = (107, 100, 89)
RULE = (201, 194, 178)
HEADER_BG = (240, 236, 227)
RED = (185, 28, 28)

FONT_REG = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size, index=0)


def text_width(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> float:
    box = draw.textbbox((0, 0), text, font=f)
    return box[2] - box[0]


def draw_text(draw, xy, text, f, fill=INK, anchor="la"):
    draw.text(xy, text, font=f, fill=fill, anchor=anchor)


def main():
    # ---- 纸张底色 + 轻微噪点 ----
    img = Image.new("RGB", (W, H), PAPER)
    noise = Image.effect_noise((W, H), 14).convert("RGB")
    img = Image.blend(img, noise, 0.035)
    draw = ImageDraw.Draw(img)

    # ---- 页眉 ----
    draw_text(draw, (MARGIN, 74), "宏达精密机械有限公司", font(26, True))
    draw_text(
        draw,
        (MARGIN, 110),
        "HUADA PRECISION MACHINERY CO., LTD.",
        font(13),
        MUTED,
    )
    draw_text(draw, (W - MARGIN, 78), "采购部 · 询价文件", font(17), MUTED, anchor="ra")
    draw_text(draw, (W - MARGIN, 106), "PURCHASING DEPT.", font(11), MUTED, anchor="ra")

    draw_text(draw, (W / 2, 168), "询 价 单", font(58, True), anchor="ma")
    draw_text(draw, (W / 2, 244), "R E Q U E S T   F O R   Q U O T A T I O N", font(13), MUTED, anchor="ma")

    draw.line([(MARGIN, 282), (W - MARGIN, 282)], fill=INK, width=2)

    # ---- 抬头信息 ----
    meta_f = font(21)
    draw_text(draw, (MARGIN, 312), "致：", meta_f, MUTED)
    draw_text(draw, (MARGIN + 46, 312), "宁波精工制造有限公司", font(21, True))
    draw_text(draw, (MARGIN, 350), "联系人：王工  ·  138-0000-0000", meta_f, MUTED)

    draw_text(draw, (W - MARGIN - 300, 312), "询价单号：", meta_f, MUTED, anchor="ra")
    draw_text(draw, (W - MARGIN, 312), "HD-2026-1020", font(21, True), anchor="ra")
    draw_text(draw, (W - MARGIN - 300, 350), "日　　期：", meta_f, MUTED, anchor="ra")
    draw_text(draw, (W - MARGIN, 350), "2026-10-20", font(21, True), anchor="ra")

    # ---- 表格 ----
    cols = [54, 210, 160, 130, 90, 60, 246, 110]
    headers = ["序号", "零件名称", "材质", "单件重量", "数量", "单位", "工艺要求", "交期"]
    rows = [
        ["01", "不锈钢法兰盘", "304不锈钢", "0.85", "120", "件", "CNC车削、去毛刺", "7天"],
        ["02", "铝合金连接块", "6061-T6铝", "0.32", "80", "件", "CNC铣削、阳极氧化", "10天"],
        ["03", "碳钢支架", "Q235碳钢", "1.20", "200", "件", "激光切割、折弯、镀锌", "12天"],
    ]

    table_top = 420
    header_h = 56
    row_h = 78
    table_bottom = table_top + header_h + row_h * len(rows)

    # 表头底色
    draw.rectangle([MARGIN, table_top, MARGIN + TABLE_W, table_top + header_h], fill=HEADER_BG)

    # 竖向线
    x = MARGIN
    xs = [x]
    for w in cols:
        x += w
        xs.append(x)
    for x in xs:
        draw.line([(x, table_top), (x, table_bottom)], fill=RULE, width=1)
    # 横向线
    for i in range(len(rows) + 2):
        y = table_top + (header_h if i else 0) + row_h * max(0, i - 1)
        if i == 0:
            y = table_top
        elif i == 1:
            y = table_top + header_h
        else:
            y = table_top + header_h + row_h * (i - 1)
        draw.line([(MARGIN, y), (MARGIN + TABLE_W, y)], fill=RULE if i not in (0, len(rows) + 1) else INK, width=1)
    # 外框
    draw.rectangle([MARGIN, table_top, MARGIN + TABLE_W, table_bottom], outline=INK, width=2)

    # 表头文字
    for i, h in enumerate(headers):
        cx = xs[i] + cols[i] / 2
        draw_text(draw, (cx, table_top + header_h / 2 - 2), h, font(21, True), anchor="mm")

    # 单元格文字 + 坐标
    boxes = {}
    field_names = ["seq", "part_name", "material", "weight", "quantity", "unit", "process", "delivery"]
    for r_idx, row in enumerate(rows):
        top = table_top + header_h + r_idx * row_h
        item_key = f"item_{r_idx + 1}"
        boxes[item_key] = {}
        for c_idx, val in enumerate(row):
            left = xs[c_idx]
            # 文字：前两列居中，其余左对齐/居中
            if c_idx in (0, 3, 4, 5, 7):
                cx = left + cols[c_idx] / 2
                draw_text(draw, (cx, top + row_h / 2 - 1), val, font(21), anchor="mm")
            else:
                draw_text(draw, (left + 14, top + row_h / 2 - 1), val, font(21), anchor="lm")
            # 归一化坐标
            pad = 4
            boxes[item_key][field_names[c_idx]] = {
                "x": round((left - pad) / W, 5),
                "y": round((top - pad) / H, 5),
                "w": round((cols[c_idx] + pad * 2) / W, 5),
                "h": round((row_h + pad * 2) / H, 5),
            }

    # ---- 备注 ----
    note_top = table_bottom + 36
    draw_text(draw, (MARGIN, note_top), "备注", font(20, True), RED)
    draw_text(draw, (MARGIN + 60, note_top), "急单，10 月 30 日前需首批交货；表面不得有划痕，报价请注明交期。", font(20))
    draw_text(draw, (MARGIN, note_top + 42), "报价要求", font(20, True), MUTED)
    draw_text(draw, (MARGIN + 100, note_top + 42), "含税、含运费；报价有效期 30 天。", font(20), MUTED)

    # ---- 落款 ----
    sign_y = 1180
    draw.line([(MARGIN, sign_y), (MARGIN + 360, sign_y)], fill=RULE, width=1)
    draw_text(draw, (MARGIN, sign_y + 14), "采购经办人：王 磊", font(19), MUTED)
    draw.line([(MARGIN + 520, sign_y), (MARGIN + 820, sign_y)], fill=RULE, width=1)
    draw_text(draw, (MARGIN + 520, sign_y + 14), "日期：2026-10-20", font(19), MUTED)

    # ---- 红色印章 ----
    stamp = Image.new("RGBA", (420, 220), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.rounded_rectangle([4, 4, 416, 216], radius=14, outline=(185, 28, 28, 235), width=5)
    sd.text((210, 58), "宏达精密机械有限公司", font=font(27, True), fill=(185, 28, 28, 235), anchor="mm")
    sd.text((210, 112), "询 价 专 用 章", font=font(30, True), fill=(185, 28, 28, 235), anchor="mm")
    sd.text((210, 165), "2026-10-20", font=font(22), fill=(185, 28, 28, 235), anchor="mm")
    stamp = stamp.rotate(-7, expand=True, resample=Image.BICUBIC)
    img.paste(stamp, (W - MARGIN - 430, 1245), stamp)

    # ---- 页脚 ----
    draw.line([(MARGIN, H - 120), (W - MARGIN, H - 120)], fill=RULE, width=1)
    draw_text(draw, (MARGIN, H - 96), "本单据由采购部发出 · 请于 3 个工作日内报价", font(16), MUTED)
    draw_text(draw, (W - MARGIN, H - 96), "第 1 页 / 共 1 页", font(16), MUTED, anchor="ra")

    img.save(OUT_IMAGE, "PNG", optimize=True)
    OUT_BOXES.write_text(json.dumps(boxes, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"图片已生成：{OUT_IMAGE}  ({img.size[0]}x{img.size[1]})")
    print(f"坐标已生成：{OUT_BOXES}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""用 fpdf2 生成中文 PDF 报价单。全程后端完成，前端只负责下载。"""

from decimal import Decimal
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

INK = (31, 31, 31)
MUTED = (107, 100, 89)
RULE = (201, 194, 178)
HEADER_BG = (240, 236, 227)
RED = (194, 65, 12)
PAPER = (251, 250, 245)

DIGITS = "零壹贰叁肆伍陆柒捌玖"
SECTION_UNITS = ["", "万", "亿"]
SMALL_UNITS = ["仟", "佰", "拾", ""]


def _font_paths() -> tuple[Path, Path]:
    """优先用 Windows 自带字体；换系统时给出明确报错。"""
    candidates = [
        (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/msyhbd.ttc")),
        (Path("C:/Windows/Fonts/simhei.ttf"), Path("C:/Windows/Fonts/simhei.ttf")),
        (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        ),
        (
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path("/System/Library/Fonts/PingFang.ttc"),
        ),
    ]
    for regular, bold in candidates:
        if regular.exists():
            return regular, bold if bold.exists() else regular
    raise RuntimeError(
        "找不到可用的中文字体。请安装微软雅黑/黑体，或在 pdf_generator.py 里指定字体路径。"
    )


def _four_digits(n: int) -> str:
    out = ""
    pending_zero = False
    for i, unit in enumerate(SMALL_UNITS):
        digit = n // (10 ** (3 - i)) % 10
        if digit == 0:
            pending_zero = True
            continue
        if pending_zero and out:
            out += "零"
        out += DIGITS[digit] + unit
        pending_zero = False
    return out


def _int_upper(n: int) -> str:
    if n == 0:
        return "零"
    sections = []
    index = 0
    while n > 0:
        section = n % 10000
        if section:
            text = _four_digits(section)
            if section < 1000 and sections:
                text = "零" + text
            sections.append(text + SECTION_UNITS[index])
        elif sections:
            sections.append("零")
        n //= 10000
        index += 1
    return "".join(reversed(sections)).replace("零零", "零").strip("零") or "零"


def rmb_upper(amount: float) -> str:
    cents = int(round(Decimal(str(amount)) * 100))
    yuan, jiao, fen = cents // 100, (cents // 10) % 10, cents % 10
    text = _int_upper(yuan) + "元"
    if jiao == 0 and fen == 0:
        return text + "整"
    if jiao:
        text += DIGITS[jiao] + "角"
    elif fen:
        text += "零"
    if fen:
        text += DIGITS[fen] + "分"
    return text


def build_pdf(order, quote: dict, summary: str) -> bytes:
    regular, bold = _font_paths()

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(14, 14, 14)
    pdf.add_page()

    def add(path: Path, style: str):
        kwargs = {"collection_font_number": 0} if path.suffix.lower() == ".ttc" else {}
        pdf.add_font("cjk", style, fname=str(path), **kwargs)

    add(regular, "")
    add(bold, "B")
    family = "cjk"

    # ---------- 页眉 ----------
    pdf.set_text_color(*MUTED)
    pdf.set_font(family, "", 9)
    pdf.cell(0, 5, "宁波精工制造有限公司", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    pdf.set_font(family, "B", 22)
    pdf.cell(0, 12, "报 价 单", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        0,
        5,
        "Q U O T A T I O N   S H E E T",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)
    pdf.set_draw_color(*INK)
    pdf.set_line_width(0.5)
    pdf.line(14, pdf.get_y(), 196, pdf.get_y())
    pdf.ln(4)

    # ---------- 抬头 ----------
    pdf.set_text_color(*MUTED)
    pdf.set_font(family, "", 9)
    pdf.cell(28, 6, "报价单号：", new_x="RIGHT", new_y="TOP")
    pdf.set_text_color(*INK)
    pdf.set_font(family, "B", 9)
    pdf.cell(55, 6, quote.get("quote_id", "-"), new_x="RIGHT", new_y="TOP")
    pdf.set_text_color(*MUTED)
    pdf.set_font(family, "", 9)
    pdf.cell(24, 6, "报价日期：", new_x="RIGHT", new_y="TOP")
    pdf.set_text_color(*INK)
    pdf.set_font(family, "B", 9)
    pdf.cell(30, 6, order.date or "-", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(*MUTED)
    pdf.set_font(family, "", 9)
    pdf.cell(24, 6, "客户：", new_x="RIGHT", new_y="TOP")
    pdf.set_text_color(*INK)
    pdf.set_font(family, "B", 9)
    pdf.cell(100, 6, order.customer or "-", new_x="RIGHT", new_y="TOP")
    pdf.set_text_color(*MUTED)
    pdf.set_font(family, "", 9)
    pdf.cell(28, 6, "询价单号：", new_x="RIGHT", new_y="TOP")
    pdf.set_text_color(*INK)
    pdf.set_font(family, "B", 9)
    pdf.cell(40, 6, order.inquiry_no or "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # ---------- 明细表 ----------
    pdf.set_font(family, "", 8)
    headers = ["序号", "零件名称", "材质", "数量", "单件重量", "工艺要求", "单件价", "小计"]
    with pdf.table(
        col_widths=(9, 35, 23, 13, 17, 40, 20, 23),
        text_align=("CENTER", "LEFT", "LEFT", "CENTER", "CENTER", "LEFT", "RIGHT", "RIGHT"),
        line_height=5,
        headings_style=FontFace(emphasis="BOLD", fill_color=HEADER_BG),
        borders_layout="ALL",
    ) as table:
        head = table.row()
        for h in headers:
            head.cell(h)
        for i, row in enumerate(quote["line_items"], 1):
            tr = table.row()
            tr.cell(str(i))
            tr.cell(row["part_name"])
            tr.cell(row["material"])
            tr.cell(f"{row['quantity']:g} {row['unit']}")
            tr.cell(f"{row['weight_kg']:g} kg")
            tr.cell(row["process"])
            tr.cell(f"¥{row['unit_price']:,.2f}")
            tr.cell(f"¥{row['line_total']:,.2f}")

    pdf.ln(3)

    # ---------- 合计 ----------
    def total_row(label: str, value: str, bold: bool = False, color=INK):
        pdf.set_text_color(*MUTED)
        pdf.set_font(family, "", 9)
        pdf.cell(120, 6, "", border=0)
        pdf.cell(34, 6, label, align="R")
        pdf.set_text_color(*color)
        pdf.set_font(family, "B" if bold else "", 10 if bold else 9)
        pdf.cell(28, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")

    total_row("零件合计", f"¥{sum(r['line_total'] for r in quote['line_items']):,.2f}")
    total_row("开机费", f"¥{quote['setup_fee']:,.2f}")
    total_row("小计", f"¥{quote['subtotal']:,.2f}")
    if quote.get("expedite"):
        total_row("急单系数", f"× {quote['expedite_multiplier']:g}")
    pdf.ln(1)
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.6)
    pdf.line(120, pdf.get_y(), 182, pdf.get_y())
    pdf.ln(2)
    total_row("合计", f"¥{quote['total']:,.2f}", bold=True, color=RED)
    pdf.ln(1)
    pdf.set_text_color(*MUTED)
    pdf.set_font(family, "", 8)
    pdf.cell(0, 5, f"人民币大写：{rmb_upper(quote['total'])}", new_x="LMARGIN", new_y="NEXT")

    # ---------- 摘要 ----------
    pdf.ln(4)
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.3)
    pdf.line(14, pdf.get_y(), 196, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(*RED)
    pdf.set_font(family, "B", 9)
    pdf.cell(0, 6, "报价摘要", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*INK)
    pdf.set_font(family, "", 9)
    pdf.multi_cell(0, 5.6, summary, align="L")

    # ---------- 条款 ----------
    pdf.ln(4)
    pdf.set_text_color(*MUTED)
    pdf.set_font(family, "", 8)
    pdf.multi_cell(
        0,
        5,
        "报价说明：本报价含税、含运费；有效期 30 天。交期以双方确认的订单为准。\n"
        "报价方：宁波精工制造有限公司 · 联系人：王工 · 138-0000-0000",
        align="L",
    )

    return bytes(pdf.output())

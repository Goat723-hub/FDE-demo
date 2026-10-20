# -*- coding: utf-8 -*-
"""
数据层。

现在用 JSON 文件，所有读写都收口在这里；以后换 SQLite 只改这个文件。
- history.json      预置的历史报价（只读，用于对比）
- quotes_log.json   本地运行时归档的报价（可写；Serverless 环境下不持久）
- inquiry_boxes.json 询价单图片上各字段的归一化坐标
"""

import json
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

PRICE_TABLE_PATH = DATA_DIR / "price_table.json"
HISTORY_PATH = DATA_DIR / "history.json"
BOXES_PATH = DATA_DIR / "inquiry_boxes.json"
QUOTES_LOG_PATH = DATA_DIR / "quotes_log.json"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _key(value: str) -> str:
    """材质名的比较键：去空格、转大写。304 和 304不锈钢 靠别名表归并。"""
    return re.sub(r"\s+", "", value or "").upper()


PRICE_TABLE = _read_json(PRICE_TABLE_PATH, {})
HISTORY = _read_json(HISTORY_PATH, [])
BOXES = _read_json(BOXES_PATH, {})

ALIASES: dict[str, str] = {}
for _canonical, _cfg in PRICE_TABLE.get("materials", {}).items():
    ALIASES[_key(_canonical)] = _canonical
    for _alias in _cfg.get("aliases", []):
        ALIASES[_key(_alias)] = _canonical


def resolve_material(value: str) -> str | None:
    """把 304 / SUS304 / 304不锈钢 归一到 304不锈钢；不认识返回 None。"""
    return ALIASES.get(_key(value))


def last_same_material(material: str) -> dict | None:
    """找同材质、日期最近的一次历史报价。"""
    canonical = resolve_material(material)
    if not canonical:
        return None
    matches = [
        row
        for row in HISTORY
        if resolve_material(row.get("material", "")) == canonical
    ]
    if not matches:
        return None
    matches.sort(key=lambda row: (row.get("date", ""), row.get("id", "")), reverse=True)
    return matches[0]


def archive_quote(entry: dict) -> None:
    """把本次报价追加到本地日志。演示环境可写；Serverless 环境不持久。"""
    try:
        log = _read_json(QUOTES_LOG_PATH, [])
        log.append(entry)
        QUOTES_LOG_PATH.write_text(
            json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        # 只读文件系统（如 Serverless）下静默跳过，不影响主流程
        pass


def new_quote_id() -> str:
    return f"Q-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

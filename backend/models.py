# -*- coding: utf-8 -*-
"""前后端之间传递的数据结构。"""

from pydantic import BaseModel, Field


class OrderInfo(BaseModel):
    customer: str | None = None
    inquiry_no: str | None = None
    date: str | None = None
    urgent: bool = False


class Item(BaseModel):
    part_name: str
    material: str
    weight_kg: float | None = None
    quantity: float
    unit: str = "件"
    process: str = ""
    delivery_days: int | None = None


class ExtractionResult(BaseModel):
    order: OrderInfo = Field(default_factory=OrderInfo)
    items: list[Item]
    boxes: dict = Field(default_factory=dict)


class ExtractRequest(BaseModel):
    image_base64: str


class QuoteRequest(BaseModel):
    order: OrderInfo = Field(default_factory=OrderInfo)
    items: list[Item]


class SummaryRequest(BaseModel):
    facts: dict

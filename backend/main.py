# -*- coding: utf-8 -*-
"""
FastAPI 入口。

链路：
    POST /api/extract   图片 -> LLM -> 结构化字段
    POST /api/quote     Python 按价格表算钱 + 查历史对比
    POST /api/summary   Python 的事实 -> LLM 写一段话
    POST /api/pdf       后端 fpdf2 生成中文 PDF

前端只负责上传、展示、编辑、下载。
"""

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from llm import DEMO_MODE, MODEL, extract_inquiry, generate_summary
from models import ExtractRequest, QuoteRequest, SummaryRequest
from pdf_generator import build_pdf
from pricing import calculate_quote

app = FastAPI(title="FDE Demo 01 · 询价单自动报价", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    if request.url.path.startswith("/api"):
        print(f"[api] {request.method} {request.url.path} -> {response.status_code} ({elapsed:.2f}s)")
    return response


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "demo" if DEMO_MODE else "live",
        "model": MODEL,
        "backend": "fastapi",
    }


@app.post("/api/extract")
def extract(req: ExtractRequest):
    try:
        return extract_inquiry(req.image_base64)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"识别失败：{exc}") from exc


@app.post("/api/quote")
def quote(req: QuoteRequest):
    try:
        return calculate_quote(req.order, req.items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/summary")
def summary(req: SummaryRequest):
    return {"summary": generate_summary(req.facts)}


@app.post("/api/pdf")
def pdf(req: QuoteRequest):
    from pricing import calculate_quote as calc

    try:
        result = calc(req.order, req.items, archive=False)
        text = generate_summary(result["facts"])
        data = build_pdf(req.order, result, text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败：{exc}") from exc

    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="quotation.pdf"'},
    )


# 静态资源：询价单图片
app.mount("/static", StaticFiles(directory=BACKEND_DIR / "static"), name="static")

# 构建后的前端（npm run build 生成 frontend/dist）
DIST_DIR = PROJECT_DIR / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="web")
else:

    @app.get("/")
    def dev_hint():
        return JSONResponse(
            {
                "message": "前端还没有构建。开发时请运行 npm run dev（端口 5173）；"
                "或者运行 npm run build 后重启本服务。",
                "api": "/docs",
            }
        )

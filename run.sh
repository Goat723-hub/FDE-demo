#!/usr/bin/env bash
# macOS / Linux 一键启动
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "[1/3] 创建 Python 虚拟环境..."
  python3 -m venv .venv
fi

echo "[2/3] 检查后端依赖..."
.venv/bin/python -m pip install -q -r requirements.txt

if [ ! -f frontend/dist/index.html ]; then
  echo "[3/3] 首次运行，构建前端..."
  (cd frontend && npm install && npm run build)
fi

echo
echo "  地址：http://127.0.0.1:8000"
echo "  没有 .env 时自动进入演示模式，不调用模型。"
echo
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

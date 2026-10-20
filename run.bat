@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo [1/3] 创建 Python 虚拟环境...
  python -m venv .venv
)

echo [2/3] 检查后端依赖...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt

if not exist "frontend\dist\index.html" (
  echo [3/3] 首次运行，构建前端...
  pushd frontend
  call npm install
  call npm run build
  popd
)

echo.
echo   地址：http://127.0.0.1:8000
echo   没有 .env 时自动进入演示模式，不调用模型。
echo.
rem 等 3 秒再开浏览器，避免服务还没起来
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

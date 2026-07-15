@echo off
chcp 65001 >nul 2>&1
title Format Converter - Dev

echo ==========================================
echo   Format Converter - 一键开发启动
echo ==========================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请安装 Python 3.10+
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Node.js，请安装 Node.js 20+
    pause
    exit /b 1
)

:: Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] 未找到 FFmpeg，音频/视频转换将不可用
    echo        Windows: winget install ffmpeg
    echo.
)

:: Install backend deps if needed
if not exist "backend\format_converter\__init__.py" (
    echo [ERROR] 未找到后端代码，请在项目根目录运行此脚本
    pause
    exit /b 1
)

echo [1/4] 检查后端依赖...
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo       安装后端依赖...
    pip install -r backend\requirements.txt
) else (
    echo       后端依赖已就绪
)

:: Install frontend deps if needed
echo [2/4] 检查前端依赖...
if not exist "frontend\node_modules" (
    echo       安装前端依赖...
    cd frontend && npm install && cd ..
) else (
    echo       前端依赖已就绪
)

:: Start backend
echo [3/4] 启动后端 (端口 8000)...
start "FormatConverter-Backend" cmd /k "cd backend && python -m uvicorn format_converter.main:app --host 0.0.0.0 --port 8000 --reload"

:: Start frontend
echo [4/4] 启动前端 (端口 5173)...
start "FormatConverter-Frontend" cmd /k "cd frontend && npx vite --host"

:: Wait and open browser
echo.
echo 等待服务启动...
timeout /t 4 /nobreak >nul
start http://localhost:5173

echo.
echo ==========================================
echo   服务已启动！
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API文档: http://localhost:8000/api/docs
echo ==========================================
echo.
echo 按任意键关闭此窗口（服务会继续运行）
pause >nul

@echo off
chcp 65001 >nul
echo ========================================
echo   OutEye Edu 1.0 后端启动脚本
echo ========================================
echo.

cd /d "%~dp0\backend"

REM 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo [信息] 安装依赖...
pip install -r requirements.txt -q

REM 检查 .env 文件
if not exist "..\.env" (
    echo [错误] 未找到 .env 配置文件
    pause
    exit /b 1
)

REM 启动服务
echo.
echo [信息] 启动后端服务...
echo [信息] API 文档: http://localhost:8000/docs
echo [信息] 按 Ctrl+C 停止服务
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause

@echo off
chcp 65001 >nul
echo ========================================
echo   OutEye Edu 1.0 前端启动脚本
echo ========================================
echo.

cd /d "%~dp0\frontend"

REM 检查 Node.js 环境
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请安装 Node.js 18+
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

REM 检查 npm 环境
npm --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 npm
    pause
    exit /b 1
)

REM 安装依赖
echo [信息] 安装前端依赖...
call npm install
if errorlevel 1 (
    echo [错误] 安装依赖失败
    pause
    exit /b 1
)

REM 启动开发服务器
echo.
echo [信息] 启动前端开发服务器...
echo [信息] 访问地址: http://localhost:3000
echo [信息] 按 Ctrl+C 停止服务
echo.
call npm run dev

pause

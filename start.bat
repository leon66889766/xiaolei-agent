@echo off
chcp 65001 >nul
title 小雷没摸鱼agent - 后端服务

echo ============================================
echo      小雷没摸鱼agent - 后端服务启动
echo ============================================
echo.

cd /d "%~dp0backend"

echo [1/3] 检查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo Python 环境已就绪。

echo [2/3] 安装依赖...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [警告] 依赖安装可能存在问题，尝试继续启动...
)

echo [3/3] 启动后端服务 (端口 5000)...
echo.
echo 后端 API 地址: http://localhost:5000
echo 用户前端: 打开 frontend/index.html
echo 管理后台: 打开 admin/index.html
echo 默认管理员: admin / admin123
echo.
echo 按 Ctrl+C 停止服务
echo ============================================

python app.py

pause

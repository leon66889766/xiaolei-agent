@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   企业微信智能机器人 WS 客户端
echo ========================================
echo.

REM 检查 websockets 是否已安装
python -c "import websockets" 2>nul
if %errorlevel% neq 0 (
    echo [安装依赖] websockets 未安装，正在安装...
    pip install websockets
    if %errorlevel% neq 0 (
        echo [错误] websockets 安装失败，请手动执行: pip install websockets
        pause
        exit /b 1
    )
)

echo [启动] 正在连接企业微信 WebSocket...
echo.
python wework_ws_client.py

pause

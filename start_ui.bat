@echo off
REM ====================================================
REM Script: Digital Janitor UI Launcher
REM Description: Activate Conda env and start Streamlit
REM ====================================================

REM Set UTF-8 code page
chcp 65001 >nul 2>&1

echo ====================================================
echo  📁 Digital Janitor - Web UI 审批中心
echo ====================================================
echo.

echo [*] 🔧 激活虚拟环境......
call conda activate janitor
if errorlevel 1 (
    echo [ERROR] Failed to activate conda environment 'janitor'
    pause
    exit /b 1
)

echo [*] 🚀 启动 Web UI...
echo.
echo [INFO] Tips:
echo    - Web页面将自动打开 http://localhost:8501
echo    - 按 Ctrl+C 停止服务器
echo.

streamlit run app.py

pause
@echo off
chcp 65001 >nul
echo ======================================
echo   A股股票监控分析系统 启动中...
echo ======================================
cd /d "%~dp0"

REM 检查虚拟环境
if exist ".venv\Scripts\python.exe" (
    echo [使用虚拟环境 .venv]
    .venv\Scripts\streamlit run app.py --server.headless true
) else (
    echo [使用系统 Python]
    python -m streamlit run app.py --server.headless true
)

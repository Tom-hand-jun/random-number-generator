@echo off
chcp 65001 >nul
cd /d "%~dp0"

where pythonw >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 pythonw，请先安装 Python 3.8+ 并勾选 "Add Python to PATH"。
    pause
    exit /b 1
)

start "" pythonw main.py
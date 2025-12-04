@echo off
REM 快速启动脚本 - Quick Start Script
REM This script helps you quickly set up and run the project

setlocal enabledelayedexpansion

echo.
echo ========================================
echo  Map Tile Crawler - Quick Start
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM 提示用户选择操作
echo Choose an option:
echo.
echo 1. Install dependencies (安装依赖)
echo 2. Download tiles (下载瓦片)
echo 3. Stitch tiles (拼接瓦片)
echo 4. Start web server (启动 Web 服务)
echo 5. View documentation (查看文档)
echo 6. Exit (退出)
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" (
    echo.
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
    echo [OK] Dependencies installed
    pause
    goto :eof
)

if "%choice%"=="2" (
    echo.
    echo Download tiles usage:
    echo.
    echo python -m src.tile_crawler --help
    echo.
    echo Example (download Beijing area):
    echo python -m src.tile_crawler ^
    echo   --bbox 115.4,39.4,117.5,41.1 ^
    echo   --zoom 8 ^
    echo   --template "YOUR_TILE_URL_TEMPLATE" ^
    echo   --outdir out ^
    echo   --convert-webp-to-png
    echo.
    pause
    goto :eof
)

if "%choice%"=="3" (
    echo.
    echo Stitch tiles usage:
    echo.
    echo Single zoom:
    echo python -m src.stitch_tiles --zoom 8 --bbox 115.4,39.4,117.5,41.1 --output map/z8.png
    echo.
    echo Batch multiple zooms:
    echo python -m src.stitch_all --bbox 115.4,39.4,117.5,41.1 --min-zoom 7 --max-zoom 12 --output-dir map
    echo.
    pause
    goto :eof
)

if "%choice%"=="4" (
    echo.
    echo Starting Flask web server...
    echo.
    python server.py
    goto :eof
)

if "%choice%"=="5" (
    echo.
    echo Opening documentation...
    echo.
    if exist "README.md" (
        start notepad README.md
    ) else (
        echo [ERROR] README.md not found
    )
    pause
    goto :eof
)

if "%choice%"=="6" (
    exit /b 0
)

echo [ERROR] Invalid choice
pause
exit /b 1

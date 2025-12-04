# PowerShell Quick Start Script
# 快速启动脚本 - 选择要执行的操作

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Map Tile Crawler - Quick Start" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Please install from https://www.python.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Choose an option:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Install dependencies (安装依赖)"
Write-Host "2. Download tiles (下载瓦片) - Show commands"
Write-Host "3. Stitch tiles (拼接瓦片) - Show commands"
Write-Host "4. Start web server (启动 Web 服务)"
Write-Host "5. View documentation (查看文档)"
Write-Host "6. Setup Git for GitHub (配置 Git)"
Write-Host "7. Exit (退出)"
Write-Host ""

$choice = Read-Host "Enter your choice (1-7)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        pip install -r requirements.txt
        Write-Host ""
        Write-Host "[OK] Dependencies installed" -ForegroundColor Green
        Read-Host "Press Enter to exit"
    }
    
    "2" {
        Write-Host ""
        Write-Host "Download tiles - Command examples:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "python -m src.tile_crawler --help" -ForegroundColor White
        Write-Host ""
        Write-Host "Example (download Beijing area, zoom 8):" -ForegroundColor White
        Write-Host ""
        Write-Host "python -m src.tile_crawler ``" -ForegroundColor White
        Write-Host "  --bbox 115.4,39.4,117.5,41.1 ``" -ForegroundColor White
        Write-Host "  --zoom 8 ``" -ForegroundColor White
        Write-Host "  --template ""YOUR_TILE_URL_TEMPLATE"" ``" -ForegroundColor White
        Write-Host "  --outdir out ``" -ForegroundColor White
        Write-Host "  --convert-webp-to-png" -ForegroundColor White
        Write-Host "" -ForegroundColor White
        Write-Host "# 使用迁移后的脚本（同项目结构）示例：" -ForegroundColor Cyan
        Write-Host "python .\\src_all\\python\\tile_crawler.py --bbox 115.4,39.4,117.5,41.1 --zoom 8 --template \"YOUR_TILE_URL_TEMPLATE\" --outdir out" -ForegroundColor White
        Write-Host ""
        Write-Host "See USAGE.md for more examples" -ForegroundColor Green
        Read-Host "Press Enter to continue"
    }
    
    "3" {
        Write-Host ""
        Write-Host "Stitch tiles - Command examples:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Single zoom level:" -ForegroundColor White
        Write-Host "python -m src.stitch_tiles --zoom 8 --bbox 115.4,39.4,117.5,41.1 --output map/z8.png" -ForegroundColor White
        Write-Host ""
        Write-Host "Batch multiple zooms:" -ForegroundColor White
        Write-Host "python -m src.stitch_all --bbox 115.4,39.4,117.5,41.1 --min-zoom 7 --max-zoom 12 --output-dir map" -ForegroundColor White
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "4" {
        Write-Host ""
        Write-Host "Starting Flask web server (using migrated location)..." -ForegroundColor Cyan
        Write-Host "Visit http://localhost:5000 in your browser" -ForegroundColor Green
        Write-Host ""
        python .\src_all\python\server.py
    }
    
    "5" {
        Write-Host ""
        Write-Host "Documentation files:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "- README.md ............ Quick reference" -ForegroundColor White
        Write-Host "- USAGE.md ............ Complete documentation (中文)" -ForegroundColor White
        Write-Host "- GITHUB_UPLOAD.md ... GitHub upload guide" -ForegroundColor White
        Write-Host "- PROJECT_SUMMARY.md . Project completion summary" -ForegroundColor White
        Write-Host ""
        Write-Host "Opening README.md..." -ForegroundColor Cyan
        if (Test-Path "README.md") {
            & notepad.exe README.md
        } else {
            Write-Host "[ERROR] README.md not found" -ForegroundColor Red
        }
    }
    
    "6" {
        Write-Host ""
        Write-Host "GitHub Setup Instructions:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Step 1: Install Git" -ForegroundColor White
        Write-Host "Download: https://git-scm.com/download/win" -ForegroundColor White
        Write-Host ""
        Write-Host "Step 2: Configure Git user" -ForegroundColor White
        Write-Host "git config --global user.name ""Your Name""" -ForegroundColor Cyan
        Write-Host "git config --global user.email ""your.email@example.com""" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Step 3: Create GitHub repository at https://github.com/new" -ForegroundColor White
        Write-Host ""
        Write-Host "Step 4: Push to GitHub" -ForegroundColor White
        Write-Host "git init" -ForegroundColor Cyan
        Write-Host "git add ." -ForegroundColor Cyan
        Write-Host "git commit -m ""Initial commit: Map tile crawler system""" -ForegroundColor Cyan
        Write-Host "git remote add origin https://github.com/YOUR_USERNAME/map-tile-crawler.git" -ForegroundColor Cyan
        Write-Host "git branch -M main" -ForegroundColor Cyan
        Write-Host "git push -u origin main" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "See GITHUB_UPLOAD.md for detailed instructions" -ForegroundColor Green
        Write-Host ""
        Read-Host "Press Enter to continue"
    }
    
    "7" {
        Write-Host ""
        Write-Host "Goodbye!" -ForegroundColor Green
        exit 0
    }
    
    default {
        Write-Host ""
        Write-Host "[ERROR] Invalid choice" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

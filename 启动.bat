@echo off
chcp 65001 >nul
title A股量化回测系统 · 一键启动终端
echo ==============================================================================
echo        A股量化回测系统 · 机构级研究终端 (MERCURY QUANT TERMINAL)
echo ==============================================================================
echo.

:: 1. 检查 Python 环境
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 运行环境！请先安装 Python 3.8+ 并添加至系统 PATH。
    pause
    exit /b 1
)

echo [1/3] Python 环境检查通过。
echo.

:: 2. 检查核心数据与最优策略配置
if not exist "strategy\strategy.json" (
    echo [2/3] 首次启动：正在执行数据质量清洗与网格参数寻优流水线...
    python app.py --mode validate
    python app.py --mode optimize
) else (
    echo [2/3] 核心数据与寻优记录已就绪。
)
echo.

:: 3. 启动 Web 可视化看板并自动唤起浏览器
echo [3/3] 正在启动 Web 看板服务 (http://127.0.0.1:5000)...
start "" "http://127.0.0.1:5000"
echo.
echo ==============================================================================
echo 服务已成功启动！请在浏览器中查看交互看板。
echo 按 Ctrl + C 即可停止回测终端服务。
echo ==============================================================================
echo.
python app.py --mode web --port 5000

pause

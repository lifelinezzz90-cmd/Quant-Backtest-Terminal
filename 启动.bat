@echo off
title A股量化回测系统 - 一键启动终端
echo ==============================================================================
echo        A股量化回测与策略验证系统
echo ==============================================================================
echo.

set "PY="

REM 1. 优先检测系统环境变量中的 Python
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import pandas, flask" >nul 2>&1
    if not errorlevel 1 set "PY=python"
)

REM 2. 若系统 Python 不可用，尝试检测 conda quant 环境
if not defined PY (
    where conda >nul 2>&1
    if not errorlevel 1 (
        call conda run -n quant python -c "import pandas, flask" >nul 2>&1
        if not errorlevel 1 (
            set "PY=conda run -n quant --no-capture-output python"
        )
    )
)

REM 3. 错误提示与退出
if not defined PY (
    echo [错误] 未检测到可用的 Python 运行环境！
    echo 请先安装 Python 3.8+ 并确保安装了 pandas 与 flask。
    pause
    exit /b 1
)

echo [1/3] Python 运行环境就绪。
echo.

REM 4. 数据自愈：缺失清洗数据时自动补跑
if not exist "data\cleaned\000300.csv" (
    echo [2/3] 检测到清洗数据缺失，正在自动补跑数据清洗流水线...
    %PY% app.py --mode validate
)

REM 5. 配置自愈：缺失寻优结果时自动寻优
if not exist "strategy\strategy.json" (
    echo [2/3] 首次启动：正在执行数据质量清洗与网格参数寻优流水线...
    %PY% app.py --mode validate
    %PY% app.py --mode optimize
) else (
    echo [2/3] 核心数据与寻优记录已就绪。
)
echo.

REM 6. 启动 Web 可视化看板（Python 将自动拉起默认浏览器）
echo [3/3] 正在启动 Web 看板服务 (http://127.0.0.1:5000)...
echo.
echo ==============================================================================
echo 服务已成功启动！终端将自动拉起默认浏览器访问交互看板。
echo 若未自动打开，请手动在浏览器访问: http://127.0.0.1:5000
echo 按 Ctrl + C 即可停止回测终端服务。
echo ==============================================================================
echo.
%PY% app.py --mode web --port 5000

pause

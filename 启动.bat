@echo off
chcp 65001 >nul
title A股量化回测系统 · 一键启动终端
echo ==============================================================================
echo        A股量化回测系统 · 机构级研究终端 (MERCURY QUANT TERMINAL)
echo ==============================================================================
echo.

:: ===== 1. Python 环境自动探测（系统 Python 优先，Conda quant 环境自动回退）=====
set "PY="

where python >nul 2>&1
if not errorlevel 1 (
    python -c "import pandas, flask" >nul 2>&1
    if not errorlevel 1 set "PY=python"
)

if not defined PY (
    where conda >nul 2>&1
    if not errorlevel 1 (
        call conda run -n quant python -c "import pandas, flask" >nul 2>&1
        if errorlevel 1 (
            echo [环境] conda quant 环境缺失或依赖不全，正在自动准备（首次约需 2-3 分钟）...
            call conda create -n quant python=3.10 -y
            echo [环境] 正在通过清华镜像安装核心依赖...
            call conda run -n quant pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        )
        set "PY=call conda run -n quant --no-capture-output python"
    )
)

if not defined PY (
    echo [错误] 未检测到可用的 Python 运行环境！
    echo        方案 A：安装 Python 3.8+ 并加入系统 PATH 后重新双击本脚本
    echo        方案 B：安装 Miniconda 后重新双击本脚本（将自动创建 quant 环境）
    pause
    exit /b 1
)

echo [1/3] Python 运行环境就绪。
echo.

:: ===== 2. 数据自愈：清洗数据缺失自动补跑，策略配置缺失自动寻优 =====
if not exist "data\cleaned\000300.csv" (
    echo [2/3] 检测到清洗数据缺失，正在自动补跑数据清洗流水线...
    %PY% app.py --mode validate
)

if not exist "strategy\strategy.json" (
    echo [2/3] 首次启动：正在执行数据质量清洗与网格参数寻优流水线...
    %PY% app.py --mode validate
    %PY% app.py --mode optimize
) else (
    echo [2/3] 核心数据与寻优记录已就绪。
)
echo.

:: ===== 3. 启动 Web 可视化看板（由 Python 自动拉起默认浏览器）=====
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

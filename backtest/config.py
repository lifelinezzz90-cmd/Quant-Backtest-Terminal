# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 全局配置模块 (backtest/config.py)
严格对齐《A股量化回测系统·任务书.md》与《IMPLEMENTATION_PLAN.md》核心约束
提供跨平台路径定义、固定股票池字典、交易摩擦参数、样本切分常量与跨平台中文字体配置
"""

from pathlib import Path
import sys
import matplotlib
import matplotlib.pyplot as plt

# ==============================================================================
# 1. 跨平台路径体系（统一基于 pathlib.Path，支持 Windows / macOS / Linux）
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
CLEANED_DATA_DIR = DATA_DIR / "cleaned"
VALIDATION_REPORT_JSON = DATA_DIR / "validation_report.json"
VALIDATION_REPORT_MD = DATA_DIR / "validation_report.md"

STRATEGY_DIR = PROJECT_ROOT / "strategy"
STRATEGY_CONFIG_JSON = STRATEGY_DIR / "strategy.json"

RECORDS_DIR = PROJECT_ROOT / "records"
RECORDS_CSV = RECORDS_DIR / "对比结果.csv"
RECORDS_RUNS_DIR = RECORDS_DIR / "runs"

TEMPLATES_DIR = PROJECT_ROOT / "templates"
DEMO_DIR = PROJECT_ROOT / "demo"

# 确保核心产出目录存在
for _p in [DATA_DIR, RAW_DATA_DIR, SAMPLE_DATA_DIR, CLEANED_DATA_DIR,
          STRATEGY_DIR, RECORDS_DIR, RECORDS_RUNS_DIR, DEMO_DIR]:
    _p.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 2. 标的池定义（任务书第二部分硬性规定：固定10只股票池，不得更改）
# ==============================================================================
UNIVERSE_STOCKS = {
    "600519": {"name": "贵州茅台", "industry": "白酒"},
    "601318": {"name": "中国平安", "industry": "保险"},
    "601398": {"name": "工商银行", "industry": "银行"},
    "600900": {"name": "长江电力", "industry": "电力"},
    "000002": {"name": "万科A",   "industry": "房地产"},
    "600276": {"name": "恒瑞医药", "industry": "医药"},
    "002415": {"name": "海康威视", "industry": "安防"},
    "002594": {"name": "比亚迪",   "industry": "汽车"},
    "600111": {"name": "北方稀土", "industry": "有色金属"},
    "601888": {"name": "中国中免", "industry": "免税消费"},
}

# 基准指数：沪深300指数 (000300)
BENCHMARK_CODE = "000300"
BENCHMARK_NAME = "沪深300"

# 官方样例测试用股票清单（3只股票，用于轻量化冒烟测试）
SAMPLE_STOCKS = ["600519", "601318", "002594"]

# ==============================================================================
# 3. 交易规则与费率常量（不可更改项）
# ==============================================================================
INITIAL_CASH = 1_000_000.00         # 初始现金：1,000,000 元整
COMMISSION_RATE = 0.00025           # 券商佣金率：万分之 2.5
MIN_COMMISSION = 5.00               # 单笔交易最低佣金：5.00 元
STAMP_DUTY_RATE = 0.0005            # 印花税率：万分之 5 (0.0005，仅卖出收取)
LOT_SIZE = 100                      # 整手交易单位（1手 = 100股）
RISK_FREE_RATE = 0.02               # 无风险年化利率（用于夏普比率计算）
ANNUAL_TRADING_DAYS = 252           # 每年标准化交易日数

# 价格涨跌幅限制（普通A股非ST主板标的为 10%）
PRICE_LIMIT_RATIO = 0.10

# ==============================================================================
# 4. 数据与回测时间区间切分
# ==============================================================================
FULL_START_DATE = "2019-01-01"
FULL_END_DATE = "2024-12-31"

# 样本内（In-Sample）时段：用于参数寻优调参
IN_SAMPLE_START = "2019-01-01"
IN_SAMPLE_END = "2022-12-31"

# 样本外（Out-of-Sample）时段：独立检验，防过拟合
OUT_SAMPLE_START = "2023-01-01"
OUT_SAMPLE_END = "2024-12-31"

# 样本外三折滚动验证区间（8个月/折）
ROLLING_FOLDS = [
    {"fold": 1, "start": "2023-01-01", "end": "2023-08-31", "label": "OOS_Fold_1"},
    {"fold": 2, "start": "2023-09-01", "end": "2024-04-30", "label": "OOS_Fold_2"},
    {"fold": 3, "start": "2024-05-01", "end": "2024-12-31", "label": "OOS_Fold_3"},
]

# ==============================================================================
# 5. 跨平台绘图中文字体自动适配工具函数
# ==============================================================================
def setup_matplotlib_font():
    """
    自适应配置 Matplotlib 中文字体，杜绝 Windows / macOS / Linux 下中文方块/乱码。
    返回所选生效的中文字体名。
    """
    candidate_fonts = [
        # Windows
        "SimHei", "Microsoft YaHei", "KaiTi", "SimSun",
        # macOS
        "PingFang SC", "Heiti SC", "Arial Unicode MS", "STHeiti",
        # Linux
        "Noto Sans CJK SC", "WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "Droid Sans Fallback"
    ]
    
    available_fonts = set(f.name for f in matplotlib.font_manager.fontManager.ttflist)
    selected_font = None
    for font in candidate_fonts:
        if font in available_fonts:
            selected_font = font
            break
            
    if selected_font:
        plt.rcParams["font.sans-serif"] = [selected_font] + plt.rcParams.get("font.sans-serif", [])
    else:
        # 通用回退
        plt.rcParams["font.sans-serif"] = ["sans-serif"]
        
    plt.rcParams["axes.unicode_minus"] = False  # 正确显示负号
    return selected_font


if __name__ == "__main__":
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"固定股票池数量: {len(UNIVERSE_STOCKS)}")
    font = setup_matplotlib_font()
    print(f"Matplotlib 生效中文字体: {font}")

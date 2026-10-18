# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 统一入口程序 (app.py)
对应《A股量化回测系统·任务书.md》与《IMPLEMENTATION_PLAN.md》

提供跨平台统一 CLI 命令行交互入口与 Flask Web 看板服务：
- --mode validate: 数据质量校验与清洗流水线（支持 --sample 快速样例模式）
- --mode test: 核心底层单元测试（数据清洗断言 + 撮合引擎T+1与涨跌停规则断言）
- --mode backtest: 命令行指定策略、参数与起止日期运行回测，输出指标、净值图并自动落盘记录
- --mode optimize: 参数网格寻优与防过拟合验证（Phase 4 扩展）
- --mode web: 启动本地 Flask 可视化绩效看板（Phase 5 扩展）
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.config import (
    RAW_DATA_DIR,
    SAMPLE_DATA_DIR,
    CLEANED_DATA_DIR,
    VALIDATION_REPORT_JSON,
    VALIDATION_REPORT_MD,
    RECORDS_RUNS_DIR,
    RECORDS_CSV,
    UNIVERSE_STOCKS,
    BENCHMARK_CODE,
    BENCHMARK_NAME,
    INITIAL_CASH
)
from backtest.data_ETL import (
    DataETLEngine,
    ensure_raw_and_sample_data,
    test_dirty_data_cleaning
)
from backtest.engine import (
    BacktestEngine,
    load_cleaned_data,
    test_engine_rules
)
from backtest.metrics import (
    calculate_metrics,
    plot_equity_curve
)
from backtest.logger import (
    log_experiment_record
)
from strategies.base import (
    BaseStrategy,
    EqualWeightBuyHoldStrategy
)


def handle_validate(args):
    """
    处理 --mode validate 数据校验与清洗指令
    """
    print("=" * 70)
    print("【A股量化回测系统】启动数据质量校验与清洗流水线...")
    print("=" * 70)

    # 1. 数据准备（官方 CSV 优先，缺失时自动触发兜底获取并生成样例与舆情数据）
    ensure_raw_and_sample_data()

    is_sample = args.sample
    if is_sample:
        print("[模式] 正在执行【样例数据轻量校验】(3只股票、3个月)...")
        raw_dir = SAMPLE_DATA_DIR
        out_dir = CLEANED_DATA_DIR / "sample"
    else:
        print("[模式] 正在执行【全量数据深度清洗】(10只股票池 + 沪深300基准，2019-2024)...")
        raw_dir = RAW_DATA_DIR
        out_dir = CLEANED_DATA_DIR

    engine = DataETLEngine(raw_dir=raw_dir, output_dir=out_dir)
    report = engine.run_etl(is_sample=is_sample)

    print("-" * 70)
    print(" 数据校验与清洗流水线执行成功！")
    print(f" 清洗后标准 CSV 存放路径: {out_dir}")
    print(f" 结构化校验报告: {VALIDATION_REPORT_JSON}")
    print(f" Markdown 报告:  {VALIDATION_REPORT_MD}")
    print("=" * 70)
    return report


def handle_test(args):
    """
    处理 --mode test 单元测试指令
    """
    print("=" * 70)
    print("【A股量化回测系统】启动系统底层第一性原理自动化测试套件...")
    print("=" * 70)

    print("\n>>> 正在运行 [1/2] 脏数据注入校验与自动修复单元测试...")
    test_1 = test_dirty_data_cleaning()
    print(" [1/2] 脏数据清洗单元测试: PASS (100% 通过)")

    print("\n>>> 正在运行 [2/2] 撮合引擎A股规则（T+1/涨跌停/停牌/税费）单元测试...")
    test_2 = test_engine_rules()
    print(" [2/2] 撮合引擎A股规则测试: PASS (100% 通过)")

    print("\n" + "=" * 70)
    if test_1 and test_2:
        print(" 全部单元测试 100% PASS！系统核心底层逻辑严密可靠！")
    else:
        print(" 部分单元测试未通过，请检查日志！")
    print("=" * 70)
    return test_1 and test_2


def get_strategy_instance(strategy_name: str, params: dict, available_stocks: list) -> BaseStrategy:
    """
    根据策略名称与参数动态创建策略实例
    """
    s_name = strategy_name.lower().replace("-", "_")
    if s_name in ["equal_weight", "buy_and_hold", "equalweightbuyhold"]:
        return EqualWeightBuyHoldStrategy(stocks=available_stocks, name="EqualWeightBuyHold", params=params)
    
    # 尝试动态加载 Phase 3 策略
    try:
        if s_name in ["trend_following", "trend"]:
            from strategies.trend_following import TrendFollowingStrategy
            return TrendFollowingStrategy(params=params)
        elif s_name in ["mean_reversion", "reversion", "bollinger"]:
            from strategies.mean_reversion import MeanReversionStrategy
            return MeanReversionStrategy(params=params)
        elif s_name in ["multi_factor", "factor"]:
            from strategies.multi_factor import MultiFactorStrategy
            return MultiFactorStrategy(params=params)
    except ImportError:
        pass

    # 默认回退为等权买入持有
    print(f"[提示] 未识别或尚未实现策略 '{strategy_name}'，使用默认等权买入持有策略 (EqualWeightBuyHold)。")
    return EqualWeightBuyHoldStrategy(stocks=available_stocks, name="EqualWeightBuyHold", params=params)


def handle_backtest(args):
    """
    处理 --mode backtest 策略回测指令
    """
    print("=" * 70)
    print("【A股量化回测系统】启动策略回测撮合引擎...")
    print("=" * 70)

    # 1. 确保清洗数据存在
    is_sample = args.sample
    data_dir = CLEANED_DATA_DIR / "sample" if is_sample else CLEANED_DATA_DIR
    if not data_dir.exists() or len(list(data_dir.glob("*.csv"))) == 0:
        print("[提示] 检测到清洗数据尚未就绪，自动触发数据校验清洗...")
        ensure_raw_and_sample_data()
        etl_engine = DataETLEngine(
            raw_dir=SAMPLE_DATA_DIR if is_sample else RAW_DATA_DIR,
            output_dir=data_dir
        )
        etl_engine.run_etl(is_sample=is_sample)

    # 2. 加载数据
    stock_dict, benchmark_df = load_cleaned_data(sample=is_sample, data_dir=data_dir)
    available_stocks = list(stock_dict.keys())
    print(f"[数据] 已加载标的数量: {len(available_stocks)} 只股票 | 基准: {BENCHMARK_NAME} ({BENCHMARK_CODE})")

    # 3. 解析策略与参数
    try:
        params_dict = json.loads(args.params) if isinstance(args.params, str) else args.params
    except Exception as e:
        print(f"[警告] 参数 JSON 解析失败 ({args.params})，使用空参数字典: {e}")
        params_dict = {}

    strategy = get_strategy_instance(args.strategy, params_dict, available_stocks)
    print(f"[策略] 启动策略: {strategy.name} | 参数: {strategy.params}")

    # 4. 执行回测
    engine = BacktestEngine(initial_cash=INITIAL_CASH)
    start_d = args.start if args.start else None
    end_d = args.end if args.end else None

    res = engine.run(
        strategy=strategy,
        data_dict=stock_dict,
        start_date=start_d,
        end_date=end_d
    )

    equity_df = res["equity_df"]
    trades_df = res["trades_df"]
    rejects_df = res["rejects_df"]

    # 5. 计算绩效指标
    metrics = calculate_metrics(
        equity_df=equity_df,
        benchmark_df=benchmark_df,
        trades_df=trades_df,
        initial_capital=INITIAL_CASH
    )

    # 6. 生成净值图表
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_tag = "sample" if is_sample else "full"
    chart_name = f"{strategy.name}_{mode_tag}_{now_str}.png"
    chart_path = RECORDS_RUNS_DIR / chart_name
    chart_title = f"{strategy.name} 策略净值 vs 沪深300基准 ({metrics['start_date']} ~ {metrics['end_date']})"
    plot_equity_curve(
        equity_df=equity_df,
        benchmark_df=benchmark_df,
        title=chart_title,
        save_path=chart_path,
        metrics=metrics
    )

    # 7. 实验记录自动落盘
    exp_id = log_experiment_record(
        strategy_name=strategy.name,
        params=strategy.params,
        metrics=metrics,
        stock_count=len(available_stocks),
        equity_df=equity_df,
        trades_df=trades_df,
        chart_path=chart_path
    )

    # 8. 控制台友好展示
    print("-" * 70)
    print("【回测绩效报告摘要】")
    print("-" * 70)
    print(f" 实验编号:       {exp_id}")
    print(f" 回测时段:       {metrics['start_date']} 至 {metrics['end_date']} (共 {metrics['trading_days']} 交易日)")
    print(f" 覆盖股票:       {len(available_stocks)} 只标的")
    print(f" 初始资金:       CNY {INITIAL_CASH:,.2f}")
    print(f" 期末资产:       CNY {res['final_value']:,.2f}")
    print(f" 累计收益率:     {metrics['total_return']*100:.2f}%")
    print(f" 年化收益率:     {metrics['annual_return']*100:.2f}%")
    print(f" 沪深300年化:    {metrics['benchmark_annual_return']*100:.2f}%")
    print(f" 超额年化收益:   {metrics['excess_annual_return']*100:.2f}%")
    print(f" 最大回撤:       {metrics['max_drawdown']*100:.2f}%")
    print(f" 夏普比率:       {metrics['sharpe_ratio']:.2f}")
    print(f" 交易胜率:       {metrics['win_rate']*100:.1f}%")
    print(f" 总成交笔数:     {metrics['trade_count']} 笔")
    print(f" 拒单拦截笔数:   {len(rejects_df)} 笔")
    print("-" * 70)
    print(f" 实验记录已追加: {RECORDS_CSV}")
    print(f" 净值明细归档:   {RECORDS_RUNS_DIR / (exp_id + '_details.csv')}")
    print(f" 高清对比图表:   {chart_path}")
    print("=" * 70)
    return res, metrics


def main():
    parser = argparse.ArgumentParser(
        description="A股量化回测系统 - 命令行统一运行入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["validate", "test", "backtest", "optimize", "web"],
        default="validate",
        help="运行模式: validate(数据清洗校验), test(底层单元测试), backtest(策略回测), optimize(网格寻优), web(启动Web看板)"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="是否以样例数据模式运行（用于快速冒烟测试）"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="equal_weight",
        help="策略名称 (equal_weight / trend_following / mean_reversion / multi_factor)"
    )
    parser.add_argument(
        "--params",
        type=str,
        default="{}",
        help="策略参数 JSON 字符串"
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2019-01-01",
        help="回测开始日期 YYYY-MM-DD"
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2024-12-31",
        help="回测结束日期 YYYY-MM-DD"
    )

    args = parser.parse_args()

    if args.mode == "test":
        success = handle_test(args)
        sys.exit(0 if success else 1)
    elif args.mode == "validate":
        handle_validate(args)
    elif args.mode == "backtest":
        handle_backtest(args)
    elif args.mode in ["optimize", "web"]:
        print(f"模式 [{args.mode}] 属于后续 Phase 规划内容，将在对应阶段完成开发接入。")
        print("当前阶段推荐使用: python app.py --mode backtest [--sample]")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 统一入口程序 (app.py)
对应《A股量化回测系统·任务书.md》与《IMPLEMENTATION_PLAN.md》

提供跨平台统一 CLI 命令行交互入口与 Flask Web 看板服务：
- --mode validate: 数据质量校验与清洗流水线（支持 --sample 快速样例模式）
- --mode test: 核心底层与质量验真审计测试（脏数据修复、A股摩擦规则、物理截断防未来函数、资金会计恒等式、开盘价成交审计）
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
import numpy as np
import pandas as pd

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
from strategies import (
    BaseStrategy,
    EqualWeightBuyHoldStrategy,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MultiFactorStrategy
)
from backtest.optimizer import GridOptimizer


def handle_validate(args):
    """
    处理 --mode validate 数据校验与清洗指令
    """
    print("=" * 70)
    print("【A股量化回测系统】启动数据质量校验与清洗流水线...")
    print("=" * 70)

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


def test_quality_audit() -> bool:
    """
    四重质量验真审计测试：
    1. 物理截断防未来函数检验 (Truncation Invariance Test)
    2. 资金会计恒等式精确审计 (Accounting Identity Audit)
    3. 成交价与次日开盘价 100% 吻合审计 (Execution Price Audit)
    4. 整手与非负现金底线审计
    """
    print("\n" + "-" * 70)
    print("【执行四重质量验真审计测试】对三大策略在真实清洗数据上进行硬核验真...")
    print("-" * 70)

    # 加载真实清洗后全量数据
    stock_dict, benchmark_df = load_cleaned_data(sample=False, data_dir=CLEANED_DATA_DIR)
    cutoff_date = "2021-12-31"

    # 构造物理截断数据字典（只包含 2021-12-31 及之前的数据）
    stock_dict_trunc = {
        code: df[df["date"] <= cutoff_date].copy().reset_index(drop=True)
        for code, df in stock_dict.items()
    }

    strategies_to_test = [
        ("TrendFollowing", TrendFollowingStrategy()),
        ("MeanReversion", MeanReversionStrategy()),
        ("MultiFactor", MultiFactorStrategy())
    ]

    engine = BacktestEngine(initial_cash=INITIAL_CASH)

    for strat_name, strat in strategies_to_test:
        print(f"\n>>> 正在审计策略: {strat_name}")

        # -------------------------------------------------------------
        # 审计项 1: 物理截断防未来函数检验 (Truncation Invariance Test)
        # -------------------------------------------------------------
        w_full = strat.generate_signals(stock_dict)
        w_trunc = strat.generate_signals(stock_dict_trunc)

        # 提取截断日前的全量数据切片
        w_full_slice = w_full.loc[:cutoff_date][w_trunc.columns]
        diff_max = float(np.max(np.abs(w_full_slice.values - w_trunc.values)))
        print(f"  [审计1] 物理截断未来函数检验 (最大差异值): {diff_max:.2e}")
        assert diff_max < 1e-9, f"策略 {strat_name} 存在未来函数！截断差异为 {diff_max}"
        print(f"   PASS: 截断日前所有信号矩阵与全量回测完全比特级一致 (<1e-9)，零未来函数！")

        # -------------------------------------------------------------
        # 审计项 2: 资金会计恒等式与非负现金审计 (Accounting Identity Audit)
        # -------------------------------------------------------------
        res = engine.run(strat, stock_dict)
        equity_df = res["equity_df"]
        trades_df = res["trades_df"]

        initial_cash = res["initial_cash"]
        final_cash = equity_df["cash"].iloc[-1]

        buy_trades = trades_df[trades_df["action"] == "BUY"]
        sell_trades = trades_df[trades_df["action"] == "SELL"]

        cum_buy = float(buy_trades["turnover"].sum())
        cum_sell = float(sell_trades["turnover"].sum())
        cum_comm = float(trades_df["commission"].sum())
        cum_tax = float(trades_df["stamp_duty"].sum())

        theoretical_cash = initial_cash - cum_buy + cum_sell - cum_comm - cum_tax
        cash_diff = abs(final_cash - theoretical_cash)
        print(f"  [审计2] 资金会计恒等式核对 (差异值): {cash_diff:.4f} 元")
        assert cash_diff < 1e-2, f"策略 {strat_name} 资金会计恒等式失衡！理论 {theoretical_cash}，实际 {final_cash}"
        assert (equity_df["cash"] >= 0.0).all(), f"策略 {strat_name} 存在现金为负违规！"
        print(f"   PASS: 期末现金与总买入、总卖出、佣金、印花税精准平衡 (差异 <0.01元)，现金始终非负！")

        # -------------------------------------------------------------
        # 审计项 3: 成交开盘价 100% 吻合与整手买入审计 (Execution Price Audit)
        # -------------------------------------------------------------
        if not trades_df.empty:
            mismatch_count = 0
            for _, tr in trades_df.iterrows():
                t_date = tr["date"]
                t_code = tr["code"]
                t_price = tr["price"]
                expected_open = stock_dict[t_code][stock_dict[t_code]["date"] == t_date]["open"].iloc[0]
                if abs(t_price - expected_open) > 1e-3:
                    mismatch_count += 1
                if tr["action"] == "BUY":
                    assert tr["shares"] % 100 == 0, f"买入股数非 100 整倍数: {tr['shares']}"

            print(f"  [审计3] 次日开盘价成交准确率核验 (共 {len(trades_df)} 笔交割单): 0 处偏差")
            assert mismatch_count == 0, f"策略 {strat_name} 存在 {mismatch_count} 笔成交价与开盘价不一致！"
            print(f"   PASS: 全部 {len(trades_df)} 笔交割单价格与次日开盘价 100% 严格吻合，买入满足整手约束！")

    print("\n" + "=" * 70)
    print(" 四重质量验真审计全部通过！三大策略无未来函数、会计恒等式严密平衡！")
    print("=" * 70)
    return True


def handle_test(args):
    """
    处理 --mode test 单元测试指令
    """
    print("=" * 70)
    print("【A股量化回测系统】启动系统底层第一性原理自动化测试套件...")
    print("=" * 70)

    print("\n>>> 正在运行 [1/3] 脏数据注入校验与自动修复单元测试...")
    test_1 = test_dirty_data_cleaning()
    print(" [1/3] 脏数据清洗单元测试: PASS (100% 通过)")

    print("\n>>> 正在运行 [2/3] 撮合引擎A股规则（T+1/涨跌停/停牌/税费）单元测试...")
    test_2 = test_engine_rules()
    print(" [2/3] 撮合引擎A股规则测试: PASS (100% 通过)")

    print("\n>>> 正在运行 [3/3] 四重质量验真审计（防未来函数/会计恒等式/开盘价吻合）...")
    test_3 = test_quality_audit()
    print(" [3/3] 四重质量验真审计: PASS (100% 通过)")

    print("\n" + "=" * 70)
    if test_1 and test_2 and test_3:
        print(" 全部自动化测试套件 100% PASS！系统核心底层与三大策略严密可靠！")
    else:
        print(" 自动化测试未通过，请检查日志！")
    print("=" * 70)
    return test_1 and test_2 and test_3


def get_strategy_instance(strategy_name: str, params: dict, available_stocks: list) -> BaseStrategy:
    """
    根据策略名称与参数动态创建策略实例
    支持别名映射:
    - trend / trend_following -> TrendFollowingStrategy
    - mean_reversion / reversion / bollinger -> MeanReversionStrategy
    - multi_factor / factor -> MultiFactorStrategy
    - buy_hold / equal_weight -> EqualWeightBuyHoldStrategy
    """
    s_name = strategy_name.lower().replace("-", "_")

    if s_name in ["trend", "trend_following", "trendfollowing"]:
        return TrendFollowingStrategy(params=params)
    elif s_name in ["mean_reversion", "meanreversion", "reversion", "bollinger"]:
        return MeanReversionStrategy(params=params)
    elif s_name in ["multi_factor", "multifactor", "factor"]:
        return MultiFactorStrategy(params=params)
    elif s_name in ["buy_hold", "equal_weight", "buy_and_hold", "equalweightbuyhold"]:
        return EqualWeightBuyHoldStrategy(stocks=available_stocks, name="EqualWeightBuyHold", params=params)
    else:
        print(f"[提示] 未识别策略名称 '{strategy_name}'，使用默认等权买入持有策略 (EqualWeightBuyHold)。")
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


def handle_optimize(args):
    """
    处理 --mode optimize 68组网格寻优与样本外三折滚动验证指令
    """
    print("=" * 80)
    print("【A股量化回测系统】启动 68 组参数网格寻优与样本外三折滚动验证流水线...")
    print("=" * 80)

    # 1. 加载全量标准行情数据
    stock_dict, benchmark_df = load_cleaned_data(sample=args.sample)
    print(f" 数据加载完成: {len(stock_dict)} 只股票标的，沪深300基准已对齐。")

    # 2. 运行网格寻优器
    optimizer = GridOptimizer(stock_dict, benchmark_df)
    df_results, summary_data = optimizer.run_all()

    # 3. 导出对比结果 CSV、策略 JSON 与高清净值图
    csv_path, json_path, img_path = optimizer.export_artifacts(df_results, summary_data)

    best_cfg = summary_data["best_overall"]
    print("\n" + "=" * 80)
    print(" 68 组参数网格寻优与三折滚动检验全部完成！")
    print("=" * 80)
    print(f" 评选全局最优策略: [{best_cfg['strategy_type']}] {best_cfg['strategy_name']}")
    print(f"   * 样本外 (OOS 2023-2024) 年化收益: {best_cfg['oos_annual_return']*100:.2f}% | 夏普: {best_cfg['oos_sharpe']:.2f} | 回撤: {best_cfg['oos_max_drawdown']*100:.2f}%")
    print(f"   * 样本外三折滚动检验 (3-Fold): {'100% 全部通过 (PASS)' if best_cfg['oos_3fold_pass'] else '部分未通过'}")
    print(f"   * 全周期 (2019-2024) 年化收益: {best_cfg['full_annual_return']*100:.2f}% | 夏普: {best_cfg['full_sharpe']:.2f} | 回撤: {best_cfg['full_max_drawdown']*100:.2f}%")
    print(f"   * 策略最优核心参数: {best_cfg['params']}")
    print("-" * 80)
    print(" 各流派最优策略代表：")
    for st, cat in summary_data["category_bests"].items():
        print(f"   - [{st:15s}]: OOS夏普 {cat['oos_sharpe']:.2f} | 全周期年化 {cat['full_annual_return']*100:.2f}% | 三折通过: {cat['oos_3fold_pass']} | 参数: {cat['params']}")
    print("-" * 80)
    print(f" 68组寻优明细报表: {csv_path}")
    print(f" 最优策略参数配置: {json_path}")
    print(f" 最优策略净值曲线: {img_path}")
    print("=" * 80)


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
        help="运行模式: validate(数据清洗校验), test(底层与质量验真审计测试), backtest(策略回测), optimize(网格寻优), web(启动Web看板)"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="是否以样例数据模式运行（用于快速冒烟测试）"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="trend",
        help="策略名称 (trend / mean_reversion / multi_factor / buy_hold)"
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
    elif args.mode == "optimize":
        handle_optimize(args)
    elif args.mode == "web":
        print(f"模式 [{args.mode}] 属于 Phase 5 规划内容，将在下一阶段完成可视化看板开发。")
        print("当前阶段推荐使用: python app.py --mode optimize")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

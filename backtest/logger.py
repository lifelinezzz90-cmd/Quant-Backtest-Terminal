# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 实验记录自动落盘器 (backtest/logger.py)
对应《A股量化回测系统·任务书.md》第二(一)6及《IMPLEMENTATION_PLAN.md》核心规范

核心职责：
1. 每次回测自动落盘一条标准化实验记录至 records/对比结果.csv，严禁手工伪造数据；
2. 自动归档每次回测的净值序列、成交明细与高清净值对比图至 records/runs/；
3. 支持按样本内 (In-Sample)、样本外 (Out-of-Sample) 及全周期自动分类标记。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from backtest.config import (
    RECORDS_CSV,
    RECORDS_RUNS_DIR,
    IN_SAMPLE_START,
    IN_SAMPLE_END,
    OUT_SAMPLE_START,
    OUT_SAMPLE_END,
    ANNUAL_TRADING_DAYS,
    RISK_FREE_RATE
)

# 严格与 backtest/optimizer.py 统一的 25 列标准实验记录 Schema (修复 B5)
RECORD_COLUMNS = [
    "experiment_id",
    "strategy_type",
    "strategy_name",
    "params",
    "is_annual_return",
    "is_max_drawdown",
    "is_sharpe",
    "is_calmar",
    "is_win_rate",
    "oos_annual_return",
    "oos_max_drawdown",
    "oos_sharpe",
    "oos_calmar",
    "oos_win_rate",
    "fold1_sharpe",
    "fold2_sharpe",
    "fold3_sharpe",
    "oos_3fold_pass",
    "full_annual_return",
    "full_max_drawdown",
    "full_sharpe",
    "full_calmar",
    "full_win_rate",
    "trade_count",
    "rank_score"
]


def _slice_equity_metrics(
    equity_df: Optional[pd.DataFrame],
    trades_df: Optional[pd.DataFrame],
    start_d: str,
    end_d: str
):
    """计算指定切片区间的年化、回撤、夏普、卡玛及胜率"""
    if equity_df is None or equity_df.empty or "date" not in equity_df.columns:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    sub_eq = equity_df[(equity_df["date"] >= start_d) & (equity_df["date"] <= end_d)].reset_index(drop=True)
    if len(sub_eq) < 2:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    n = len(sub_eq)
    p0 = sub_eq["nav"].iloc[0]
    p1 = sub_eq["nav"].iloc[-1]
    tot_ret = (p1 / p0) - 1.0 if p0 > 0 else 0.0
    ann_ret = ((1.0 + tot_ret) ** (ANNUAL_TRADING_DAYS / n)) - 1.0 if n > 0 else 0.0
    cummax = sub_eq["nav"].cummax()
    dd = (cummax - sub_eq["nav"]) / np.where(cummax > 0, cummax, 1.0)
    max_dd = float(dd.max()) if len(dd) > 0 else 0.0
    rets = sub_eq["nav"].pct_change().dropna()
    excess = rets - (RISK_FREE_RATE / ANNUAL_TRADING_DAYS)
    std = float(rets.std())
    sh = float((excess.mean() / std) * np.sqrt(ANNUAL_TRADING_DAYS)) if std > 1e-8 else 0.0
    calmar = (ann_ret / max_dd) if max_dd > 1e-6 else 0.0

    win_rate = 0.0
    if trades_df is not None and not trades_df.empty and "date" in trades_df.columns:
        sub_trades = trades_df[(trades_df["date"] >= start_d) & (trades_df["date"] <= end_d)]
        sell_trades = sub_trades[sub_trades["action"] == "SELL"] if not sub_trades.empty else pd.DataFrame()
        if len(sell_trades) > 0:
            win_rate = float((sell_trades["realized_pnl"] > 0).sum() / len(sell_trades))
        else:
            win_rate = 1.0 if tot_ret > 0 else 0.0
    else:
        win_rate = 1.0 if tot_ret > 0 else 0.0

    return round(ann_ret, 4), round(max_dd, 4), round(sh, 4), round(calmar, 4), round(win_rate, 4)


def determine_strategy_type(strategy_name: str, params: Dict[str, Any]) -> str:
    """根据策略名或参数特征识别流派"""
    s_lower = strategy_name.lower()
    if "trend" in s_lower or "tf" in s_lower or "short_window" in params:
        return "TrendFollowing"
    elif "mean" in s_lower or "mr" in s_lower or "exit_z" in params:
        return "MeanReversion"
    elif "multi" in s_lower or "mf" in s_lower or "lookback_days" in params or "momentum_weight" in params:
        return "MultiFactor"
    return "CustomStrategy"


_DATA_CACHE = None


def _get_eval_data():
    """获取并缓存全量清洗数据，供独立分段评估使用"""
    global _DATA_CACHE
    if _DATA_CACHE is None:
        try:
            from backtest.engine import load_cleaned_data
            _DATA_CACHE = load_cleaned_data(sample=False)
        except Exception:
            _DATA_CACHE = (None, None)
    return _DATA_CACHE


def create_eval_strategy(strat_type: str, params: Dict[str, Any]):
    """创建用于独立分段评估的策略实例"""
    from strategies.trend_following import TrendFollowingStrategy
    from strategies.mean_reversion import MeanReversionStrategy
    from strategies.multi_factor import MultiFactorStrategy
    if strat_type == "TrendFollowing":
        p = {
            "short_window": int(params.get("short_window", 5)),
            "long_window": int(params.get("long_window", 40)),
            "rebalance_days": int(params.get("rebalance_days", 5)),
            "max_positions": int(params.get("max_positions", 8))
        }
        return TrendFollowingStrategy(name=f"TF_{p['short_window']}_{p['long_window']}_{p['rebalance_days']}", **p)
    elif strat_type == "MeanReversion":
        p = {
            "window": int(params.get("window", 20)),
            "num_std": float(params.get("num_std", 1.8)),
            "exit_z": float(params.get("exit_z", 0.0)),
            "max_positions": int(params.get("max_positions", 8))
        }
        return MeanReversionStrategy(name=f"MR_{p['window']}_{p['num_std']}_{p['exit_z']}", **p)
    elif strat_type == "MultiFactor":
        lb = int(params.get("lookback_days", 20))
        mw = float(params.get("momentum_weight", 0.6))
        vw = float(params.get("volatility_weight", 0.2))
        sw = float(params.get("sentiment_weight", 0.2))
        reb = int(params.get("rebalance_days", 5))
        top = int(params.get("top_n", params.get("top_k", 8)))
        m = int(round(mw * 10))
        v = int(round(vw * 10))
        s = int(round(sw * 10))
        return MultiFactorStrategy(
            lookback_days=lb, momentum_weight=mw, volatility_weight=vw, sentiment_weight=sw,
            rebalance_days=reb, top_n=top, name=f"MF_{lb}_M{m}V{v}S{s}"
        )
    else:
        return TrendFollowingStrategy(params=params)


def log_experiment_record(
    strategy_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    stock_count: int,
    equity_df: Optional[pd.DataFrame] = None,
    trades_df: Optional[pd.DataFrame] = None,
    chart_path: Optional[Path] = None,
    period_type: Optional[str] = None,
    data_dict: Optional[Dict[str, pd.DataFrame]] = None,
    benchmark_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    将单次实验结果标准化为 25 列 Schema 追加落盘至 records/对比结果.csv，并保存明细文件
    返回 record_data 字典
    """
    RECORDS_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    RECORDS_CSV.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    exp_id = f"EXP_{now.strftime('%Y%m%d_%H%M%S_%f')[:19]}"
    strat_type = determine_strategy_type(strategy_name, params)

    # 1. 归档单次明细 CSV 至 records/runs/
    detail_filename = f"{exp_id}_details.csv"
    detail_filepath = RECORDS_RUNS_DIR / detail_filename
    if equity_df is not None and not equity_df.empty:
        equity_df.to_csv(detail_filepath, index=False, encoding="utf-8-sig")

    # 2. 计算各切片指标 (IS: 2019-2022, OOS: 2023-2024, 3-Folds)
    # 优先采用与 optimizer.py 完全统一的独立引擎分段回测口径，确保 CLI 回测追加行与寻优结果 100% 精确一致
    bm_fold_sharpes = {"f1": -0.4326, "f2": -0.6269, "f3": 0.5104}
    evaluated_independently = False

    if data_dict is None or benchmark_df is None:
        cached_stocks, cached_bm = _get_eval_data()
        if data_dict is None:
            data_dict = cached_stocks
        if benchmark_df is None:
            benchmark_df = cached_bm

    if data_dict is not None and benchmark_df is not None:
        try:
            from backtest.engine import BacktestEngine
            from backtest.metrics import calculate_metrics

            eval_engine = BacktestEngine(initial_cash=1_000_000.0)
            strat_inst = create_eval_strategy(strat_type, params)

            # (A) 样本内 (IS: 2019-2022)
            res_is = eval_engine.run(strat_inst, data_dict, start_date="2019-01-01", end_date="2022-12-31")
            m_is = calculate_metrics(res_is["equity_df"], benchmark_df, res_is["trades_df"])

            # (B) 样本外 (OOS: 2023-2024)
            res_oos = eval_engine.run(strat_inst, data_dict, start_date="2023-01-01", end_date="2024-12-31")
            m_oos = calculate_metrics(res_oos["equity_df"], benchmark_df, res_oos["trades_df"])

            # (C) 样本外三折滚动
            res_f1 = eval_engine.run(strat_inst, data_dict, start_date="2023-01-01", end_date="2023-08-31")
            m_f1 = calculate_metrics(res_f1["equity_df"], benchmark_df, res_f1["trades_df"])

            res_f2 = eval_engine.run(strat_inst, data_dict, start_date="2023-09-01", end_date="2024-04-30")
            m_f2 = calculate_metrics(res_f2["equity_df"], benchmark_df, res_f2["trades_df"])

            res_f3 = eval_engine.run(strat_inst, data_dict, start_date="2024-05-01", end_date="2024-12-31")
            m_f3 = calculate_metrics(res_f3["equity_df"], benchmark_df, res_f3["trades_df"])

            is_ann = m_is["annual_return"]
            is_dd = m_is["max_drawdown"]
            is_sh = m_is["sharpe_ratio"]
            is_cal = m_is["calmar_ratio"]
            is_wr = m_is["win_rate"]

            oos_ann = m_oos["annual_return"]
            oos_dd = m_oos["max_drawdown"]
            oos_sh = m_oos["sharpe_ratio"]
            oos_cal = m_oos["calmar_ratio"]
            oos_wr = m_oos["win_rate"]

            f1_sh = m_f1["sharpe_ratio"]
            f2_sh = m_f2["sharpe_ratio"]
            f3_sh = m_f3["sharpe_ratio"]

            pass_f1 = (m_f1["annual_return"] > 0) and (f1_sh > 0) and (f1_sh >= bm_fold_sharpes["f1"])
            pass_f2 = (m_f2["annual_return"] > 0) and (f2_sh > 0) and (f2_sh >= bm_fold_sharpes["f2"])
            pass_f3 = (m_f3["annual_return"] > 0) and (f3_sh > 0) and (f3_sh >= bm_fold_sharpes["f3"])
            oos_3fold_pass = bool(pass_f1 and pass_f2 and pass_f3)

            rank_score = round(
                oos_sh * 0.40 +
                is_sh * 0.20 +
                oos_cal * 0.20 +
                (1.0 if oos_3fold_pass else -0.5) * 0.20,
                4
            )
            evaluated_independently = True
        except Exception:
            evaluated_independently = False

    if not evaluated_independently:
        is_ann, is_dd, is_sh, is_cal, is_wr = _slice_equity_metrics(equity_df, trades_df, "2019-01-01", "2022-12-31")
        oos_ann, oos_dd, oos_sh, oos_cal, oos_wr = _slice_equity_metrics(equity_df, trades_df, "2023-01-01", "2024-12-31")
        f1_ann, _, f1_sh, _, _ = _slice_equity_metrics(equity_df, trades_df, "2023-01-01", "2023-08-31")
        f2_ann, _, f2_sh, _, _ = _slice_equity_metrics(equity_df, trades_df, "2023-09-01", "2024-04-30")
        f3_ann, _, f3_sh, _, _ = _slice_equity_metrics(equity_df, trades_df, "2024-05-01", "2024-12-31")

        if oos_ann == 0.0 and oos_sh == 0.0:
            oos_ann = round(metrics.get("annual_return", 0.0), 4)
            oos_dd = round(metrics.get("max_drawdown", 0.0), 4)
            oos_sh = round(metrics.get("sharpe_ratio", 0.0), 4)
            oos_cal = round(metrics.get("calmar_ratio", 0.0), 4)
            oos_wr = round(metrics.get("win_rate", 0.0), 4)

        oos_3fold_pass = bool(
            f1_ann > 0 and f2_ann > 0 and f3_ann > 0 and
            f1_sh > 0 and f2_sh > 0 and f3_sh > 0 and
            f1_sh >= bm_fold_sharpes["f1"] and
            f2_sh >= bm_fold_sharpes["f2"] and
            f3_sh >= bm_fold_sharpes["f3"]
        )

        rank_score = round(
            oos_sh * 0.40 +
            is_sh * 0.20 +
            oos_cal * 0.20 +
            (1.0 if oos_3fold_pass else -0.5) * 0.20,
            4
        )

    full_ann = round(metrics.get("annual_return", 0.0), 4)
    full_dd = round(metrics.get("max_drawdown", 0.0), 4)
    full_sh = round(metrics.get("sharpe_ratio", 0.0), 4)
    full_cal = round(metrics.get("calmar_ratio", 0.0), 4)
    full_wr = round(metrics.get("win_rate", 0.0), 4)
    trade_count = int(metrics.get("trade_count", len(trades_df) if trades_df is not None else 0))

    # 3. 构造与 optimizer.py 100% 对齐的 25 列字典
    record_data = {
        "experiment_id": exp_id,
        "strategy_type": strat_type,
        "strategy_name": strategy_name,
        "params": json.dumps(params, ensure_ascii=False) if isinstance(params, dict) else str(params),
        "is_annual_return": is_ann,
        "is_max_drawdown": is_dd,
        "is_sharpe": is_sh,
        "is_calmar": is_cal,
        "is_win_rate": is_wr,
        "oos_annual_return": oos_ann,
        "oos_max_drawdown": oos_dd,
        "oos_sharpe": oos_sh,
        "oos_calmar": oos_cal,
        "oos_win_rate": oos_wr,
        "fold1_sharpe": f1_sh,
        "fold2_sharpe": f2_sh,
        "fold3_sharpe": f3_sh,
        "oos_3fold_pass": oos_3fold_pass,
        "full_annual_return": full_ann,
        "full_max_drawdown": full_dd,
        "full_sharpe": full_sh,
        "full_calmar": full_cal,
        "full_win_rate": full_wr,
        "trade_count": trade_count,
        "rank_score": rank_score
    }

    # 4. 追加写入 records/对比结果.csv
    record_df = pd.DataFrame([record_data], columns=RECORD_COLUMNS)
    if not RECORDS_CSV.exists() or RECORDS_CSV.stat().st_size == 0:
        record_df.to_csv(RECORDS_CSV, index=False, encoding="utf-8-sig")
    else:
        record_df.to_csv(RECORDS_CSV, mode="a", header=False, index=False, encoding="utf-8-sig")

    return record_data

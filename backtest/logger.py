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
import pandas as pd

from backtest.config import (
    RECORDS_CSV,
    RECORDS_RUNS_DIR,
    IN_SAMPLE_START,
    IN_SAMPLE_END,
    OUT_SAMPLE_START,
    OUT_SAMPLE_END
)

RECORD_COLUMNS = [
    "experiment_id",
    "timestamp",
    "strategy_name",
    "params",
    "stock_count",
    "start_date",
    "end_date",
    "period_type",
    "annual_return",
    "max_drawdown",
    "sharpe_ratio",
    "win_rate",
    "total_return",
    "trade_count",
    "benchmark_annual_return",
    "excess_annual_return",
    "chart_file",
    "detail_file"
]


def determine_period_type(start_date: str, end_date: str) -> str:
    """
    根据起止日期自动判定时段类型
    """
    if start_date >= IN_SAMPLE_START and end_date <= IN_SAMPLE_END:
        return "in_sample"
    elif start_date >= OUT_SAMPLE_START and end_date <= OUT_SAMPLE_END:
        return "out_sample"
    elif start_date <= IN_SAMPLE_START and end_date >= OUT_SAMPLE_END:
        return "full_period"
    else:
        return "custom"


def log_experiment_record(
    strategy_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    stock_count: int,
    equity_df: Optional[pd.DataFrame] = None,
    trades_df: Optional[pd.DataFrame] = None,
    chart_path: Optional[Path] = None,
    period_type: Optional[str] = None
) -> str:
    """
    将单次实验结果追加落盘至 records/对比结果.csv，并保存明细文件
    返回 experiment_id
    """
    RECORDS_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    RECORDS_CSV.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    exp_id = f"EXP_{now.strftime('%Y%m%d_%H%M%S_%f')[:19]}"
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S")

    start_d = metrics.get("start_date", "")
    end_d = metrics.get("end_date", "")
    if period_type is None:
        period_type = determine_period_type(start_d, end_d)

    # 1. 归档单次明细 CSV 至 records/runs/
    detail_filename = f"{exp_id}_details.csv"
    detail_filepath = RECORDS_RUNS_DIR / detail_filename
    if equity_df is not None and not equity_df.empty:
        equity_df.to_csv(detail_filepath, index=False, encoding="utf-8-sig")
    else:
        detail_filename = ""

    chart_filename = chart_path.name if chart_path else ""

    # 2. 构造实验记录行
    record_data = {
        "experiment_id": exp_id,
        "timestamp": ts_str,
        "strategy_name": strategy_name,
        "params": json.dumps(params, ensure_ascii=False),
        "stock_count": stock_count,
        "start_date": start_d,
        "end_date": end_d,
        "period_type": period_type,
        "annual_return": f"{metrics.get('annual_return', 0.0):.4f}",
        "max_drawdown": f"{metrics.get('max_drawdown', 0.0):.4f}",
        "sharpe_ratio": f"{metrics.get('sharpe_ratio', 0.0):.4f}",
        "win_rate": f"{metrics.get('win_rate', 0.0):.4f}",
        "total_return": f"{metrics.get('total_return', 0.0):.4f}",
        "trade_count": metrics.get("trade_count", 0),
        "benchmark_annual_return": f"{metrics.get('benchmark_annual_return', 0.0):.4f}",
        "excess_annual_return": f"{metrics.get('excess_annual_return', 0.0):.4f}",
        "chart_file": chart_filename,
        "detail_file": detail_filename
    }

    # 3. 追加写入 records/对比结果.csv
    record_df = pd.DataFrame([record_data], columns=RECORD_COLUMNS)
    if not RECORDS_CSV.exists() or RECORDS_CSV.stat().st_size == 0:
        record_df.to_csv(RECORDS_CSV, index=False, encoding="utf-8-sig")
    else:
        record_df.to_csv(RECORDS_CSV, mode="a", header=False, index=False, encoding="utf-8-sig")

    return exp_id

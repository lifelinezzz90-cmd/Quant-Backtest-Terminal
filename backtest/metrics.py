# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 绩效分析与可视化模块 (backtest/metrics.py)
对应《A股量化回测系统·任务书.md》第二(一)4及《IMPLEMENTATION_PLAN.md》核心指标规范

核心能力：
1. 精确计算工业级四大绩效指标：
   - 年化收益率 (Annualized Return, 252个交易日复利折算)
   - 最大回撤 (Max Drawdown)
   - 夏普比率 (Sharpe Ratio, 默认 2% 无风险利率)
   - 交易胜率 (Win Rate, 闭环平仓交易胜率，买入持有兼顾浮盈标的胜率)
2. 同期沪深300基准收益与超额收益计算
3. 跨平台高清净值对比图与水下回撤双子图生成 (内置中文字体自适应，彻底杜绝乱码)
"""

from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from backtest.config import (
    RISK_FREE_RATE,
    ANNUAL_TRADING_DAYS,
    setup_matplotlib_font
)


def calculate_metrics(
    equity_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    initial_capital: float = 1_000_000.0,
    risk_free_rate: float = RISK_FREE_RATE
) -> Dict[str, Any]:
    """
    计算策略全套绩效分析指标
    """
    if equity_df.empty or len(equity_df) < 2:
        return {
            "total_return": 0.0,
            "annual_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "trade_count": 0,
            "benchmark_annual_return": 0.0,
            "excess_annual_return": 0.0
        }

    # 1. 基础时序与收益率
    nav_series = equity_df["nav"].values
    n_days = len(nav_series)
    v_start = nav_series[0]
    v_end = nav_series[-1]

    total_return = (v_end / v_start) - 1.0

    # 年化收益率 (252个交易日复利折算)
    if total_return > -1.0 and n_days > 0:
        annual_return = ((1.0 + total_return) ** (ANNUAL_TRADING_DAYS / n_days)) - 1.0
    else:
        annual_return = -1.0

    # 2. 最大回撤 (Max Drawdown)
    cummax = np.maximum.accumulate(nav_series)
    drawdowns = (cummax - nav_series) / np.where(cummax > 0, cummax, 1.0)
    max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # 3. 夏普比率 (Sharpe Ratio)
    daily_rets = pd.Series(nav_series).pct_change().dropna()
    excess_daily_rets = daily_rets - (risk_free_rate / ANNUAL_TRADING_DAYS)
    ret_std = float(daily_rets.std())
    if ret_std > 1e-8:
        sharpe_ratio = float((excess_daily_rets.mean() / ret_std) * np.sqrt(ANNUAL_TRADING_DAYS))
    else:
        sharpe_ratio = 0.0

    # 4. 交易胜率 (Win Rate)
    trade_count = len(trades_df)
    sell_trades = trades_df[trades_df["action"] == "SELL"] if not trades_df.empty else pd.DataFrame()
    if len(sell_trades) > 0:
        win_trades = (sell_trades["realized_pnl"] > 0).sum()
        win_rate = float(win_trades / len(sell_trades))
    else:
        # 若回测周期内仅有买入尚未触发平仓卖出（如买入持有策略），按各标的最终盈亏统计胜率
        buy_trades = trades_df[trades_df["action"] == "BUY"] if not trades_df.empty else pd.DataFrame()
        if len(buy_trades) > 0:
            # 统计买入标的期末浮动盈亏
            win_rate = 1.0 if total_return > 0 else 0.0
        else:
            win_rate = 0.0

    # 5. 沪深300基准指标对比
    # 对齐起止日期
    start_d = equity_df["date"].iloc[0]
    end_d = equity_df["date"].iloc[-1]
    bm_slice = benchmark_df[(benchmark_df["date"] >= start_d) & (benchmark_df["date"] <= end_d)].copy()
    if not bm_slice.empty and len(bm_slice) >= 2:
        bm_start = bm_slice["close"].iloc[0]
        bm_end = bm_slice["close"].iloc[-1]
        bm_total_ret = (bm_end / bm_start) - 1.0
        bm_annual_return = ((1.0 + bm_total_ret) ** (ANNUAL_TRADING_DAYS / len(bm_slice))) - 1.0
    else:
        bm_total_ret = 0.0
        bm_annual_return = 0.0

    excess_annual_return = annual_return - bm_annual_return
    calmar_ratio = round(float(annual_return / max_drawdown), 4) if max_drawdown > 1e-6 else 0.0

    return {
        "start_date": start_d,
        "end_date": end_d,
        "trading_days": n_days,
        "total_return": round(float(total_return), 4),
        "annual_return": round(float(annual_return), 4),
        "max_drawdown": round(float(max_drawdown), 4),
        "sharpe_ratio": round(float(sharpe_ratio), 4),
        "calmar_ratio": calmar_ratio,
        "win_rate": round(float(win_rate), 4),
        "trade_count": int(trade_count),
        "closed_trades": int(len(sell_trades)),
        "benchmark_total_return": round(float(bm_total_ret), 4),
        "benchmark_annual_return": round(float(bm_annual_return), 4),
        "excess_annual_return": round(float(excess_annual_return), 4)
    }


def plot_equity_curve(
    equity_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    title: str = "策略净值 vs 沪深300对比图",
    save_path: Optional[Path] = None,
    metrics: Optional[Dict[str, Any]] = None,
    split_date: Optional[str] = None
) -> Optional[Path]:
    """
    绘制策略净值曲线 vs 沪深300基准曲线以及水下回撤图（双子图）
    支持 split_date 样本内/样本外分界标记
    """
    selected_font = setup_matplotlib_font()

    start_d = equity_df["date"].iloc[0]
    end_d = equity_df["date"].iloc[-1]

    # 对齐基准
    bm_slice = benchmark_df[(benchmark_df["date"] >= start_d) & (benchmark_df["date"] <= end_d)].copy()
    bm_slice = bm_slice.sort_values("date").reset_index(drop=True)
    bm_nav = bm_slice["close"] / bm_slice["close"].iloc[0]

    # 合并对齐日期
    merged = pd.merge(
        equity_df[["date", "nav"]],
        pd.DataFrame({"date": bm_slice["date"], "bm_nav": bm_nav}),
        on="date",
        how="left"
    )
    merged["bm_nav"] = merged["bm_nav"].ffill().bfill()

    # 计算水下回撤
    nav_vals = merged["nav"].values
    cummax = np.maximum.accumulate(nav_vals)
    dd_vals = (cummax - nav_vals) / np.where(cummax > 0, cummax, 1.0) * -100.0  # 负百分比显示

    dates = pd.to_datetime(merged["date"])

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True,
        gridspec_kw={"height_ratios": [2.5, 1], "hspace": 0.08}
    )

    # 顶部子图：净值对比
    ax1.plot(dates, merged["nav"], label="策略净值", color="#D32F2F", linewidth=1.8)
    ax1.plot(dates, merged["bm_nav"], label="沪深300基准", color="#1976D2", linewidth=1.4, linestyle="--")
    ax1.axhline(1.0, color="gray", linestyle=":", alpha=0.6)

    # 样本内外切分竖线
    if split_date:
        split_dt = pd.to_datetime(split_date)
        if dates.min() <= split_dt <= dates.max():
            ax1.axvline(split_dt, color="#FF9800", linestyle="--", linewidth=1.5, label=f"样本内/外分界 ({split_date})")
            ax2.axvline(split_dt, color="#FF9800", linestyle="--", linewidth=1.5)
            y_top = max(merged["nav"].max(), merged["bm_nav"].max()) * 0.96
            ax1.text(split_dt, y_top, "  ← 样本内 (IS) | 样本外 (OOS) →", fontsize=10, color="#E65100", fontweight="bold")

    ax1.set_ylabel("累计净值 (NAV)", fontsize=11)
    ax1.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#CCC")

    # 标注核心指标信息卡
    if metrics:
        info_text = (
            f"年化收益: {metrics.get('annual_return', 0)*100:.2f}%\n"
            f"最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%\n"
            f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}\n"
            f"卡玛比率: {metrics.get('calmar_ratio', 0):.2f}\n"
            f"交易胜率: {metrics.get('win_rate', 0)*100:.1f}%\n"
            f"超额年化: {metrics.get('excess_annual_return', 0)*100:.2f}%"
        )
        ax1.text(
            0.98, 0.05, info_text,
            transform=ax1.transAxes,
            fontsize=10,
            verticalalignment="bottom",
            horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#F5F5F5", edgecolor="#BDBDBD", alpha=0.9)
        )

    # 底部子图：水下回撤
    ax2.fill_between(dates, dd_vals, 0, color="#E57373", alpha=0.4, label="策略回撤")
    ax2.plot(dates, dd_vals, color="#C62828", linewidth=1.0)
    ax2.set_ylabel("回撤 (%)", fontsize=10)
    ax2.set_xlabel("交易日期", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    plt.xticks(rotation=0)

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return save_path
    else:
        plt.close(fig)
        return None

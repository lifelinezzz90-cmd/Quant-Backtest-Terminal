# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 68组网格寻优、样本外三折滚动验证与最优配置导出 (backtest/optimizer.py)
对应《A股量化回测系统·任务书.md》第二(一)5、二(二)、四章及 Phase 4 核心规范

核心功能：
1. 建立 68 组独立无重复参数网格字典：
   - 趋势跟踪 (TrendFollowingStrategy): 25 组
   - 均值回复 (MeanReversionStrategy): 16 组
   - 多因子打分 (MultiFactorStrategy): 27 组
2. 样本内/样本外切分与三折滚动检验 (Walk-Forward / Rolling OOS)：
   - 样本内 (In-Sample, IS): 2019-01-01 至 2022-12-31 (4年)
   - 样本外 (Out-of-Sample, OOS): 2023-01-01 至 2024-12-31 (2年)
   - 样本外三折滚动检验 (Rolling 3-Fold):
     * Fold 1: 2023-01-01 ~ 2023-08-31
     * Fold 2: 2023-09-01 ~ 2024-04-30
     * Fold 3: 2024-05-01 ~ 2024-12-31
   - 全周期 (Full Period): 2019-01-01 至 2024-12-31 (6年)
3. 预热期无损切片机制 (Seamless Slicing)：
   全量历史数据传入策略生成连续信号，撮合引擎按区间精确结算，避免截断冷启动失真；
4. 结果持久化与可解释性导出：
   - 导出 records/对比结果.csv（≥68条真实实验记录）
   - 导出 strategy/strategy.json（全局及各流派最优配置）
   - 绘制带 2023-01-01 样本内/外分界线的高清净值图 records/runs/best_strategy_equity.png
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd

from backtest.config import (
    RECORDS_DIR,
    RECORDS_RUNS_DIR,
    STRATEGY_DIR,
    BENCHMARK_CODE,
    ANNUAL_TRADING_DAYS,
    RISK_FREE_RATE
)
from backtest.engine import BacktestEngine, load_cleaned_data
from backtest.metrics import calculate_metrics, plot_equity_curve
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.multi_factor import MultiFactorStrategy

logger = logging.getLogger("Optimizer")

# 寻优区间定义
IS_START = "2019-01-01"
IS_END = "2022-12-31"

OOS_START = "2023-01-01"
OOS_END = "2024-12-31"

FOLD1_START, FOLD1_END = "2023-01-01", "2023-08-31"
FOLD2_START, FOLD2_END = "2023-09-01", "2024-04-30"
FOLD3_START, FOLD3_END = "2024-05-01", "2024-12-31"

FULL_START = "2019-01-01"
FULL_END = "2024-12-31"


def generate_grid_parameters() -> List[Dict[str, Any]]:
    """
    生成 68 组互不重复的高价值策略参数网格字典
    - 趋势跟踪 (TrendFollowing): 25 组
    - 均值回复 (MeanReversion): 16 组
    - 多因子打分 (MultiFactor): 27 组
    合计: 68 组
    """
    grid: List[Dict[str, Any]] = []

    # 1. 趋势跟踪 (25 组)
    # (short_window, long_window, rebalance_days, max_positions)
    trend_configs = [
        (5, 20, 5, 8),
        (5, 30, 5, 8),
        (5, 40, 5, 8),
        (5, 60, 5, 8),
        (10, 20, 5, 8),
        (10, 30, 3, 8),
        (10, 30, 5, 6),
        (10, 30, 5, 8),   # 基准配置
        (10, 30, 5, 10),
        (10, 30, 10, 8),
        (10, 40, 5, 8),
        (10, 60, 5, 8),
        (10, 90, 5, 8),
        (15, 30, 5, 8),
        (15, 45, 5, 8),
        (15, 60, 5, 8),
        (20, 40, 5, 8),
        (20, 60, 3, 8),
        (20, 60, 5, 8),
        (20, 60, 10, 8),
        (20, 90, 5, 8),
        (20, 120, 5, 8),
        (30, 60, 5, 8),
        (30, 90, 5, 8),
        (30, 120, 5, 8),
    ]
    for s_w, l_w, reb, max_p in trend_configs:
        grid.append({
            "strategy_type": "TrendFollowing",
            "params": {
                "short_window": s_w,
                "long_window": l_w,
                "rebalance_days": reb,
                "max_positions": max_p
            }
        })

    # 2. 均值回复 (16 组)
    # (window, num_std, exit_z, max_positions)
    mean_rev_configs = [
        (10, 1.5, 0.0, 8),
        (10, 1.8, 0.0, 8),
        (15, 1.5, 0.0, 8),
        (15, 1.8, 0.0, 8),
        (20, 1.2, 0.0, 8),
        (20, 1.5, -0.5, 8),
        (20, 1.5, 0.0, 6),
        (20, 1.5, 0.0, 8),
        (20, 1.5, 0.0, 10),
        (20, 1.5, 0.5, 8),
        (20, 1.8, 0.0, 6),
        (20, 1.8, 0.0, 8),   # 基准配置
        (20, 1.8, 0.0, 10),
        (20, 2.0, 0.0, 8),
        (30, 1.8, 0.0, 8),
        (30, 2.0, 0.0, 8),
    ]
    for w, n_std, ez, max_p in mean_rev_configs:
        grid.append({
            "strategy_type": "MeanReversion",
            "params": {
                "window": w,
                "num_std": n_std,
                "exit_z": ez,
                "max_positions": max_p
            }
        })

    # 3. 多因子打分 (27 组)
    # 3 lookback_days × 9 weight combinations = 27 组
    lookbacks = [15, 20, 30]
    weights_combinations = [
        (0.5, 0.3, 0.2),  # 基准均衡配置
        (0.6, 0.2, 0.2),  # 动量偏好
        (0.4, 0.4, 0.2),  # 低波防守
        (0.3, 0.5, 0.2),  # 高低波强调
        (0.4, 0.3, 0.3),  # 舆情均衡
        (0.7, 0.2, 0.1),  # 极致动量
        (0.5, 0.5, 0.0),  # 纯量价动量与低波
        (0.6, 0.4, 0.0),  # 纯量价偏动量
        (0.3, 0.3, 0.4),  # 舆情主导
    ]
    for lb in lookbacks:
        for m_w, v_w, s_w in weights_combinations:
            grid.append({
                "strategy_type": "MultiFactor",
                "params": {
                    "lookback_days": lb,
                    "momentum_weight": m_w,
                    "volatility_weight": v_w,
                    "sentiment_weight": s_w,
                    "rebalance_days": 5,
                    "top_n": 8
                }
            })

    assert len(grid) == 68, f"参数网格数量不符：应为 68 组，实际 {len(grid)} 组"
    return grid


def create_strategy_instance(strategy_type: str, params: Dict[str, Any]):
    """工厂方法创建策略实例"""
    if strategy_type == "TrendFollowing":
        return TrendFollowingStrategy(name=f"TF_{params['short_window']}_{params['long_window']}_{params['rebalance_days']}", **params)
    elif strategy_type == "MeanReversion":
        return MeanReversionStrategy(name=f"MR_{params['window']}_{params['num_std']}_{params['exit_z']}", **params)
    elif strategy_type == "MultiFactor":
        m = int(params["momentum_weight"] * 10)
        v = int(params["volatility_weight"] * 10)
        s = int(params["sentiment_weight"] * 10)
        return MultiFactorStrategy(name=f"MF_{params['lookback_days']}_M{m}V{v}S{s}", **params)
    else:
        raise ValueError(f"未知的策略类型: {strategy_type}")


class GridOptimizer:
    """
    高拟真网格寻优与样本外验证执行器
    """

    def __init__(self, data_dict: Dict[str, pd.DataFrame], benchmark_df: pd.DataFrame):
        self.data_dict = data_dict
        self.benchmark_df = benchmark_df
        self.engine = BacktestEngine(initial_cash=1_000_000.0)

        # 预先计算基准在各区间的夏普比率，作为样本外折叠验证的基准线
        self.bm_sharpe_dict = self._calc_benchmark_sharpes()

    def _calc_benchmark_sharpes(self) -> Dict[str, float]:
        """计算基准在各子区间的夏普比率"""
        bm = self.benchmark_df.sort_values("date").reset_index(drop=True)
        res = {}
        for name, s_d, e_d in [
            ("fold1", FOLD1_START, FOLD1_END),
            ("fold2", FOLD2_START, FOLD2_END),
            ("fold3", FOLD3_START, FOLD3_END),
            ("oos", OOS_START, OOS_END),
            ("is", IS_START, IS_END),
            ("full", FULL_START, FULL_END),
        ]:
            sub = bm[(bm["date"] >= s_d) & (bm["date"] <= e_d)]
            if len(sub) > 2:
                rets = sub["close"].pct_change().dropna()
                excess = rets - (RISK_FREE_RATE / ANNUAL_TRADING_DAYS)
                std = rets.std()
                sh = float((excess.mean() / std) * np.sqrt(ANNUAL_TRADING_DAYS)) if std > 1e-8 else 0.0
                res[name] = round(sh, 4)
            else:
                res[name] = 0.0
        return res

    def run_all(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        运行全部 68 组网格寻优，返回对比结果 DataFrame 及最优策略汇总
        """
        grid = generate_grid_parameters()
        records: List[Dict[str, Any]] = []

        total = len(grid)
        logger.info(f"开始执行 68 组参数网格寻优与三折滚动检验 (总组合数: {total})...")

        for idx, item in enumerate(grid, 1):
            strategy_type = item["strategy_type"]
            params = item["params"]
            strategy = create_strategy_instance(strategy_type, params)

            # 1. 预热期无损切片：全量历史数据生成连续信号
            weights_df = strategy.generate_signals(self.data_dict)

            # 2. 依次撮合结算各个子区间
            # (A) 全周期 (Full: 2019-2024)
            res_full = self.engine.run(strategy, self.data_dict, start_date=FULL_START, end_date=FULL_END)
            m_full = calculate_metrics(res_full["equity_df"], self.benchmark_df, res_full["trades_df"])

            # (B) 样本内 (IS: 2019-2022)
            res_is = self.engine.run(strategy, self.data_dict, start_date=IS_START, end_date=IS_END)
            m_is = calculate_metrics(res_is["equity_df"], self.benchmark_df, res_is["trades_df"])

            # (C) 样本外 (OOS: 2023-2024)
            res_oos = self.engine.run(strategy, self.data_dict, start_date=OOS_START, end_date=OOS_END)
            m_oos = calculate_metrics(res_oos["equity_df"], self.benchmark_df, res_oos["trades_df"])

            # (D) 样本外三折滚动 (Fold 1, Fold 2, Fold 3)
            res_f1 = self.engine.run(strategy, self.data_dict, start_date=FOLD1_START, end_date=FOLD1_END)
            m_f1 = calculate_metrics(res_f1["equity_df"], self.benchmark_df, res_f1["trades_df"])

            res_f2 = self.engine.run(strategy, self.data_dict, start_date=FOLD2_START, end_date=FOLD2_END)
            m_f2 = calculate_metrics(res_f2["equity_df"], self.benchmark_df, res_f2["trades_df"])

            res_f3 = self.engine.run(strategy, self.data_dict, start_date=FOLD3_START, end_date=FOLD3_END)
            m_f3 = calculate_metrics(res_f3["equity_df"], self.benchmark_df, res_f3["trades_df"])

            # 3. 三折滚动验证判定 (每折夏普 > 0 或 不劣于同期基准)
            f1_sh = m_f1["sharpe_ratio"]
            f2_sh = m_f2["sharpe_ratio"]
            f3_sh = m_f3["sharpe_ratio"]

            pass_f1 = (f1_sh > 0) or (f1_sh >= self.bm_sharpe_dict["fold1"])
            pass_f2 = (f2_sh > 0) or (f2_sh >= self.bm_sharpe_dict["fold2"])
            pass_f3 = (f3_sh > 0) or (f3_sh >= self.bm_sharpe_dict["fold3"])
            oos_3fold_pass = bool(pass_f1 and pass_f2 and pass_f3)

            # 4. 稳健综合评分: 重点考察样本外夏普、样本外卡玛比率及三折一致性
            rank_score = (
                m_oos["sharpe_ratio"] * 0.40 +
                m_is["sharpe_ratio"] * 0.20 +
                m_oos["calmar_ratio"] * 0.20 +
                (1.0 if oos_3fold_pass else -0.5) * 0.20
            )

            exp_id = f"OPT_{idx:03d}_{strategy_type}"

            rec = {
                "experiment_id": exp_id,
                "strategy_type": strategy_type,
                "strategy_name": strategy.name,
                "params": json.dumps(params, ensure_ascii=False),
                "is_annual_return": m_is["annual_return"],
                "is_max_drawdown": m_is["max_drawdown"],
                "is_sharpe": m_is["sharpe_ratio"],
                "is_calmar": m_is["calmar_ratio"],
                "is_win_rate": m_is["win_rate"],
                "oos_annual_return": m_oos["annual_return"],
                "oos_max_drawdown": m_oos["max_drawdown"],
                "oos_sharpe": m_oos["sharpe_ratio"],
                "oos_calmar": m_oos["calmar_ratio"],
                "oos_win_rate": m_oos["win_rate"],
                "fold1_sharpe": f1_sh,
                "fold2_sharpe": f2_sh,
                "fold3_sharpe": f3_sh,
                "oos_3fold_pass": oos_3fold_pass,
                "full_annual_return": m_full["annual_return"],
                "full_max_drawdown": m_full["max_drawdown"],
                "full_sharpe": m_full["sharpe_ratio"],
                "full_calmar": m_full["calmar_ratio"],
                "full_win_rate": m_full["win_rate"],
                "trade_count": m_full["trade_count"],
                "rank_score": round(rank_score, 4)
            }
            records.append(rec)

            if idx % 10 == 0 or idx == total:
                logger.info(f"[{idx}/{total}] 寻优推进: {strategy_type} {params} -> OOS夏普: {m_oos['sharpe_ratio']:.2f}, 三折验证: {oos_3fold_pass}")

        df_results = pd.DataFrame(records)

        # 排序：优先三折通过，其次按综合得分从高到低排序
        df_results = df_results.sort_values(
            by=["oos_3fold_pass", "rank_score", "oos_sharpe"],
            ascending=[False, False, False]
        ).reset_index(drop=True)

        # 评选全局最优策略与各类别最优策略
        best_overall_row = df_results.iloc[0]
        category_bests: Dict[str, Dict[str, Any]] = {}

        for st in ["TrendFollowing", "MeanReversion", "MultiFactor"]:
            sub_df = df_results[df_results["strategy_type"] == st]
            if not sub_df.empty:
                cat_best = sub_df.iloc[0]
                category_bests[st] = {
                    "experiment_id": cat_best["experiment_id"],
                    "strategy_name": cat_best["strategy_name"],
                    "params": json.loads(cat_best["params"]),
                    "oos_annual_return": float(cat_best["oos_annual_return"]),
                    "oos_sharpe": float(cat_best["oos_sharpe"]),
                    "oos_max_drawdown": float(cat_best["oos_max_drawdown"]),
                    "oos_3fold_pass": bool(cat_best["oos_3fold_pass"]),
                    "full_annual_return": float(cat_best["full_annual_return"]),
                    "full_sharpe": float(cat_best["full_sharpe"]),
                    "full_max_drawdown": float(cat_best["full_max_drawdown"])
                }

        best_overall = {
            "strategy_type": best_overall_row["strategy_type"],
            "strategy_name": best_overall_row["strategy_name"],
            "params": json.loads(best_overall_row["params"]),
            "oos_annual_return": float(best_overall_row["oos_annual_return"]),
            "oos_sharpe": float(best_overall_row["oos_sharpe"]),
            "oos_max_drawdown": float(best_overall_row["oos_max_drawdown"]),
            "oos_calmar": float(best_overall_row["oos_calmar"]),
            "oos_3fold_pass": bool(best_overall_row["oos_3fold_pass"]),
            "is_annual_return": float(best_overall_row["is_annual_return"]),
            "is_sharpe": float(best_overall_row["is_sharpe"]),
            "full_annual_return": float(best_overall_row["full_annual_return"]),
            "full_sharpe": float(best_overall_row["full_sharpe"]),
            "full_max_drawdown": float(best_overall_row["full_max_drawdown"]),
            "full_calmar": float(best_overall_row["full_calmar"]),
            "full_win_rate": float(best_overall_row["full_win_rate"]),
            "trade_count": int(best_overall_row["trade_count"])
        }

        export_summary = {
            "best_overall": best_overall,
            "category_bests": category_bests,
            "benchmark_summary": self.bm_sharpe_dict,
            "total_evaluated_combinations": total,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return df_results, export_summary

    def export_artifacts(self, df_results: pd.DataFrame, summary_data: Dict[str, Any]) -> Tuple[Path, Path, Path]:
        """
        导出寻优产物：
        1. records/对比结果.csv
        2. strategy/strategy.json
        3. records/runs/best_strategy_equity.png
        """
        RECORDS_DIR.mkdir(parents=True, exist_ok=True)
        RECORDS_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        STRATEGY_DIR.mkdir(parents=True, exist_ok=True)

        # 1. 导出 records/对比结果.csv
        csv_path = RECORDS_DIR / "对比结果.csv"
        df_results.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"68组对比结果已成功导出至: {csv_path}")

        # 2. 导出 strategy/strategy.json
        json_path = STRATEGY_DIR / "strategy.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        logger.info(f"最优策略配置已成功导出至: {json_path}")

        # 3. 运行全局最优策略的全周期回测，绘制带 2023-01-01 样本内外分界竖线的高清净值图
        best_cfg = summary_data["best_overall"]
        best_strategy = create_strategy_instance(best_cfg["strategy_type"], best_cfg["params"])
        best_res = self.engine.run(best_strategy, self.data_dict, start_date=FULL_START, end_date=FULL_END)
        best_metrics = calculate_metrics(best_res["equity_df"], self.benchmark_df, best_res["trades_df"])

        img_path = RECORDS_RUNS_DIR / "best_strategy_equity.png"
        plot_equity_curve(
            equity_df=best_res["equity_df"],
            benchmark_df=self.benchmark_df,
            title=f"全局最优策略 [{best_cfg['strategy_type']}] 全周期净值表现 (2019-2024)",
            save_path=img_path,
            metrics=best_metrics,
            split_date=OOS_START
        )
        logger.info(f"全局最优策略高清对比图已保存至: {img_path}")

        return csv_path, json_path, img_path

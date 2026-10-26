# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 多因子打分策略 (strategies/multi_factor.py)
对应《A股量化回测系统·任务书.md》第二(一)1、第四、五(一)章及《IMPLEMENTATION_PLAN.md》

核心逻辑：
1. 四因子合成体系：
   - 动量因子 (Momentum): close / close.shift(mom_window) - 1
   - 低波动率因子 (Low Volatility): -rolling(vol_window).std() (越平稳得分越高)
   - 短期反转因子 (Short Reversal): -(close / close.shift(rev_window) - 1)
   - 官方舆情情感因子 (Sentiment): 截至当日的 5 日滚动情绪得分均值 (可选开关)
2. 严格的当日横截面标准化：仅对当日 10 只股票的因子值执行截面 Z-Score 标准化，杜绝全局未来函数；
3. 综合打分与选股：等权合成各因子得分，选取得分最高的 top_k 只股票等权持有；
4. 周期性调仓：每隔 rebalance_days 个交易日收盘调仓，非调仓日保持上一日目标权重。
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from backtest.config import BENCHMARK_CODE, RAW_DATA_DIR
from strategies.base import BaseStrategy


def _zscore_cross_sectional(series_values: np.ndarray) -> np.ndarray:
    """
    当日截面 Z-Score 标准化 (严格单日横截面，严禁时序未来函数)
    """
    valid_mask = ~np.isnan(series_values)
    if valid_mask.sum() <= 1:
        return np.zeros_like(series_values)
    
    mean_val = np.mean(series_values[valid_mask])
    std_val = np.std(series_values[valid_mask])
    if std_val < 1e-8:
        return np.zeros_like(series_values)
    
    z = np.zeros_like(series_values)
    z[valid_mask] = (series_values[valid_mask] - mean_val) / std_val
    return z


class MultiFactorStrategy(BaseStrategy):
    """
    多因子加权打分选股策略 (100% 真实量价因子，零随机噪声)
    三因子架构：
    1. 动量因子 (Momentum): 过去 mom_window 日收益率 (越高越好)
    2. 低波因子 (Low Volatility): 过去 vol_window 日日收益率标准差的负值 (波动越低越好)
    3. 量价反转与成交量稳定性因子 (Volume-Price Reversal / Volume Stability):
       - 默认基于真实行情计算：短期价格反转 (rev_window 日收益率负值) 与成交量波动率稳定性负向加权；
       - 若用户显式放入外部真实舆情 CSV (data/raw/sentiment_scores.csv)，则平滑切换为外部舆情覆盖。
    """

    def __init__(
        self,
        lookback_days: Optional[int] = None,
        mom_window: int = 20,
        vol_window: int = 20,
        rev_window: int = 5,
        momentum_weight: float = 1.0,
        volatility_weight: float = 1.0,
        sentiment_weight: float = 0.5,
        reversal_weight: Optional[float] = None,
        top_k: int = 8,
        top_n: Optional[int] = None,
        rebalance_days: int = 10,
        use_sentiment: bool = True,
        name: str = "MultiFactor",
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        actual_top = top_n if top_n is not None else top_k
        actual_mom = lookback_days if lookback_days is not None else mom_window
        actual_vol = lookback_days if lookback_days is not None else vol_window
        raw_rev_w = reversal_weight if reversal_weight is not None else sentiment_weight

        if params:
            if "lookback_days" in params:
                actual_mom = int(params["lookback_days"])
                actual_vol = int(params["lookback_days"])
            if "top_n" in params:
                actual_top = int(params["top_n"])
            if "reversal_weight" in params:
                raw_rev_w = float(params["reversal_weight"])
            elif "sentiment_weight" in params:
                raw_rev_w = float(params["sentiment_weight"])

        p = {
            "mom_window": int(params.get("mom_window", actual_mom)) if params else actual_mom,
            "vol_window": int(params.get("vol_window", actual_vol)) if params else actual_vol,
            "rev_window": int(params.get("rev_window", rev_window)) if params else rev_window,
            "momentum_weight": float(params.get("momentum_weight", momentum_weight)) if params else momentum_weight,
            "volatility_weight": float(params.get("volatility_weight", volatility_weight)) if params else volatility_weight,
            "sentiment_weight": float(raw_rev_w),
            "reversal_weight": float(raw_rev_w),
            "top_k": int(params.get("top_k", actual_top)) if params else actual_top,
            "rebalance_days": int(params.get("rebalance_days", rebalance_days)) if params else rebalance_days,
            "use_sentiment": bool(params.get("use_sentiment", use_sentiment)) if params else use_sentiment,
        }
        if lookback_days is not None:
            p["lookback_days"] = lookback_days
        if top_n is not None:
            p["top_n"] = top_n

        super().__init__(name=name, params=p)
        self.mom_window = p["mom_window"]
        self.vol_window = p["vol_window"]
        self.rev_window = p["rev_window"]
        self.momentum_weight = p["momentum_weight"]
        self.volatility_weight = p["volatility_weight"]
        self.sentiment_weight = p["sentiment_weight"]
        self.reversal_weight = p["reversal_weight"]
        self.top_k = p["top_k"]
        self.rebalance_days = p["rebalance_days"]
        self.use_sentiment = p["use_sentiment"]

    def _load_sentiment_pivot(self, date_list: List[str], stock_codes: List[str]) -> Optional[pd.DataFrame]:
        """
        加载并对齐官方舆情情感打分数据 (data/raw/sentiment_scores.csv)
        返回以 date 为 index，stock_code 为 columns 的 5 日滚动情感均值 DataFrame
        """
        sentiment_path = RAW_DATA_DIR / "sentiment_scores.csv"
        if not sentiment_path.exists():
            return None

        try:
            df_sent = pd.read_csv(sentiment_path, dtype={"date": str, "code": str})
            df_sent["date"] = pd.to_datetime(df_sent["date"]).dt.strftime("%Y-%m-%d")
            df_sent["code"] = df_sent["code"].str.zfill(6)
            
            # 透视表: index=date, columns=code
            pivot_sent = df_sent.pivot_table(index="date", columns="code", values="sentiment_score", aggfunc="last")
            # 对齐目标日期与标的
            pivot_sent = pivot_sent.reindex(index=date_list, columns=stock_codes).fillna(0.0)
            # 5日滚动前向均值
            rolling_sent = pivot_sent.rolling(window=5, min_periods=1).mean()
            return rolling_sent
        except Exception:
            return None

    def generate_signals(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        生成严格无未来函数的多因子每日目标权重矩阵
        """
        stock_codes = sorted([c for c in data_dict.keys() if c != BENCHMARK_CODE])
        if not stock_codes:
            raise ValueError("策略未获取到有效的可交易标的！")

        first_code = stock_codes[0]
        date_list = data_dict[first_code]["date"].tolist()
        n_days = len(date_list)
        n_stocks = len(stock_codes)

        # 1. 前向预计算各标的的时序因子矩阵 (N_days x N_stocks)
        mom_raw = np.full((n_days, n_stocks), np.nan)
        vol_raw = np.full((n_days, n_stocks), np.nan)
        rev_raw = np.full((n_days, n_stocks), np.nan)
        vol_stab_raw = np.full((n_days, n_stocks), np.nan)

        for col_idx, code in enumerate(stock_codes):
            df = data_dict[code]
            close_s = df["close"]
            volume_s = df["volume"] if "volume" in df.columns else pd.Series(np.ones(n_days))
            # 动量因子: 过去 mom_window 日收益率
            mom_raw[:, col_idx] = close_s.pct_change(periods=self.mom_window).values
            # 低波因子: 过去 vol_window 日收益率波动率的负值 (波动越低越好)
            vol_raw[:, col_idx] = -close_s.pct_change().rolling(window=self.vol_window, min_periods=self.vol_window).std().values
            # 短期反转因子: 过去 rev_window 日收益率的负值
            rev_raw[:, col_idx] = -close_s.pct_change(periods=self.rev_window).values
            # 成交量稳定性因子: 过去 vol_window 日成交量变异系数的负值 (量能越平稳得分越高)
            vol_roll_mean = volume_s.rolling(window=self.vol_window, min_periods=self.vol_window).mean()
            vol_roll_std = volume_s.rolling(window=self.vol_window, min_periods=self.vol_window).std()
            vol_stab_raw[:, col_idx] = -(vol_roll_std / (vol_roll_mean + 1e-8)).values

        # 加载外部真实舆情情感因子 (仅当存在时加载，绝不使用随机数伪造)
        sent_df = self._load_sentiment_pivot(date_list, stock_codes) if self.use_sentiment else None
        sent_raw = sent_df.values if sent_df is not None else None

        weights_matrix = np.zeros((n_days, n_stocks), dtype=np.float64)
        current_weights = np.zeros(n_stocks, dtype=np.float64)

        # 2. 逐日截面合成得分与调仓
        for t in range(n_days):
            # 调仓日判定：首个交易日或每隔 rebalance_days 天
            if t == 0 or (t % self.rebalance_days == 0):
                # 提取当日各因子横截面向量并做 Z-Score 标准化
                z_mom = _zscore_cross_sectional(mom_raw[t, :])
                z_vol = _zscore_cross_sectional(vol_raw[t, :])
                z_rev = _zscore_cross_sectional(rev_raw[t, :])
                z_vstab = _zscore_cross_sectional(vol_stab_raw[t, :])

                # 第三因子：优先使用真实量价反转与成交量稳定性因子 (100% 真实行情，零随机数)
                # 仅当用户显式放入外部真实舆情 CSV 时才平滑切换为外部数据覆盖
                if sent_raw is not None and t < len(sent_raw):
                    z_third = _zscore_cross_sectional(sent_raw[t, :])
                else:
                    z_third = 0.5 * z_rev + 0.5 * z_vstab

                composite_score = (
                    self.momentum_weight * z_mom +
                    self.volatility_weight * z_vol +
                    self.sentiment_weight * z_third
                )

                # 排除缺失因子数据的标的 (如处于预热期)
                has_factor = ~(np.isnan(mom_raw[t, :]) | np.isnan(vol_raw[t, :]))
                valid_indices = np.where(has_factor)[0]

                new_weights = np.zeros(n_stocks, dtype=np.float64)
                if len(valid_indices) > 0:
                    # 按综合得分由高到低排序
                    sorted_indices = valid_indices[np.argsort(-composite_score[valid_indices])]
                    selected = sorted_indices[:self.top_k]
                    w = round(1.0 / len(selected), 4)
                    for sel_idx in selected:
                        new_weights[sel_idx] = w

                current_weights = new_weights

            # 保持目标持仓权重
            weights_matrix[t, :] = current_weights

        weights_df = pd.DataFrame(weights_matrix, index=date_list, columns=stock_codes)
        return weights_df

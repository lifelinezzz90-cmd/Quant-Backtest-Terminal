# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 趋势跟踪策略 (strategies/trend_following.py)
对应《A股量化回测系统·任务书.md》第二(一)1、附录及《IMPLEMENTATION_PLAN.md》

核心逻辑：
1. 均线交叉与动量增强：计算每只股票 short_window 与 long_window 的收盘价简单移动平均线 (SMA)；
2. 调仓与持仓筛选：每隔 rebalance_days 个交易日收盘，筛选 SMA_short > SMA_long 的标的；
3. 风险控制与分散配置：若合格标的大于 max_positions，按 short_window 动量涨幅降序排列选取前 max_positions 只等权持有；
4. 绝对零未来函数：仅基于滚动历史收盘价计算，非调仓日保持上一期目标权重。
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from backtest.config import BENCHMARK_CODE
from strategies.base import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    """
    趋势跟踪策略 (双均线交叉 + 动量优选)
    """

    def __init__(
        self,
        short_window: int = 10,
        long_window: int = 30,
        max_positions: int = 8,
        rebalance_days: int = 5,
        name: str = "TrendFollowing",
        params: Optional[Dict[str, Any]] = None
    ):
        p = {
            "short_window": int(params.get("short_window", short_window)) if params else short_window,
            "long_window": int(params.get("long_window", long_window)) if params else long_window,
            "max_positions": int(params.get("max_positions", max_positions)) if params else max_positions,
            "rebalance_days": int(params.get("rebalance_days", rebalance_days)) if params else rebalance_days,
        }
        super().__init__(name=name, params=p)
        self.short_window = p["short_window"]
        self.long_window = p["long_window"]
        self.max_positions = p["max_positions"]
        self.rebalance_days = p["rebalance_days"]

    def generate_signals(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        生成严格无未来函数的每日目标权重矩阵
        """
        # 排除基准指数
        stock_codes = sorted([c for c in data_dict.keys() if c != BENCHMARK_CODE])
        if not stock_codes:
            raise ValueError("策略未获取到有效的可交易标的！")

        first_code = stock_codes[0]
        date_list = data_dict[first_code]["date"].tolist()
        n_days = len(date_list)

        # 预计算每只股票的均线与动量 (仅前向 rolling)
        sma_short_dict = {}
        sma_long_dict = {}
        mom_dict = {}

        for code in stock_codes:
            df = data_dict[code]
            close_s = df["close"]
            sma_s = close_s.rolling(window=self.short_window, min_periods=self.short_window).mean()
            sma_l = close_s.rolling(window=self.long_window, min_periods=self.long_window).mean()
            # 动量: 近期短周期涨幅
            mom_s = close_s.pct_change(periods=self.short_window)

            sma_short_dict[code] = sma_s.values
            sma_long_dict[code] = sma_l.values
            mom_dict[code] = mom_s.values

        weights_matrix = np.zeros((n_days, len(stock_codes)), dtype=np.float64)
        current_weights = np.zeros(len(stock_codes), dtype=np.float64)

        # 逐日生成目标权重（严禁未来函数）
        for t in range(n_days):
            # 调仓日判定：首个交易日或每隔 rebalance_days 天
            if t == 0 or (t % self.rebalance_days == 0):
                selected = []
                for idx, code in enumerate(stock_codes):
                    s_val = sma_short_dict[code][t]
                    l_val = sma_long_dict[code][t]
                    # 必须有足够的历史窗口形成有效均线
                    if np.isnan(s_val) or np.isnan(l_val):
                        continue
                    if s_val > l_val:
                        m_val = mom_dict[code][t]
                        selected.append((idx, code, m_val if not np.isnan(m_val) else 0.0))

                new_weights = np.zeros(len(stock_codes), dtype=np.float64)
                if selected:
                    # 若超过最大持仓数，按动量降序截取前 max_positions 只
                    if len(selected) > self.max_positions:
                        selected.sort(key=lambda x: x[2], reverse=True)
                        selected = selected[:self.max_positions]

                    # 目标权重分配
                    w = round(1.0 / len(selected), 4)
                    for item in selected:
                        new_weights[item[0]] = w

                current_weights = new_weights

            # 记录当日收盘目标权重
            weights_matrix[t, :] = current_weights

        weights_df = pd.DataFrame(weights_matrix, index=date_list, columns=stock_codes)
        return weights_df

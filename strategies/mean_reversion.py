# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 均值回复策略 (strategies/mean_reversion.py)
对应《A股量化回测系统·任务书.md》第二(一)1、附录及《IMPLEMENTATION_PLAN.md》

核心逻辑：
1. 布林带/Z-Score 波动通道：计算每只股票收盘价的 window 日均线与标准差；
2. 超跌买入与均值回归平仓状态机：
   - 当股票处于空仓状态且 z_score < -num_std 时，触发超跌反弹建仓信号 (state = 1)；
   - 当股票处于持仓状态且 z_score >= exit_z 时，触发均线回归平仓信号 (state = 0)；
3. 多标的分散与头寸管理：对处于持有状态的标的分配目标权重 (单票基准 1.0 / max_positions)；
4. 严格零未来函数：逐日前向更新状态机，物理截断不变。
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from backtest.config import BENCHMARK_CODE
from strategies.base import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    均值回复策略 (布林带突破回归 + 状态机追踪)
    """

    def __init__(
        self,
        window: int = 20,
        num_std: float = 1.8,
        exit_z: float = 0.0,
        max_positions: int = 8,
        name: str = "MeanReversion",
        params: Optional[Dict[str, Any]] = None
    ):
        p = {
            "window": int(params.get("window", window)) if params else window,
            "num_std": float(params.get("num_std", num_std)) if params else num_std,
            "exit_z": float(params.get("exit_z", exit_z)) if params else exit_z,
            "max_positions": int(params.get("max_positions", max_positions)) if params else max_positions,
        }
        super().__init__(name=name, params=p)
        self.window = p["window"]
        self.num_std = p["num_std"]
        self.exit_z = p["exit_z"]
        self.max_positions = p["max_positions"]

    def generate_signals(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        生成严格无未来函数的每日目标权重矩阵
        """
        stock_codes = sorted([c for c in data_dict.keys() if c != BENCHMARK_CODE])
        if not stock_codes:
            raise ValueError("策略未获取到有效的可交易标的！")

        first_code = stock_codes[0]
        date_list = data_dict[first_code]["date"].tolist()
        n_days = len(date_list)

        # 预计算每只股票的 Z-Score (仅滚动历史窗口)
        z_score_dict = {}
        for code in stock_codes:
            close_s = data_dict[code]["close"]
            mid = close_s.rolling(window=self.window, min_periods=self.window).mean()
            std = close_s.rolling(window=self.window, min_periods=self.window).std()
            z = (close_s - mid) / (std + 1e-8)
            z_score_dict[code] = z.values

        weights_matrix = np.zeros((n_days, len(stock_codes)), dtype=np.float64)
        
        # 维护每只股票的持有状态 (0: 空仓, 1: 持仓)
        holding_states = {code: 0 for code in stock_codes}

        for t in range(n_days):
            active_codes = []
            for idx, code in enumerate(stock_codes):
                z_val = z_score_dict[code][t]
                if np.isnan(z_val):
                    continue

                curr_state = holding_states[code]
                if curr_state == 0:
                    # 空仓状态：超跌买入信号触发
                    if z_val < -self.num_std:
                        holding_states[code] = 1
                        active_codes.append(idx)
                else:
                    # 持仓状态：价格已回归均线或上方，触发平仓信号
                    if z_val >= self.exit_z:
                        holding_states[code] = 0
                    else:
                        active_codes.append(idx)

            # 资金权重分配
            if active_codes:
                if len(active_codes) <= self.max_positions:
                    w = round(1.0 / self.max_positions, 4)
                else:
                    w = round(1.0 / len(active_codes), 4)

                for a_idx in active_codes:
                    weights_matrix[t, a_idx] = w

        weights_df = pd.DataFrame(weights_matrix, index=date_list, columns=stock_codes)
        return weights_df

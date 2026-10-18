# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 策略基类模块 (strategies/base.py)
对应《A股量化回测系统·任务书.md》第二(一)1、五(一)及《IMPLEMENTATION_PLAN.md》核心契约

定义所有策略必须继承的抽象基类 BaseStrategy：
- 规范化参数管理与名称标识
- 核心抽象接口 generate_signals(data_dict) -> pd.DataFrame 目标权重矩阵
- 内置基准/测试用等权买入持有策略 EqualWeightBuyHoldStrategy
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from backtest.config import BENCHMARK_CODE


class BaseStrategy(ABC):
    """
    策略抽象基类
    所有具体策略（趋势跟踪、均值回复、多因子打分）均继承此类
    """

    def __init__(self, name: str = "BaseStrategy", params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        核心信号生成函数（无未来函数）
        
        参数:
            data_dict: 字典形式对齐的行情数据，Key 为股票代码（如 '600519'），
                       Value 为清洗后的 DataFrame（包含 date, open, high, low, close, volume 等列）
                       
        返回:
            weights_df: 目标持仓权重 DataFrame:
                - index: 交易日期 (str, YYYY-MM-DD)
                - columns: 股票代码 (str)
                - values: 目标持仓权重 [0.0, 1.0]，且每日所有股票权重之和 <= 1.0
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', params={self.params})>"


class EqualWeightBuyHoldStrategy(BaseStrategy):
    """
    等权买入持有策略（用于基准对照与回测引擎冒烟测试）
    在首个交易日收盘生成目标等权分配信号，后续交易日保持权重不变
    """

    def __init__(self, stocks: Optional[List[str]] = None, name: str = "EqualWeightBuyHold", params: Optional[Dict[str, Any]] = None):
        p = params or {}
        if stocks is not None:
            p["stocks"] = stocks
        super().__init__(name=name, params=p)
        self.target_stocks = stocks

    def generate_signals(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        # 排除基准指数 000300
        available_stocks = [c for c in data_dict.keys() if c != BENCHMARK_CODE]
        if self.target_stocks:
            stock_list = [c for c in self.target_stocks if c in available_stocks]
        else:
            stock_list = available_stocks

        if not stock_list:
            raise ValueError("策略未找到有效的可交易股票池标的")

        # 提取基准时间轴（从任一股票或基准数据中提取）
        first_df = next(iter(data_dict.values()))
        date_series = first_df["date"].tolist()

        n_stocks = len(stock_list)
        weight_per_stock = round(1.0 / n_stocks, 4)

        # 构造全部交易日的权重矩阵
        weights_data = {code: np.full(len(date_series), weight_per_stock) for code in stock_list}
        weights_df = pd.DataFrame(weights_data, index=date_series)
        return weights_df

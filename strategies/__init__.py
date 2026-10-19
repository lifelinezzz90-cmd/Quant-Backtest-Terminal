# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 策略插件包 (strategies)
"""

from strategies.base import BaseStrategy, EqualWeightBuyHoldStrategy
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.multi_factor import MultiFactorStrategy

__all__ = [
    "BaseStrategy",
    "EqualWeightBuyHoldStrategy",
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "MultiFactorStrategy"
]

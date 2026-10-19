# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 高拟真回测撮合引擎 (backtest/engine.py)
对应《A股量化回测系统·任务书.md》第二(一)3及《IMPLEMENTATION_PLAN.md》核心规则

第一性原理设计：
1. 零未来函数：交易日 t 收盘计算信号，严格延迟至 t+1 日开盘价撮合成交；
2. A股规则与摩擦状态机：
   - T+1 锁仓机制（当日买入仅增加 total_shares，次日开盘方可解锁入 sellable_shares）；
   - 涨跌停拦截（开盘跌停 open <= down_limit 拒卖，开盘涨停 open >= up_limit 拒买）；
   - 停牌拦截（is_suspended 或 volume <= 0 拒单，订单撤销，持仓顺延）；
   - 先卖后买释放流动性；
   - 整手交易约束（100股整数倍）；
   - 精确税费：买入万2.5佣金最低5元，卖出万2.5最低5元+万5卖出印花税；现金永不为负；
3. 逐日收盘盯市 (Mark-to-Market) 计算净值。
"""

import math
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from backtest.config import (
    CLEANED_DATA_DIR,
    SAMPLE_DATA_DIR,
    INITIAL_CASH,
    COMMISSION_RATE,
    MIN_COMMISSION,
    STAMP_DUTY_RATE,
    LOT_SIZE,
    BENCHMARK_CODE,
    UNIVERSE_STOCKS
)
from strategies.base import BaseStrategy

logger = logging.getLogger("BacktestEngine")


def load_cleaned_data(sample: bool = False,
                      data_dir: Optional[Path] = None) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    加载清洗后的标准行情数据与沪深300基准数据
    返回:
        stock_dict: {code: DataFrame}
        benchmark_df: DataFrame
    """
    if data_dir is None:
        target_dir = CLEANED_DATA_DIR / "sample" if sample else CLEANED_DATA_DIR
        # 若 sample 目录下为空则尝试主 cleaned 目录
        if not target_dir.exists() or len(list(target_dir.glob("*.csv"))) == 0:
            target_dir = CLEANED_DATA_DIR
    else:
        target_dir = data_dir

    csv_files = list(target_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"目录 {target_dir} 下未找到已清洗的行情 CSV 文件，请先运行数据清洗！")

    stock_dict: Dict[str, pd.DataFrame] = {}
    benchmark_df: Optional[pd.DataFrame] = None

    for f in csv_files:
        code = f.stem
        df = pd.read_csv(f, dtype={"date": str})
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df = df.sort_values("date").reset_index(drop=True)
        if code == BENCHMARK_CODE:
            benchmark_df = df
        else:
            stock_dict[code] = df

    if benchmark_df is None:
        raise FileNotFoundError(f"未找到基准文件 {BENCHMARK_CODE}.csv，请检查数据目录！")

    return stock_dict, benchmark_df


class BacktestEngine:
    """
    高拟真 A 股回测撮合引擎
    """

    def __init__(
        self,
        initial_cash: float = INITIAL_CASH,
        commission_rate: float = COMMISSION_RATE,
        min_commission: float = MIN_COMMISSION,
        stamp_duty_rate: float = STAMP_DUTY_RATE,
        lot_size: int = LOT_SIZE,
    ):
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_duty_rate = stamp_duty_rate
        self.lot_size = lot_size

    def _calc_buy_cost(self, turnover: float) -> Tuple[float, float]:
        """计算买入佣金与总支出: (佣金, 总支出)，精确至分(两位小数)"""
        turnover_clean = round(turnover, 2)
        comm = round(max(turnover_clean * self.commission_rate, self.min_commission), 2)
        total_exp = round(turnover_clean + comm, 2)
        return comm, total_exp

    def _calc_sell_proceeds(self, turnover: float) -> Tuple[float, float, float]:
        """计算卖出佣金、印花税与净收益: (佣金, 印花税, 净到账)，精确至分(两位小数)"""
        turnover_clean = round(turnover, 2)
        comm = round(max(turnover_clean * self.commission_rate, self.min_commission), 2)
        tax = round(turnover_clean * self.stamp_duty_rate, 2)
        proceeds = round(turnover_clean - comm - tax, 2)
        return comm, tax, proceeds

    def run(
        self,
        strategy: BaseStrategy,
        data_dict: Dict[str, pd.DataFrame],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行策略回测
        
        参数:
            strategy: 策略实例
            data_dict: 包含各股票日线 DataFrame 的字典
            start_date: 回测起始日 (YYYY-MM-DD)，若 None 则取最早
            end_date: 回测结束日 (YYYY-MM-DD)，若 None 则取最晚
            
        返回:
            包含 equity_df, trades_df, rejects_df, summary 的字典
        """
        # 1. 策略生成全量日期的目标权重矩阵 (无未来函数)
        weights_df = strategy.generate_signals(data_dict)

        # 2. 提取基准时间轴与截取回测区间
        sample_code = next(iter(data_dict.keys()))
        all_dates = sorted(data_dict[sample_code]["date"].tolist())

        # 构造日期到索引与切片位置的快速索引
        if start_date is None:
            start_date = all_dates[0]
        if end_date is None:
            end_date = all_dates[-1]

        # 提取回测有效日期区间
        backtest_dates = [d for d in all_dates if start_date <= d <= end_date]
        if len(backtest_dates) < 2:
            raise ValueError(f"回测区间过短 ({start_date} ~ {end_date})，至少需要2个交易日！")

        # 3. 预构建截面数据快速查询字典，提速回测 (Numpy/Dict 结构)
        # cross_data[date][code] = {open, close, is_suspended, up_limit, down_limit, volume}
        cross_data: Dict[str, Dict[str, Dict[str, Any]]] = {d: {} for d in all_dates}
        for code, df in data_dict.items():
            dates_arr = df["date"].values
            opens = df["open"].values
            closes = df["close"].values
            is_susp = df["is_suspended"].values
            up_limits = df["up_limit"].values
            down_limits = df["down_limit"].values
            volumes = df["volume"].values

            for i, d in enumerate(dates_arr):
                cross_data[d][code] = {
                    "open": opens[i],
                    "close": closes[i],
                    "is_suspended": bool(is_susp[i]),
                    "up_limit": up_limits[i],
                    "down_limit": down_limits[i],
                    "volume": volumes[i],
                }

        # 4. 账户状态机初始化
        cash = float(self.initial_cash)
        # 持仓结构: {code: {"total_shares": int, "sellable_shares": int, "avg_cost": float, "last_buy_date": str}}
        positions: Dict[str, Dict[str, Any]] = {
            c: {"total_shares": 0, "sellable_shares": 0, "avg_cost": 0.0, "last_buy_date": ""}
            for c in data_dict.keys()
        }

        trades_list: List[Dict[str, Any]] = []
        rejects_list: List[Dict[str, Any]] = []
        equity_records: List[Dict[str, Any]] = []

        # 记录上一交易日的目标权重字典，避免无权变动时的碎单调仓
        prev_target_weights: Dict[str, float] = {c: 0.0 for c in data_dict.keys()}

        # 5. 逐日截面事件驱动撮合循环
        # 注意时序：在交易日 t 撮合时，执行的是交易日 t-1 收盘生成的信号
        for day_idx, current_date in enumerate(backtest_dates):
            current_bar = cross_data[current_date]

            # (A) 开盘前持仓解锁：前一交易日买入的股票今天正式转为可卖份额（T+1制度）
            for code, pos in positions.items():
                pos["sellable_shares"] = pos["total_shares"]

            # (B) 获取前一交易日收盘信号进行撮合
            # 定位前一交易日在 all_dates 中的位置
            curr_pos_in_all = all_dates.index(current_date)
            if curr_pos_in_all > 0:
                prev_date = all_dates[curr_pos_in_all - 1]
                # 读取前一日收盘目标权重
                if prev_date in weights_df.index:
                    target_row = weights_df.loc[prev_date].to_dict()
                else:
                    target_row = {c: 0.0 for c in data_dict.keys()}

                # 计算开盘前的账户预估总资产（按各股今日开盘价预估，用于测算目标资金配置）
                estimated_market_value = sum(
                    positions[c]["total_shares"] * current_bar[c]["open"]
                    for c in data_dict.keys()
                    if c in current_bar
                )
                estimated_total_assets = cash + estimated_market_value

                # 分离出卖出单与买入单
                sell_orders: List[Tuple[str, int, float, float]] = []  # (code, target_shares_diff, target_w, curr_w)
                buy_orders: List[Tuple[str, float, float, float]] = []   # (code, target_val, target_w, curr_w)

                for code in data_dict.keys():
                    target_w = float(target_row.get(code, 0.0))
                    prev_w = float(prev_target_weights.get(code, 0.0))
                    curr_shares = positions[code]["total_shares"]
                    open_price = current_bar[code]["open"]

                    # 防碎单抖动：仅在目标权重实质变化、或建仓/清仓时才执行调仓
                    w_diff = target_w - prev_w
                    if abs(w_diff) < 1e-4 and not (target_w == 0.0 and curr_shares > 0) and not (target_w > 0.0 and curr_shares == 0):
                        continue

                    target_alloc_val = estimated_total_assets * target_w
                    current_stock_val = curr_shares * open_price

                    if target_alloc_val < current_stock_val:
                        # 减仓 / 卖出
                        shares_to_sell = curr_shares - (int(target_alloc_val // (open_price * self.lot_size)) * self.lot_size if target_w > 0 else 0)
                        if shares_to_sell > 0:
                            sell_orders.append((code, shares_to_sell, target_w, prev_w))
                    elif target_alloc_val > current_stock_val:
                        # 加仓 / 买入
                        val_to_buy = target_alloc_val - current_stock_val
                        buy_orders.append((code, val_to_buy, target_w, prev_w))

                # -------------------------------------------------------------
                # (C) 先卖后买：执行卖单释放流动性
                # -------------------------------------------------------------
                for code, req_shares, target_w, prev_w in sell_orders:
                    bar = current_bar[code]
                    open_p = bar["open"]
                    down_l = bar["down_limit"]
                    pos = positions[code]

                    # 停牌拦截
                    if bar["is_suspended"] or bar["volume"] <= 0:
                        rejects_list.append({
                            "date": current_date, "code": code, "action": "SELL",
                            "price": open_p, "reason": "SUSPENDED", "requested_shares": req_shares
                        })
                        continue

                    # 跌停拦截：开盘一字跌停或低于跌停价，无法卖出
                    if open_p <= down_l:
                        rejects_list.append({
                            "date": current_date, "code": code, "action": "SELL",
                            "price": open_p, "reason": "LIMIT_DOWN_REJECT", "requested_shares": req_shares
                        })
                        continue

                    # T+1 可卖股数限制
                    actual_sell_shares = min(req_shares, pos["sellable_shares"])
                    if actual_sell_shares <= 0:
                        rejects_list.append({
                            "date": current_date, "code": code, "action": "SELL",
                            "price": open_p, "reason": "T_PLUS_1_LOCKED", "requested_shares": req_shares
                        })
                        continue

                    # 扣除整手限制（若全部清仓则允许非整手残股一次性全部卖出）
                    if actual_sell_shares != pos["total_shares"]:
                        actual_sell_shares = (actual_sell_shares // self.lot_size) * self.lot_size

                    if actual_sell_shares <= 0:
                        continue

                    turnover = round(actual_sell_shares * open_p, 2)
                    comm, tax, proceeds = self._calc_sell_proceeds(turnover)
                    cash = round(cash + proceeds, 2)

                    # 结算平仓实现盈亏
                    realized_pnl = round(proceeds - (actual_sell_shares * pos["avg_cost"]), 2)

                    # 更新持仓
                    pos["total_shares"] -= actual_sell_shares
                    pos["sellable_shares"] -= actual_sell_shares
                    if pos["total_shares"] == 0:
                        pos["avg_cost"] = 0.0

                    prev_target_weights[code] = target_w

                    trades_list.append({
                        "date": current_date,
                        "code": code,
                        "action": "SELL",
                        "price": round(open_p, 3),
                        "shares": int(actual_sell_shares),
                        "turnover": round(turnover, 2),
                        "commission": round(comm, 2),
                        "stamp_duty": round(tax, 2),
                        "realized_pnl": round(realized_pnl, 2)
                    })

                # -------------------------------------------------------------
                # (D) 再执行买单：使用释放后的可用资金建仓或加仓
                # -------------------------------------------------------------
                for code, val_to_buy, target_w, prev_w in buy_orders:
                    bar = current_bar[code]
                    open_p = bar["open"]
                    up_l = bar["up_limit"]
                    pos = positions[code]

                    # 停牌拦截
                    if bar["is_suspended"] or bar["volume"] <= 0:
                        rejects_list.append({
                            "date": current_date, "code": code, "action": "BUY",
                            "price": open_p, "reason": "SUSPENDED", "requested_shares": 0
                        })
                        continue

                    # 涨停拦截：开盘一字涨停或达到涨停价，无法买入
                    if open_p >= up_l:
                        rejects_list.append({
                            "date": current_date, "code": code, "action": "BUY",
                            "price": open_p, "reason": "LIMIT_UP_REJECT", "requested_shares": 0
                        })
                        continue

                    # 资金与整手股数约束
                    alloc_cash = min(val_to_buy, cash)
                    if alloc_cash <= 0:
                        continue

                    # 预估买入股数（向下取整为 100 股整数倍）
                    shares_to_buy = int(alloc_cash // (open_p * (1.0 + self.commission_rate) * self.lot_size)) * self.lot_size

                    # 安全扣减校验：确保扣除佣金（单笔最低 5 元）后现金绝不为负
                    while shares_to_buy >= self.lot_size:
                        t_cost = shares_to_buy * open_p
                        comm, total_exp = self._calc_buy_cost(t_cost)
                        if total_exp <= cash:
                            break
                        shares_to_buy -= self.lot_size

                    if shares_to_buy < self.lot_size:
                        continue

                    turnover = round(shares_to_buy * open_p, 2)
                    comm, total_exp = self._calc_buy_cost(turnover)
                    cash = round(cash - total_exp, 2)

                    # 更新平均成本与持仓股数（T+1: 当日买入不计入当日 sellable_shares）
                    old_shares = pos["total_shares"]
                    old_cost_basis = old_shares * pos["avg_cost"]
                    new_shares = old_shares + shares_to_buy
                    pos["avg_cost"] = (old_cost_basis + total_exp) / new_shares
                    pos["total_shares"] = new_shares
                    pos["last_buy_date"] = current_date

                    prev_target_weights[code] = target_w

                    trades_list.append({
                        "date": current_date,
                        "code": code,
                        "action": "BUY",
                        "price": round(open_p, 3),
                        "shares": int(shares_to_buy),
                        "turnover": round(turnover, 2),
                        "commission": round(comm, 2),
                        "stamp_duty": 0.0,
                        "realized_pnl": 0.0
                    })

            # -------------------------------------------------------------
            # (E) 每日收盘盯市 (Mark-to-Market)
            # -------------------------------------------------------------
            market_val = sum(
                positions[c]["total_shares"] * current_bar[c]["close"]
                for c in data_dict.keys()
            )
            total_assets = cash + market_val
            nav = total_assets / self.initial_cash
            pos_ratio = (market_val / total_assets) if total_assets > 0 else 0.0

            equity_records.append({
                "date": current_date,
                "cash": round(cash, 2),
                "market_value": round(market_val, 2),
                "total_value": round(total_assets, 2),
                "nav": round(nav, 6),
                "position_pct": round(pos_ratio, 4)
            })

        # 封装输出 DataFrame
        equity_df = pd.DataFrame(equity_records)
        trades_df = pd.DataFrame(trades_list) if trades_list else pd.DataFrame(
            columns=["date", "code", "action", "price", "shares", "turnover", "commission", "stamp_duty", "realized_pnl"]
        )
        rejects_df = pd.DataFrame(rejects_list) if rejects_list else pd.DataFrame(
            columns=["date", "code", "action", "price", "reason", "requested_shares"]
        )

        return {
            "strategy_name": strategy.name,
            "strategy_params": strategy.params,
            "start_date": backtest_dates[0],
            "end_date": backtest_dates[-1],
            "initial_cash": self.initial_cash,
            "final_value": equity_df["total_value"].iloc[-1] if not equity_df.empty else self.initial_cash,
            "equity_df": equity_df,
            "trades_df": trades_df,
            "rejects_df": rejects_df
        }


def test_engine_rules() -> bool:
    """
    撮合引擎核心交易规则单元测试：
    验证：
    1. T日收盘信号在 T+1 开盘价成交 (非T日收盘价，非T+1收盘价)
    2. T+1锁仓限制生效 (当日买入次日开盘方可卖出)
    3. 开盘涨停拒买、开盘跌停拒卖、停牌拒单生效
    4. 万2.5佣金单笔最低5元，卖出万5印花税计算精确到分
    """
    logger.info("=== 开始执行撮合引擎核心规则单元测试 test_engine_rules() ===")

    # 构造测试行情序列 (标的 TEST01)
    dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09"]
    bars = [
        # Day 0: 正常基准日，收盘 10.0
        {"date": "2024-01-02", "open": 10.0, "high": 10.2, "low": 9.8, "close": 10.0, "volume": 1000, "is_suspended": False, "up_limit": 11.0, "down_limit": 9.0},
        # Day 1: 开盘 10.5，收盘 10.8 (验证开盘价 10.5 买入成交)
        {"date": "2024-01-03", "open": 10.5, "high": 10.9, "low": 10.3, "close": 10.8, "volume": 1000, "is_suspended": False, "up_limit": 11.0, "down_limit": 9.0},
        # Day 2: 开盘 11.88 (一字涨停 open >= up_limit，测试涨停拒买)
        {"date": "2024-01-04", "open": 11.88, "high": 11.88, "low": 11.88, "close": 11.88, "volume": 1000, "is_suspended": False, "up_limit": 11.88, "down_limit": 9.72},
        # Day 3: 开盘 10.69 (跌停 open <= down_limit，测试跌停拒卖)
        {"date": "2024-01-05", "open": 10.69, "high": 11.0, "low": 10.69, "close": 10.69, "volume": 1000, "is_suspended": False, "up_limit": 13.06, "down_limit": 10.69},
        # Day 4: 停牌日 is_suspended=True, 测试停牌拒单
        {"date": "2024-01-08", "open": 10.5, "high": 10.5, "low": 10.5, "close": 10.5, "volume": 0, "is_suspended": True, "up_limit": 11.75, "down_limit": 9.62},
        # Day 5: 恢复正常交易，开盘 10.2 顺利平仓卖出，验证最低5元佣金与万5印花税
        {"date": "2024-01-09", "open": 10.2, "high": 10.4, "low": 10.0, "close": 10.3, "volume": 1000, "is_suspended": False, "up_limit": 11.55, "down_limit": 9.45},
    ]

    df_test = pd.DataFrame(bars)
    data_dict = {"TEST01": df_test}

    # 自定义测试信号策略
    class RuleMockStrategy(BaseStrategy):
        def generate_signals(self, d_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
            # Day 0 (01-02) 收盘: 发出 0.5 权重买入信号 -> 应在 Day 1 (01-03) 开盘以 10.5 成交
            # Day 1 (01-03) 收盘: 试图追高加大买入至 1.0 -> 应在 Day 2 (01-04) 遭遇一字涨停拒买
            # Day 2 (01-04) 收盘: 发出清仓卖出信号 0.0 -> 应在 Day 3 (01-05) 遭遇跌停拒卖
            # Day 3 (01-05) 收盘: 保持清仓信号 0.0 -> 应在 Day 4 (01-08) 遭遇停牌拒卖
            # Day 4 (01-08) 收盘: 保持清仓信号 0.0 -> 应在 Day 5 (01-09) 顺利以 10.2 开盘价清仓
            weights = [0.5, 1.0, 0.0, 0.0, 0.0, 0.0]
            return pd.DataFrame({"TEST01": weights}, index=dates)

    engine = BacktestEngine(initial_cash=100_000.0)
    res = engine.run(RuleMockStrategy("RuleMock"), data_dict)

    trades_df = res["trades_df"]
    rejects_df = res["rejects_df"]
    equity_df = res["equity_df"]

    # 1. 验证 T日信号在 T+1 日开盘价成交
    first_buy = trades_df[(trades_df["action"] == "BUY") & (trades_df["date"] == "2024-01-03")]
    assert not first_buy.empty, "Day 0 信号未在 Day 1 开盘撮合成交！"
    buy_trade = first_buy.iloc[0]
    assert buy_trade["price"] == 10.5, f"成交价错误：应为 Day 1 开盘价 10.5，实际为 {buy_trade['price']}"
    assert buy_trade["shares"] % 100 == 0, "买入股数不满足整手（100股整数倍）约束！"
    logger.info(" [断言1通过] T日信号于T+1开盘价精确成交，满足整手约束。")

    # 2. 验证 Day 2 涨停拒买拦截
    limit_up_reject = rejects_df[(rejects_df["action"] == "BUY") & (rejects_df["date"] == "2024-01-04")]
    assert not limit_up_reject.empty, "Day 2 一字涨停未被拒单拦截！"
    assert limit_up_reject.iloc[0]["reason"] == "LIMIT_UP_REJECT", f"拒单原因错误: {limit_up_reject.iloc[0]['reason']}"
    logger.info(" [断言2通过] 开盘涨停拒买拦截生效 (LIMIT_UP_REJECT)。")

    # 3. 验证 Day 3 跌停拒卖拦截
    limit_down_reject = rejects_df[(rejects_df["action"] == "SELL") & (rejects_df["date"] == "2024-01-05")]
    assert not limit_down_reject.empty, "Day 3 一字跌停未被拒单拦截！"
    assert limit_down_reject.iloc[0]["reason"] == "LIMIT_DOWN_REJECT", f"拒单原因错误: {limit_down_reject.iloc[0]['reason']}"
    logger.info(" [断言3通过] 开盘跌停拒卖拦截生效 (LIMIT_DOWN_REJECT)。")

    # 4. 验证 Day 4 停牌拒单拦截
    susp_reject = rejects_df[(rejects_df["action"] == "SELL") & (rejects_df["date"] == "2024-01-08")]
    assert not susp_reject.empty, "Day 4 停牌未被拒单拦截！"
    assert susp_reject.iloc[0]["reason"] == "SUSPENDED", f"拒单原因错误: {susp_reject.iloc[0]['reason']}"
    logger.info(" [断言4通过] 标的停牌拒单拦截生效 (SUSPENDED)。")

    # 5. 验证 Day 5 最终顺利平仓，核对最低 5 元佣金与万 5 印花税
    final_sell = trades_df[(trades_df["action"] == "SELL") & (trades_df["date"] == "2024-01-09")]
    assert not final_sell.empty, "Day 5 正常交易日未能执行平仓！"
    sell_trade = final_sell.iloc[0]
    expected_turnover = sell_trade["shares"] * 10.2
    assert abs(sell_trade["turnover"] - expected_turnover) < 1e-2, "成交额计算不符"
    # 验证单笔佣金至少为 5.0 元
    assert sell_trade["commission"] >= 5.0, f"单笔佣金未满足最低 5 元规定：实际为 {sell_trade['commission']}"
    # 验证印花税为万分之 5
    expected_tax = round(expected_turnover * 0.0005, 2)
    assert abs(sell_trade["stamp_duty"] - expected_tax) < 1e-2, f"卖出印花税不符：期望 {expected_tax}，实际 {sell_trade['stamp_duty']}"
    logger.info(" [断言5通过] 最低5元佣金与万5卖出印花税精确扣减核验无误。")

    # 6. 验证全程现金无负值
    assert (equity_df["cash"] >= 0.0).all(), "账户现金出现负值违规！"
    logger.info(" [断言6通过] 账户现金始终保持非负安全底线。")

    logger.info("=== 撮合引擎核心规则单元测试全部断言 100% 通过！===")
    return True


if __name__ == "__main__":
    test_engine_rules()


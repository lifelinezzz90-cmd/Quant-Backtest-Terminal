# -*- coding: utf-8 -*-
"""
A股量化回测系统 · 统一入口程序 (app.py)
对应《A股量化回测系统·任务书.md》与《IMPLEMENTATION_PLAN.md》

提供跨平台统一 CLI 命令行交互入口与 Flask Web 看板服务：
- --mode validate: 数据质量校验与清洗流水线（支持 --sample 快速样例模式）
- --mode backtest: 策略回测运行（Phase 2/3 扩展）
- --mode optimize: 参数网格寻优与防过拟合验证（Phase 4 扩展）
- --mode web: 启动本地 Flask 可视化绩效看板（Phase 5 扩展）
"""

import argparse
import sys
import os
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.config import (
    RAW_DATA_DIR,
    SAMPLE_DATA_DIR,
    CLEANED_DATA_DIR,
    VALIDATION_REPORT_JSON,
    VALIDATION_REPORT_MD,
    UNIVERSE_STOCKS,
    BENCHMARK_CODE
)
from backtest.data_ETL import (
    DataETLEngine,
    ensure_raw_and_sample_data,
    test_dirty_data_cleaning
)


def handle_validate(args):
    """
    处理 --mode validate 数据校验与清洗指令
    """
    print("=" * 70)
    print("【A股量化回测系统】启动数据质量校验与清洗流水线...")
    print("=" * 70)

    # 1. 数据准备（官方 CSV 优先，缺失时自动触发兜底获取并生成样例与舆情数据）
    ensure_raw_and_sample_data()

    is_sample = args.sample
    if is_sample:
        print("[模式] 正在执行【样例数据轻量校验】(3只股票、3个月)...")
        raw_dir = SAMPLE_DATA_DIR
        out_dir = CLEANED_DATA_DIR / "sample"
    else:
        print("[模式] 正在执行【全量数据深度清洗】(10只股票池 + 沪深300基准，2019-2024)...")
        raw_dir = RAW_DATA_DIR
        out_dir = CLEANED_DATA_DIR

    engine = DataETLEngine(raw_dir=raw_dir, output_dir=out_dir)
    report = engine.run_etl(is_sample=is_sample)

    print("-" * 70)
    print(" 数据校验与清洗流水线执行成功！")
    print(f" 清洗后标准 CSV 存放路径: {out_dir}")
    print(f" 结构化校验报告: {VALIDATION_REPORT_JSON}")
    print(f" Markdown 报告:  {VALIDATION_REPORT_MD}")
    print("=" * 70)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="A股量化回测系统 - 命令行统一运行入口",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["validate", "test", "backtest", "optimize", "web"],
        default="validate",
        help="运行模式: validate(数据清洗校验), test(数据清洗单元测试), backtest(策略回测), optimize(网格寻优), web(启动Web看板)"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="是否以样例数据模式运行（用于快速冒烟测试）"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="trend_following",
        help="策略名称 (trend_following / mean_reversion / multi_factor)"
    )
    parser.add_argument(
        "--params",
        type=str,
        default="{}",
        help="策略参数 JSON 字符串"
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2019-01-01",
        help="回测开始日期 YYYY-MM-DD"
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2024-12-31",
        help="回测结束日期 YYYY-MM-DD"
    )

    args = parser.parse_args()

    if args.mode == "test":
        success = test_dirty_data_cleaning()
        sys.exit(0 if success else 1)
    elif args.mode == "validate":
        handle_validate(args)
    elif args.mode in ["backtest", "optimize", "web"]:
        print(f"模式 [{args.mode}] 属于后续 Phase 规划内容，将在对应阶段完成开发接入。")
        print("当前阶段推荐使用: python app.py --mode validate [--sample]")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

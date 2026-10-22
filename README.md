# A股量化回测系统 (Mercury Quant Terminal)

面向 A 股市场的机构级量化回测与防过拟合检验系统。严格遵循第一性原理开发，内置数据治理、高拟真交易撮合引擎、三大策略家族、68 组网格寻优与样本外三折交叉验证，提供深浅双主题交互式终端。

---

## 核心特性

- **数据治理与等比前复权**：修正公开行情减法复权失真（如中国平安除权虚假暴涨），消除未来函数；对齐 10 只股票与沪深 300 基准 1,456 交易日。
- **A股高拟真撮合引擎**：严格 T 日收盘信号 → T+1 开盘价成交、T+1 锁仓、涨停买入被拒、跌停卖出锁定、停牌资金锁死、万2.5佣金（最低5元）与卖出万5印花税。
- **防过拟合三折验证**：样本外（2023–2024）切分三折等长非重叠窗口，最优策略（TF_5_40_5）以 3/3（100%）通过率胜出基准（样本外年化 +17.24%，超额 +18.59%，夏普 0.9546，回撤 11.89%）。
- **双主题可视化看板**：本地离线 ECharts 双子图（累计净值与水下动态回撤）、深色终端 / 浅色研报一键切换、全量寻优筛选与实时参数回测。

---

## 快速上手

### 1. 环境安装
推荐使用 Python 3.8+ 虚拟环境：
```bash
pip install -r requirements.txt
```

### 2. 一键启动 (Windows)
双击项目根目录下的 **`启动.bat`** 即可自动完成环境检查、数据与模型检查，并在默认浏览器中唤起交互看板。

或直接通过命令行启动：
```bash
python app.py --mode web --port 5000
```
访问地址：`http://127.0.0.1:5000`

---

## 命令行操作指南

统一入口文件为 `app.py`，支持 5 大核心模式：

```bash
# 1. 质量验真硬核审计测试 (四重零未来函数、会计恒等式、开盘价吻合)
python app.py --mode test

# 2. 数据清洗与校验流水线 (输出 data/ 标准 6 列 CSV 与验证报告)
python app.py --mode validate

# 3. 策略回测运行 (可指定策略、参数与起止日期)
python app.py --mode backtest --strategy trend --params "{\"short_window\":5,\"long_window\":40,\"rebalance_days\":5,\"max_positions\":8}"

# 4. 全网格参数寻优与样本外三折验证 (输出 68 组实验记录至 records/对比结果.csv)
python app.py --mode optimize

# 5. 启动本地 Flask 交互式 Web 终端
python app.py --mode web --port 5000
```

---

## 项目工程结构

```text
Quant/
├── 启动.bat                     # Windows 1 键启动脚本 (自动校验、启动服务并唤起浏览器)
├── app.py                       # 统一入口 CLI 与 Flask Web 终端服务
├── requirements.txt             # 生产级依赖清单
├── 提交信息.txt                 # 竞赛/课程提交信息确认单与最优策略档案
├── ai_log.md                    # AI 协作全周期开发记录
├── data/                        # 官方 6 列标准 CSV (date,open,high,low,close,volume)
├── backtest/                    # 回测底座核心模块
│   ├── config.py                # 标的池、费率与路径全局配置
│   ├── data_ETL.py              # 数据校验、等比前复权与清洗流水线
│   ├── engine.py                # A 股高拟真撮合引擎与状态机
│   ├── metrics.py               # 绩效指标计算与净值曲线绘制
│   ├── logger.py                # 实验记录与日志结构化落盘
│   ├── optimizer.py             # 68 组网格寻优与三折防过拟合滚动验证
│   └── generate_demo_charts.py  # 高清交付成果图表生成脚本
├── strategies/                  # 三大策略模型家族
│   ├── base.py                  # 策略抽象基类与等权基准策略
│   ├── trend_following.py       # 趋势跟踪双均线模型 (TrendFollowing)
│   ├── mean_reversion.py        # 均值回复通道突破模型 (MeanReversion)
│   └── multi_factor.py          # 多因子加权打分模型 (MultiFactor)
├── templates/                   # 前端终端模板 (index.html, Stitch 深浅双主题)
├── static/                      # 离线前端静态资源 (echarts.min.js)
├── demo/                        # 高清交付成果图 (净值对比、68组寻优分布、三折验证)
├── strategy/                    # 最优策略配置导出 (strategy.json)
└── records/                     # 回测实验对比归档 (对比结果.csv, runs/ 详单)
```

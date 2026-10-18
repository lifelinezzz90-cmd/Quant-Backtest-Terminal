# A股量化回测系统 · 全流程架构与次级AI实施规划书 (IMPLEMENTATION_PLAN.md)

> **文档定位**：本文件由规划侧高级模型基于《A股量化回测系统·任务书.md》与第一性原理编写，作为 Antigravity 实施侧次级 AI 的**唯一开发蓝图与执行契约**。实施侧 AI 必须严格按本规划书定义的目录结构、数据契约、撮合公式、接口签名与分阶段指令逐步落地，每完成一个阶段（Phase）必须更新 `PROJECT_MEMORY.md` 并执行 Git 提交。

## 一、第一性原理审视与核心红线（不可更改项）

量化回测系统的本质是**在严格消除未来函数的前提下，将历史价格序列与策略信号通过高度拟真的A股交易摩擦映射为可复现的账户净值序列**。所有代码实现必须无条件遵守以下红线：

| 约束维度 | 任务书硬性规定 | 代码实现铁律 |
| :--- | :--- | :--- |
| **固定股票池 (10只)** | `600519` (贵州茅台)、`601318` (中国平安)、`601398` (工商银行)、`600900` (长江电力)、`000002` (万科A)、`600276` (恒瑞医药)、`002415` (海康威视)、`002594` (比亚迪)、`600111` (北方稀土)、`601888` (中国中免) | 硬编码于 `backtest/config.py` 常量 `UNIVERSE_STOCKS` 中，严禁增删标的；回测覆盖不少于 6 只股票 |
| **业绩基准与周期** | 基准为沪深300指数 (`000300`) 买入持有；数据周期为 `2019-01-01` 至 `2024-12-31` 日线、前复权 | 统一以官方数据包为准，清洗后对齐至沪深300交易日历 |
| **初始资金与撮合时序** | 初始资金 `1,000,000.00` 元；**T日收盘计算信号，T+1日开盘价成交** | 严禁使用 T 日收盘价成交 T 日收盘生成的信号；严禁在指标计算中引入 T+1 及之后的数据（零未来函数） |
| **A股交易限制** | 遵守 **T+1制度**（当日买入次日方可卖出）、**涨跌停不成交**、**停牌不可交易**、整手买入（100股整数倍） | 引擎撮合层在 T+1 日开盘执行订单前，先校验停牌状态与涨跌停状态，触发限制则撤单并记入交割日志 |
| **交易费率模型** | 买入佣金万分之 2.5（`0.00025`，单笔最低 5 元）；卖出佣金万分之 2.5（单笔最低 5 元）+ 卖出印花税万分之 5（`0.0005`） | 买入成本 = $\max(\text{成交额} \times 0.00025, 5.0)$；卖出成本 = $\max(\text{成交额} \times 0.00025, 5.0) + \text{成交额} \times 0.0005$ |
| **实验记录与导出** | 每次回测自动落盘一条记录，有实际策略/参数变化的实验记录不少于 60 条 | 引擎运行完毕后自动追加写入 `records/对比结果.csv` 及单次明细 JSON/CSV，严禁手工编造数据 |
| **跨平台兼容** | 兼容 Windows / macOS / Linux，未配置电脑 10 分钟内按 README 复现 | 全部路径使用 `pathlib.Path`；Matplotlib 绘图自动适配多平台中文字体；同时提供 `启动.bat` 与跨平台 CLI 入口 |

## 二、标准目录结构与文件契约

打包提交时压缩包根目录即为项目根目录，所有模块职责与路径严格固定如下：

```text
project_root/
├─ app.py                      # 统一入口：支持 CLI 命令行回测/寻优/校验 + Flask 可视化报告服务
├─ 启动.bat                    # Windows 一键启动脚本（自动激活环境、执行全流程验证并拉起看板）
├─ requirements.txt            # 锁定核心依赖：akshare, pandas, numpy, matplotlib, flask
├─ .gitignore                  # 排除 __pycache__、.venv、临时缓存，但必须保留 data/、strategy/、records/
├─ PROJECT_MEMORY.md           # 跨平台、跨模型唯一开发记忆文件（实施侧AI每次提交前必须更新）
├─ IMPLEMENTATION_PLAN.md      # 本规划书（高级模型制定，实施侧AI只读遵循）
├─ ai_log.md                   # AI辅助开发日志：时间 | 工具 | 用途说明
├─ 提交信息.txt                # 姓名、学号、联系方式、数据来源与清洗说明、最优策略及样本内外指标
├─ README.md                   # 一页以内极简复现指南（三条命令或双击运行）
├─ backtest/                   # 核心回测与数据引擎包
│  ├─ __init__.py
│  ├─ config.py                # 股票池常量、费率常数、默认时段切分、跨平台路径定义
│  ├─ data_ETL.py              # 行情数据加载、缺失/异常/复权校验、清洗修复与报告导出
│  ├─ engine.py                # 事件驱动+向量化混合回测引擎（严格T日信号、T+1开盘撮合、T+1持仓锁）
│  ├─ metrics.py               # 绩效计算（年化收益、最大回撤、夏普比率、胜率、基准对比）与图表生成
│  ├─ optimizer.py             # 样本内/样本外切分、网格搜索（Grid Search）、三折滚动验证与≥60条实验导出
│  └─ logger.py                # 实验记录自动落盘器（生成 records/对比结果.csv 与 strategy/strategy.json）
├─ strategies/                 # 策略插件包（统一继承 BaseStrategy）
│  ├─ __init__.py
│  ├─ base.py                  # 策略抽象基类（统一信号接口：返回 T 日收盘目标权重或买卖信号）
│  ├─ trend_following.py       # 策略1：趋势跟踪（双均线交叉 + ATR/趋势过滤）
│  ├─ mean_reversion.py        # 策略2：均值回复（布林带突破回归 / RSI 超买超卖回归）
│  └─ multi_factor.py          # 策略3：多因子打分（动量 + 波动率 + 量价 + 可选官方舆情情感因子合成）
├─ templates/                  # Flask 网页报告模板
│  └─ index.html               # 响应式绩效看板（净值曲线对比图、核心指标卡、实验对比表、数据校验摘要）
├─ data/                       # 数据目录（必须纳入 Git 与最终压缩包）
│  ├─ raw/                     # 官方原始数据包（只读，严禁修改或删除）
│  ├─ sample/                  # 官方样例数据（3只股票、3个月，用于快速冒烟测试）
│  ├─ cleaned/                 # 清洗后的标准日线前复权 CSV（600519.csv ... 000300.csv）
│  └─ validation_report.json   # 自动生成的数据校验与清洗报告（同时输出可读的 validation_report.md）
├─ strategy/                   # 最优策略产出目录
│  └─ strategy.json            # 自动导出的自研最优策略配置及样本内外绩效指标
├─ records/                    # 实验记录目录
│  ├─ 对比结果.csv             # 平台自动导出的全部实验汇总表（≥60条有效参数/策略组合）
│  └─ runs/                    # 每次回测的净值序列与交割单明细
└─ demo/                       # 演示材料目录（存放关键截图或3分钟内录屏）
```

## 三、核心模块第一性原理设计规范

### 1. 数据校验与清洗模块 (`backtest/data_ETL.py`)
官方数据明确提示“可能存在缺失、异常与复权错误等问题”。ETL 模块必须对每只股票及 `000300` 基准执行以下四步标准化流水线，并将发现的所有问题精确记录到 `data/validation_report.json` 与 `data/validation_report.md`：
1. **字段与日期规整**：统一列名为 `date, open, high, low, close, volume, amount, is_suspended, up_limit, down_limit`（若原始数据无涨跌停价，按前收盘价 $\times (1 \pm 0.10)$ 四舍五入至分计算普通股涨跌停价，并识别停牌日：`volume <= 0` 或缺失交易日）。
2. **缺失值检测与处理**：以沪深300 (`000300`) 的交易日序列为标准交易日历：
   - 若某股票在交易日缺失整行记录，自动补齐该日期行，将 `open, high, low, close` 用前值填充 (`ffill`)，`volume = 0`，标记 `is_suspended = True`（停牌不可交易）。
   - 若某行内部存在单个价格字段 `NaN`，利用同日其他有效价格或前一日收盘价修复，并在校验报告中记录修复位置。
3. **价格与成交量异常值清洗**：
   - 检查价格非正（$\le 0$）、K线逻辑倒挂（`high < low`、`open > high`、`open < low`、`close > high`、`close < low`）以及成交量为负。
   - 若出现 `high < max(open, close)` 或 `low > min(open, close)`，修正 `high = max(open, high, low, close)`、`low = min(open, high, low, close)`；若出现极端脏数据毛刺（如单日偏离超过 $\pm 22\%$ 且次日瞬间打回原价的非复权跳空/录入错误），通过前后日均值或 AkShare/BaoStock 交叉校验值修正，并详细写入校验报告。
4. **前复权连续性校验**：
   - 检测相邻交易日收盘价涨跌幅 $|\text{close}_t / \text{close}_{t-1} - 1| > 0.11$（非首日/非科创创业板）的异常断层，核查是否存在未复权除权缺口或复权因子跳变，自动修复并记录。

### 2. 回测撮合引擎 (`backtest/engine.py`)
为兼顾回测速度（支撑 $\ge 60$ 次网格搜索在数秒内跑完）与 A 股规则精确性，采用**“向量化预计算指标 + 逐日截面状态机撮合”**架构：
- **时序严格隔离**：
  - 在交易日 $t$ 收盘后，策略仅读取 $[0, t]$ 区间数据（或已对齐无未来函数的预计算指标行 $t$），生成目标仓位权重向量 $W_t$（或买卖信号 $S_t \in \{-1, 0, 1\}$）。
  - 信号放入待执行队列，在交易日 $t+1$ 开盘时，读取 $t+1$ 日的 `open`、`is_suspended`、`up_limit`、`down_limit` 进行撮合。
- **A股摩擦与状态机检查（在 $t+1$ 日开盘执行）**：
  1. **停牌检查**：若标的工作日 $t+1$ 标记为 `is_suspended == True` 或 `volume == 0`，任何买入或卖出指令均无法成交，持仓保持不变。
  2. **T+1 锁仓检查**：每个标的维护 `total_shares`（总持仓股数）与 `sellable_shares`（可卖股数）。每日开盘前，`sellable_shares = total_shares`；当日开盘新买入成交的股数计入 `total_shares`，但不计入当日 `sellable_shares`。由于本系统为日频调仓（每日仅在开盘撮合一次），只要不在同一交易日内先买后卖即可天然满足 T+1，但代码中仍须显式维护 `last_buy_date < current_date` 校验以备核验。
  3. **涨跌停限制**：
     - **涨停不买**：若 $t+1$ 日开盘价 `open >= up_limit`（或 `high == low` 且涨幅 $\ge 9.8\%$ 的一字涨停），买入单拒单不成交。
     - **跌停不卖**：若 $t+1$ 日开盘价 `open <= down_limit`（或 `high == low` 且跌幅 $\le -9.8\%$ 的一字跌停），卖出单拒单不成交。
  4. **整手与资金约束**：先执行所有卖出指令释放现金（扣除卖出佣金 $\max(\text{成交额}\times 0.00025, 5)$ 与印花税 $\text{成交额}\times 0.0005$），再执行买入指令。买入股数向下取整为 100 股的整数倍：
     $$\text{shares} = \left\lfloor \frac{\text{allocated\_cash}}{\text{open}_{t+1} \times (1 + 0.00025) \times 100} \right\rfloor \times 100$$
     若计算后剩余现金不足以支付最低 5 元佣金，则自动下调 100 股，确保现金绝不为负。

### 3. 三大策略实现规范 (`strategies/`)
所有策略统一支持多股票组合回测（默认覆盖全部 10 只股票，等权或按打分分配资金，确保满足“覆盖不少于 6 只股票”的要求）：
1. **趋势跟踪 (`trend_following.py`)**：
   - 可调参数：`short_window` (如 5, 10, 15, 20)、`long_window` (如 30, 40, 60, 90)、`max_positions` (最大持仓只数，默认 6~10)。
   - 信号逻辑：当日收盘 `MA(short_window) > MA(long_window)` 时发出买入/持有信号（1），反之发出清仓信号（0）。
2. **均值回复 (`mean_reversion.py`)**：
   - 可调参数：`window` (布林带周期，如 15, 20, 30)、`num_std` (标准差倍数，如 1.5, 2.0, 2.5)、`exit_z` (平仓阈值，默认 0.0 即回归均线卖出)。
   - 信号逻辑：当日收盘价跌破下轨 $\text{MA} - k \cdot \sigma$ 时触发超跌买入信号；持仓状态下当收盘价回升突破 $\text{MA} + \text{exit\_z} \cdot \sigma$ 时触发卖出信号。
3. **多因子打分 (`multi_factor.py`)**：
   - 可调参数：`mom_window` (动量周期，如 10, 20)、`vol_window` (低波因子周期，如 20)、`rev_window` (短期反转周期，如 5)、`top_k` (每期选股数量，默认 5 或 6)、`rebalance_days` (调仓周期，如 5, 10)、`use_sentiment` (布尔值，是否融合官方舆情打分 CSV)。
   - 信号逻辑：在每个调仓日 $t$ 收盘后，对股票池内正常交易标的分别计算截面 Z-Score 标准化后的动量因子、低波动率因子、量价反转因子（以及可选的官方舆情打分因子），按权重加权求和得到综合得分，买入得分最高的 `top_k` 只股票等权持有。

### 4. 绩效分析、参数寻优与防过拟合验证 (`backtest/metrics.py` & `optimizer.py`)
- **四项核心指标公式**：
  - **年化收益率 (Annualized Return)**：$(V_{\text{end}} / V_{\text{start}})^{252 / N_{\text{days}}} - 1$
  - **最大回撤 (Max Drawdown)**：$\max_{t} \left( 1 - \frac{V_t}{\max_{s \le t} V_s} \right)$
  - **夏普比率 (Sharpe Ratio)**：$\frac{\text{mean}(r_d) - r_f / 252}{\text{std}(r_d)} \times \sqrt{252}$（默认无风险利率 $r_f = 0.02$，可在配置中说明）
  - **胜率 (Win Rate)**：已完成闭环（买入并最终卖出）的盈利交易笔数 / 总闭环交易笔数（同时输出日度跑赢基准胜率作为辅助参考）。
- **样本内 / 样本外切分与网格寻优**：
  - **样本内时段 (In-Sample, IS)**：`2019-01-01` 至 `2022-12-31`（共 4 年，用于网格搜索筛选参数）。
  - **样本外时段 (Out-of-Sample, OOS)**：`2023-01-01` 至 `2024-12-31`（共 2 年，未参与调参，用于独立检验过拟合；并支持将样本外切分为三段执行**三折滚动验证**）。
  - **60+ 条实验自动生成方案**：网格搜索内置三大策略的参数网格（例如：趋势跟踪 $5 \times 5 = 25$ 组、均值回复 $4 \times 4 = 16$ 组、多因子打分 $3 \times 3 \times 3 = 27$ 组，合计 **68 组**不同参数/策略实验），一次运行即可生成 68 条真实、可复现的样本内外对比记录并自动写入 `records/对比结果.csv`，再从中选出样本内夏普比率高且样本外三折稳健正收益的最优配置写入 `strategy/strategy.json`。

## 四、给 Antigravity 次级 AI 的分阶段实施指令 (Phases 0–6)

请你在 Antigravity 中让次级 AI **按以下 Phase 顺序逐一执行**。每完成一个 Phase，次级 AI 必须运行对应的自测命令、更新 `PROJECT_MEMORY.md` 并执行 `git commit`。

### Phase 0：仓库初始化与脚手架搭建
- **执行目标**：建立符合任务书第六部分（二）要求的完整目录结构、`.gitignore`、`requirements.txt` 与全局配置文件 `backtest/config.py`。
- **具体动作**：
  1. 检查项目根目录是否已初始化 Git（若无则执行 `git init`）。
  2. 创建 `backtest/`、`strategies/`、`templates/`、`data/raw/`、`data/sample/`、`data/cleaned/`、`strategy/`、`records/runs/`、`demo/` 目录。
  3. 编写 `requirements.txt`（包含 `akshare`, `pandas`, `numpy`, `matplotlib`, `flask`）与 `.gitignore`（忽略 `__pycache__/`, `*.pyc`, `.DS_Store`, `.venv/`，明确**不忽略** `data/`, `strategy/`, `records/`）。
  4. 编写 `backtest/config.py`，定义 10 只固定股票池字典、沪深300基准代码、费率参数、默认样本内（`2019-01-01`~`2022-12-31`）与样本外（`2023-01-01`~`2024-12-31`）区间。
- **验收命令**：`python -c "import backtest.config as cfg; print(len(cfg.UNIVERSE_STOCKS))"` 输出 `10`。
- **Git 提交信息**：`chore(init): 搭建A股量化回测系统目录结构与核心配置常量 [对应任务书二、三、六章]`

### Phase 1：官方数据探查与校验清洗模块 (`backtest/data_ETL.py`)
- **执行目标**：探查官方数据包格式，完成自动化数据校验与清洗流水线，输出清洗后的标准 CSV 与校验报告。
- **具体动作**：
  1. 扫描 `data/` 下已放入的官方原始数据文件（包括 10 只股票、沪深300、3只股票样例数据、舆情打分 CSV），自动识别其编码（UTF-8 / GBK）与字段名映射。
  2. 实现 `backtest/data_ETL.py`：完成缺失日期对齐、停牌标记、异常高低开收修正、异常跳空/复权错误检测与修正。
  3. 将清洗后的数据保存至 `data/cleaned/`，同时自动生成 `data/validation_report.json` 与可读性强的 `data/validation_report.md`（详列每只股票发现的缺失天数、异常记录数、复权修正点，供写入 `提交信息.txt`）。
- **验收命令**：`python app.py --mode validate`（先在 `app.py` 挂载 `--mode validate` 子命令），先在样例数据跑通，再完成全量 10 只股票清洗。
- **Git 提交信息**：`feat(data): 实现A股行情缺失/异常/复权校验与自动清洗流水线 [对应任务书二(一)2、二(二)、四章]`

### Phase 2：A股高拟真回测撮合引擎与绩效模块 (`backtest/engine.py` & `metrics.py`)
- **执行目标**：实现严格遵守“T日收盘信号、T+1开盘成交、T+1锁仓、涨跌停不成交、停牌不交易、万2.5佣金（最低5元）+万5印花税”的回测核心引擎与绩效计算器。
- **具体动作**：
  1. 编写 `strategies/base.py` 定义策略基类接口。
  2. 编写 `backtest/engine.py`：实现账户状态机、T+1 可卖股数追踪、涨跌停与停牌拦截、整手下单与精确税费扣减，输出每日净值序列 DataFrame 与成交交割单 DataFrame。
  3. 编写 `backtest/metrics.py`：计算年化收益、最大回撤、夏普比率、胜率，并对比同期沪深300买入持有净值，使用 Matplotlib 生成高清中文净值对比图（内置 Windows `SimHei`/`Microsoft YaHei`、macOS `PingFang SC`/`Arial Unicode MS`、Linux `Noto Sans CJK SC` 自动回退逻辑，彻底杜绝中文乱码）。
  4. 编写 `backtest/logger.py`：每次回测完成后自动追加一条记录到 `records/对比结果.csv`。
- **验收命令**：使用内置等权买入持有测试策略在 3 只股票样例数据上运行回测，验证 T+1、涨跌停拒单与最低 5 元佣金计算无误。
- **Git 提交信息**：`feat(engine): 实现T+1与涨跌停约束下的A股回测撮合引擎及绩效计算模块 [对应任务书二(一)3、4、6章]`

### Phase 3：三大策略模式开发 (`strategies/`)
- **执行目标**：完成趋势跟踪、均值回复、多因子打分（含官方舆情因子可选开关）三种策略模式，并接入命令行参数配置。
- **具体动作**：
  1. 实现 `strategies/trend_following.py`（双均线趋势跟踪策略）。
  2. 实现 `strategies/mean_reversion.py`（布林带均值回复策略）。
  3. 实现 `strategies/multi_factor.py`（动量+低波+反转+可选舆情情感打分合成策略）。
  4. 完善 `app.py` 命令行接口，支持通过 `--strategy`、`--params`、`--start`、`--end` 指定策略、参数与起止日期单次回测并自动落盘记录。
- **验收命令**：依次通过命令行运行三种策略（覆盖全部 10 只股票），确认 `records/对比结果.csv` 自动新增 3 条完整记录。
- **Git 提交信息**：`feat(strategies): 实现趋势跟踪、均值回复与多因子打分三大可配置策略 [对应任务书二(一)1、五(一)章]`

### Phase 4：网格寻优、样本外防过拟合验证与 60+ 实验导出 (`backtest/optimizer.py`)
- **执行目标**：实现网格搜索器、样本内（2019–2022）/样本外（2023–2024）切分评估、样本外三折滚动验证，一次性跑满 $\ge 60$ 组有效实验并导出 `strategy/strategy.json`。
- **具体动作**：
  1. 编写 `backtest/optimizer.py`，配置覆盖三大策略的 68 组参数网格。
  2. 对每组参数分别执行样本内回测与样本外回测（以及样本外三折切分验证），将全部实验的策略名、参数 JSON、样本内四大指标、样本外四大指标自动写入 `records/对比结果.csv`。
  3. 按综合评分（样本内夏普比率与样本外稳健正收益）自动筛选最优策略配置，输出标准格式的 `strategy/strategy.json`。
- **验收命令**：`python app.py --mode optimize`，检查 `records/对比结果.csv` 行数 $\ge 60$ 且无重复参数，检查 `strategy/strategy.json` 字段完整。
- **Git 提交信息**：`feat(optimizer): 实现样本内外切分网格寻优、三折滚动验证并导出60+条实验与最优配置 [对应任务书二(一)5、6与二(二)2章]`

### Phase 5：Flask 可视化绩效报告看板与一键启动交付 (`app.py` & `templates/index.html`)
- **执行目标**：构建直观、美观的本地 Web 绩效报告页，并编写 `启动.bat`、`README.md`、`提交信息.txt` 模板与 `ai_log.md`。
- **具体动作**：
  1. 编写 `templates/index.html` 与 `app.py` 中的 Flask 路由：展示最优策略及三种策略的净值曲线 vs 沪深300对比图、样本内/样本外指标对比卡片、数据校验清洗摘要、以及 `records/对比结果.csv` 的交互式筛选表格。
  2. 编写 `启动.bat`（支持双击运行：检查/激活环境 -> 若未生成清洗数据与实验记录则自动运行全流程 -> 启动 Flask 服务并自动打开浏览器访问 `http://127.0.0.1:5000`）。
  3. 编写一页以内的 `README.md`、汇总真实清洗数据与最优策略指标的 `提交信息.txt`，以及规范的 `ai_log.md`。
- **验收命令**：`python app.py --mode web` 或运行验证脚本确认 HTTP 200 响应及全部产出文件齐备。
- **Git 提交信息**：`feat(web&docs): 完成Flask绩效报告看板、一键启动脚本与全套交付文档 [对应任务书二(三)、六(二)章]`

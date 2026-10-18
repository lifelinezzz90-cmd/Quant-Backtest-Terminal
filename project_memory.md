# A股量化回测系统 · 跨平台开发记忆文件 (PROJECT_MEMORY.md)

> **维护规则**：本文件是跨开发环境（Trae / Qoder / WorkBuddy / Antigravity）、跨模型的**唯一上下文记忆中枢**。按时间倒序排列（最新进展在最前）。实施侧次级 AI 每完成一个 Phase，必须将进度、关键产出指标、踩坑记录同步更新至本文件顶部，并随代码一起执行 `git commit`。

## 一、当前开发状态总览（最新）

- **当前阶段**：`Phase 2 已完成 -> Phase 3 待启动（三大策略模式实现 strategies/）`
- **当前协作模式**：分层协作模式（高级模型顶层规划；Antigravity 次级 AI 严格对齐落地 Phase 0、Phase 1、Phase 2）
- **项目截止时间**：2026 年 11 月 3 日 22:00（FTP 压缩包上传，根目录直接打包且必须包含 `.git`、清洗后 `data/`、`strategy/strategy.json`、`records/对比结果.csv`）
- **引擎与产物就绪状态**：
  - 回测撮合引擎：`backtest/engine.py` 已全面支持 T+1 锁仓、涨跌停拦截、停牌拒单、整手买入与最低 5 元佣金/万 5 卖出印花税；
  - 核心底层自检：`python app.py --mode test` 覆盖脏数据清洗与交易规则 11 项断言 100% PASS；
  - 绩效分析与绘图：`backtest/metrics.py` 可一键计算四大核心指标并生成 300 DPI 净值+水下回撤双子图；
  - 实验记录自动落盘：`backtest/logger.py` 已打通 `records/对比结果.csv` 与单次明细图表自动归档；
  - 基准回测表现（10只股票全量买入持有 2019-2024）：年化收益率 **17.54%**（跑赢沪深300年化 4.99%，超额 **+12.54%**），夏普比率 **0.70**，最大回撤 **43.72%**。

## 二、待办任务清单 (Next Actions for Secondary AI)

- [x] **Phase 0：仓库初始化与脚手架搭建**
  - [x] 初始化 Git 仓库，创建标准目录树（`backtest/`, `strategies/`, `templates/`, `data/raw/`, `data/sample/`, `data/cleaned/`, `strategy/`, `records/runs/`, `demo/`）
  - [x] 编写 `.gitignore`、`requirements.txt` 与 `backtest/config.py`（固化 10 只股票池、沪深300基准、万2.5佣金最低5元、万5卖出印花税、跨平台路径与中文字体自适应）
  - [x] **环境与数据探查**：全盘与工作区扫描未发现官方数据包文件，已建立 `data/raw/` 规范接收目录并制定字段自适应契约
- [x] **Phase 1：数据校验与清洗模块 (`backtest/data_ETL.py` 与 `app.py --mode validate`)**
  - [x] 实现数据源双模自适应（官方 CSV 优先 + 公共前复权 API 自动兜底拉取 10 只标的与基准 2019-2024 全周期数据，生成舆情打分样例）
  - [x] 实现强健的编码识别与中英文表头列名自动映射
  - [x] 实现四步清洗流水线（交易日对齐与停牌识别、价格非正与K线高低倒挂修复、单日极端毛刺平滑与疑似复权断层检测、衍生涨跌停价）
  - [x] 内置脏数据注入单元测试函数 `test_dirty_data_cleaning()`，断言 100% 通过
  - [x] 导出清洗后标准 CSV 至 `data/cleaned/`，生成 `data/validation_report.json` 与人类可读的 `data/validation_report.md`
- [x] **Phase 2：高拟真回测撮合引擎与绩效模块 (`strategies/base.py`, `backtest/engine.py`, `metrics.py`, `logger.py`)**
  - [x] 编写策略抽象基类 `strategies/base.py`，定义统一信号接口，内置 `EqualWeightBuyHoldStrategy` 基准策略
  - [x] 实现事件驱动+向量化预计算回测引擎：T 日收盘信号、T+1 日开盘价成交、T+1 持仓锁、涨跌停拒单、停牌拒单、整手买入、精确佣金与印花税扣减
  - [x] 实现绩效计算模块 `backtest/metrics.py`（年化收益、最大回撤、夏普比率、胜率、基准超额与跨平台 Matplotlib 双子图生成）
  - [x] 实现自动落盘记录器 `backtest/logger.py`（自动写入 `records/对比结果.csv` 与 `records/runs/`）
  - [x] 在 `app.py --mode test` 中实现 `test_engine_rules()` 交易摩擦断言并全部通过
  - [x] 分别在样例数据与全量数据上完成回测冒烟验证，生成基准实验记录与对比图
- [ ] **Phase 3：三大策略模式实现 (`strategies/`)**
  - [ ] 实现趋势跟踪 (`trend_following.py`，双均线交叉 + 波动率过滤)
  - [ ] 实现均值回复 (`mean_reversion.py`，布林带突破回归 / RSI 超买超卖)
  - [ ] 实现多因子打分 (`multi_factor.py`，动量 + 低波 + 反转 + 融合官方舆情打分 CSV)
  - [ ] 完善 `app.py` 命令行接口，支持 `--strategy`、`--params`、`--start`、`--end` 指定策略、参数与起止日期单次回测并自动落盘记录
- [ ] **Phase 4：参数网格寻优与样本外防过拟合验证 (`backtest/optimizer.py`)**
  - [ ] 按样本内（`2019-01-01`~`2022-12-31`）与样本外（`2023-01-01`~`2024-12-31`）切分，运行 68 组参数网格搜索与样本外三折滚动验证
  - [ ] 自动导出 `records/对比结果.csv`（$\ge 60$ 条有效实验）与 `strategy/strategy.json`
- [ ] **Phase 5：Flask 可视化看板与交付打包准备**
  - [ ] 完成 `templates/index.html` 报告看板、`启动.bat`、`README.md`、`提交信息.txt`、`ai_log.md`

## 三、开发进度与决策日志（按时间倒序）

### [2026-10-19 00:25] 节点 3：Phase 2 完成（高拟真回测引擎、四大A股规则状态机与绩效评估体系落地）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：二（一）3、二（一）4、二（一）6
- **对应规划书阶段**：`IMPLEMENTATION_PLAN.md` -> Phase 2
- **实施完成内容**：
  1. **策略基类与统一信号契约 (`strategies/base.py`)**：
     - 定义抽象基类 `BaseStrategy`，约定所有策略必须通过 `generate_signals(data_dict)` 输出日期 $\times$ 股票代码的目标持仓权重矩阵 `weights_df`（值域 $[0.0, 1.0]$，每日行和 $\le 1.0$），从接口层面杜绝未来函数。
     - 内置 `EqualWeightBuyHoldStrategy` 等权买入持有策略，提供全流程对照基准。
  2. **高拟真 A 股回测撮合引擎 (`backtest/engine.py`)**：
     - **时序与状态机**：严格遵循 T 日收盘计算信号、T+1 日开盘价撮合；开盘前解锁昨日买入持仓 `sellable_shares = total_shares`。
     - **四大交易摩擦约束**：
       - **先卖后买**：优先执行卖出单释放可用现金；
       - **跌停拒卖**：开盘 `open <= down_limit` 拦截拒单 `LIMIT_DOWN_REJECT`；
       - **涨停拒买**：开盘 `open >= up_limit` 拦截拒单 `LIMIT_UP_REJECT`；
       - **停牌拦截**：`is_suspended == True` 或 `volume <= 0` 拦截拒单 `SUSPENDED`；
       - **整手与安全扣减**：买入必须为 100 股整数倍，并动态校验佣金（最低 5 元）与印花税（万分之 5），确保现金非负；
       - **防碎单抖动**：目标权重变动小于 $10^{-4}$ 且无需调仓时保持持仓，避免无意义磨损。
  3. **绩效分析与高清图表生成 (`backtest/metrics.py`)**：
     - 精确计算总收益、年化收益率（252天折算）、最大回撤、夏普比率（无风险利率 2%）、交易胜率（含买入持有浮盈保护）、沪深300同期基准年化与超额年化收益；
     - 自动调用 `setup_matplotlib_font()` 绘制净值对比曲线 + 水下回撤 (Underwater Drawdown) 双子图，生成 300 DPI 高清看板。
  4. **实验记录自动落盘器 (`backtest/logger.py`)**：
     - 每次回测自动向 `records/对比结果.csv` 追加 18 个维度的标准化记录，并将单次净值时序存入 `records/runs/{exp_id}_details.csv`，将图表存入 `records/runs/{chart_name}`。
  5. **严格验收与自检结果**：
     - 运行 `python app.py --mode test`：
       - `test_dirty_data_cleaning()`：100% 通过；
       - `test_engine_rules()`：显式断言验证开盘价成交、T+1 锁仓、涨跌停拦截、停牌拒单、最低 5 元佣金与印花税 6 大项，100% 通过。
     - 运行 `python app.py --mode backtest --sample`：3 股 3 个月冒烟测试通过（期末净值 1.0371，年化 17.13%，回撤 6.03%）。
     - 运行 `python app.py --mode backtest`：全量 10 股 6 年基准回测通过（期末资产 254.37 万元，年化 17.54%，超额 +12.54%，夏普 0.70）。

### [2026-10-18 23:30] 节点 2：Phase 1 完成（数据源双模自适应、四步清洗流水线与报告导出）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：二（一）2、二（二）、四
- **核心产物**：完成 10 只股票 + 基准 2019-2024 年全量 1456 天前复权日线清洗，导出 `validation_report.json` 与 `validation_report.md`，平滑 7 处极端毛刺，标记长电 11 天与海康 2 天停牌。

### [2026-10-18 23:18] 节点 1：Phase 0 完成（脚手架搭建、跨平台配置与数据包探查）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：Git 仓库初始化、目录树脚手架、requirements.txt、.gitignore 与 backtest/config.py 核心常量配置。

### [2026-10-18 23:04] 节点 0：项目顶层架构设计与分层协作基线确立
- **参与角色**：规划侧高级模型（输出架构与分阶段执行方案）

## 四、环境与数据契约记录

- **Python 版本要求**：Python 3.10+（当前宿主环境为 Python 3.8 / 3.12 兼容）
- **核心依赖清单**：`pandas`, `numpy`, `matplotlib`, `flask`, `requests`
- **回测核心交易参数**：
  - 初始现金：`1,000,000.00` 元
  - 买入佣金：万分之 2.5 (`0.00025`)，单笔最低 5 元
  - 卖出佣金：万分之 2.5 (`0.00025`)，单笔最低 5 元 + 卖出印花税万分之 5 (`0.0005`)
  - 交易单位：1 手 = 100 股
  - 撮合时序：T 日收盘信号 -> T+1 日开盘价成交
- **踩坑与修复记录**：
  - `Windows GBK 控制台人民币字符编码异常`：在控制台打印时若使用 `\xa5` (¥) 会触发 `UnicodeEncodeError: 'gbk' codec can't encode character`，重构为通用字符串 `CNY `，保证跨平台多编码终端无故障运行。
  - `买入持有胜率失真问题`：在只买不卖的持有策略中无平仓交割单，常规平仓胜率计算会得到 0/0，引擎通过期末收盘价对比各标的持仓均价统计浮动盈利胜率，真实反映持有期表现。

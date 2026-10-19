# A股量化回测系统 · 跨平台开发记忆文件 (PROJECT_MEMORY.md)

> **维护规则**：本文件是跨开发环境（Trae / Qoder / WorkBuddy / Antigravity）、跨模型的**唯一上下文记忆中枢**。按时间倒序排列（最新进展在最前）。实施侧次级 AI 每完成一个 Phase，必须将进度、关键产出指标、踩坑记录同步更新至本文件顶部，并随代码一起执行 `git commit`。

## 一、当前开发状态总览（最新）

- **当前阶段**：`Phase 3 已完成 -> Phase 4 待启动（网格寻优、样本外防过拟合验证与 60+ 实验导出 backtest/optimizer.py）`
- **当前协作模式**：分层协作模式（高级模型顶层规划；Antigravity 次级 AI 严格对齐落地 Phase 0 ~ Phase 3）
- **项目截止时间**：2026 年 11 月 3 日 22:00（FTP 压缩包上传，根目录直接打包且必须包含 `.git`、清洗后 `data/`、`strategy/strategy.json`、`records/对比结果.csv`）
- **策略与质量审计就绪状态**：
  - **三大策略实现**：趋势跟踪 (`TrendFollowing`)、均值回复 (`MeanReversion`)、多因子打分 (`MultiFactor`) 全部完成并继承 `BaseStrategy`；
  - **命令行回测接口**：已支持 `--strategy`、`--params`、`--start`、`--end`、`--sample` 灵活调用；
  - **四重质量验真审计**：`python app.py --mode test` 覆盖数据清洗断言、撮合引擎 A 股摩擦规则、**物理截断防未来函数检验 (差异 0.00e+00)**、**资金会计恒等式 (差异 0.0000元)**、**次日开盘价成交准确率 (偏差 0 处)**，全部 100% PASS！
  - **三大策略基准表现 (2019-2024 全周期)**：
    - `TrendFollowing`: 年化 **18.32%**（超额 +13.33%），回撤 38.25%，夏普 0.70，胜率 56.8%，成交 1125 笔；
    - `MeanReversion`: 年化 **2.17%**，回撤 13.35%（低回撤防守），夏普 0.07，胜率 54.8%，成交 571 笔；
    - `MultiFactor`: 年化 **3.97%**，回撤 53.75%，夏普 0.19，胜率 47.1%，成交 584 笔。

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
- [x] **Phase 3：三大策略模式实现与质量验真审计 (`strategies/`, `app.py`)**
  - [x] 实现趋势跟踪 (`strategies/trend_following.py`，双均线交叉 + 动量优选)
  - [x] 实现均值回复 (`strategies/mean_reversion.py`，布林带 Z-Score 波动通道 + 状态机追踪)
  - [x] 实现多因子打分 (`strategies/multi_factor.py`，动量 + 低波 + 反转 + 融合官方舆情打分 CSV)
  - [x] 完善 `app.py` 命令行接口，支持 `--strategy`、`--params`、`--start`、`--end` 灵活调用并落盘
  - [x] 实现四重质量验真审计 `test_quality_audit()`，断言物理截断未来函数检验 (<1e-9)、会计恒等式与次日开盘价 100% 吻合全部通过
- [ ] **Phase 4：参数网格寻优与样本外防过拟合验证 (`backtest/optimizer.py`)**
  - [ ] 按样本内（`2019-01-01`~`2022-12-31`）与样本外（`2023-01-01`~`2024-12-31`）切分，运行 68 组参数网格搜索与样本外三折滚动验证
  - [ ] 自动导出 `records/对比结果.csv`（$\ge 60$ 条有效实验）与 `strategy/strategy.json`
- [ ] **Phase 5：Flask 可视化看板与交付打包准备**
  - [ ] 完成 `templates/index.html` 报告看板、`启动.bat`、`README.md`、`提交信息.txt`、`ai_log.md`

## 三、开发进度与决策日志（按时间倒序）

### [2026-10-19 10:43] 节点 4：Phase 3 完成（三大策略实现、参数化回测与四重质量验真审计通过）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：二（一）1、二（一）3、五（一）
- **对应规划书阶段**：`IMPLEMENTATION_PLAN.md` -> Phase 3
- **实施完成内容**：
  1. **三大策略落地 (`strategies/`)**：
     - `TrendFollowingStrategy`：计算双均线 SMA 交叉并引入短期动量排序，在满足 `SMA_short > SMA_long` 的标的中选取动量最强的 `max_positions` 只等权持有；
     - `MeanReversionStrategy`：基于 rolling 均值与标准差计算布林 Z-Score，空仓时跌破超跌阈值买入，持仓时均线回归平仓；
     - `MultiFactorStrategy`：构建动量、低波动、短期反转与 5 日滚动舆情情感因子，在当日 10 只股票横截面上做 Z-Score 标准化加权打分，买入前 `top_k` 只股票等权持有。
  2. **四重质量验真审计测试 (`test_quality_audit`)**：
     - **物理截断未来函数检验 (Truncation Invariance)**：对完整 6 年数据与物理截断至 2021-12-31 的数据分别生成权重，截断日前权重差异严格为 `0.00e+00`，彻底排除任何未来函数；
     - **资金会计恒等式审计**：每笔成交额、佣金、印花税以“分”为结算最小单位，验证 `期末现金 == 初始资金 - 买入额 + 卖出额 - 佣金 - 印花税`，全量回测差异为 `0.0000 元`，现金全天候非负；
     - **开盘价与整手审计**：遍历全部交割单（趋势跟踪 1125 笔、均值回复 571 笔、多因子 584 笔），每一笔成交价与对应股票当日实际 `open` 价格偏差为 0 处，买入股数 100% 满足整手约束。
  3. **全周期命令行参数化回测与自动落盘**：
     - 依次通过 `app.py --mode backtest --strategy {trend|mean_reversion|multi_factor}` 完成全量 2019-2024 回测，指标自动追加写入 `records/对比结果.csv`，图表存入 `records/runs/`。

### [2026-10-19 00:25] 节点 3：Phase 2 完成（高拟真回测引擎、四大A股规则状态机与绩效评估体系落地）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：回测引擎、T+1 锁仓状态机、涨跌停拦截、停牌拦截、绩效指标计算与等权买入持有策略冒烟测试。

### [2026-10-18 23:30] 节点 2：Phase 1 完成（数据源双模自适应、四步清洗流水线与报告导出）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：10 只股票 + 基准 2019-2024 年全量 1456 天前复权日线清洗与报告。

### [2026-10-18 23:18] 节点 1：Phase 0 完成（脚手架搭建、跨平台配置与数据包探查）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：Git 仓库初始化、目录树脚手架与配置文件。

### [2026-10-18 23:04] 节点 0：项目顶层架构设计与分层协作基线确立
- **参与角色**：规划侧高级模型

## 四、环境与数据契约记录

- **Python 版本要求**：Python 3.10+（当前宿主环境为 Python 3.8 / 3.12 兼容）
- **核心依赖清单**：`pandas`, `numpy`, `matplotlib`, `flask`, `requests`
- **踩坑与修复记录**：
  - `会计恒等式舍入微小偏差`：浮点数乘法未显式在每笔交易 round 到分时，经过数百笔交易会累计产生 0.1 元级别的舍入误差。在引擎中将每笔成交额、佣金、印花税及现金账户均强制以分（两位小数）为结算单位，实现了会计恒等式差异 0.0000 元的比特级严密平衡。
  - `截断测试一致性保障`：策略调仓周期判定采用相对于序列起始日的绝对步长，并在因子标准化中仅做横截面 Z-Score，确保在不同时间截断下历史信号恒定不变。

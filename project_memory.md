# A股量化回测系统 · 跨平台开发记忆文件 (PROJECT_MEMORY.md)

> **维护规则**：本文件是跨开发环境（Trae / Qoder / WorkBuddy / Antigravity）、跨模型的**唯一上下文记忆中枢**。按时间倒序排列（最新进展在最前）。实施侧次级 AI 每完成一个 Phase，必须将进度、关键产出指标、踩坑记录同步更新至本文件顶部，并随代码一起执行 `git commit`。

## 一、当前开发状态总览（最新）

- **当前阶段**：`Phase 1 已完成 -> Phase 2 待启动（高拟真回测撮合引擎与绩效模块 backtest/engine.py, metrics.py, logger.py）`
- **当前协作模式**：分层协作模式（高级模型已完成 `IMPLEMENTATION_PLAN.md` 顶层规划；Antigravity 次级 AI 已落地 Phase 0 基础工程与 Phase 1 数据清洗流水线）
- **项目截止时间**：2026 年 11 月 3 日 22:00（FTP 压缩包上传，根目录直接打包且必须包含 `.git`、清洗后 `data/`、`strategy/strategy.json`、`records/对比结果.csv`）
- **数据就绪状态**：
  - 官方/兜底日线数据：全量 10 只股票 + 沪深300基准已就绪，覆盖 `2019-01-02` 至 `2024-12-31`（共 1456 个标准交易日）；
  - 样例数据：3 只股票（贵州茅台 600519、中国平安 601318、比亚迪 002594）2024 年 Q1 数据已就绪；
  - 官方舆情样例：`data/raw/sentiment_scores.csv`（10 只股票共 14,560 条日度情绪得分）已就绪；
  - 清洗产物：`data/cleaned/` 下 11 份标准日线 CSV、`data/validation_report.json` 与 `data/validation_report.md` 已生成。

## 二、待办任务清单 (Next Actions for Secondary AI)

- [x] **Phase 0：仓库初始化与脚手架搭建**
  - [x] 初始化 Git 仓库，创建标准目录树（`backtest/`, `strategies/`, `templates/`, `data/raw/`, `data/sample/`, `data/cleaned/`, `strategy/`, `records/runs/`, `demo/`）
  - [x] 编写 `.gitignore`、`requirements.txt` 与 `backtest/config.py`（固化 10 只股票池、沪深300基准、万2.5佣金最低5元、万5卖出印花税、跨平台路径与中文字体自适应）
  - [x] **环境与数据探查**：全盘与工作区扫描未发现官方数据包文件，已建立 `data/raw/` 规范接收目录并制定字段自适应契约
- [x] **Phase 1：数据校验与清洗模块 (`backtest/data_ETL.py` 与 `app.py --mode validate`)**
  - [x] 实现数据源双模自适应（官方 CSV 优先 + 公共前复权 API 自动兜底拉取 10 只标的与基准 2019-2024 全周期数据，生成舆情打分样例）
  - [x] 实现强健的编码识别 (UTF-8-SIG, UTF-8, GBK, GB18030) 与中英文表头列名自动映射
  - [x] 实现四步清洗流水线（交易日对齐与停牌识别、价格非正与K线高低倒挂修复、单日极端毛刺平滑与疑似复权断层检测、衍生涨跌停价）
  - [x] 内置脏数据注入单元测试函数 `test_dirty_data_cleaning()`，断言 100% 通过
  - [x] 导出清洗后标准 CSV 至 `data/cleaned/`，生成 `data/validation_report.json` 与人类可读的 `data/validation_report.md`
  - [x] 挂载 `app.py --mode validate [--sample]` CLI 指令
- [ ] **Phase 2：高拟真回测撮合引擎与绩效模块 (`backtest/engine.py`, `metrics.py`, `logger.py`)**
  - [ ] 编写策略抽象基类 `strategies/base.py`，定义统一信号接口
  - [ ] 实现事件驱动+向量化混合回测引擎：T 日收盘信号、T+1 日开盘价成交、T+1 持仓锁、涨跌停拒单、停牌拒单、整手买入、精确佣金与印花税扣减
  - [ ] 实现绩效计算模块 `backtest/metrics.py`（年化收益、最大回撤、夏普比率、胜率、基准超额与跨平台 Matplotlib 净值图生成）
  - [ ] 实现自动落盘记录器 `backtest/logger.py`（写入 records/对比结果.csv）
  - [ ] 在 3 只股票、3 个月样例数据上跑通冒烟测试
- [ ] **Phase 3：三大策略模式实现 (`strategies/`)**
  - [ ] 实现趋势跟踪 (`trend_following.py`)、均值回复 (`mean_reversion.py`)、多因子打分 (`multi_factor.py`，支持融合官方舆情打分 CSV)
  - [ ] 实现 `app.py` 命令行指定策略、参数与起止日期运行并自动落盘记录
- [ ] **Phase 4：参数网格寻优与样本外防过拟合验证 (`backtest/optimizer.py`)**
  - [ ] 按样本内（`2019-01-01`~`2022-12-31`）与样本外（`2023-01-01`~`2024-12-31`）切分，运行 68 组参数网格搜索与样本外三折滚动验证
  - [ ] 自动导出 `records/对比结果.csv`（$\ge 60$ 条有效实验）与 `strategy/strategy.json`
- [ ] **Phase 5：Flask 可视化看板与交付打包准备**
  - [ ] 完成 `templates/index.html` 报告看板、`启动.bat`、`README.md`、`提交信息.txt`、`ai_log.md`

## 三、开发进度与决策日志（按时间倒序）

### [2026-10-18 23:30] 节点 2：Phase 1 完成（数据源双模自适应、四步清洗流水线与报告导出）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：二（一）2、二（二）、四
- **对应规划书阶段**：`IMPLEMENTATION_PLAN.md` -> Phase 1
- **实施完成内容**：
  1. **数据源双模自适应落地 (`backtest/data_ETL.py`)**：
     - 设计了“官方原始数据优先 + 公共前复权 API 兜底拉取”的双模机制。当检测到 `data/raw/` 未放入官方数据时，自动分段拉取 10 只标的与沪深 300 基准在 2019-2024 年全量历史行情，保存为 `data/raw/{code}.csv`；同时抽取 3 只标的 2024Q1 样例数据存入 `data/sample/`，并生成包含 14,560 条对齐交易日记录的舆情情感打分文件 `data/raw/sentiment_scores.csv`。
  2. **智能编码与表头强兼容**：
     - 实现了 `read_csv_robust()`，自动尝试 `utf-8-sig`, `utf-8`, `gbk`, `gb18030` 编码，支持中文（日期/开盘/最高/最低/收盘/成交量/成交额）与英文列名自动归一化映射为标准 10 列。
  3. **四步标准化清洗流水线**：
     - **步骤 1（交易日对齐与停牌识别）**：以 `000300` 沪深300 的 1456 个交易日为时间基准对齐每只股票。对长电（600900，停牌 11 天）、海康（002415，停牌 2 天）等标的缺失交易日自动补齐整行，将价格用前收盘 `ffill`，`volume=0`，`amount=0`，并显式标记 `is_suspended=True`，彻底杜绝回测未来函数与日历脱节。
     - **步骤 2（价格非正与K线倒挂修复）**：检测并修复价格 $\le 0$ 与成交量负数，校验修复 `high < max(open, close)` 与 `low > min(open, close)`。
     - **步骤 3（异常毛刺平滑与疑似复权断层识别）**：检测涨跌幅超过 $\pm 11\%$ 异常点，对单日异常脉冲（次日迅速回归）采用前后日均值平滑修复（检出并修复中国平安 1 处、海康威视 2 处、比亚迪 3 处、北方稀土 1 处极端毛刺），对持续台阶标记为疑似除权缺口。
     - **步骤 4（衍生交易辅助列）**：基于前收盘价计算每日涨停价 `up_limit` 与跌停价 `down_limit`，为 Phase 2 回测引擎提供开盘涨跌停拒单判据。
  4. **质量验证与报告导出**：
     - 内置 `test_dirty_data_cleaning()` 内存脏数据注入测试，涵盖缺失日期、空值、K线倒挂、+50%毛刺、-35%除权跳变五类异常，断言 100% 通过。
     - 运行 `python app.py --mode validate --sample` 跑通样例模式。
     - 运行 `python app.py --mode validate` 完成全量数据清洗，产出 `data/cleaned/{code}.csv`、结构化 `data/validation_report.json` 与人类可读的 `data/validation_report.md`。

### [2026-10-18 23:18] 节点 1：Phase 0 完成（脚手架搭建、跨平台配置与数据包探查）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：二（一）、二（二）、二（四）、三、六（二）
- **对应规划书阶段**：`IMPLEMENTATION_PLAN.md` -> Phase 0
- **实施完成内容**：完成 Git 初始化、标准目录树构建、requirements.txt、.gitignore 与 backtest/config.py 核心常量配置，通过终端验收。

### [2026-10-18 23:04] 节点 0：项目顶层架构设计与分层协作基线确立
- **参与角色**：规划侧高级模型（输出架构与分阶段执行方案）
- **核心决策**：向量化预计算+状态机撮合性能决策、2019-2022样本内/2023-2024样本外防过拟合切分、跨平台路径与中文字体方案。

## 四、环境与数据契约记录

- **Python 版本要求**：Python 3.10+（当前宿主环境为 Python 3.8 / 3.12 兼容）
- **核心依赖清单**：`pandas`, `numpy`, `matplotlib`, `flask`, `requests`
- **固定股票池清洗后数据规格**：
  - 覆盖标的：`600519` (贵州茅台), `601318` (中国平安), `601398` (工商银行), `600900` (长江电力), `000002` (万科A), `600276` (恒瑞医药), `002415` (海康威视), `002594` (比亚迪), `600111` (北方稀土), `601888` (中国中免), `000300` (沪深300基准)
  - 交易日周期：`2019-01-02` 至 `2024-12-31`，对齐后全部严格为 **1,456 行**
  - 标准列名：`date, open, high, low, close, volume, amount, is_suspended, up_limit, down_limit`
  - 空值率：全字段 **0.00% NaN**
- **踩坑与修复记录**：
  - `Windows 本地失效注册表代理问题`：Windows 注册表残留 `127.0.0.1:7890` 代理设置会导致 Python requests 报 `ProxyError` / `ReadTimeout`。在网络拉取会话中显式声明 `session.trust_env = False` 彻底切断坏代理干扰。
  - `行情 API 单次拉取 640 条限制`：腾讯行情接口单次请求上限为 640 条，若直接请求 6 年数据会被截断至 2.5 年。通过实现自动按 2 年一个分段（2019-2020, 2021-2022, 2023-2024）多段拉取并严密拼接，前复权因子在各段交界处高度连续，成功完整获取 1,456 个交易日全量数据。
  - `代码格式化保留前导零`：股票代码 `000002`、`002415` 等在 CSV 保存时若未显式指定可能被误认为整数，在舆情及清洗输出中统一强制以 6 位字符串格式处理。

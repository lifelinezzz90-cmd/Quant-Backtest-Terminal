# A股量化回测系统 · 跨平台开发记忆文件 (PROJECT_MEMORY.md)

> **维护规则**：本文件是跨开发环境（Trae / Qoder / WorkBuddy / Antigravity）、跨模型的**唯一上下文记忆中枢**。按时间倒序排列（最新进展在最前）。实施侧次级 AI 每完成一个 Phase，必须将进度、关键产出指标、踩坑记录同步更新至本文件顶部，并随代码一起执行 `git commit`。

## 一、当前开发状态总览（最新）

- **当前阶段**：`Phase 0 已完成 -> Phase 1 待启动（数据校验与清洗模块 backtest/data_ETL.py）`
- **当前协作模式**：分层协作模式（高级模型已完成 `IMPLEMENTATION_PLAN.md` 顶层规划；Antigravity 次级 AI 已落地 Phase 0 基础工程脚手架）
- **项目截止时间**：2026 年 11 月 3 日 22:00（FTP 压缩包上传，根目录直接打包且必须包含 `.git`、清洗后 `data/`、`strategy/strategy.json`、`records/对比结果.csv`）
- **Git 状态**：已初始化 Git 仓库，建立标准跟踪规则

## 二、待办任务清单 (Next Actions for Secondary AI)

- [x] **Phase 0：仓库初始化与脚手架搭建**
  - [x] 初始化 Git 仓库，创建标准目录树（`backtest/`, `strategies/`, `templates/`, `data/raw/`, `data/sample/`, `data/cleaned/`, `strategy/`, `records/runs/`, `demo/`）
  - [x] 编写 `.gitignore`（显式保留 data/、strategy/、records/）、`requirements.txt` 与 `backtest/config.py`（固化 10 只股票池、沪深300基准、万2.5佣金最低5元、万5卖出印花税、跨平台路径与中文字体自适应）
  - [x] **环境与数据探查**：全盘与工作区扫描未发现官方数据包文件，已建立 `data/raw/` 规范接收目录并制定字段自适应契约
- [ ] **Phase 1：数据校验与清洗模块 (`backtest/data_ETL.py`)**
  - [ ] 接收/加载官方数据包（若无本地数据包则支持 AkShare 交叉下载作为备用方案）
  - [ ] 实现缺失交易日对齐（标记停牌）、价格倒挂与毛刺清洗、前复权跳空检测
  - [ ] 导出清洗后 CSV 至 `data/cleaned/`，生成 `data/validation_report.json` 与 `data/validation_report.md`
- [ ] **Phase 2：高拟真回测撮合引擎与绩效模块 (`backtest/engine.py`, `metrics.py`, `logger.py`)**
  - [ ] 实现 T 日收盘信号、T+1 日开盘价成交、T+1 持仓锁、涨跌停拒单、停牌拒单、精确佣金与印花税扣减
  - [ ] 先在官方 3 只股票、3 个月样例数据上跑通冒烟测试
- [ ] **Phase 3：三大策略模式实现 (`strategies/`)**
  - [ ] 实现趋势跟踪 (`trend_following.py`)、均值回复 (`mean_reversion.py`)、多因子打分 (`multi_factor.py`，支持融合官方舆情打分 CSV)
  - [ ] 实现 `app.py` 命令行指定策略、参数与起止日期运行
- [ ] **Phase 4：参数网格寻优与样本外防过拟合验证 (`backtest/optimizer.py`)**
  - [ ] 按样本内（`2019-01-01`~`2022-12-31`）与样本外（`2023-01-01`~`2024-12-31`）切分，运行 68 组参数网格搜索与样本外三折滚动验证
  - [ ] 自动导出 `records/对比结果.csv`（$\ge 60$ 条有效实验）与 `strategy/strategy.json`
- [ ] **Phase 5：Flask 可视化看板与交付打包准备**
  - [ ] 完成 `templates/index.html` 报告看板、`启动.bat`、`README.md`、`提交信息.txt`、`ai_log.md`

## 三、开发进度与决策日志（按时间倒序）

### [2026-10-18 23:18] 节点 1：Phase 0 完成（脚手架搭建、跨平台配置与数据包探查）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：二（一）、二（二）、二（四）、三、六（二）
- **对应规划书阶段**：`IMPLEMENTATION_PLAN.md` -> Phase 0
- **实施完成内容**：
  1. **Git 仓库与目录树搭建**：在根目录下执行 `git init`，创建了 `backtest/`, `strategies/`, `templates/`, `data/raw/`, `data/sample/`, `data/cleaned/`, `strategy/`, `records/runs/`, `demo/` 全部标准子目录，并在空目录中设置占位符以确保纳入 Git 版本控制。
  2. **依赖与版本控制配置**：编写 `requirements.txt` 锁定 `pandas`, `numpy`, `matplotlib`, `flask`, `akshare` 核心依赖；编写 `.gitignore` 排除系统与开发临时文件，并设置反向规则 `!data/`, `!strategy/`, `!records/` 严格保证交割成果不被忽略。
  3. **全局核心配置常量落地 (`backtest/config.py`)**：
     - 固化 10 只股票池字典（代码、股票名称、行业分布）及沪深300基准代码 `000300`；
     - 固化交易摩擦：买入万 2.5 最低 5 元、卖出万 2.5 最低 5 元 + 印花税万 5；整手买入（100股整数倍）；主板涨跌幅限制 10%；
     - 固化全样本（2019-2024）、样本内（2019-2022）、样本外（2023-2024）与三折滚动验证时段；
     - 全路径强制采用 `pathlib.Path` 保证跨平台无缝迁移；
     - 内置跨平台 Matplotlib 中文字体自适应加载函数 `setup_matplotlib_font()`，优先命中 Windows `SimHei`/`Microsoft YaHei`，杜绝图表乱码。
  4. **本地数据包探查结论**：
     - 当前工作区根目录及系统常见下载目录中尚未检测到官方发布的预置数据包文件（CSV/ZIP）。
     - 实施策略：已经在 `data/raw/` 建立标准目录，待用户将官方数据放入后，Phase 1 ETL 模块将自动遍历解析；同时 ETL 模块内部设计兼容层，支持无缝处理常见的中文列名（日期、开盘、最高、最低、收盘、成交量、成交额）与英文列名（date, open, high, low, close, volume, amount），若用户暂未放入本地数据，支持一键通过备用数据源拉取并生成规范文件。
  5. **阶段验收结果**：
     - 运行 `python -c "import backtest.config as cfg; print(len(cfg.UNIVERSE_STOCKS))"`，成功输出 `10`。
     - 运行 `python backtest/config.py`，成功识别项目根目录并自动绑定 Windows 字体 `SimHei`。

### [2026-10-18 23:04] 节点 0：项目顶层架构设计与分层协作基线确立
- **参与角色**：规划侧高级模型（输出架构与分阶段执行方案）
- **关联章节**：《A股量化回测系统·任务书.md》全部章节（一至九及附录）
- **核心决策与背景**：
  1. **撮合与性能平衡决策（第一性原理）**：由于任务书要求完成不少于 60 条不同参数/策略的实验记录，规划采用“预对齐三维矩阵/字典 + 逐日截面 Numpy/Dict 状态机撮合”方案，既 100% 还原 T+1 锁仓、涨跌停不成交、停牌不交易、最低 5 元佣金与整手约束，又能将单次 6 年 10 股回测耗时压缩至 0.1 秒以内。
  2. **防过拟合与样本切分决策**：固定 2019–2022 年（4年）为样本内（In-Sample）调参期，2023–2024 年（2年）为样本外（Out-of-Sample）独立验证期，并内置样本外三折滚动验证，结合官方提供的舆情情感打分数据作为多因子策略的可选第四因子。
  3. **跨平台无痛复现决策**：所有文件路径操作强制使用 `pathlib.Path`；Matplotlib 绘图统一封装跨平台中文字体自动检测函数，规避 Windows/macOS/Linux 切换时的中文乱码问题。

## 四、环境与数据契约记录

- **Python 版本要求**：Python 3.10+（当前宿主环境为 Python 3.8 / 3.12 兼容）
- **核心依赖清单**：`akshare`, `pandas`, `numpy`, `matplotlib`, `flask`
- **固定股票池 (10只)**：
  - `600519` 贵州茅台 (白酒)
  - `601318` 中国平安 (保险)
  - `601398` 工商银行 (银行)
  - `600900` 长江电力 (电力)
  - `000002` 万科A (房地产)
  - `600276` 恒瑞医药 (医药)
  - `002415` 海康威视 (安防)
  - `002594` 比亚迪 (汽车)
  - `600111` 北方稀土 (有色金属)
  - `601888` 中国中免 (免税消费)
- **基准代码**：`000300`（沪深300指数）
- **数据存放规范**：
  - 官方原始数据：`data/raw/`（用户放置，ETL 自动适配常见 CSV 格式）
  - 官方样例数据：`data/sample/`（用于 3 只股票、3 个月的快速冒烟测试）
  - 清洗标准数据：`data/cleaned/`（规整为统一字段 `date, open, high, low, close, volume, amount, is_suspended, up_limit, down_limit`）
  - 校验报告：`data/validation_report.json` 与 `data/validation_report.md`
- **踩坑与修复记录**：
  - `Windows 控制台编码问题`：PowerShell 终端默认输出非 UTF-8 时中文会乱码，在 Python 模块及脚本中显式声明 `# -*- coding: utf-8 -*-`，文件统一使用 UTF-8 无 BOM 保存。


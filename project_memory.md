# A股量化回测系统 · 跨平台开发记忆文件 (PROJECT_MEMORY.md)

> **维护规则**：本文件是跨开发环境（Trae / Qoder / WorkBuddy / Antigravity）、跨模型的**唯一上下文记忆中枢**。按时间倒序排列（最新进展在最前）。实施侧次级 AI 每完成一个 Phase，必须将进度、关键产出指标、踩坑记录同步更新至本文件顶部，并随代码一起执行 `git commit`。

## 一、当前开发状态总览（最新）

- **当前阶段**：`Phase 0 ~ Phase 5 全流程圆满交付收官 (100% 验收就绪)`
- **当前协作模式**：分层协作模式（高级模型顶层规划；Antigravity 次级实施 AI 严格对齐落地 Phase 0 ~ Phase 5 全套交付件）
- **项目截止时间**：2026 年 11 月 3 日 22:00（FTP 压缩包上传，根目录直接打包且必须包含 `.git`、清洗后 `data/`、`strategy/strategy.json`、`records/对比结果.csv`）
- **Phase 5 最终收官与交互修复成果 (Latest)**：
  - **全量 Material 图标英文代号根除**：彻底移除外网 Google Material Symbols 字体依赖，全面清理 HTML 与 JavaScript 中所有残存英文图标代号（`query_stats` 改为纯加粗大写 `Q` Logo，移除所有标题前的 `show_chart`、`instant_mix`、`fact_check` 等，移除按钮上的 `bolt`、`refresh`、`restart_alt`、`file_download`，移除下拉框内重叠的 `expand_more`）；回测 Loading 状态采用轻量纯 CSS 旋转动画圆环，彻底告别 360 度旋转的 `hourglass_empty` 英文单词。
  - **三策略参数动态切换与容错打通**：前端参数面板随「趋势跟踪 (TrendFollowing)」、「多因子打分 (MultiFactor)」、「均值回复 (MeanReversion)」下拉与预设切换无缝动态更新 4 项核心参数；多因子策略对齐任务书绑定 `lookback_days`、`momentum_weight`、`volatility_weight`、`sentiment_weight`（自动附加 `rebalance_days=5, top_n=8`）；后端 `app.py` 与策略构造器健全类型过滤与默认值保护，杜绝参数类型转换与非法关键字异常。
  - **DOM 操作空指针防御 (Null-Safety)**：前端封装 `safeSetText` / `safeSetHTML` 判空防护，彻底根治因标签更新引发的 `TypeError: Cannot set properties of null`，捕获异常时精准打印 `err.message`。
  - **68 组实验基准防污染隔离**：`POST /api/backtest` 自定义回测独立归档运行数据至 `records/runs/`，严禁向 `records/对比结果.csv` 追加脏记录；首屏 `GET /api/dashboard` 永久加载全局最优 `TF_5_40_5`（年化 `+17.24%`、回撤 `-11.89%`、夏普 `0.9546`、胜率 `58.24%`），实验库恢复并永久保持纯净 68 行。
  - **可视化终端精修与双主题**：完成 `templates/index.html` 像素级排版对齐与防折行超框优化；顶栏实现「🌙 深色终端 / ☀️ 浅色研报」一键无缝双主题切换；布局采用 Grid 等高拉伸（`items-stretch`），彻底清除浅色模式所有深色容器残框（导航胶囊、三折卡片、黄色预警 Banner、输入框、下拉框与表格全量语义化配色修复）。
  - **数据治理表格首行防遮挡**：重构 `.sticky-table` 表头为实心不透明背景（深色 `#161b26` / 浅色 `#f1f5f9`），设置 `border-collapse: separate; border-spacing: 0;` 并规范表头内边距，彻底解决首行（万科A/贵州茅台）被表头遮挡的问题。
  - **Windows 中文字体回退根治**：彻底消除将中文元素赋予 `font-mono` / `font-metric-tabular` 导致的 Windows DirectWrite 回退至点阵新宋体（NSimSun）发虚发涩缺陷。确立全局界面中文字体栈为 `-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif !important;`，仅对纯数值与代码（`.num, code, .font-mono-num`）精准启用 `JetBrains Mono` 等宽字体。
  - **离线 ECharts 双子图交互**：引入本地离线 `static/echarts.min.js`（1,029,203 bytes），实现策略累积净值曲线（带 2023-01-03 样本外分界纵线、极值标注与面积渐变）+ 沪深300基准对比虚线 + 水下动态回撤面积子图（0.00% 至 -28.55%），多指标联动浮窗与窗口 resize 自适应。
  - **后端真实 API 全打通**：`app.py` 提供 `GET /api/dashboard`、`POST /api/backtest`、`GET /api/export_csv`。前端直连真实回测引擎，支持参数实时表单提交、秒级高保真撮合重算并动态更新曲线与 68 组实验库首行。
  - **全套交付文件与脚本**：
    - `启动.bat`：Windows 1 键自动化环境与数据检查、启动 Flask 服务并自动唤起默认浏览器；
    - `README.md`：精炼控制在 1 页左右，包含快速上手、CLI 模式与目录结构；
    - `提交信息.txt`：包含团队信息占位符、数据治理与等比前复权技术发现、最优策略全套指标汇总；
    - `ai_log.md`：全流程规范记录 Phase 0 至 Phase 5 的 AI 协作记录；
    - `demo/`：三张 300 DPI 无乱码高清交付成果图（最优策略净值与回撤对比、三大策略流派68组寻优分布、样本外三折滚动验证对比）。
- **数据对齐与底层状态**：
  - **主办方 6 列规范对齐**：全量 10 只股票及沪深 300 基准日线直接存放于 `data/{code}.csv`，严格统一为 6 列：`date,open,high,low,close,volume`，日期 `YYYY-MM-DD`，价格为等比前复权；
  - **等比前复权与零未来函数**：全面废除公开接口减法复权，以 2024-12-31 最新不复权收盘价为锚点，利用后复权序列按等比折算因子折算，中国平安 (`601318`) 在 `2019-02-25` 真实收益率精确还原为 **+8.22%**（彻底根治 12.37% 假毛刺）；毛刺修复采用纯前向 `prev_close` 平滑；
  - **撮合引擎挂单状态机**：新增 `pending_rebalance` 状态机，因涨跌停或停牌拒单的交易在次日开市自动补单成交；
  - **测试与审计 100% PASS**：脏数据清洗、撮合规则（含自动补单）、物理截断未来函数检验 (0.00e+00)、会计恒等式 (0.0000元误差)、开盘价成交 (100%) 全部通过。
- **68 组网格寻优与样本外三折滚动验证结果**：
  - **评估组合数**：趋势跟踪 25 组 + 均值回复 16 组 + 多因子打分 27 组 = **68 组独立组合全部完成回测与多周期评估**；
  - **评选全局最优策略**：`TrendFollowingStrategy (TF_5_40_5)`
    - 参数：`short_window=5, long_window=40, rebalance_days=5, max_positions=8`
    - **样本外 (OOS: 2023-2024)**：年化收益率 **17.24%** | 夏普比率 **0.9546** | 最大回撤 **11.89%** | 卡玛比率 **1.4498**
    - **样本外三折滚动验证 (3-Fold)**：**100% 全部通过 (3/3 PASS)**（Fold 1 夏普 0.16 > 基准 -0.43，Fold 2 夏普 1.09 > 基准 -0.63，Fold 3 夏普 1.25 > 基准 0.51）
    - **全周期 (Full: 2019-2024)**：年化收益率 **13.87%** | 夏普比率 **0.6249** | 最大回撤 **28.55%** | 交易胜率 **58.24%** | 成交 **1048** 笔
  - **核心交付物**：
    - `records/对比结果.csv`: 68 条无重复参数完整回测记录
    - `strategy/strategy.json`: 全局最优及各类别最优配置
    - `records/runs/best_strategy_equity.png`: 带 2023-01-01 样本内/外分界线的高清净值曲线图

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
- [x] **Phase 3.5：数据规格对齐与底座热修复 (`backtest/data_ETL.py`, `backtest/engine.py`)**
  - [x] 行情数据直接存入根目录 `data/{code}.csv`，严格统一为 6 列：`date,open,high,low,close,volume`，日期格式 `YYYY-MM-DD`
  - [x] 废除腾讯减法复权，改用「等比前复权 (Proportional Forward Adjustment)」，以 2024-12-31 最新不复权收盘价为锚点，日收益率 100% 还原真实股票收益率，中国平安 2019-02-25 真实日收益率还原为 +8.22%
  - [x] ETL 毛刺修复采用纯前向收盘价平滑，彻底消除未来信息泄露
  - [x] 引擎增加 `pending_rebalance` 挂单状态机，并在单元测试中增加断言 7 验证涨跌停拒单后次日自动补单成交
- [x] **Phase 4：参数网格寻优与样本外防过拟合验证 (`backtest/optimizer.py`, `app.py --mode optimize`)**
  - [x] 设计 68 组无重复参数网格字典（趋势跟踪 25 组、均值回复 16 组、多因子 27 组）
  - [x] 实施样本内 (2019-2022)、样本外 (2023-2024)、样本外三折滚动检验 (Fold 1, Fold 2, Fold 3) 与全周期 (2019-2024) 测评
  - [x] 预热期无损切片机制保障指标无冷启动失真
  - [x] 导出 `records/对比结果.csv`（68条无重复记录）与 `strategy/strategy.json`
  - [x] 绘制带 2023-01-01 样本内外分界竖线的高清净值图 `records/runs/best_strategy_equity.png`
- [x] **Phase 5：Flask 可视化看板与全套交付件收官**
  - [x] 完成 `templates/index.html` Stitch 风格终端精修，支持「🌙 深色终端 / ☀️ 浅色研报」一键无缝双主题与排版防超框
  - [x] 嵌入本地离线 `static/echarts.min.js`，实现累计净值（含 2023-01-03 样本外分界纵线）与水下动态回撤双子图联动
  - [x] 全面打通 `app.py` 后端真实 API（`GET /api/dashboard`, `POST /api/backtest`, `GET /api/export_csv`），支持前端实时表单回测
  - [x] 编写 Windows 一键启动脚本 `启动.bat`、极简交付说明 `README.md` 与参赛确认单 `提交信息.txt`
  - [x] 更新 `ai_log.md` 记录全流程 AI 协作过程，并在 `demo/` 目录下生成 3 张 300 DPI 无乱码高清成果图
  - [x] 完成全套自动化验真测试（`python app.py --mode test` 100% 通过）

## 三、开发进度与决策日志（按时间倒序）

### [2026-10-23 00:45] 节点 7：Phase 5 封版收尾（严格同步 strategy.json 真实三折指标与根目录清理）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：第五章、第六章
- **实施完成内容**：
  1. **三折滚动交叉验证指标 100% 真实对齐**：
     - 将 `strategy/strategy.json`、`app.py` (`/api/dashboard`)、`templates/index.html` 与 `提交信息.txt` 中的三折验证指标严格统一为最优策略 `TF_5_40_5` 的真实数据：`Fold 1: +0.16 (基准 -0.43，超额 +0.59)`、`Fold 2: +1.09 (基准 -0.63，超额 +1.72)`、`Fold 3: +1.25 (基准 +0.51，超额 +0.74)`，3/3 (100%) 全部 PASS；
     - 彻底消除前端硬编码示例数值，前端 `renderRolling3Fold()` 自动从 API 接口获取并响应式动态更新卡片数值。
  2. **根目录结构与启动脚本规范化**：
     - 将 `generate_demo_charts.py` 移入 `backtest/generate_demo_charts.py`，移除临时 `scripts/` 目录，将 Stitch 设计草图移入 `templates/`，确保项目根目录严格遵循任务书标准；
     - 校准 `启动.bat` 的 CRLF 换行符与 `@echo off` / `chcp 65001 >nul`，保障 Windows 命令行双击运行无乱码；
     - 重新生成 `demo/3_样本外三折滚动验证对比.png`，图表数值与说明完全与 `strategy.json` 真实数据比特级对齐。
  3. **自动化测试验证**：
     - 重新执行 `python app.py --mode test`，全套测试与四重验真审计全部 100% 通过。

### [2026-10-22 23:45] 节点 6：Phase 5 完成（Stitch双主题交互看板精修、真实API全打通与全套交付文档就绪）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：第五章、第六章
- **对应规划书阶段**：`IMPLEMENTATION_PLAN.md` -> Phase 5
- **实施完成内容**：
  1. **前端终端像素级精修与双主题支持 (`templates/index.html`)**：
     - 去除冗长括号副标题，为所有数值、标签添加 `tabular-nums` 与 `whitespace-nowrap`，彻底消除折行撑歪卡片问题；
     - 引入 `html[data-theme="light"]` 完善浅色主题适配（石板灰背景 `#f8fafc`、白卡 `#ffffff`、深字 `#0f172a`），在顶栏提供切换按钮，并自动调整 ECharts 图表底色与轴网格线；
     - 采用 CSS Grid 等高拉伸（`items-stretch`），确保左侧图表与右侧策略配置控制台高度严格对齐。
  2. **离线 ECharts 双子图与后端 API 全打通 (`app.py`, `static/echarts.min.js`)**：
     - 保存 1.02MB 完整版 `echarts.min.js` 至 `static/` 目录，杜绝离线测试或断网报错；
     - 绘制累计净值（主轴，带最高/最低标注、面积渐变与 2023-01-03 样本外分界虚线）与水下动态回撤面积图（副轴）；
     - 页面加载自动调用 `GET /api/dashboard` 绑定真实 KPI、三折验证、数据治理与 68 组实验库（支持类别筛选与多字段排序）；
     - 点击“立即运行高保真回测”调用 `POST /api/backtest` 毫秒级重算并平滑刷新图表与指标，新记录置顶插入实验表格。
  3. **交付文档与启动脚本收官**：
     - 编写 `启动.bat`：Windows 下自动执行环境与数据完整性校验，启动 Flask 服务并唤起浏览器打开 `http://127.0.0.1:5000`；
     - 编写精炼 `< 1` 页的 `README.md`，涵盖项目亮点、极简安装、一键启动与 CLI 指南；
     - 编写 `提交信息.txt`，规范记录考生信息、数据清洗与等比前复权技术发现、最优策略全套参数与指标；
     - 在 `demo/` 目录中生成 3 张 300 DPI 无乱码高清成果图表；
     - 更新 `ai_log.md` 记录 Phase 0 ~ Phase 5 全流程。

### [2026-10-20 00:05] 节点 5：Phase 3.5 & Phase 4 完成（等比前复权6列标准、挂单状态机与68组样本内外网格寻优）
- **参与角色**：实施侧次级 AI (Antigravity)
- **对应任务书章节**：二（一）2、二（一）5、二（二）、四章及主办方最新数据规格说明
- **对应规划书阶段**：`IMPLEMENTATION_PLAN.md` -> Phase 3.5 & Phase 4
- **实施完成内容**：
  1. **等比前复权与 6 列标准对齐**：
     - 数据交付目录统一至 `data/{code}.csv`，包含 `000300.csv` 与 10 只股票，严格统一为 6 列 (`date,open,high,low,close,volume`)；
     - 废除公开行情减法复权，以 2024-12-31 最新不复权价格为锚点，采用等比折算因子 $\alpha = P_{latest\_unadj} / P_{latest\_hfq}$ 全局折算，保证历史上除权除息之外所有交易日的前复权收益率与真实持股日收益率 100% 绝对一致（`601318` 2019-02-25 涨幅还原为 +8.22%）；
     - 毛刺平滑算法弃用任何未来数据插值，统一采用 `prev_close` 单向前向平滑；
     - `load_cleaned_data()` 优先读取 6 列标准 CSV 并在内存中动态计算 `is_suspended`, `up_limit`, `down_limit`, `amount`。
  2. **挂单状态机与自动补单 (`pending_rebalance`)**：
     - 撮合引擎在标的因停牌、涨停（买入）或跌停（卖出）被拒单时，置 `pending_rebalance[code] = True`；
     - 次日开市时，即使策略目标权重未变，引擎主动重试挂单调仓并在成交后清零；
     - 在 `test_engine_rules()` 中增加断言 7 验证涨停拒买后次日自动补单成交，测试 100% PASS。
  3. **68 组网格寻优与三折滚动检验 (`backtest/optimizer.py`)**：
     - 严格设计趋势跟踪 25 组、均值回复 16 组、多因子 27 组共 68 组独立参数网格；
     - 采用全量预热生成连续信号，按样本内 (2019-2022)、样本外 (2023-2024)、样本外三折滚动 (2023.01-08, 2023.09-2024.04, 2024.05-12) 与全周期无损切片撮合；
     - 综合评选出全局最优策略 `TrendFollowingStrategy (TF_5_40_5)`：样本外夏普 0.95，年化 17.24%，回撤 11.89%，三折滚动验证 100% 全部通过 (PASS)；
     - 成功导出 `records/对比结果.csv` (68条)、`strategy/strategy.json` 与带 2023-01-01 样本内外分界竖线的高清净值图 `records/runs/best_strategy_equity.png`。

### [2026-10-19 10:43] 节点 4：Phase 3 完成（三大策略实现、参数化回测与四重质量验真审计通过）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：三大策略落地、四重质量验真审计（截断差异 0.00e+00、会计恒等式误差 0.0000元、开盘价 100% 吻合）。

### [2026-10-19 00:25] 节点 3：Phase 2 完成（高拟真回测引擎、四大A股规则状态机与绩效评估体系落地）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：回测引擎、T+1 锁仓状态机、涨跌停拦截、停牌拦截、绩效指标计算与等权买入持有策略冒烟测试。

### [2026-10-18 23:30] 节点 2：Phase 1 完成（数据源双模自适应、四步清洗流水线与报告导出）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：10 只股票 + 基准 2019-2024 年全量 1456 天日线清洗与报告。

### [2026-10-18 23:18] 节点 1：Phase 0 完成（脚手架搭建、跨平台配置与数据包探查）
- **参与角色**：实施侧次级 AI (Antigravity)
- **核心产物**：Git 仓库初始化、目录树脚手架与配置文件。

### [2026-10-18 23:04] 节点 0：项目顶层架构设计与分层协作基线确立
- **参与角色**：规划侧高级模型

## 四、环境与数据契约记录

- **Python 版本要求**：Python 3.10+（当前宿主环境为 Python 3.8 / 3.12 兼容）
- **核心依赖清单**：`pandas`, `numpy`, `matplotlib`, `flask`, `requests`
- **踩坑与修复记录**：
  - `减法复权失真与等比前复权`：公开接口（如腾讯 `qfqday`）采用减法复权，将历史分红从股价中直接扣减，导致低价区间分母被虚假压缩，中国平安 `601318` 在 2019-02-25 涨幅被放大为 12.37% 并被误判为毛刺；改用等比前复权法（以 2024-12-31 最新不复权收盘价为锚点，利用后复权序列按等比缩放因子换算），日收益率 100% 还原真实股票收益率（还原为 +8.22%），彻底解决数据失真。
  - `ETL 零未来函数`：毛刺平滑算法原先在双向回弹时使用了 `(prev_close + next_close) / 2` 均值平滑，引入了微量未来信息；现全面改为只使用前收盘价 `prev_close` 进行单向前向平滑，彻底消除未来信息泄露。
  - `挂单状态机防漏单`：策略调仓在因涨跌停或停牌被拦截后，若后续交易日策略目标权重未变，可能错过补单机会；在引擎中维护 `pending_rebalance` 状态字典，次日即使目标权重差为 0 也强制重试调仓，直至成交。
  - `会计恒等式舍入微小偏差`：浮点数乘法未显式在每笔交易 round 到分时，经过数百笔交易会累计产生 0.1 元级别的舍入误差。在引擎中将每笔成交额、佣金、印花税及现金账户均强制以分（两位小数）为结算单位，实现了会计恒等式差异 0.0000 元的比特级严密平衡。

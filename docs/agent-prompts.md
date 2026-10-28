# 子代理提示词汇总（DeviceLoan MVP）

> 来源：OpenCode 本地会话数据库 `session_v2` / `session_message` 的 `user` 消息，原文提取，未改写。
> 主会话：`ses_e974b4970ffeaiOzI5aH7pS10A`（阅读材料并制定执行计划）。
> 汇总范围：该主会话下 **26 个子代理会话**、**30 条用户消息**，总字数约 **50,907**。
> 模型：23 条会话为 `opencode/deepseek-v4.1-flash-free#high`；CR-02 的 3 条（24–26）为 `deepseek/deepseek-flash#high`。

说明：

1. 每条提示词首行的 `You are a subagent spawned by another session.` 是 OpenCode 运行时自动加的前缀，不是 PM 手写内容；为保持原文完整，正文保留。
2. 同一子代理会话可能有多条用户消息：第 1 条是首次派单，后续是返工或补充要求；文中按“用户消息 1 / 共 N”标注。
3. 第 21、23 条都是 UAT 条件 C1 的补测任务，属于重复派发；第 21 条未产出有效结果，第 23 条为后续重派并成功。正文保留两次原文，便于对比。
4. 为便于复制，提示词正文使用四反引号代码块包裹；原文中的三反引号命令块不会被截断。

## 1. 一览

| # | 阶段 | 角色 | 任务 | 会话 ID | 用户消息 | 字数 |
|---:|---|---|---|---|---:|---:|
| 1 | 启动 | `ba-architect` | 启动阶段：商业论证/章程/干系人 | `ses_e97404953ffe3P8XAnz1J25WPx` | 1 | 2,401 |
| 2 | 启动 | `ccb-sponsor` | 评审批复项目章程与商业论证 | `ses_e973da747ffehz6lRDWf0C1aHE` | 1 | 1,209 |
| 3 | 启动 | `ba-architect` | 按CCB条件出v1.1 | `ses_e973cf092ffeKxPZOxwmK3wwpv` | 1 | 1,665 |
| 4 | 规划 | `ba-architect` | 规划：范围与架构契约 | `ses_e972f7fd1ffe8n7PjfmtcjGtoh` | 1 | 2,976 |
| 5 | 规划 | `ba-architect` | 规划：WBS与风险质量计划 | `ses_e972c12dbffe4Fot0SK8t1Iti5` | 1 | 1,970 |
| 6 | 规划 | `ccb-sponsor` | 规划基线评审 | `ses_e9724a577ffeg7bo5aIKrXLEWX` | 1 | 1,434 |
| 7 | 执行 | `dev-engineer` | WP1 账户与角色权限 | `ses_e970f9598ffeyFzo7fFg5ObW5V` | 1 | 2,390 |
| 8 | 执行 | `qa-engineer` | QA1 验收账户与权限 | `ses_e970d14d7ffeslAxDrBWrQnodn` | 1 | 1,776 |
| 9 | 执行 | `dev-engineer` | WP2 设备目录与查询 | `ses_e9700e8f3ffeFVYPwNvEkMsT9c` | 3 | 3,443 |
| 10 | 执行 | `qa-engineer` | QA2 验收设备查询 | `ses_e96fd89b9ffeT5es5mMwrhOk5u` | 1 | 1,790 |
| 11 | 执行 | `dev-engineer` | WP3 申请审批与冲突阻止 | `ses_e96e9c7a3ffeeT3Y5x1DPRb28D` | 2 | 3,391 |
| 12 | 执行 | `qa-engineer` | QA3 验收申请审批 | `ses_e96e2c106ffeCWWn44qoe4y6wV` | 1 | 2,178 |
| 13 | 执行 | `dev-engineer` | WP4 借出归还与逾期 | `ses_e96e28b8cffeLtsvlk8kHEVp2Y` | 2 | 3,112 |
| 14 | 变更 | `ba-architect` | CR-01 候补队列影响分析 | `ses_e96dd3439ffe2BsL2y5z09pei2` | 1 | 1,598 |
| 15 | 执行 | `qa-engineer` | QA4 验收借出归还 | `ses_e96d92be6ffelCt5pna6AdA1u1` | 1 | 1,762 |
| 16 | 变更 | `ccb-sponsor` | CR-01 变更裁定 | `ses_e96d6061bffe4u3TpeDUKDw8bs` | 1 | 1,424 |
| 17 | 执行 | `dev-engineer` | WP5 统计与审计 | `ses_e96cae91efferD65WQD4VPGP1p` | 1 | 2,579 |
| 18 | 执行 | `dev-engineer` | 演示数据脚本（瘦身版） | `ses_e96ca9e74ffeQKIP0MANtqLDR8` | 1 | 1,408 |
| 19 | 执行 | `qa-engineer` | QA5 验收统计与审计 | `ses_e96c58608ffeAOLp5VENc6QM5R` | 1 | 1,632 |
| 20 | 收尾 | `qa-engineer` | UAT 验收（阶段5） | `ses_e96a4e697ffeO5OeOodcHfHJHd` | 1 | 1,313 |
| 21 | 收尾 | `qa-engineer` | 补 TC-NFR-07-01 用例 | `ses_e969d92ccffeMVvJ16UY0jHGhI` | 1 | 779 |
| 22 | 收尾 | `ccb-sponsor` | 收尾追认：储备与遗留 | `ses_e969d66f7ffeBCMpOhWmQzJyxe` | 1 | 1,091 |
| 23 | 收尾 | `qa-engineer` | 补 NFR-07 追溯用例 | `ses_e969964ecffejXXsf8HcFk3es4` | 1 | 1,057 |
| 24 | 变更 | `ccb-sponsor` | CR-02 候补队列裁定 | `ses_e934a141fffeDTYdRZw7Lbw94y` | 1 | 907 |
| 25 | 变更 | `dev-engineer` | 实现 WP6 候补队列 | `ses_e9349a8eeffeFWx7S5zpJ0YG7I` | 1 | 3,301 |
| 26 | 变更 | `qa-engineer` | WP6 候补队列验证 | `ses_e9346322effe4adk8YWADVbmuQ` | 1 | 2,321 |

按阶段统计：启动 3 条、规划 3 条、执行 11 条、变更 5 条、收尾 4 条；其中 3 条执行任务带返工追加，2 条为 C1 重复派发。

## 2. 这些提示词的共同结构

| 要素 | 常见写法 | 作用 |
|---|---|---|
| 角色与任务号 | “你是本项目的 BA / Dev / QA / CCB”“任务书编号 1.1–1.3”“WBS 3.5” | 先锁定角色边界和任务范围 |
| 只读输入 | “必读（只读这三份，不要通读仓库）”后列文件与章节 | 控制上下文，避免子代理在海量文档里跑偏 |
| 写入白名单 | “只写这两个文件”“只新建 `tests/...`”“不改 `src/`” | 防止越权修改和职责混淆 |
| 固定口径 | 预算、工期、退出码、公式、表结构、命令名 | 让多个子代理的产物能拼在一起 |
| 验收/自检 | TC 编号、A–O 自检矩阵、必跑命令、期望退出码 | 把“做完了”变成可检查的证据 |
| 回执格式 | `STATUS / DELIVERABLES / CHECKS / ...` | 让 PM 能快速验收、归档、决定是否返工 |
| 禁止事项 | 不写测试、不改产品代码、不装包、不联网、不编造输出 | 把角色边界写成硬约束 |

一个明显的规律是：**提示词越接近“任务书 + 接口契约 + 验收单”，子代理的产出越稳定**。反过来，像“帮我实现候补队列”这种没有写入白名单和退出码的写法，在多智能体环境里很容易越界或反复返工。

## 3. 提示词原文

### 3.1 启动阶段

#### 01｜启动阶段：商业论证/章程/干系人

- 会话：`ses_e97404953ffe3P8XAnz1J25WPx`
- 角色：`ba-architect`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 2,401 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 BA/架构师。任务书编号 1.1–1.3（启动阶段）。只产出下面三个文档，不做其他事。

## 只读输入（不要通读仓库其他文件）
- `00-customer-brief.md`（全文，唯一需求来源）
- `reference/文档模板.md` 的第 1、2、3、4、5 节（商业论证、干系人登记表、干系人管理策略、项目章程、启动会议程）
- `reference/净现值和挣值管理.md` 开头到 NPV 局限一节
- `plan/rates.csv`（虚拟日薪）
- `lab1.md` 的提交要求部分（了解报告最终要什么）

## 只写这三个文件（禁止写其它任何文件）
1. `docs/01-business-case.md`
2. `docs/02-charter.md`
3. `docs/03-stakeholders-kickoff.md`

## 统一设定
- 项目名称：实验室设备借用管理系统（DeviceLoan MVP）
- 客户：某高校实验中心。团队是"多智能体项目团队"，成员用**职位 + 模型名称**表示，不要编造人名。
- 所有姓名/学号/联系方式/签名统一写 `【待填】`，不要编。
- 技术约束沿用客户档案：Python 标准库 + SQLite、命令行、无第三方依赖。
- 需求一律用原 ID 引用（CRQ-01~CRQ-10、NFR-01~NFR-07），**不要复述需求全文**；CRQ-10 只作为"变更候选"，不得写进范围基线。
- 预算口径：批准总预算 ¥17,800 = 成本基线 ¥15,800 + 应急储备 ¥2,000；客户侧硬约束是"修订后总成本 ≤ ¥19,700"。启动阶段（任务 1.1–1.5）已用 2.5 人日 ≈ ¥1,550（BA 1.5 天×600、PM 0.5 天×800、CCB 0.5 天×500）。
- 工期口径：20 个工作日（客户成功标准）。
- 文档风格：中文、平实、表格优先，每份控制在 1–2 屏；不写"行业黑话"，不写角色扮演对话（AI 开会没有意义，启动会写成"议程 + 决议 + 待办"即可）。

## 1. `docs/01-business-case.md`（六段以内）
按模板 1 的骨架压缩：背景与问题 / 业务目标 / 方案比选（至少含"什么也不做"和"直接采购现成系统"两个备选）/ 初步需求（按 ID 归类，一表带过）/ 成本与 NPV / 进度与主要风险。

NPV 要求（重要，我会计复核）：
- 3 年、折现率 10%，C0 = -17,800。
- 收益必须是可追溯的乘法链，例如"节省管理员工时 384 小时/年 × ¥50/小时 = ¥19,200/年"、"减少设备重复采购 ¥5,000/年"，并给出 2–3 条明确标注"假设、待确认"的参数。
- 必须给出逐期表：年度、净现金流、折现因子、现值、累计现值；给出 NPV 合计、投资回收期（口径：C0 ÷ 首年净现金流，换算成月）。
- 客户成功标准要求 NPV > 0 且回收期 < 12 个月，你的数字必须自洽且满足（若无法满足就如实写并给建议，不要硬凑）。
- 不要运行 python 或其他命令（你的 shell 权限只允许 `Get-FileHash` 和 `python tools/*`，`python -c` 会被拒绝）。手算表格即可，但要保证加减乘除正确。

## 2. `docs/02-charter.md`
覆盖模板 4 的全部字段：项目名称、开始/完成日期（用"第 1 个工作日～第 20 个工作日"这种相对写法，不编具体日历日期）、预算信息（拆成 成本基线/应急储备/客户上限/启动阶段已用）、项目经理（`【待填】` + 职位说明）、项目目标、成功标准（直接绑定客户档案第 5 节的 5 条，不加码）、方法（五过程组 + 多智能体分工 + 迭代交付 5 个工作包 + 变更控制委员会）、角色与职责矩阵（PM/BA/Dev/QA/CCB 五行，列：角色、职责、主要产出、模型或占位说明）、签名栏（`【待填】` × 发起人/项目经理/客户代表）、意见栏（留空，标注"由发起人评审后填写"）。
另加一小节"假设与制约"：20 个工作日、¥19,700 上限、MVP 不替代线下流程、单人单角色。

## 3. `docs/03-stakeholders-kickoff.md`
- 干系人登记表：学生/教师、实验室管理员、实验中心主任、实验中心（客户/发起方）、智能体项目团队（PM/BA/Dev/QA/CCB）。列：干系人、职位/身份、内外部、项目角色、联系方式（智能体写"会话内交互"，人写 `【待填】`）。
- 干系人管理策略表：利益相关度、影响程度、管理策略（一列写具体动作，例如"每周状态报告 + 演示会验收"）。
- 启动会：议程 5 项、决议 3–5 条（例如"基线范围锁定 CRQ-01~09，CRQ-10 进入变更候选"）、待办表（事项/责任人/截止），不写对话。

## 交付要求
- 三个文件写完后，回执按你的模板输出（STATUS / DELIVERABLES / CHECKS / ASSUMPTIONS / OPEN_ISSUES），CHECKS 只写你真实执行过的命令（可以跑 `Get-FileHash docs/*.md` 做一次存在性/完整性确认），没有执行就写 none。
- 不要修改 `docs/` 以外的任何文件；不要写计划数据、WBS、代码或测试。
- 文档里出现的每一个汇总数字（NPV、总成本、人日）都必须能从文档内的明细加出来，我会逐项复核。
````

#### 02｜评审批复项目章程与商业论证

- 会话：`ses_e973da747ffehz6lRDWf0C1aHE`
- 角色：`ccb-sponsor`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,209 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目发起人（实验中心主任）兼 CCB。现在只评审"项目章程与商业论证是否可以批准"，不要评审其他内容。

## 决策包（只读这两份文件，不要通读仓库）
- `docs/02-charter.md`（项目章程 v1.0）
- `docs/01-business-case.md`（商业论证 v1.0）

## 背景要点
- 客户：某高校实验中心；项目：实验室设备借用管理系统（DeviceLoan MVP），Python 标准库 + SQLite 的命令行原型。
- 客户硬约束：20 个工作日内完成；修订后总成本 ≤ ¥19,700；NPV（3 年、10%）> 0 且回收期 < 12 个月；CRQ-01~08 必须可演示。
- 章程申报：成本基线 ¥15,800 + 应急储备 ¥2,000 = 批准预算 ¥17,800；¥17,800 与 ¥19,700 之间 ¥1,900 为管理储备。
- 范围基线为 CRQ-01~09 + NFR-01~07；CRQ-10（候补队列）为变更候选，走 CR-01。

## 请评审并给出结论
重点核这几条（不足就写进 CONDITIONS，不要自行改写文件）：
1. 章程的成功标准是否严格绑定客户档案第 5 节，有没有偷偷加码或漏项（尤其 20 个工作日、¥19,700、NPV）。
2. 预算结构是否自洽：15,800 + 2,000 = 17,800；17,800 + 1,900 = 19,700；启动阶段 ¥1,550 是否已含在基线的 25 人日里。
3. NPV 的收益假设（B1 节省工时 ¥19,200/年、B2 重复采购 ¥5,000/年、O1 运维 −¥1,200/年，年净现金流 ¥23,000）是否"可验证"，还是必须补证。回收期 9.3 个月是否算得对（口径：17,800 ÷ 23,000）。
4. 范围是否明确排除 CRQ-10；有没有把"候补通知/自动递补"误纳入。
5. 20 个工作日 + 5 个工作包 + 单角色单智能体的组织方式是否存在明显不可行之处。

只能选一个结论：APPROVE / APPROVE WITH CONDITIONS / REJECT / DEFER。
- 若选 APPROVE WITH CONDITIONS，条件必须可验证（指向文件、数字或下一步动作），不超过 4 条。
- 若认为财务假设需要客户书面确认才能生效，请把"确认后再进入执行"写成条件，而不是直接批准。

回执按你的模板输出：DECISION / SUBJECT / RATIONALE（≤5 条，引用文件与数字）/ CONDITIONS / BUDGET（计划/已发生/上限/偏差）/ OPEN_ISSUES。不要修改任何文件，不要运行命令。
````

#### 03｜按CCB条件出v1.1

- 会话：`ses_e973cf092ffeKxPZOxwmK3wwpv`
- 角色：`ba-architect`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,665 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 BA/架构师。上一次你交付的 `docs/01-business-case.md` v1.0 与 `docs/02-charter.md` v1.0 已被发起人评审，结论是"有条件批准"。本次任务：按其中 2 条条件出 v1.1，只改这两个文件。

## 只读输入
- `docs/02-charter.md`、`docs/01-business-case.md`（当前 v1.0，你要在其上修订）
- 需要核对成功标准原文时可读 `00-customer-brief.md` 第 5 节

## 条件 1（改 `docs/02-charter.md`，版本升到 v1.1）
- §4 表格 S5 删去"约"字，改为"20 个工作日内完成，修订成本 ≤ ¥19,700"（与客户硬约束一致）。
- §4 表格增加一列"客户档案条目"，把 S1–S6 一一对应到客户需求档案第 5 节的 5 个 bullet（注意：S1/S2/S3/S4 分别对应前 4 个 bullet，S5/S6 对应第 5、6 个 bullet，请按原文实际条数标注，不要硬凑 5 条）。
- 文档头"状态"改为"有条件批准（待签署），v1.1"；在 §9"意见"下补一小段"发起人评审结论"：结论为有条件批准，列出 4 条条件，逐条标注状态（已闭合 / 待办及责任人）。4 条条件原文摘要如下：
  1. S5 措辞与成功标准映射（本次闭合）；
  2. 财务参数 B1/B2/O1 需客户书面确认，并补 B1、B2 同时下降 25% 的组合敏感性（敏感性本次闭合，客户确认待办，责任人：客户代表【待填】）；
  3. 进度基线须写明 CR-01 评审与实现的 Dev/QA 人日及储备来源；CR-01 评审的 ¥250 出自管理储备（本次仅在 §2 加一条脚注说明口径，具体人日与排期由 PM 在进度基线中落实，标"待办，责任人 PM"）；
  4. 签署与模型名称填齐后状态转"已批准"（待办，责任人：PM 与【待填】）。
- 在 §2 预算表下加一行脚注：变更评审（每次 0.5 人日 / ¥250）由未分配管理储备（¥1,900）承担，不占用 CCB 的 1.0 人日基线。

## 条件 2（改 `docs/01-business-case.md`，版本升到 v1.1）
- §5.3 之后补一条**组合敏感性**：B1 与 B2 同时下降 25%，即 B1 = 19,200×0.75 = 14,400、B2 = 5,000×0.75 = 3,750、O1 不变 −1,200 → 年净现金流 = 16,950。给出 3 年 10% 折现的 NPV 与回收期（回收期口径同前：17,800 ÷ 年净现金流），逐期现值列出来，保留 2 位小数。必须自己算对，不要运行命令。
- 在 §5.2 表格下补一句：上述参数为 BA 估算，**尚未取得客户书面确认**，确认记录随客户反馈归档；本实验以客户需求档案为唯一书面需求来源，参数确认由客户代表【待填】完成。
- 文档头状态改为"v1.1，财务参数待客户确认"。
- 结论段不要因为条件未闭合就改写"推荐"结论，但必须明确写"若组合敏感性下 NPV 仍为正、回收期仍在 12 个月内，则推荐结论不变"。

## 硬要求
- 只改这两个文件，不动 `docs/03-stakeholders-kickoff.md`，不写其他文件，不跑除 `Get-FileHash` 外的命令。
- 所有新增数字要能从文档内明细加出来；表格保持紧凑，不要扩写篇幅（v1.1 相比 v1.0 每份最多增加 15 行）。
- 回执按模板输出（STATUS/DELIVERABLES/CHECKS/ASSUMPTIONS/OPEN_ISSUES），并明确报告组合敏感性的三个数字：年净现金流、NPV、回收期（月）。
````

### 3.2 规划阶段

#### 04｜规划：范围与架构契约

- 会话：`ses_e972f7fd1ffe8n7PjfmtcjGtoh`
- 角色：`ba-architect`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 2,976 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目 BA/架构师，任务 2.1–2.2（规划阶段）。产出两份文档，供后续 Dev 实现与 QA 写测试使用。

## 只读输入
- `00-customer-brief.md`（全文，唯一需求来源）
- `docs/02-charter.md`（只读 §3 项目目标、§4 成功标准、§7 假设与制约）
- `docs/01-business-case.md` §4（需求分组）
- `reference/文档模板.md` 第 7 节（范围说明书）

## 只写这两个文件
1. `docs/04-scope.md` —— 范围说明书 + 需求追溯矩阵（RTM）
2. `docs/05-architecture.md` —— 架构、数据模型、CLI 契约

## 固定背景（不要改动）
- 项目：实验室设备借用管理系统（DeviceLoan MVP）；Python 3.11 标准库 + SQLite；命令行；零第三方依赖。
- 基线范围：CRQ-01~CRQ-09 与 NFR-01~NFR-07；**CRQ-10（候补队列）不在基线**，只在文档里标为"变更候选 CR-01"。
- 5 个开发工作包：WP1 账户与角色权限（CRQ-01）、WP2 设备目录与查询（CRQ-02）、WP3 申请与审批 + 冲突阻止（CRQ-03/04/05/09）、WP4 借出/归还/逾期（CRQ-06）、WP5 统计与审计（CRQ-07/08）。演示数据与脚本不算开发工作包，由 WP5 之后单独一步完成。
- 目标规模：演示数据 20 台设备、8 个用户、50 条借用记录量级；单次查询 < 1 秒。

## `docs/04-scope.md` 要求（控制在 2 屏）
1. 项目起因（3 行内，引用章程/商业论证，不复述）。
2. 范围内 / 范围外（表格）：范围外必须含 CRQ-10 候补队列、候补通知、自动递补、Web/图形界面、移动端、与资产系统或学籍系统集成、多校区、邮件/短信通知、正式上线运维。
3. 产品可交付物与项目管理可交付物（两列清单，各 5–7 条，一句话一条）。
4. 验收标准：把章程 S1–S6 逐条落到"怎么验"（演示脚本 / 自动化测试 / 数据核对 / 财务复核），不新增指标。
5. 假设与制约（3–5 条，从章程 §7 提炼，不复制全文）。
6. RTM 表格，16 行：`需求ID | 一句话说明（≤12 字）| 优先级 | 实现工作包(WP1–WP5) | 验收/测试用例ID | 状态(基线)`。CRQ-01~09 + NFR-01~07 全覆盖；CRQ-10 单独一行标"变更候选、不在基线"。测试用例 ID 用 `TC-<需求ID>-01` 这种格式，**每个需求至少 1 条**，仅 CRQ-05 需要 2 条（冲突/不冲突）。

## `docs/05-architecture.md` 要求（控制在 3 屏，表格优先）
1. 文件布局（固定，Dev 必须照此实现）：
   `src/main.py`（argparse 入口与命令分发）、`src/db.py`（连接与建表）、`src/auth.py`、`src/devices.py`、`src/requests.py`、`src/loans.py`、`src/stats.py`、`src/audit.py`；测试在 `tests/test_*.py`（unittest）。
2. 数据模型：表 `users / devices / requests / loans / audit_log`，每表列名、类型、约束、说明。必须体现：密码存 `password_hash`+`salt`（PBKDF2-HMAC-SHA256，不少于 10 万次迭代）；时间字段存 ISO 8601 字符串（UTC）；`requests` 有状态机 `pending/approved/rejected/cancelled`；`loans` 有 `due_at/returned_at`。**不要设计 waitlist 表**（不在基线）。
3. 冲突规则（CRQ-05 唯一判定口径，必须逐字明确）：
   - 时段按半开区间 `[start, end)` 判定；
   - 冲突条件：`new.start < existing.end AND new.end > existing.start`；
   - 只对同一 `device_id` 且状态为 `approved`（以及已借出的 `loans` 未归还）的记录判定；
   - `rejected/cancelled` 不占用；首尾相接（前一段 end == 后一段 start）**不算冲突**；
   - 审批通过时以数据库事务写入，冲突则返回退出码 4，不落任何状态变更。
4. CLI 契约表：命令、参数、必填/可选、输出（统一 JSON 到 stdout）、退出码。命令至少覆盖：`init-db`、`seed`（演示数据）、`login`、`device list`、`device search --name/--category/--from/--to`、`request submit|cancel|list|show`、`request approve|reject --reason`、`loan checkout|return`、`stats usage|overdue`、`audit list`。退出码统一：`0` 成功、`1` 业务拒绝（如无权限审批）、`2` 参数错误、`3` 未登录/角色不符、`4` 时段冲突。
5. 权限规则（NFR-04）：student 只能看/操作自己的申请；admin 可审批、登记借还、看统计；director 只读统计。给出"角色 × 命令"矩阵。
6. 统计口径（CRQ-07，公式写死）：
   - 借用次数 = 状态为 approved 的申请数；
   - 逾期率 = 逾期归还的借出记录数 ÷ 已归还借出记录数（无归还有效记录时返回 0）；
   - 设备利用率 = 该设备已批准借出时长合计 ÷ 统计区间时长（上限 1，超过按 1 记并在输出里标 `overbooked=true`）。
7. 审计日志（CRQ-08）：记录字段与必须记录的 6 类事件（登录、提交申请、批准、拒绝、借出、归还）。
8. 契约稳定性声明：Dev 不得改命令名、参数名、退出码、表结构；如需变更由 PM 走变更流程。

## 写作要求
- 中文、平实、表格优先；不要写示例代码大段实现，只写接口与字段。
- 不写测试代码（那是 QA 的活），只给 TC ID 与验收点。
- 不跑除 `Get-FileHash` 外的命令；不修改其他文件。
- 回执按模板：STATUS / DELIVERABLES / CHECKS / ASSUMPTIONS / OPEN_ISSUES。CHECKS 里如实写（若被权限拒绝就写被拒绝，不要编造通过）。
````

#### 05｜规划：WBS与风险质量计划

- 会话：`ses_e972c12dbffe4Fot0SK8t1Iti5`
- 角色：`ba-architect`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,970 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目 BA/架构师，任务 2.3–2.4（规划阶段）。上一轮你已交付 `docs/04-scope.md` 与 `docs/05-architecture.md`（现行有效，不要改）。本轮产出两份新文档。

## 只读输入
- `plan/tasks.csv`（**30 个任务的唯一清单**：id、阶段、名称、资源、人日、工期、前置、里程碑）
- `docs/04-scope.md`（范围、RTM、验收标准）
- `docs/05-architecture.md`（契约）
- `docs/02-charter.md` §4 成功标准、§7 制约
- `docs/01-business-case.md` §6 风险表 R1–R5

## 只写这两个文件
1. `docs/06-wbs.md`
2. `docs/09-risk-quality.md`

## `docs/06-wbs.md`（控制在 2.5 屏）
1. 一句话说明：WBS 编号与 `plan/tasks.csv` 的 `id` 一一对应，导入 MS Project 的 XML 在 `wbs/wbs.xml`（由 PM 生成），本文件是便于人读的说明与词典。
2. WBS 树（表格，30 行，按阶段分组）：`WBS | 任务 | 负责人 | 工期(天) | 前置 | 类型(管理/开发/验证)`。数值必须与 `plan/tasks.csv` 完全一致，不要自己改工期或人日。
3. WBS 词典：只写 8 条——5 个开发工作包 WP1–WP5（3.1/3.3/3.5/3.7/3.9），加 2.1 范围与RTM、2.6 成本基线、5.1 验收演示。每条 4 行以内：`工作包编号与名称 | 负责人 | 交付物 | 验收标准（引用 RTM 的 TC 编号）| 前置依赖`。人日不要重复写，注明"人日与预算见 `plan/tasks.csv` 与 `docs/08-cost.md`"。
4. 工作包与需求的对应关系（一表带过，WP1–WP5 ↔ CRQ/NFR），与 `04-scope.md` §6 保持一致。
5. 3–5 条说明：为什么这样分解（按交付物而非按角色）、控制账户（每个阶段）、开发包与验证包成对出现的原因。

## `docs/09-risk-quality.md`（控制在 2 屏）
### 风险登记表（8 行）
列：`ID | 风险 | 概率 | 影响 | 等级 | 应对 | 责任人 | 触发信号`。
- 保留 `01-business-case.md` 的 R1–R5 并沿用原编号，按需把应对写具体（例如 R1 对应 TC-CRQ-05-01/02）。
- 新增 3 条，建议方向：CRQ-10 变更获批后挤占关键路径（R6）、口令哈希与角色校验实现错误导致越权（R7）、演示数据与测试数据混用污染验收（R8）。可自行调整，但必须与前 5 条不重复。
- 等级用"高/中/低"，并给出 1–3 条"高风险应对预算来自应急储备 ¥2,000"的说明（不编具体金额分配）。

### 质量与测试计划
1. 质量目标：绑定章程 S2、S3（冲突必须拦住、测试全绿、无严重缺陷），不新增指标。
2. 测试层级与责任（表）：单元/集成（关键路径：登录→查询→申请→审批→借出→归还）/CLI 端到端（JSON 字段与退出码）/UAT 演示。写明 QA 写测试、Dev 只做自检。
3. 入口与出口准则：每个工作包进入 QA 的条件（代码落盘、`python -m py_compile` 通过、命令可运行）；通过条件（该 WP 的 TC 全过、无严重缺陷、无新增第三方依赖）。
4. 缺陷等级定义（严重/一般/轻微，各 1 行）：严重 = 数据错误或安全漏洞（越权、明文口令、冲突未拦住）；一般 = 命令行为与契约不符；轻微 = 输出格式/文案问题。
5. 质量检查点：每工作包 QA 一次、变更后回归一次、验收前一次全量；记录落在 `docs/evidence/`。
6. 一句"质量成本"说明：返工计入成本偏差，不通过则不进入下一包。

## 硬要求
- 只写这两个文件；不改 `plan/tasks.csv`、不改上一轮文档；不跑除 `Get-FileHash`/`glob`/`grep` 外的命令。
- 所有引用用文件路径 + 章节号，不复述大段内容。
- 回执按模板：STATUS / DELIVERABLES / CHECKS / ASSUMPTIONS / OPEN_ISSUES。CHECKS 写真实结果（被拒绝也如实写）。
````

#### 06｜规划基线评审

- 会话：`ses_e9724a577ffeg7bo5aIKrXLEWX`
- 角色：`ccb-sponsor`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,434 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目发起人兼 CCB。本次做**规划基线评审**（关口 M2），只审"范围/进度/成本三基线是否可以冻结"，不评审实现细节。

## 决策包（只读这些文件，不要通读仓库）
- `docs/04-scope.md`（范围说明书 + RTM，17 行：16 条基线 + CRQ-10 变更候选）
- `docs/05-architecture.md`（架构与 CLI 契约：8 个模块、5 张表、冲突规则 7 条、16 条命令、退出码 0–4、统计口径）
- `docs/06-wbs.md`（30 条 WBS + 8 条词典）
- `docs/07-schedule.md`（CPM 18.75 天、关键路径 21 任务、CCPM 9.38+4.69=14.06、变更预留 1,675）
- `docs/08-cost.md`（BAC 15,800 = 25 人日；应急 2,000；管理储备 1,900；EV 规则）
- `docs/09-risk-quality.md`（R1–R8、测试层级、缺陷等级）
- `plan/tasks.csv`（唯一数据源，30 行）

## 需重点核的 6 条
1. **范围边界**：CRQ-10 是否被严格排除在基线外（只出现在"变更候选"处），有没有把候补通知/自动递补偷带进来。
2. **追溯完整性**：RTM 16 条基线需求是否每条都有 WP 与 TC；NFR-01/NFR-07 这类"全局"需求是否也有归属，而不是空着。
3. **进度可行性**：CPM 18.75 天 ≤ 20 天；关键路径是否真的串起启动→规划→开发链→收尾；CCPM 的 9.38+4.69=14.06 是否算对（各任务砍 50%，PB 为砍掉总量的一半）；变更预留 1,675 是否在管理储备 1,900 之内。
4. **成本一致性**：25.0 人日 × 日薪 = 15,800；+2,000 应急 = 17,800；+1,900 管理储备 = 19,700；三者是否与章程 §2 完全一致；§2 分阶段 1,550+3,650+8,700+800+1,100 是否等于 15,800。
5. **契约可测性**：冲突规则、退出码、统计公式是否足以让 QA 写出确定性的测试；有没有"看情况""视实现而定"这类模糊表述。
6. **风险与质量**：R1–R8 是否覆盖关键风险（冲突判定、变更挤占关键路径、越权/明文口令、数据混用）；缺陷等级是否能让 QA 判 PASS/FAIL。

## 结论只能是
`APPROVE` / `APPROVE WITH CONDITIONS` / `REJECT` / `DEFER`。
- 若要带条件，最多 4 条，每条必须可验证（指向文件+章节+数字或下一步动作），且不得要求重写整份文档。
- 允许你在结论里明确"进入执行后禁止再改基线数字，除非走 CR"。

## 回执格式
DECISION / SUBJECT / RATIONALE（≤5 条，引用文件与数字）/ CONDITIONS（无则 none）/ BUDGET（计划/已发生/上限/偏差，已发生指启动阶段实际 ¥1,721 vs 计划 ¥1,550）/ OPEN_ISSUES（只列真正未闭合项）。
不要修改文件，不要执行命令。
````

### 3.3 执行阶段

#### 07｜WP1 账户与角色权限

- 会话：`ses_e970f9598ffeyFzo7fFg5ObW5V`
- 角色：`dev-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 2,390 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 Dev，执行工作包 **WP1 账户与角色权限**（WBS 3.1，1.75 人日）。这是第一个工作包，要建起项目骨架。

## 必读（只读这三份，不要通读仓库）
- `docs/05-architecture.md` —— 唯一契约。重点：§1 文件布局、§2 数据模型（5 张表的字段/类型/约束）、§4 CLI 契约（命令/参数/输出/退出码 0–4）、§5 角色×命令矩阵。**命令名、参数名、退出码、表结构一律不得改动。**
- `docs/04-scope.md` §6 —— RTM，本包对应 TC-CRQ-01-01、TC-NFR-01-01、TC-NFR-03-01、TC-NFR-04-01。
- `docs/10-work-packages.md` —— WP1 卡片（做什么/不做什么/退出标准）。

## 本包只做这四件事
1. `src/db.py`：连接（`--db` 参数或环境变量 `DEVICELOAN_DB`，默认 `data/deviceloan.db`，目录不存在则创建）、`PRAGMA foreign_keys=ON`、建 5 张表的 DDL（严格按契约 §2：users / devices / requests / loans / audit_log）、事务上下文管理器（异常回滚）。
2. `src/auth.py`：PBKDF2-HMAC-SHA256（≥100,000 次迭代，16 字节随机盐，存 salt 与 hash 的十六进制）、口令校验、`login` 写 `data/session.json`（username/role/created_at）、读会话、角色校验辅助函数（供后续包复用）。
3. `src/audit.py`：只做**写**审计（`log(conn, actor, action, target, result, detail)`，与业务同一事务）；审计查询留给 WP5。
4. `src/main.py`：argparse 骨架 + 统一 JSON 输出 + 退出码映射。**本包只注册 3 个子命令**：`init-db`、`seed`、`login`。不要提前注册 request/device/loan/stats/audit 子命令（未实现的命令不应存在）。

## seed 的数据（QA 会照此验收）
- 用户 8 个：`student1`…`student6`（role=student）、`admin`（role=admin）、`director`（role=director）；口令统一 `Passw0rd!`，只存盐与哈希，**任何表里都不得出现明文**。
- 设备 20 台：虚构名称与类别（如 显微镜/示波器/投影仪/笔记本），字段按契约 §2 填，状态为可借。
- `init-db` 幂等（重复执行不报错）；`seed` 若 users 已有数据返回退出码 1 并提示已初始化。
- 时间字段一律 ISO 8601 字符串（UTC，形如 `2026-10-23T08:00:00Z`）。

## 硬约束
- 只用标准库（argparse/sqlite3/hashlib/os/sys/json/datetime/secrets），零第三方依赖。
- 每条命令成功时 stdout 输出单行 JSON（UTF-8，`ensure_ascii=False`）；失败时 `{"error":"<code>","message":"..."}` 且退出码按契约（0 成功 / 1 业务拒绝 / 2 参数错误 / 3 未登录或角色不符 / 4 时段冲突）。
- 不写测试（QA 负责）、不写文档、不改 `docs/` 与 `plan/` 下任何文件。
- 代码风格朴素：函数短、无防御性过度包装、无日志框架、无配置类。

## 必须实际跑（Windows / PowerShell）
```
python -m py_compile src/db.py src/auth.py src/audit.py src/main.py
python src/main.py init-db
python src/main.py seed
python src/main.py login --username admin --password Passw0rd!
python src/main.py login --username admin --password wrong      # 期望退出码 1
python src/main.py login --username nobody --password Passw0rd! # 期望退出码 1
```
另外用 sqlite3 查一次：`select count(*) from users;`（应为 8）、`select count(*) from devices;`（应为 20）、并确认 users 表里没有 `Passw0rd!` 明文（如 `select * from users where password_hash like '%Passw0rd%';` 应为 0 行）。

## 回执格式
STATUS / WBS_ID / FILES（逐个文件一句话职责）/ COMMANDS_RUN（命令 + 实际输出摘要 + 退出码）/ ACCEPTANCE（逐条 TC 是否满足及证据）/ DEVIATIONS（无则 none）/ OPEN_ISSUES。
不要编造命令结果；失败就如实写失败与原因。
````

#### 08｜QA1 验收账户与权限

- 会话：`ses_e970d14d7ffeslAxDrBWrQnodn`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,776 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 QA，独立验收工作包 **WP1 账户与角色权限**（QA 包 WBS 3.2）。Dev 已完成并自检，你不得修改产品代码，只写测试与证据。

## 必读
- `docs/05-architecture.md` §1（文件布局）、§2（5 张表字段与约束）、§4（CLI 契约与退出码 0–4）、§5（角色×命令矩阵）
- `docs/04-scope.md` §6（RTM：CRQ-01、NFR-01、NFR-03、NFR-04 及 TC 编号）
- `docs/10-work-packages.md` 的 WP1 卡片（验收标准与退出标准）
- 现有实现：`src/db.py`、`src/auth.py`、`src/audit.py`、`src/main.py`（只读）

## 已知情况（来自 Dev 回执，需你复核而非采信）
- 口令 PBKDF2-HMAC-SHA256 120,000 次迭代，盐 16 字节；seed 生成 8 用户（student1–6 / admin / director，口令均 `Passw0rd!`）与 20 台设备。
- 当前只注册了 `init-db`、`seed`、`login` 三个子命令，因此 **TC-NFR-04-01 无法用 CLI 端到端验**（无 admin 专属命令可调）。你的处理方式：写一个 unittest 直接调用 `auth` 的角色判定函数（如 `has_role`）验证 student 对 admin 操作返回 False / 抛权限错误，并在证据里注明"端到端回归由 WP3 完成"。

## 你要做的事
1. 写测试 `tests/test_wp1_auth.py`（unittest，标准库），覆盖：
   - `init-db` 幂等；`seed` 生成 8 用户 + 20 设备；重复 `seed` 退出码 1
   - `login` 成功返回 role 正确；错误口令 / 不存在用户退出码 1；缺参数退出码 2
   - 会话文件 `data/session.json` 含 username/role，**不含任何口令字段**
   - 数据库中无明文口令（查 `password_hash`/`salt` 不含 `Passw0rd`，并对库文件做一次字节扫描）
   - 无第三方依赖：解析 `src/*.py` 的 import，只允许标准库白名单
   - 角色判定单元测试（对应 TC-NFR-04-01，注明端到端待 WP3）
2. **隔离测试库**：所有 CLI 调用都加 `--db <临时路径>`（或设 `DEVICELOAN_DB`），不要污染 `data/deviceloan.db`；测试结束清理临时文件。
3. 跑测试并记录真实输出：`python -m unittest discover -s tests -v`（或直接跑该文件）。
4. 写证据 `docs/evidence/qa-wp1.md`：命令、实际输出摘要、逐条 TC 结论（PASS/FAIL）、发现的问题（含严重等级：严重/一般/轻微）、结论 PASS/FAIL/BLOCKED。

## 判定口径
- 只按契约判，不按"看起来能跑"判；契约没写的行为不算缺陷，但要在证据里记为"契约未规定"。
- 任一 TC FAIL 或存在严重缺陷 → 结论 FAIL，列出可复现步骤；不得自行改代码"顺手修好"。
- 允许轻微问题（如 JSON 字段顺序、错误码文案）存在，但必须列出。

## 硬约束
- 只写 `tests/` 与 `docs/evidence/qa-wp1.md`；不改 `src/`、`docs/` 其他文件、`plan/`。
- 命令只用 `python`，不装包、不联网。
- 回执：STATUS / WBS_ID / TESTS（文件与用例数）/ RESULT（PASS/FAIL/BLOCKED）/ TC_RESULTS（逐条）/ DEFECTS（ID、等级、复现、期望 vs 实际）/ NOTES。所有输出如实，禁止编造。
````

#### 09｜WP2 设备目录与查询

- 会话：`ses_e9700e8f3ffeFVYPwNvEkMsT9c`
- 角色：`dev-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：3 条，共 3,443 字

**用户消息 1 / 共 3（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 Dev，执行工作包 **WP2 设备目录与查询**（WBS 3.3，1.25 人日）。前一包 WP1 已完成并通过 QA（`src/db.py`/`auth.py`/`audit.py`/`main.py` 已有 init-db/seed/login）。

## 必读（只读）
- `docs/05-architecture.md` §1 文件布局、§2 数据模型（devices 表字段）、§3 冲突规则（时段判定口径）、§4 CLI 契约（`device list` / `device search` 的参数与输出）、§5 权限矩阵
- `docs/04-scope.md` §6：本包对应 TC-CRQ-02-01、TC-NFR-02-01
- `docs/10-work-packages.md` WP2 卡片
- 现有代码：`src/main.py`（看命令如何注册与输出）、`src/db.py`、`src/auth.py` —— 只读，按现有风格扩展

## 本包只做这些
1. 新建 `src/devices.py`：
   - `list_devices(conn, category=None, status=None)`：按类别/状态过滤，按 `code` 升序。
   - `search_devices(conn, name=None, category=None, start=None, end=None)`：名称模糊匹配（`LIKE %name%`）、类别精确；给定时段时计算 `available` 与该时段冲突的已批准借用数量 `conflicts`。
   - 时段判定严格按契约 §3：半开区间 `[start,end)`，`new.start < existing.end AND new.end > existing.start`；只统计 `requests.status='approved'` 与未归还的 `loans`；首尾相接不算冲突。
2. 在 `src/main.py` 注册两个子命令（**只加这两个**，不要提前注册 request/loan/stats/audit）：
   - `device list [--category X] [--status available|borrowed|unavailable]`
   - `device search [--name X] [--category Y] [--from ISO] [--to ISO]`
   - `--from`/`--to` 必须成对出现，否则退出码 2。
3. 权限（契约 §5）：`device list` 与 `device search` 对未登录用户是否放行，按契约写；若契约要求登录，则无会话返回 3。
4. 时间参数接受 ISO 8601（允许 `2026-11-03T08:00:00Z` 与 `2026-11-03T08:00:00` 两种写法），内部统一为 UTC 存储格式再比较。

## 硬约束
- 只用标准库；不改 `src/db.py` 的表结构（devices 表已存在）；不改 `src/auth.py` 的对外函数名。
- 输出单行 JSON 到 stdout；错误 `{"error":"<code>","message":"..."}`；退出码 0/1/2/3/4。
- 不写测试、不写文档、不改 `docs/` `plan/`。
- 已有 WP1 测试必须仍然通过（`python -m unittest discover -s tests`），不要改动 `tests/`。

## 必须实际跑（PowerShell）
```
python -m py_compile src/*.py
python -m unittest discover -s tests
python src/main.py init-db --db <临时库>
python src/main.py seed --db <临时库>
python src/main.py login --username admin --password Passw0rd! --db <临时库>
python src/main.py device list --db <临时库>
python src/main.py device search --name 显微 --db <临时库>
python src/main.py device search --from 2026-11-03T08:00:00Z --db <临时库>   # 期望 2
```
（`--db` 若你的实现是全局参数，放命令前后均可，但要与 WP1 保持一致；用临时库，不要污染 `data/deviceloan.db`。）

## 回执
STATUS / WBS_ID / FILES / COMMANDS_RUN（命令 + 输出摘要 + 退出码）/ ACCEPTANCE（TC-CRQ-02-01、TC-NFR-02-01 证据）/ DEVIATIONS / OPEN_ISSUES。禁止编造输出。
````

**用户消息 2 / 共 3（后续追加/返工）**

````text
返工一项（不扩大范围）：`device list --status` 的取值必须与契约 §2 的 `devices.status` 枚举一致，只允许 `available | maintenance | retired`。

- 去掉 `borrowed` 与 `unavailable` 两个别名及其映射逻辑；`--status` 直接作为 SQL 条件使用。
- 输出里的 `status` 字段仍返回数据库原值。
- 其余行为（search、时段冲突、权限、退出码）不变。

改完重跑：`python -m py_compile src/*.py`、`python -m unittest discover -s tests`（13 条必须仍全过）、以及 `device list --status maintenance`（临时库，期望 0 条且退出码 0）、`device list --status borrowed`（期望退出码 2）。

回执只写：STATUS / CHANGED / COMMANDS_RUN（真实输出）/ TESTS。
````

**用户消息 3 / 共 3（后续追加/返工）**

````text
返工一项（WP2 设备查询的冲突口径，小改）：未归还的 `loans` 目前按 `[checked_out_at, due_at)` 占位，导致"设备已逾期未还，仍可批准 due_at 之后的新申请"。改为：

- **未归还的借出（`returned_at IS NULL`）从 `checked_out_at` 起一直占用，没有结束时间**：任何查询/审批区间只要满足 `new.end > checked_out_at` 就算冲突（不再看 `due_at`）。
- 已归还（`returned_at` 非空）完全不计。
- `requests.status='approved'` 的判定不变（仍按申请自身的 `start_at/end_at` 半开区间）。
- 同一笔申请与其借出记录仍只计 1 次冲突。

改完重跑：`python -m py_compile`（显式列文件）、`python -m unittest discover -s tests`（34 条必须全过）。

额外自检（临时库）：插入一条 `checked_out_at=2026-11-03T08:00`、`due_at=2026-11-03T10:00`、`returned_at=NULL` 的 loan，然后 `device search --from 2026-11-04T08:00:00 --to 2026-11-04T10:00:00`，期望该设备 `conflicts=1, available=false`；把该 loan 的 `returned_at` 填上后重跑，期望 `conflicts=0`。

回执：STATUS / CHANGED / COMMANDS_RUN（真实输出）/ TESTS。
````

#### 10｜QA2 验收设备查询

- 会话：`ses_e96fd89b9ffeT5es5mMwrhOk5u`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,790 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 QA，独立验收 **WP2 设备目录与查询**（QA 包 WBS 3.4）。不得修改产品代码。

## 必读
- `docs/05-architecture.md` §2（devices 表、requests/loans 表字段）、§3（冲突判定 7 条）、§4（`device list` / `device search` 的参数、输出、退出码）、§5（权限矩阵）
- `docs/04-scope.md` §6：TC-CRQ-02-01、TC-NFR-02-01
- `docs/10-work-packages.md` WP2 卡片
- 实现只读：`src/devices.py`、`src/main.py`

## 已知情况（需复核，不采信）
- `device list [--category] [--status available|maintenance|retired]`；`device search [--name] [--category] [--from] [--to]`，至少给 1 个条件，`--from/--to` 成对。
- 设备状态只有三种枚举（不含 borrowed），这是上一轮返工的结果，专门验一下。
- 两个命令都要求登录，无会话退出码 3。

## 你要做的事
1. 写 `tests/test_wp2_devices.py`（unittest，标准库），覆盖：
   - `device list`：20 条、按 code 升序、category 过滤、三种 status 取值、非法 status 退出码 2
   - `device search`：按名称模糊、按类别、按时段；无任何条件 → 2；只给 `--from` → 2；`--to` 早于 `--from` → 2；非法 ISO → 2
   - **冲突判定**（本包核心）：用 sqlite3 直接向临时库插入 requests/loans 构造场景，逐条验契约 §3：
     a) approved 区间 [08:00,10:00) 查询 [09:00,11:00) → conflicts=1, available=false
     b) 首尾相接：approved [08:00,10:00) 查询 [10:00,11:00) → conflicts=0, available=true
     c) pending / rejected / cancelled 不占时段
     d) 已借出未归还的 loans 占时段；已归还（returned_at 非空）不占
     e) 同一笔 approved 申请 + 其对应未还 loan 只计 1 次冲突（不重复计数）
   - 权限：无会话 → 3；student 登录可查
   - 性能：seed 后 20 台设备、50 条借用记录量级下，单次 `device search` 进程内耗时 < 1 秒（用 `time.perf_counter` 包住函数调用即可，别把解释器启动算进去）
2. 全部用临时库（`--db` 或 `DEVICELOAN_DB`），测试后清理；不污染 `data/`。
3. 跑 `python -m unittest discover -s tests -v`，确认 WP1 的 13 条仍通过。
4. 写 `docs/evidence/qa-wp2.md`：命令与真实输出摘要、逐条 TC 结论、缺陷（等级 + 复现 + 期望 vs 实际）、结论 PASS/FAIL/BLOCKED。

## 判定口径
- 契约优先；实现自行扩展但契约没写的，记为"契约未规定"或缺陷（若与契约冲突则是缺陷）。
- 有严重缺陷或任一 TC FAIL → FAIL；不要顺手改产品代码。

## 硬约束
- 只写 `tests/` 与 `docs/evidence/qa-wp2.md`；不改 `src/`、其他 docs、`plan/`。
- 回执：STATUS / TESTS / RESULT / TC_RESULTS / DEFECTS / NOTES。
````

#### 11｜WP3 申请审批与冲突阻止

- 会话：`ses_e96e9c7a3ffeeT3Y5x1DPRb28D`
- 角色：`dev-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：2 条，共 3,391 字

**用户消息 1 / 共 2（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 Dev，执行工作包 **WP3 申请审批与冲突阻止**（WBS 3.5，2.0 人日）。这是全项目风险最高的包：CRQ-05 的冲突拦截是验收硬指标。

## 背景（重要）
前两个包因"契约取值/口径未自测"各触发返工，WP2 返工 2 次。本包要求**交付前用自检矩阵逐条跑过**（见文末），缺一条视为未完成。

## 必读（只读）
- `docs/05-architecture.md`：§2（requests 表、状态机、loans 表）、§3（冲突规则 7 条，含"未归还 loan 无结束占用"的新口径）、§4（6 条 request 命令的参数/输出/退出码）、§5（角色×命令矩阵）、§7（审计事件）
- `docs/04-scope.md` §6：TC-CRQ-03-01、TC-CRQ-04-01、TC-CRQ-05-01/02、TC-CRQ-09-01
- `docs/10-work-packages.md` WP3 卡片
- 现有代码：`src/main.py`（命令注册方式）、`src/devices.py`（冲突查询的现有写法，可复用其时间比较逻辑）、`src/audit.py`、`src/auth.py` —— 只读，按现有风格扩展

## 本包做什么
新建 `src/requests.py`，在 `src/main.py` 注册 6 个子命令（**只这 6 个**）：
1. `request submit --device <code|id> --from <ISO> --to <ISO> --purpose <text>`
   - 设备不存在 → 1；`from >= to` 或时间格式错 → 2；purpose 空 → 2；未登录 → 3
   - **不做冲突预检**（契约 §3 第 6 条）
   - 写 `request_submit` 审计
2. `request cancel --request-id <id>`：只能取消**本人**的 `pending`（否则 1）；非本人 → 1；不存在 → 1
3. `request list [--status X] [--all]`：student 只看自己；admin 加 `--all` 看全部；director → 3
4. `request show --request-id <id>`：本人或 admin；否则 1；含 `loan` 摘要（可空）
5. `request approve --request-id <id>`：
   - 非 admin → 3；不存在 → 1；非 pending → 1
   - **单事务**：写 `status='approved'`、`decided_by`、`decided_at` → 复查冲突 → 冲突则**整事务回滚**并退出码 4，stdout `{"error":"time_conflict","conflicts":[{"request_id":..,"start_at":..,"end_at":..}]}`
   - 写 `request_approve` 审计
6. `request reject --request-id <id> --reason <text>`：非 admin → 3；非 pending → 1；缺/空 reason → 2；写 `request_reject` 审计（detail 含 reason）

## 自检矩阵（交付前必须逐条真跑，回执里贴真实输出与退出码）
| 场景 | 期望 |
|---|---|
| A. student 提交申请 | 0，status=pending，库中 1 行 |
| B. submit 时 from>=to | 2 |
| C. submit 设备不存在 | 1 |
| D. 未登录 submit | 3 |
| E. admin 批准 A 的申请 | 0，approved |
| F. 再提交同设备同时段申请并被批准 | **4**，且该申请仍为 pending（回滚验证：查库） |
| G. 首尾相接：申请 [E 的 end, end+2h) 被批准 | 0（不算冲突） |
| H. student 取消他人申请 | 1 |
| I. student 取消自己的 pending | 0，cancelled |
| J. 取消已批准的申请 | 1 |
| K. director 调 request list | 3 |
| L. reject 不带 --reason | 2 |
| M. 重复批准同一申请 | 1 |
| N. 已批准申请占用期间，该设备另一 pending 被拒绝（reject） | 0 |
| O. 未归还 loan 从 checked_out_at 起占用（可直接在临时库插 loan 验证 approve 返回 4） | 4 |

## 硬约束
- 只用标准库；不改表结构（requests/loans/audit_log 已在 `db.py` 建好）；不改 `auth.py`/`devices.py` 的对外函数签名。
- 冲突判定必须与 `devices.py` 的查询侧口径一致（半开区间、approved + 未还 loan 无结束占用、同一申请与借出只计一次）。
- 单行 JSON 输出；退出码只用 0/1/2/3/4；错误格式 `{"error":"<code>","message":"..."}`。
- 不写测试、不改 `docs/` `plan/` `tests/`；已有的 34 条测试必须仍全过。

## 必跑命令
```
python -m py_compile src/db.py src/auth.py src/audit.py src/devices.py src/requests.py src/main.py
python -m unittest discover -s tests
```
外加自检矩阵 A–O，全部用**临时库**（`--db` 或 `DEVICELOAN_DB`），不要动 `data/deviceloan.db`。

## 回执
STATUS / WBS_ID / FILES / SELF_CHECK（A–O 表格：场景、命令、实际输出摘要、退出码、是否通过）/ COMMANDS_RUN / DEVIATIONS / OPEN_ISSUES。自检失败的项不得隐瞒；如果时间不够，优先保证 approve 的事务回滚与退出码 4 正确。
````

**用户消息 2 / 共 2（后续追加/返工）**

````text
返工一项（小改）：契约 §2 规定设备 `status` 为 `maintenance` / `retired` 时**不可借**，但当前 `request submit` 没拦。

要求：
1. `request submit`：设备状态不是 `available` → 退出码 1，`{"error":"device_unavailable","message":"设备当前不可借"}`。
2. `request approve`：审批时再查一次设备状态（提交后可能被改成维护），非 `available` → 退出码 1，同一错误码；此时不写 approved、不改任何状态。
3. 其它逻辑不动。

重跑：`python -m py_compile`（显式列文件）、`python -m unittest discover -s tests`（预期仍是 33 过 / 1 条 WP1 陈旧用例失败，那条由 QA 改），并用临时库验证：
- 把某设备 status 改为 maintenance，student 对它 submit → 1；
- 改回 available，submit → 0；再改成 retired，approve → 1 且库中仍为 pending。

回执：STATUS / CHANGED / COMMANDS_RUN（真实输出）/ TESTS。
````

#### 12｜QA3 验收申请审批

- 会话：`ses_e96e2c106ffeCWWn44qoe4y6wV`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 2,178 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 QA，独立验收 **WP3 申请审批与冲突阻止**（QA 包 WBS 3.6）。不得修改产品代码。

## 并发说明（重要）
PM 正在并行推进 WP4（改 `src/loans.py` 与 `src/main.py`）。为避免被测代码在你跑测试时变化，PM 已在 `%TEMP%\qa3-snap` 冻结了 WP3 完成时刻的 `src/` 与 `tests/`。

- **所有产品代码只从快照跑**：`cd $env:TEMP\qa3-snap` 再执行命令；不要把仓库里的 `src/` 当被测对象。
- 若你改了测试文件，先改仓库的 `tests/`（QA 拥有），再复制到快照后运行。
- 证据写在仓库 `docs/evidence/qa-wp3.md`（这个路径不会被 WP4 触碰）。

## 必读（仓库内，只读）
- `docs/05-architecture.md` §2（requests/loans 表与状态机）、§3（冲突规则，含"未归还 loan 无结束占用"）、§4（request 6 条命令）、§5（权限矩阵）、§7（审计事件）
- `docs/04-scope.md` §6：TC-CRQ-03-01、TC-CRQ-04-01、TC-CRQ-05-01/02、TC-CRQ-09-01
- `docs/10-work-packages.md` WP3 卡片

## 已知情况（需复核）
- Dev 自检 A–O 全过，含冲突回滚（退出码 4 且库内仍 pending）、首尾相接 0 冲突。
- 设备 `maintenance/retired` 现在 submit 与 approve 都返回 1（`device_unavailable`）。
- 已有 34 条测试中 1 条是 WP1 时期写的陈旧用例：`tests/test_wp1_auth.py::test_wp1_unimplemented_commands_not_registered` 断言 `request list` 未注册（期望 2）；WP3 按要求注册后它返回 3（未登录），该用例与新契约天然矛盾。

## 你要做的事
1. **修订那条陈旧测试**（只改测试，不改代码）：改成断言"WP3 之后 `request list` 已注册；无会话调用返回 3"，并顺带覆盖 TC-NFR-04-01 的端到端（student 调 admin 命令 → 3，例如 student 调 `request approve`）。改在仓库 `tests/test_wp1_auth.py`，然后把该文件复制进快照。
2. 写 `tests/test_wp3_requests.py`（unittest，标准库），至少覆盖：
   - 状态机：submit→pending；approve→approved；reject→rejected（带 reason）；cancel→cancelled（仅本人 pending）；终态不可再变（重复 approve/cancel → 1）
   - 冲突：重叠→退出码 4 且**回滚**（该申请仍 pending、decided_by/decided_at 为空、库里无新增 approved）；首尾相接→0；pending/rejected/cancelled 不占位；未还 loan 从 checked_out_at 起无限占位→4；归还后解除→0
   - 权限：student 不能 approve/reject（3）；director 不能 list/show（3）；student 只能看自己的 list、看他人 show → 1
   - 参数：from>=to → 2；purpose 空 → 2；reject 缺 reason → 2；request-id 不存在 → 1
   - 设备状态：maintenance/retired 时 submit → 1；submit 后把设备改 retired，approve → 1 且仍 pending
   - 审计：submit/approve/reject/cancel 各写一条，冲突回滚时**不留** approve 审计
3. 在快照跑全量：`python -m unittest discover -s tests -v`（应 35+ 条全过；任何失败要分辨是产品缺陷还是测试问题）。
4. 写 `docs/evidence/qa-wp3.md`：命令与真实输出、逐条 TC 结论、缺陷（等级/复现/期望 vs 实际）、结论 PASS/FAIL/BLOCKED。

## 判定口径
- 以契约为准；契约未写的行为记为"契约未规定"。
- 严重缺陷（冲突未拦住、回滚不彻底、越权）= FAIL。不要顺手改产品代码。

## 硬约束
- 不改 `src/`、不改其他 docs、不改 `plan/`；不装包、不联网。
- 回执：STATUS / TESTS / RESULT / TC_RESULTS / DEFECTS / NOTES。
````

#### 13｜WP4 借出归还与逾期

- 会话：`ses_e96e28b8cffeLtsvlk8kHEVp2Y`
- 角色：`dev-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：2 条，共 3,112 字

**用户消息 1 / 共 2（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 Dev，执行工作包 **WP4 借出、归还与逾期**（WBS 3.7，1.5 人日）。WP3 已完成（`src/requests.py` 已实现审批与冲突）。

## 背景
WP2 因未按契约自测被返工 2 次，WP3 漏了设备状态也被返工。本包同样要求交付前跑**自检矩阵**并把真实输出贴回执。

## 必读（只读）
- `docs/05-architecture.md` §2（loans 表字段与"一条已批准申请只能借出一次"、逾期唯一口径）、§4（`loan checkout` / `loan return` 的参数/输出/退出码）、§5（权限矩阵：admin 才能借还）、§7（审计事件 `loan_checkout` / `loan_return`）
- `docs/04-scope.md` §6：TC-CRQ-06-01
- `docs/10-work-packages.md` WP4 卡片
- 现有代码：`src/main.py`（命令注册）、`src/requests.py`（错误类与审计写法，可复用风格）、`src/audit.py` —— 只读，不改它们的逻辑

## 本包做什么
新建 `src/loans.py`，在 `src/main.py` 注册 2 个子命令（**只这 2 个**）：
1. `loan checkout --request-id <id>`
   - 仅 admin（否则 3）；申请不存在 → 1；申请状态非 approved → 1；该申请已有借出记录（`request_id` UNIQUE）→ 1（重复借出）
   - 写 `loans`：`request_id`、`device_id`、`user_id` 取申请的，`checked_out_at` = 当前 UTC 时间，`due_at` = 申请的 `end_at`
   - 输出 `{"loan_id":..,"request_id":..,"due_at":..}`；写 `loan_checkout` 审计
2. `loan return --loan-id <id>`
   - 仅 admin（否则 3）；借出记录不存在 → 1；已归还（`returned_at` 非空）→ 1
   - 写 `returned_at` = 当前 UTC；输出 `{"loan_id":..,"returned_at":..,"overdue":bool,"days_late":N}`
   - **逾期天数口径**（契约 §6）：`days_late = max(1, ceil((returned_at - due_at) 的秒数 / 86400))`，仅当 `returned_at > due_at`；否则 `overdue=false, days_late=0`
   - 写 `loan_return` 审计

## 自检矩阵（交付前逐条真跑，回执贴输出与退出码）
| 场景 | 期望 |
|---|---|
| A. admin 对 approved 申请 checkout | 0，loan 行 1 条，due_at = 申请 end_at |
| B. 同一申请再次 checkout | 1（重复借出） |
| C. 对 pending 申请 checkout | 1 |
| D. student 调 checkout | 3 |
| E. 未登录调 checkout | 3 |
| F. 未到 due_at 就 return | 0，overdue=false，days_late=0 |
| G. 超过 due_at 3.5 小时返回 | 0，overdue=true，days_late=1（ceil 向上取整） |
| H. 超过 due_at 2 天 1 小时返回 | 0，overdue=true，days_late=3 |
| I. 同一 loan 再次 return | 1 |
| J. 不存在的 loan-id return | 1 |
| K. student 调 return | 3 |
| L. 审计：checkout 与 return 各 1 条，result=ok | 通过 |
| M. checkout 后该设备时段冲突判定仍生效（未归还 loan 无结束占用） | 用 `device search --from <远期>` 查该设备，conflicts>=1 |

## 硬约束
- 只用标准库；不改表结构；不改 `requests.py`/`devices.py`/`auth.py` 的对外行为。
- 单行 JSON；退出码 0/1/2/3；错误 `{"error":"<code>","message":"..."}`。
- 不写测试、不改 `docs/` `plan/` `tests/`。
- 注意：QA 正在对 WP3 的快照写测试，**不要修改 `tests/`**；`src/main.py` 里不要动已有 request/device 命令的注册代码。

## 必跑
```
python -m py_compile src/db.py src/auth.py src/audit.py src/devices.py src/requests.py src/loans.py src/main.py
python -m unittest discover -s tests
```
（当前仓库测试可能因 QA 正在修订而短暂不稳定；若失败，判断是否与本包改动相关，与 loans 无关的失败如实说明即可。）
外加 A–M 自检，全部用临时库。

## 回执
STATUS / WBS_ID / FILES / SELF_CHECK（A–M 表）/ COMMANDS_RUN / DEVIATIONS / OPEN_ISSUES。
````

**用户消息 2 / 共 2（后续追加/返工）**

````text
返工一项（小改）：QA4 指出 `loan checkout` 没有复查设备状态。契约 §2 规定 `maintenance` / `retired` 的设备不可借——审批时查过，但审批后设备可能被改成维护，借出时仍需拦住。

要求：
1. `loan checkout`：对应设备的 `status` 不是 `available` → 退出码 1，`{"error":"device_unavailable","message":"设备当前不可借"}`；不写 `loans`、不写审计。
2. 其它逻辑不动（重复借出、申请状态校验、逾期计算、归还）。
3. 同步把 `docs/05-architecture.md` §2 或 §4 里"设备状态检查"的表述补一句：**submit / approve / checkout 三处都要查设备状态**（只改这一句，不动别的）。

重跑：
- `python -m unittest discover -s tests`（59 条必须全过）
- 临时库自检：把设备改为 maintenance，对已 approved 申请 checkout → 1 且 loans 表 0 行；改回 available 再 checkout → 0。

回执：STATUS / CHANGED / COMMANDS_RUN（真实输出）/ TESTS。
````

#### 15｜QA4 验收借出归还

- 会话：`ses_e96d92be6ffelCt5pna6AdA1u1`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,762 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 QA，独立验收 **WP4 借出、归还与逾期**（QA 包 WBS 3.8）。不得修改产品代码。

## 必读
- `docs/05-architecture.md` §2（loans 表：`request_id` UNIQUE、`checked_out_at`、`due_at`、`returned_at`；逾期唯一口径）、§4（`loan checkout` / `loan return` 参数与退出码）、§5（权限矩阵：仅 admin 可借还）、§7（审计事件 `loan_checkout` / `loan_return`）
- `docs/04-scope.md` §6：TC-CRQ-06-01
- `docs/10-work-packages.md` WP4 卡片
- 实现只读：`src/loans.py`、`src/main.py`
- 现有测试：`tests/test_wp1_auth.py`（14）、`tests/test_wp2_devices.py`（21）、`tests/test_wp3_requests.py`（14）

## 已知情况（需复核，不采信）
- Dev 自检 A–M 全过，含重复借出 1、pending 申请借出 1、逾期天数向上取整。
- 逾期口径：`days_late = max(1, ceil((returned_at − due_at) 秒数 / 86400))`，仅在 `returned_at > due_at` 时生效。

## 你要做的事
1. 写 `tests/test_wp4_loans.py`（unittest，标准库），覆盖：
   - checkout：对 approved 申请成功、`due_at` 等于申请 `end_at`、同一申请二次借出 → 1、对 pending/rejected/cancelled 申请 → 1、不存在的 request-id → 1、student → 3、未登录 → 3
   - return：正常归还 → 0 且 `overdue=false, days_late=0`；逾期 1 秒 → `days_late=1`（验证 ceil 与 max(1,·)）；逾期 3.5 小时 → 1；逾期 2 天 1 小时 → 3；二次归还 → 1；不存在的 loan-id → 1；student → 3
   - 逾期边界：恰好 `returned_at == due_at` → 不逾期（0）
   - 审计：checkout / return 各写 1 条 `ok`；失败路径（重复借出、重复归还）不得写 `ok`
   - 联动：checkout 后 `device search` 对后续任意时段应显示该设备 `available=false, conflicts>=1`；return 之后恢复 `available=true, conflicts=0`
   - 数据一致性：`loans.device_id` / `user_id` 与对应申请一致
2. 全部使用临时库与临时会话文件，不污染 `data/`。
3. 跑 `python -m unittest discover -s tests -v`（预期 49 + 新增，全过）。
4. 写 `docs/evidence/qa-wp4.md`：命令与真实输出、TC-CRQ-06-01 结论、缺陷（等级/复现/期望 vs 实际）、结论 PASS/FAIL/BLOCKED。

## 判定口径
- 契约优先；契约未写的行为记"契约未规定"。
- 逾期计算错误、权限越界、审计缺失、重复借出未拦住 = FAIL。

## 硬约束
- 只写 `tests/test_wp4_loans.py` 与 `docs/evidence/qa-wp4.md`；不改 `src/`、其他 docs、`plan/`、其它测试文件。
- 回执：STATUS / TESTS / RESULT / TC_RESULTS / DEFECTS / NOTES。
````

#### 17｜WP5 统计与审计

- 会话：`ses_e96cae91efferD65WQD4VPGP1p`
- 角色：`dev-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 2,579 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 Dev2（赶工，与另一个开发会话并行）。执行 **WP5 统计与审计**（WBS 3.9，2.25 人日）。项目已完成 WP1–WP4（登录/设备/申请审批冲突/借出归还），59 条测试全绿。

## 并行说明
另一个开发会话正在写**演示数据脚本**（`scripts/` 目录下，不碰 `src/`）。你只碰 `src/`，不要创建 `scripts/`，不要改 `tests/`。

## 必读（只读）
- `docs/05-architecture.md` §2（requests / loans / audit_log 表）、§4（`stats usage` / `stats overdue` / `audit list` 的参数、输出、退出码）、§5（权限矩阵）、**§6 统计口径（公式写死，必须逐条照做）**、§7（审计事件）
- `docs/04-scope.md` §6：TC-CRQ-07-01、TC-CRQ-08-01、TC-NFR-06-01
- `docs/10-work-packages.md` WP5 卡片

## 本包做什么
新建 `src/stats.py`，在 `src/main.py` 注册 3 个子命令（**只这 3 个**）：
1. `stats usage --from <ISO> --to <ISO>`（admin 或 director，仅只读；student → 3）
   - 输出 `{"range":{"from":..,"to":..},"overdue_rate":x,"devices":[{"device_id","borrow_count","utilization","overbooked"}]}`
   - 口径严格按 §6：借用次数按 `start_at ∈ [from,to)` 且 approved 计数；利用率 = 交集秒数 ÷ (to−from)，>1 截为 1 且 `overbooked=true`，保留 4 位小数；`to <= from` → 2
2. `stats overdue [--from <ISO>] [--to <ISO>]`（默认全期间；admin / director）
   - `{"items":[{"loan_id","request_id","device_id","due_at","returned_at","days_late"}]}`
   - 逾期记录：`returned_at > due_at`（已还逾期）与 `returned_at IS NULL AND 当前时间 > due_at`（未还逾期）；`days_late` 口径与 `loans.py` 一致（`max(1, ceil(秒/86400))`，未还的按"当前时间"算）
3. `audit list [--action X] [--user <name>] [--from ISO] [--to ISO] [--limit N]`（默认 50，**仅 admin**，director → 3）
   - 输出 `{"items":[{"at","actor_name","action","target_type","target_id","result"}]}`，按 `at` 倒序

## 自检矩阵（交付前逐条真跑，回执贴真实输出与退出码）
| 场景 | 期望 |
|---|---|
| A. admin 查 usage，区间内有 2 条 approved | borrow_count 正确，utilization 在 0–1 之间且保留 4 位 |
| B. 同一设备同区间有 2 条 approved 重叠 | utilization 截为 1，overbooked=true |
| C. `--to <= --from` | 2 |
| D. student 查 usage | 3 |
| E. director 查 usage | 0 |
| F. 有 1 条已还逾期 + 1 条未还逾期 | `stats overdue` 返回 2 条，days_late 分别正确 |
| G. 正常归还的记录 | 不出现在 overdue |
| H. audit list 默认 50 条、按时间倒序 | 通过 |
| I. audit list --action login --limit 2 | 只返回 2 条且都是 login |
| J. director 调 audit list | 3 |
| K. student 调 audit list | 3 |
| L. 未登录调任一 stats 命令 | 3 |

## 硬约束
- 只用标准库；不改表结构；不改 `requests.py` / `loans.py` / `devices.py` / `auth.py` 的对外行为；`main.py` 只追加注册与分发。
- 单行 JSON 输出；退出码 0/1/2/3；错误 `{"error":"<code>","message":"..."}`。
- 不写测试、不改 `docs/` `plan/` `tests/`。
- 已有 59 条测试必须仍全过。

## 必跑
```
python -m py_compile src/db.py src/auth.py src/audit.py src/devices.py src/requests.py src/loans.py src/stats.py src/main.py
python -m unittest discover -s tests
```
外加 A–L 自检（临时库，不要动 `data/deviceloan.db`）。

## 回执
STATUS / WBS_ID / FILES / SELF_CHECK（A–L 表：场景、命令、输出摘要、退出码、通过）/ COMMANDS_RUN / DEVIATIONS / OPEN_ISSUES。
````

#### 18｜演示数据脚本（瘦身版）

- 会话：`ses_e96ca9e74ffeQKIP0MANtqLDR8`
- 角色：`dev-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,408 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 Dev，负责 **演示数据脚本（WBS 3.11，瘦身后 0.5 人日）**。项目已完成 WP1–WP4，59 条测试全绿，CLI 命令：`init-db`、`seed`、`login`、`device list/search`、`request submit/cancel/list/show/approve/reject`、`loan checkout/return`。

## 并行说明
另一个开发会话正在写 `src/stats.py` 并改动 `src/main.py`（统计与审计命令）。**你只创建 `scripts/` 下的文件，绝对不要改 `src/`、`tests/`、`docs/`、`plan/`。**

## 目标（瘦身版，只做最小闭环，不做多场景堆量）
新建 `scripts/demo.py`（单文件，纯标准库，Windows 下可跑）：

1. 用 `argparse` 接受 `--db <路径>`（默认 `data/demo.db`）、`--force`（存在则删除重建）。
2. 调用项目自己的 CLI（`python src/main.py ...`，用 `subprocess`），按顺序生成一套可演示数据：
   - `init-db` + `seed`
   - 学生登录（用 `seed` 里的 `student1`，密码见 `src/db.py` 的 seed 实现，**自己去读代码确认，不要猜**）
   - 提交 1 条申请（选一台设备，时间取"明天 09:00–11:00"）
   - 管理员登录，批准该申请
   - 借出、再归还
3. 每步打印执行的命令与退出码；任一步非 0 立即停止并打印该步 stdout/stderr。
4. 结束时打印一份摘要：设备数、申请数、借出数、审计条数（直接查 SQLite 统计，只读）。
5. 脚本要可重复执行：默认库已存在时提示并退出码 2，加 `--force` 才重建。

## 自检（必须真跑，回执贴输出）
- `python scripts/demo.py --db %TEMP%\demo_check.db --force` → 退出码 0，摘要数字正确（申请 1 条 approved、借出 1 条已归还）
- 再跑一次不带 `--force` → 退出码 2 且有提示
- 再跑一次带 `--force` → 退出码 0
- 跑完 `python src/main.py request list --all --db %TEMP%\demo_check.db`（用 admin 会话）能查到那条申请

## 硬约束
- 只用标准库；不安装依赖；不改 `src/`、`tests/`、`docs/`、`plan/`。
- 时间用 ISO 8601（`YYYY-MM-DDTHH:MM:SSZ`）；脚本里的日期用"运行当天 + 1 天"动态计算，不要写死 2026 年。
- 不要把任何演示库写进仓库的 `data/`，自检一律用临时目录。
- 回执：STATUS / FILE / SELF_CHECK（命令 + 输出摘要 + 退出码）/ DEVIATIONS / OPEN_ISSUES。
````

#### 19｜QA5 验收统计与审计

- 会话：`ses_e96c58608ffeAOLp5VENc6QM5R`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,632 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 QA，独立验收 **WP5 统计与审计**（QA 包 WBS 3.10）以及**演示数据脚本**。不得修改产品代码。

## 必读
- `docs/05-architecture.md` §4（`stats usage` / `stats overdue` / `audit list` 参数与退出码）、§5（权限矩阵）、**§6 统计口径（公式写死）**、§7（审计事件）
- `docs/04-scope.md` §6：TC-CRQ-07-01、TC-CRQ-08-01、TC-NFR-06-01、TC-NFR-05-01
- 实现只读：`src/stats.py`、`src/audit.py`、`src/main.py`、`scripts/demo.py`
- 现有测试：`tests/` 下 4 个文件（59 条）

## 你要做的事
1. 写 `tests/test_wp5_stats.py`（unittest，标准库），覆盖：
   - **stats usage**：借用次数按 `start_at ∈ [from,to)` 计 approved；利用率 = 交集秒数 ÷ (to−from)，保留 4 位；>1 截为 1 且 `overbooked=true`；`to <= from` → 2；区间内无 approved → 全 0 且 `overdue_rate=0`
   - **逾期率**：已还逾期数 ÷ 已还总数；无已还记录时分母为 0 → 返回 0（不是报错）
   - **stats overdue**：已还逾期与未还逾期都要列出；`days_late` = max(1, ceil(秒/86400))；准时归还的不出现；未还但未到 due_at 的不出现
   - **权限**：usage/overdue —— student → 3，admin/director → 0；audit list —— student/director → 3，admin → 0；未登录 → 3
   - **audit list**：默认最多 50 条、`at` 倒序；`--action` / `--user` / `--from --to` / `--limit` 过滤正确；`--limit 0` 或负数 → 2
   - **演示脚本**：`python scripts/demo.py --db <临时库> --force` → 0，且摘要显示 申请 1 条 approved、借出 1 条已归还；不带 `--force` 重复执行 → 2；再次 `--force` → 0（用 `subprocess` 调，断言退出码与 stdout 关键字，不要依赖中文精确匹配）
2. 全部使用临时库与临时会话文件，不污染 `data/`。
3. 跑 `python -m unittest discover -s tests -v`（59 + 新增，全过）。
4. 写 `docs/evidence/qa-wp5.md`：命令与真实输出、逐条 TC 结论、缺陷（等级/复现/期望 vs 实际）、结论 PASS/FAIL/BLOCKED。

## 判定口径
- 契约优先；口径按 §6 公式逐条核对，不要"看着差不多就过"。
- 统计数字算错、权限越界、逾期判定错误 = FAIL。

## 硬约束
- 只写 `tests/test_wp5_stats.py` 与 `docs/evidence/qa-wp5.md`；不改 `src/`、`scripts/`、其他 docs、`plan/`、其它测试文件。
- 回执：STATUS / TESTS / RESULT / TC_RESULTS / DEFECTS / NOTES。
````

### 3.4 变更管理（CR-01 / CR-02）

#### 14｜CR-01 候补队列影响分析

- 会话：`ses_e96dd3439ffe2BsL2y5z09pei2`
- 角色：`ba-architect`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,598 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 BA。任务：为变更请求 **CR-01（候补队列）** 做影响分析，产出给 CCB 决策用的材料。**不要写产品代码**。

## 背景
- 项目：实验室设备借用管理系统（DeviceLoan MVP），Python 3.11 标准库 + SQLite CLI，零第三方依赖。
- 基线范围（`docs/04-scope.md` §6）已冻结 16 条需求；`00-customer-brief.md` §6 记录客户在演示后提出：设备不可用时学生可登记候补，管理员可查看候补名单；候补通知、自动递补**不在本次范围**。
- 当前进度：WP1–WP4 已开发（登录/设备查询/申请审批与冲突/借出归还），第 4 个工作包正在验收。基线：工期 18.75 天、成本 15,800 元、批准预算 17,800（含应急 2,000）、管理储备 1,900。
- 已预留：CR-01 若批准，预计 2.5 人日 / ¥1,475，从管理储备支出；实现排在验收之前。

## 必读
- `00-customer-brief.md`（§3 需求、§5 成功标准、§6 变更）
- `docs/04-scope.md`（§2 范围/不在范围、§6 RTM）
- `docs/05-architecture.md`（§2 数据模型、§3 冲突规则、§4 CLI 契约、§5 权限矩阵、§7 审计事件）
- `docs/07-schedule.md`（关键路径、缓冲）、`docs/08-cost.md`（预算与储备）
- `docs/09-risk-quality.md`

## 产出（只写这一个文件）
`docs/evidence/cr01-impact.md`，结构：

1. **变更描述与验收口径**：候补登记的触发条件（设备在该时段不可用？还是任意时段都可登记？给出你的推荐并说明理由）；去重规则；谁能看到什么（student 只看自己，admin 看全部）；与 CRQ-05 冲突判定的关系（候补**不占用**时段，不得影响 approve 判定）。
2. **影响面**：
   - 数据模型：是否需要新表？字段与唯一约束（给出建议的 DDL 要点，不写完整代码）
   - CLI：新增/修改哪些命令（参数、输出、退出码），是否影响已有 16 条命令
   - 权限矩阵、审计事件的新增项
   - RTM 与测试：新增需求编号（CRQ-11？）、对应 TC 编号
3. **方案对比**（至少 3 个）：
   - 方案 A 完整（登记 + 管理员名单 + 取消登记）
   - 方案 B 最小（登记 + 名单，不做取消/去重联动）
   - 方案 C 不实现 / 延后到二期
   每个方案给：人日、金额、对关键路径的影响（天）、风险。
4. **对基线的影响**：工期（18.75 → ?）、成本基线、是否动用管理储备、是否需要 CCB 批准。
5. **建议**：推荐哪个方案 + 一句话理由；给出**不做**的后果。
6. **给 CCB 的决策要点**：3–5 条，可直接勾选。

## 硬约束
- 只新建 `docs/evidence/cr01-impact.md`；不改 `docs/` 其他文件、`src/`、`tests/`、`plan/`。
- 数字要与现有基线自洽：如需新增人日，必须说明换算（日薪 BA 600 / Dev 650 / QA 450）。
- 篇幅控制在 150 行以内，表格优先，不要写行业黑话。
- 回执：STATUS / FILE / RECOMMENDATION / ESTIMATE（人日、金额、工期影响）/ OPEN_ISSUES。
````

#### 16｜CR-01 变更裁定

- 会话：`ses_e96d6061bffe4u3TpeDUKDw8bs`
- 角色：`ccb-sponsor`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,424 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 CCB（变更控制委员会）/ 发起人代表。裁定变更请求 **CR-01 候补队列**。只做裁定，不写代码、不改文件。

## 决策包（请自行阅读，勿采信本段摘要）

1. 客户诉求：`00-customer-brief.md` §6 —— 设备不可用时学生可登记候补，管理员可看候补名单；候补通知与自动递补不在范围。
2. 影响分析：`docs/evidence/cr01-impact.md` —— 三个方案 A/B/C，BA 推荐方案 B（2.5 人日 / ¥1,475 / 关键路径 +1.0 天）。
3. 最新执行数据：`docs/evidence/stage3-log.md` —— 截至数据日期 12.75：EV 9,575、AC 11,035.50、PV 10,625、CPI 0.868、SPI 0.901、EAC 18,210.02、缓冲消耗 43.3%（黄区），已启动赶工（对 3.9 + 3.11 加派 Dev2，+758 元，缩短 0.87 天）。
4. 基线约束：`docs/02-charter.md`（预算/授权）、`docs/07-schedule.md` §5（缓冲规则）、`docs/08-cost.md`（应急储备与管理储备的使用边界：应急仅用于 R1–R8 已知风险，管理储备用于范围类变更）。
5. 验收口径：`docs/04-scope.md` §6（RTM 16 条基线需求）。

## 你必须自己核算的关键数字（不要直接采用别人给的结论）

- 不批准 CR-01、按已启动赶工执行：预测 EAC 与完工时间。
  参考：剩余计划工作量 = 15,800 − 9,575 = 6,225；赶工追加 758。
- 批准方案 B、按已启动赶工执行：BAC 由 15,800 变为 17,275（`cr01-impact.md` §4），再叠加赶工 758；预测 EAC 与完工时间。
- 判断：哪一个方案同时满足客户两条硬约束（20 个工作日内完成、修订成本 ≈ ≤19,700），哪一个会破。

## 裁定选项（必须选一个）

- **A 批准并本次实施**：接受工期与成本影响，必要时同步置换等量范围（须写明置换什么）。
- **B 有条件批准、延后实施**：承认需求成立并纳入产品待办/二期范围，但本次迭代不交付；写入范围登记，不动本次工期与成本基线。
- **C 拒绝**：需求不成立或成本不可接受，记录理由与二次提出的条件。

## 输出格式（严格按此，便于 PM 归档到 `docs/evidence/ccb-cr01.md`）

1. **裁定**：A / B / C（一句话结论）
2. **核算**：两种情形的 EAC 与完工天数（列出算式，标明是否满足 20 天与 19,700）
3. **理由**：3–5 条，指向具体证据
4. **附加条件**：若有，逐条写明可验证的条件（例如"若二期实施，须先…"）
5. **对基线的影响**：哪些基线文档需要升版、是否动管理储备/应急储备
6. **给客户的回复要点**：2–3 句，平实语言

约束：不得修改任何文件；不得假设未提供的测试结果；如果决策包内部有矛盾（例如影响分析用的缓冲读数与实际不符），必须指出并以最新数据为准。
````

#### 24｜CR-02 候补队列裁定

- 会话：`ses_e934a141fffeDTYdRZw7Lbw94y`
- 角色：`ccb-sponsor`
- 模型：`deepseek/deepseek-flash#high`
- 用户消息：1 条，共 907 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的变更控制委员会（CCB）与发起人代表。请只做评审与裁定，不要改文件、不要运行命令。

背景事实：
- 项目 DeviceLoan MVP 已按 16 条需求完成一期验收，EVM 数据已冻结（EV 15,800、AC 17,974.90、CPI 0.879、SPI 1.000），一期不再改动。
- 客户需求档案 §6 提出 CR-01 候补队列（CRQ-10：设备不可用时学生可登记候补，管理员可查看名单；通知、自动递补不在范围）。
- 原 CCB 裁定为“有条件批准、延后实施”，理由：本期实施需 2.5 人日 / ¥1,475 / 关键路径 +1.0 天，会把工期推到 20.91 天、成本逼近/超过 19,700，破两条硬约束（见 docs/evidence/cr01-impact.md、ccb-cr01.md）。
- 现在客户坚持要实际交付该变更。PM 提议开 CR-02：作为一期验收后的二期增量交付，不改一期范围基线、进度基线、成本基线、EVM 与验收结论；二期单独记 2.5 人日 / ¥1,475；范围只做“登记 + 名单”，不做通知、自动递补、取消候补。
- 验收口径沿用 cr01-impact.md 的 AC1–AC4：AC1 登记成功（退出码 0、库中 1 条 waiting、审计 waitlist_join）；AC2 同人同设备重叠时段重复登记拒绝（退出码 1、无新增）；AC3 候补不占位（approve 的冲突判定与有无候补记录无关）；AC4 可见性（admin 需 --all 看全部、student 只看本人、director 退出码 3）。

请输出一份可直接归档的裁定，控制在 300 字以内，包含：
1. 结论（批准 / 有条件批准 / 拒绝）；
2. 范围边界（做什么、不做什么）；
3. 对一期基线/EVM/验收的影响；
4. 二期成本与工期口径；
5. 2–4 条附加条件（如测试证据、文档升版、不预占一期储备等）。

只输出裁定正文，不要解释你的推理过程。
````

#### 25｜实现 WP6 候补队列

- 会话：`ses_e9349a8eeffeFWx7S5zpJ0YG7I`
- 角色：`dev-engineer`
- 模型：`deepseek/deepseek-flash#high`
- 用户消息：1 条，共 3,301 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
工作目录：D:\StudyJava\Project-Management\hwk1

实现一个工作包 WP6（CR-02 二期增量）：候补队列。只写产品代码，不写测试、不改文档、不改一期基线。用 Python 3.11 标准库，无第三方依赖，风格与现有 `src/` 一致。

先读这些文件，按现有模式实现：
- src/main.py（argparse 子命令、CLIError、JSON 输出、退出码）
- src/db.py（SCHEMA、transaction）
- src/requests.py（find_device、find_conflicts、权限与错误模式）
- src/audit.py、src/auth.py
- tests/test_wp3_requests.py（了解 CLI 调用与测试约定，但不要修改它）

## 需求（契约）

### 1. 数据表
在 `src/db.py` 的 SCHEMA 中新增：

```sql
CREATE TABLE IF NOT EXISTS waitlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('waiting','cancelled')) DEFAULT 'waiting',
    note TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_waitlists_device ON waitlists(device_id, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_waitlists_user ON waitlists(user_id);
```

`seed --reset` 清空表时，在 `requests` 之前加 `waitlists`（注意外键顺序）。不要改变 `seed` 的输出字段。

### 2. 新模块 `src/waitlist.py`
定义 `WaitlistError(Exception)`，属性 `code/error/message`，与 `RequestError` 同构。

`join(conn, user, device_ref, start, end, note=None)`：
- 只有 `student` 可登记；其他角色 → `WaitlistError(3, "forbidden", "仅学生可登记候补")`。
- 设备用 `requests.find_device` 查；不存在 → `(1, "device_not_found", "设备不存在")`。
- `note` 去空白；长度 > 200 → `(2, "bad_args", "备注不能超过 200 字符")`。
- 去重：同一 `user_id` + `device_id` + `status='waiting'` + 时段重叠（半开区间：`start_at < 新end AND end_at > 新start`）→ `(1, "duplicate_waitlist", "该设备该时段已有候补登记")`。
- `available_now`：设备 `status='available'` 且该时段没有已批准申请、没有未归还借出。可直接调用 `requests.find_conflicts(conn, device_id, 0, start, end)`，`available_now = (device["status"] == "available" and not conflicts)`。候补登记本身**不占用**时段，也**不因不可用而拒绝**。
- 事务内插入，`created_at = db.now_iso()`；审计 `audit.log(conn, user, "waitlist_join", ("waitlist", waitlist_id), "ok", {"device_id": ..., "start_at": ..., "end_at": ...})`。
- 返回 `{"waitlist_id": id, "status": "waiting", "available_now": bool}`。

`list_waitlists(conn, user, show_all=False, device_ref=None, status=None)`：
- `director` → `(3, "forbidden", "主任无权查看候补名单")`。
- `student` 且 `show_all=True` → `(3, "forbidden", "--all 仅管理员可用")`。
- `student` 只看本人；`admin` 只有 `show_all=True` 才看全部，否则只看本人（admin 不能登记，通常为空）。
- `--device` 支持设备编号或数字 id；查不到就返回空列表，不报错。
- `status` 由 argparse 限定为 `waiting` / `cancelled`。
- 输出按 `id` 升序，每项字段：`waitlist_id, device_id, user_id, start_at, end_at, status, created_at`。

### 3. CLI（src/main.py）
新增：

```
waitlist join --device DEV-001 --from 2026-11-02T08:00:00Z --to 2026-11-02T12:00:00Z [--note ...]
waitlist list [--all] [--device DEV-001] [--status waiting|cancelled]
```

- `join`：时间用 `devices.normalize_iso` 校验，非法或 `start >= end` → `CLIError(2, "bad_args", ...)`；调用 `waitlist.join`。
- `list`：调用 `waitlist.list_waitlists`。
- 在 `main()` 的异常处理里加 `except waitlist.WaitlistError`，按 `exc.code` 返回。
- 命令组与现有 `request`/`loan` 风格一致，支持 `--db`。

## 约束

- 不改 `requests.py` 的 approve/冲突逻辑；候补不占位是硬要求。
- 不改现有测试；不新增测试文件（QA 会写）。
- 不更新 docs。
- 完成后运行：`python -m unittest discover -s tests -v`，确认原 76 条全绿。
- 另跑几条手工冒烟（可用临时库）：seed、student 登录、waitlist join、重复 join、waitlist list、admin --all、director 拒绝，确认 JSON 与退出码。

返回执行回执：改了哪些文件、关键设计点、测试命令与结果、手工冒烟结果、遗留风险。不要贴大段代码。
````

#### 26｜WP6 候补队列验证

- 会话：`ses_e9346322effe4adk8YWADVbmuQ`
- 角色：`qa-engineer`
- 模型：`deepseek/deepseek-flash#high`
- 用户消息：1 条，共 2,321 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
工作目录：D:\StudyJava\Project-Management\hwk1

对 WP6（CR-02 候补队列二期增量）做独立验证。你可以改测试与写证据，**不得修改产品代码**（src/db.py、src/main.py、src/waitlist.py、src/requests.py 等）。如果发现产品缺陷，判 FAIL 并写清复现步骤，不要自行修复。

先读：
- `src/waitlist.py`、`src/main.py`（waitlist 命令组）、`src/db.py`、`src/requests.py`
- `tests/test_wp3_requests.py`（CLI 子进程测试模式、临时库、会话文件约定）
- `tests/test_wp1_auth.py` 第 20–40 行（LOCAL_MODULES 白名单）
- `docs/evidence/ccb-cr02.md`（AC1–AC4 验收口径）

## 任务 1：修一处测试白名单
`tests/test_wp1_auth.py` 的 `LOCAL_MODULES` 目前是硬编码集合，缺少新本地模块 `waitlist`，导致 `test_tc_nfr_01_01_no_third_party_imports` 误报。把 `"waitlist"` 加进该集合。这是测试侧白名单维护，不算放宽断言。

## 任务 2：新增 `tests/test_wp6_waitlist.py`
用与 `test_wp3_requests.py` 相同的模式：临时目录、临时 DB、`subprocess` 调 CLI、显式 `--db`、会话落临时目录。至少覆盖：

**AC1 登记成功**
- student1 登录，`waitlist join --device DEV-001 --from 2026-11-02T08:00:00Z --to 2026-11-02T12:00:00Z --note 课程实验`
- 退出码 0；JSON 含 `waitlist_id`、`status=waiting`、`available_now=true`
- 库中 `waitlists` 1 条 `waiting`；`audit_log` 中 `action='waitlist_join'` 1 条
- `waitlist list` 返回本人记录，字段齐全

**AC2 重复登记**
- 同人同设备重叠时段 10:00–11:00 → 退出码 1，`error=duplicate_waitlist`，`waitlists` 仍 1 条
- 首尾相接 12:00–14:00 → 退出码 0（半开区间不重叠）
- 另一学生同设备同时段 → 允许（去重只限本人）

**AC3 候补不占位**
- student2 提交 DEV-002 的 pending 申请；student1 对同时段登记候补；admin 批准该申请 → 退出码 0、状态 approved，不出现 `time_conflict`
- 再提交一个与已批准申请重叠的申请并由 admin 批准 → 仍应退出码 4（原冲突逻辑未被破坏）
- 对照：没有候补记录时，同样场景的 approve 结果一致

**AC4 可见性**
- student1 与 student2 各登记一条
- student1 `waitlist list` 只看到本人；student1 `waitlist list --all` → 退出码 3
- admin `waitlist list` 无 `--all` → 空列表；admin `--all` → 看到两条
- admin `waitlist list --all --device DEV-001` 过滤正确；`--device 1` 与编号等价
- director `waitlist list` → 退出码 3；admin/director `waitlist join` → 退出码 3

**边界**
- 非法时间、start>=end、note 超过 200 字符 → 退出码 2
- 设备不存在 → 退出码 1 `device_not_found`
- 设备已有批准申请占用时登记候补 → 成功但 `available_now=false`
- `seed --reset` 后 `waitlists` 清零，且 seed 输出字段不变

**NFR**
- 确认 `src/` 只 import 标准库与本地模块（白名单修好后全绿）

## 任务 3：运行与证据
- 运行 `python -m unittest discover -s tests -v`，记录总数与结果（原 76 + 新增）。
- 运行 `python tests/test_wp6_waitlist.py -v`，记录每条用例。
- 写 `docs/evidence/qa-wp6.md`：范围、环境、AC1–AC4 对照表、测试命令、通过数/失败数、发现的缺陷（如有）、结论 PASS/FAIL/BLOCKED。要短，表格优先，不贴大段代码。
- 不要改 `docs/04-scope.md`、`docs/05-architecture.md` 等文档（PM 负责）。

返回执行回执：改了哪些文件、测试统计、AC 逐条结论、失败项（如有）、证据文件路径。
````

### 3.5 收尾阶段

#### 20｜UAT 验收（阶段5）

- 会话：`ses_e96a4e697ffeO5OeOodcHfHJHd`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,313 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 QA，执行 **UAT 用户验收测试**（WBS 5.1）。不得修改产品代码。

## 目标
按客户成功标准与基线 RTM 做一次独立验收，产出可给客户签字的验收报告 `docs/evidence/uat.md`。

## 必读
- `00-customer-brief.md` §3（CRQ-01~10）、§4（NFR-01~07）、§5（成功标准）
- `docs/04-scope.md` §6（RTM，16 条基线需求与 TC 编号）
- `docs/05-architecture.md`（CLI 契约与权限矩阵）
- `docs/evidence/qa-wp1..wp5.md`（已有验收证据，作为引用，不重复造轮子）

## 你要做的事
1. 选一个干净的临时目录，跑 `python scripts/demo.py --db <临时库> --force`，确认演示链路可用（退出码 0，摘要合理）。
2. 按 RTM 16 条逐一验收。每条给出：需求 ID、验收方式（自动化用例编号 / 手工 CLI 命令）、实际结果、结论（PASS/FAIL）。
   - 自动化部分直接引用 `tests/` 下已有用例（73 条），说明哪条覆盖哪条需求；不要重复写测试。
   - 手工部分用 CLI 走一遍**客户视角**的主流程：查询设备 → 提交申请 → 管理员批准 → 借出 → 归还 → 查看统计 → 查看审计。
3. 检查成功标准：
   - CRQ-01~08 是否全部可演示
   - 冲突预约是否被阻止（现场再造一次重叠场景）
   - 自动化测试是否通过（跑一次 `python -m unittest discover -s tests`，记录真实数字）
   - 关键需求能否追溯到 WBS 与测试
   - 成本/工期是否在承诺内（引用 `docs/evidence/stage3-log.md` 最新 EVM 与 `docs/08-cost.md`；不要自己重算预算）
4. 跑一次 NFR-05 隔离检查：确认 `data/deviceloan.db` 与 `data/session.json` 的修改时间在你开始测试前后**没有变化**。
5. 写 `docs/evidence/uat.md`：
   - 验收环境与方法
   - 16 条需求逐条结论表
   - 成功标准逐条结论
   - 缺陷清单（无则写"无"）+ 遗留问题（引用 QA 各包的观察项）
   - 验收结论（建议通过 / 有条件通过 / 不通过）+ 客户签字栏（姓名与日期留 `【待填】`）

## 硬约束
- 只写 `docs/evidence/uat.md`；不改 `src/`、`scripts/`、`tests/`、`plan/`、其他 docs。
- 不联网、不装包；全部用临时库。
- 回执：STATUS / VERDICT / FAILED_ITEMS（若有）/ FILE / NOTES。
````

#### 21｜补 TC-NFR-07-01 用例

- 会话：`ses_e969d92ccffeMVvJ16UY0jHGhI`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 779 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
UAT 条件 C1：补一条与 RTM 编号同名的用例，关掉 TC-NFR-07-01 的追溯缺口。只做这一件事。

## 要求
新建 `tests/test_tc_nfr_07_01.py`（unittest，标准库），用例名与方法名都要带 `tc_nfr_07_01`，验证 **NFR-07：时间统一 ISO 8601**：

1. `device search --from/--to` 接受 `YYYY-MM-DDTHH:MM:SSZ` 与 `YYYY-MM-DDTHH:MM:SS` 两种写法，且在两种写法下对同一区间的冲突判定结果一致。
2. `request submit` 产出的 `start_at` / `end_at`、`loan checkout` 产出的 `due_at`、`loan return` 产出的 `returned_at` 都是 ISO 8601 字符串（正则 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`）。
3. 非法时间格式（如 `2026-13-01T00:00:00Z`、`not-a-date`）返回退出码 2。

用临时库与临时会话，不污染 `data/`。跑 `python -m unittest tests.test_tc_nfr_07_01 -v` 与 `python -m unittest discover -s tests`（应为 74 条全过）。

## 硬约束
- 只新建这一个测试文件；不改 `src/`、`scripts/`、`plan/`、其他 docs 与其他测试。
- 回执：STATUS / FILE / TESTS（真实数字）/ NOTES。
````

#### 22｜收尾追认：储备与遗留

- 会话：`ses_e969d66f7ffeBCMpOhWmQzJyxe`
- 角色：`ccb-sponsor`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,091 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
你是本项目的 CCB / 发起人代表。做**收尾前的追认**（不是新裁定），只审不写文件。

## 待追认事项（数据来自 UAT 与监控报告）

1. **成本超支动用管理储备**：截至数据日期 17.75，BAC 15,800、AC 16,794.90、EV 14,700、CPI 0.875、EAC 18,051.66（另有 17.25 数据点 EAC 18,635.93 的口径）。AC 已超 BAC 994.90，EAC 超批准预算 17,800 约 252–836 元（取决于取哪个数据点）。管理储备余额 1,500。请核定：批准动用的金额上限（按 EAC 上限 18,636 计算即 836），并确认剩余额度。
2. **CR-01 延后执行的闭环**：此前裁定"有条件批准、延后实施"，UAT 按 16 条基线验收。确认该裁定结案，不因验收而重新打开。
3. **NPV 组合敏感性**：`01-business-case.md` §5.4 记录压力情景回收期 12.6 个月，略超客户成功标准的"回收期小于 12 个月"（NPV 仍为正）。请判断这是否构成验收障碍，或作为已知偏差接受。
4. **UAT 有条件通过的三项条件**：C1 补 TC-NFR-07-01 用例（QA 正在做）、C2 客户使用须知（PM 写入 README）、C3 本追认。请确认 C3 的闭环条件。

## 必须自己核对的文件
- `docs/evidence/uat.md`（§5.2 遗留问题、§5.3 条件）
- `docs/evidence/stage4-monitor.md`（§3 预测、§4 储备）
- `docs/evidence/ccb-cr01.md`（CR-01 裁定与止损条款）
- `docs/08-cost.md`（储备表）
- `01-business-case.md` §5.3 / §5.4（NPV 与敏感性）

## 输出格式

1. **追认结论**：三项分别"追认 / 不追认（理由）"
2. **核定金额**：管理储备可动用上限、余额、记账口径（是否进 BAC）
3. **验收意见**：是否同意"有条件通过"，条件 C3 的闭环标准
4. **遗留事项**：必须带入二期或运维期的条目（不超过 6 条，按严重度排序）
5. **给客户的结论**：2–3 句

约束：不修改任何文件；不假设未提供的测试结果；如两个 EAC 口径冲突，选保守值并说明。
````

#### 23｜补 NFR-07 追溯用例

- 会话：`ses_e969964ecffejXXsf8HcFk3es4`
- 角色：`qa-engineer`
- 模型：`opencode/deepseek-v4.1-flash-free#high`
- 用户消息：1 条，共 1,057 字

**用户消息 1 / 共 1（首次派单）**

````text
You are a subagent spawned by another session.
只做一件小事：UAT 条件 C1 要求补一条与 RTM 编号同名的测试用例，覆盖 NFR-07（时间统一 ISO 8601）。产品代码已完成，73 条测试全绿。

## 产出
新建 `tests/test_tc_nfr_07_01.py`（unittest，只用标准库）。类名 `TCNFR0701Test`，其中至少一个方法名含 `tc_nfr_07_01`。

三条断言：
1. `device search --from 2026-11-03T08:00:00Z --to 2026-11-03T10:00:00Z`（带 Z）与 `--from 2026-11-03T08:00:00 --to 2026-11-03T10:00:00`（不带 Z）对同一设备返回相同的 `available` / `conflicts`。
2. `request submit` 的 `start_at`/`end_at`、`loan checkout` 的 `due_at`、`loan return` 的 `returned_at` 均匹配 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`。
3. 非法时间（`2026-13-01T00:00:00Z`、`not-a-date`）退出码为 2。

实现方式参考同目录已有测试（`tests/test_wp2_devices.py` 的临时库与 CLI 调用写法，直接用 `subprocess` 调 `src/main.py`，`--db` 指向 `tempfile.mkdtemp()`，会话文件用 `DEVICELOAN_SESSION` 指向临时路径）。管理员口令是 `Passw0rd!`（见 `src/main.py`），学生账号 `student1`。

## 必须
- 跑 `python -m unittest tests.test_tc_nfr_07_01 -v`（3 条通过）与 `python -m unittest discover -s tests`（应为 74 条全过），把真实数字写进回执。
- 只新建这一个文件；不改 `src/`、`scripts/`、`plan/`、其他测试与文档。
- 回执：STATUS / FILE / TESTS（真实数字）/ NOTES。如果做不到，直接说明卡在哪一步，不要留空。
````

## 4. 可复用模板

下面这份模板是从上述提示词里抽出来的最小骨架，替换花括号内容即可：

````text
你是本项目的 {角色}。执行 {任务编号} {任务名称}（{人日} 人日）。
只产出下面 {N} 个文件，不做其他事。

## 只读输入（不要通读仓库其他文件）
- {文件/章节，唯一口径}
- {参考模板/数据源}

## 只写这些文件（禁止写其它任何文件）
1. {输出文件 1}
2. {输出文件 2}

## 固定口径
- 项目/技术栈：{...}
- 预算/工期/范围：{...}
- 接口/退出码/公式：{...}
- 未确定项统一写 `【待填】`，不要编造。

## 验收与自检
- 对应 TC：{TC 编号}
- 必跑命令：{命令}
- 自检矩阵：{场景 → 期望退出码/输出}

## 硬约束
- 只改 {白名单}；不改 {禁止目录}。
- 不写测试/不写文档/不装包/不联网（按角色取舍）。
- 禁止编造命令输出；失败如实写。

## 回执
STATUS / FILES / COMMANDS_RUN / ACCEPTANCE / DEVIATIONS / OPEN_ISSUES
````

## 5. 使用后的几点观察

1. **写入白名单是最有效的约束**。BA 只写 `docs/`、Dev 只写 `src/`、QA 只写 `tests/` 与 `docs/evidence/`，三者的职责在文件层面就分开了，返工范围也可控。
2. **接口契约要由 BA 先冻结，Dev 的提示词只引用章节号**。例如 WP1–WP5 都写“按 `docs/05-architecture.md` §2/§4/§5，不得改命令名、参数名、退出码、表结构”，避免每个包各自解释需求。
3. **QA 的提示词要明确“不采信 Dev 回执，只按契约复核”**。QA1–QA5 都写了“已知情况（需复核，不采信）”，这能减少“开发者自证”的偏差。
4. **变更类提示词必须带数据日期和硬约束**。CR-01 的 CCB 提示词直接要求用最新 `stage3-log.md` 的 12.75 数据点重算，而不是采用旧影响分析里的缓冲读数；这是后来改判延期的重要原因。
5. **短任务也要给验收口径**。C1 的两次派发说明：只写“补一条用例”不够，还要写清当前真实测试总数、文件白名单、跑哪两条命令；否则子代理会围绕“73/74/76”这种数字反复确认。
6. **提示词长度不是问题，歧义才是问题**。这批提示词从 477 字到 3,301 字不等，平均约 1,697 字；长的提示词通常包含自检矩阵和契约引用，反而返工更少。

---

文档生成时间：2026-10-28。原始数据仍保留在 OpenCode 本地数据库中；如会话被清理，以本文件为准。

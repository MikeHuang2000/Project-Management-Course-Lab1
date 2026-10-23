# UAT 用户验收测试报告：实验室设备借用管理系统（DeviceLoan MVP）

| 项目 | 内容 |
|---|---|
| 文档编号 / 版本 | UAT-01 v1.0 |
| 对应 WBS | 5.1 验收演示与 UAT（`06-wbs.md` §1） |
| 验收依据 | `00-customer-brief.md` §3/§4/§5、`04-scope.md` §4（S1–S6）+ §6（RTM 16 条基线）、`05-architecture.md`（CLI 契约与权限矩阵） |
| 执行者 | QA（DeepSeek V4.1 Flash Free） |
| 日期 | 2026-10-23 |
| 被测对象 | 仓库工作副本 `src/`（8 模块）、`scripts/demo.py`、`tests/`（5 文件 73 条用例）；**只读，未修改任何产品与测试代码** |
| 结论 | **有条件通过**（无产品缺陷；3 项文档/口径条件见 §5.3） |

## 1 验收环境与方法

| 项 | 值 |
|---|---|
| 平台 | Windows（win32），PowerShell 控制台，输出以 UTF-8 捕获 |
| 运行时 | Python 3.11.9（MSC v.1938 64 bit） |
| 技术栈核对 | 仅标准库 + SQLite（TC-NFR-01-01 由 AST 扫描断言，见 §3） |
| 数据隔离 | 数据库 `C:\Users\Lenovo\AppData\Local\Temp\uat-wbs51-20261023-232420\uat.db`、`demo.db`；会话文件 `<同上目录>\session.json`（`DEVICELOAN_SESSION` 指向临时路径）。全程未使用仓库 `data/` |
| 自动化测试 | `python -m unittest discover -s tests`（唯一一次全量运行，不带 `-v`） |
| 手工验收 | 以客户视角按"查询 → 申请 → 审批 → 借出 → 归还 → 统计 → 审计"顺序跑 CLI，分 5 批执行（含冲突再造、越权与异常路径），逐条记录命令、退出码与 stdout |
| 不做的部分 | 未重算预算/NPV（按 PM 指示引用既有文档）、未重写测试、未装包、未联网 |

方法说明：自动化部分只**引用**既有 73 条用例，用 TC 编号与用例名对应；手工部分只补自动化难以体现的"客户视角闭环"与现场冲突场景。产品代码与测试代码零改动。

## 2 演示链路与自动化结果（原始数字）

### 2.1 演示脚本

```text
python scripts\demo.py --db <TEMP>\uat-wbs51-...\demo.db --force
  init-db  退出码 0 | seed 0 | login(student1) 0 | request submit 0 | login(admin) 0
  request approve 0 | loan checkout 0 | loan return 0
  摘要: 设备数 20 / 申请数 1（approved 1）/ 借出数 1（已归还 1）/ 审计条数 6
       申请 ID 1，借出 ID 1，时段 2026-10-24T09:00:00Z ~ 2026-10-24T11:00:00Z
DEMO_EXIT=0
```

结论：演示链路可用，退出码 0，摘要与 `04-scope.md` §3 的演示数据规模（20 台设备 / 8 用户）一致（8 用户由 `seed` 输出 `{"users": 8, ...}` 体现）。

### 2.2 自动化测试（全量，一次）

```text
python -m unittest discover -s tests
..................................
[TC-NFR-02-01] search_devices elapsed = 0.0021s (20 devices / 50 requests / 25 loans)
.......................................
----------------------------------------------------------------------
Ran 73 tests in 99.556s
OK
EXIT=0
```

**73 passed / 0 failed / 0 skipped**，与 QA5 记录的 73 条一致（WP1 14 + WP2 21 + WP3 14 + WP4 10 + WP5 14）。

### 2.3 隔离核对（NFR-05 落地检查）

| 文件 | 测试前（23:24:20） | 测试后（23:26:30） |
|---|---|---|
| `data/deviceloan.db` | 40960 B，`2026/10/23 21:28:11` | 40960 B，`2026/10/23 21:28:11` |
| `data/session.json` | 76 B，`2026/10/23 21:28:11` | 76 B，`2026/10/23 21:28:11` |

修改时间与大小完全一致，本轮 UAT（含演示脚本、全量测试、全部手工命令）**未写入仓库运行期文件**。

## 3 16 条基线需求逐条结论

自动化列中的用例均位于 `tests/`；手工列为本次 UAT 实际执行的命令（`--db` 指临时库）。

| 需求ID | 客户可感知的标准 | 验收方式（自动化 / 手工） | 实际结果 | 结论 |
|---|---|---|---|---|
| CRQ-01 | 登录后按角色使用系统 | `test_tc_crq_01_01_login_returns_correct_role`、`login_wrong_password_exits_1`、`login_unknown_user_exits_1`、`login_missing_args_exits_2`、`seed_creates_8_users_20_devices`；手工 `login`（student1–4 / admin / director 六个角色） | 六个角色登录均退出码 0 并返回 `{"user_id","username","role"}`；错误口令 1、未知用户 1、缺参 2 | PASS |
| CRQ-02 | 按名称、类别、可用时段查询设备 | `test_tc_crq_02_01_*`（11 条）；手工 `device search --category 显微镜 --from/--to`、`--name 示波`、未还借出与归还后各一次 | 显微镜 3 条全 `available:true`；示波 3 条；DEV-001 有未还借出时 `available:false, conflicts:1`，归还后恢复 `true/0` | PASS |
| CRQ-03 | 提交借用申请（用途 + 起止时间） | `test_tc_crq_03_01_submit_creates_pending_request`；手工 `request submit` 共 7 次（DEV-001 ×5、DEV-002、DEV-006） | 均退出码 0，返回 `{"request_id":N,"status":"pending"}`，时间归一化为 ISO 8601 `Z` | PASS |
| CRQ-04 | 审批或拒绝，拒绝必填原因 | `test_tc_crq_04_01_approve_pending_request`、`test_tc_crq_04_01_reject_records_reason`；手工 `request approve`（成功 5 次 / 冲突 2 次）、`request reject`（缺与带 `--reason` 各 1 次） | approve 0 并写 `decided_at`；`reject` 缺 `--reason` → 2；带原因 → 0 且 `request show` 中 `reject_reason:"设备已被占用"`、`decided_by:7` | PASS |
| CRQ-05 | 阻止同一设备同一时段重复批准 | `test_tc_crq_05_01_overlap_returns_4_and_rolls_back`、`test_tc_crq_05_02_back_to_back_allowed`、`test_pending_rejected_cancelled_do_not_occupy`、`test_unreturned_loan_blocks_later_slot_until_returned`；手工现场造重叠 2 次 | 见 §4.2：两次重叠审批均退出码 4 且库内无变更；首尾相接退出码 0 | PASS |
| CRQ-06 | 登记借出、归还，标记逾期 | `test_tc_crq_06_01_checkout_and_return_on_time`、`test_return_overdue_days_late`、`test_overdue_boundary_exact_due_at`、重复借出/归还 3 条；手工 checkout×3、return×4 | `due_at` 取申请 `end_at`；准时归还 `overdue:false, days_late:0`；`due_at=2026-10-20T10:00:00Z` 的记录归还时 `overdue:true, days_late:4`；二次归还 → 1 `already_returned` | PASS |
| CRQ-07 | 查看借用次数、逾期率、设备利用率 | `test_tc_crq_07_01_borrow_count_and_utilization`、`test_overdue_rate_formula`、`test_overdue_rate_zero_denominator`、`test_utilization_clamped_when_overbooked`、`test_overdue_list_returned_and_unreturned` 等 8 条；手工 `stats usage`、`stats overdue` | 12 月区间：DEV-001 `borrow_count:4, utilization:0.0194, overbooked:false`，`overdue_rate:0.0`；10 月区间 `overdue_rate:1.0`；`stats overdue` 列出 `loan_id 3, days_late 4` | PASS |
| CRQ-08 | 记录关键操作日志，便于追溯 | `test_tc_crq_08_01_audit_list_default_limit_and_order`、`test_audit_events_for_request_actions`、`test_tc_crq_06_01_*`（借还审计）；手工 `audit list --limit 20`、`--action request_reject`、`--action request_approve` | 一条完整主流程后可按 `at` 倒序查得 `login / request_submit / request_cancel / request_approve / request_reject / loan_checkout / loan_return` 七类记录，字段含 `actor_name/target_type/target_id/result` | PASS |
| CRQ-09 | 取消尚未批准的申请 | `test_tc_crq_09_01_cancel_only_own_pending`；手工 `request cancel --request-id 2` | 退出码 0，`{"request_id":2,"status":"cancelled"}`；`request show` 与列表同步为 cancelled；他人/非 pending → 1（自动化断言） | PASS |
| NFR-01 | 仅标准库 + SQLite | `test_tc_nfr_01_01_no_third_party_imports`（AST 扫描 `src/` 全部 import） | 差集为空，无第三方依赖；本轮 73 条测试未装包、未联网即可运行 | PASS |
| NFR-02 | 关键查询 < 1 秒 | `test_tc_nfr_02_01_search_under_one_second`（`time.perf_counter`，0.0021s）；手工 CLI 端到端 3 次 | 函数级 0.0021s；命令级（含解释器启动）109 / 109 / 122 ms，均远小于 1 秒 | PASS |
| NFR-03 | 密码不得明文存储 | `test_tc_nfr_03_01_no_plaintext_password_in_db`；手工字节扫描 `uat.db`、`demo.db` | 两个库 ASCII 字节流均不含 `Passw0rd`；`user_id/username` 正常可见（预期） | PASS |
| NFR-04 | 学生仅看/操作自己的数据，只有管理员能审批和统计 | `test_tc_nfr_04_01_student_sees_only_own_requests`、`test_permission_matrix_role_checks`、`test_tc_nfr_04_01_student_calling_admin_command_exits_3`；手工越权 5 次 | student `request list` 仅返回 `user_id:1` 的 2 条；student `audit list` → 3；director `request approve` → 3、`audit list` → 3；admin 可 `list --all`、审批、统计；admin `request submit` → 3 | PASS |
| NFR-05 | 测试数据与演示数据隔离，不写入真实个人信息 | `test_tc_nfr_05_01_demo_force_and_guard`；手工 §2.3 前后指纹 + 演示库 `seed` 用户名为虚构姓名（陈晓、李雷、王芳…） | `data/` 两个文件 mtime 与大小前后一致（21:28:11，40960 B / 76 B）；演示数据无真实个人信息字段 | PASS |
| NFR-06 | 关键操作写审计日志（六类） | `test_tc_nfr_06_01_audit_filters` + WP1–WP4 各包审计断言；手工按 `--action` 逐类检索 | 六类事件 `login / request_submit / request_approve / request_reject / loan_checkout / loan_return` 全部可查、`result:ok`、`target_type` 正确；失败登录记 `result:denied` | PASS |
| NFR-07 | 时间统一 ISO 8601、同一时区 | 无同名 TC 用例；由 `test_wp1_auth.py:125` 的正则断言 + 各用例内 ISO 字面量间接覆盖；手工核对全部输出 | 所有输出的时间字段均为 `YYYY-MM-DDTHH:MM:SSZ` 秒级 UTC；带 `+08:00` 偏移的输入被折算为 UTC（`--from 2026-12-10T16:00:00+08:00` 与 `T08:00:00Z` 结果一致） | PASS（覆盖方式为间接断言，见 §5.2 遗留 R-UAT-03） |

RTM 17 行中第 17 行 CRQ-10（候补队列）为变更候选，CCB 裁定"有条件批准、延后实施"（`docs/evidence/ccb-cr01.md`），不在本次验收范围，**判 N/A（延后至二期）**，与 `04-scope.md` §2/§6 一致。

## 4 成功标准逐条结论（`00-customer-brief.md` §5）

### 4.1 CRQ-01~08 全部可演示 — **满足**

8 条必须需求在 §3 中全部有 PASS 证据，且 §2.1 的演示脚本以一条命令串起"建库→播种→提交→批准→借出→归还"，退出码 0。

### 4.2 冲突预约被阻止 — **满足（现场再造）**

| 场景 | 命令 | 结果 |
|---|---|---|
| 未归还借出占位（DEV-001 借出未还，due 2026-12-20T12:00） | `request approve --request-id 4`（申请时段 2026-12-28T08:00–12:00） | **EXIT 4** `{"error":"time_conflict","conflicts":[{"request_id":3,"start_at":"2026-10-23T15:25:30Z","end_at":null}]}` |
| 同一申请失败后状态 | `request show --request-id 4` | `status:"pending"`、`decided_by:null`、`decided_at:null` → 整事务回滚生效 |
| 归还后再批 | `loan return --loan-id 2` → `request approve --request-id 4` | EXIT 0，`status:"approved"`（占用随归还解除） |
| 两条已批准申请重叠（#4 批准 12-28 08:00–12:00，申请 12-28 10:00–14:00） | `request approve --request-id 6` | **EXIT 4** `{"error":"time_conflict","conflicts":[{"request_id":4,"start_at":"2026-12-28T08:00:00Z","end_at":"2026-12-28T12:00:00Z"}]}` |
| 首尾相接（#3 为 12-20 08:00–12:00，申请 12-20 12:00–14:00） | `request approve --request-id 5` | EXIT 0，判定为不冲突 |

客户最关心的"到现场才发现冲突"在这一版被前置拦截，且失败后数据库无残留状态。

### 4.3 自动化测试通过、无严重缺陷 — **满足**

73 条全绿（§2.2）；本次 UAT 与 WP1–WP5 五份 QA 证据合计 **严重缺陷 0、一般产品缺陷 0**。

### 4.4 关键需求可追溯到 WBS 与测试用例 — **基本满足（1 处缺口）**

- 16 条基线需求在 `04-scope.md` §6 均挂了实现工作包（WP1–WP5）与 TC 编号，WBS `06-wbs.md` §1（3.1/3.3/3.5/3.7/3.9）与 §2 词典的 TC 清单与之逐条一致，无悬空工作包。
- 15 条需求的 TC 编号在 `tests/` 中都有**同名用例**（`test_tc_*` 共 37 个既有用例名，见 §3）。
- **缺口**：`TC-NFR-07-01` 没有同名用例，NFR-07 只由 `test_wp1_auth.py:125` 的一条正则断言与各用例的 ISO 字面量间接覆盖。属追溯文档与测试命名不一致，非产品缺陷，见 §5.2 R-UAT-03。

### 4.5 成本与工期在承诺内 — **满足（余量很薄）**

引用 `docs/evidence/stage3-log.md` 最新 EVM（数据日期 17.25 工作日）与 `docs/08-cost.md`，未自行重算：

| 指标 | 值 | 承诺 | 判定 |
|---|---|---|---|
| PV / EV / AC | 14,300.00 / 13,900.00 / 16,394.90 | — | — |
| CV / SV / CPI / SPI | −2,494.90 / −400.00 / 0.848 / 0.972 | — | — |
| EAC（按 CPI 外推） | 18,635.93 | ≤ 19,700（客户上限） | 满足 |
| 完工预测 | 18.92 天（含缓冲约 19.5 天） | ≤ 20 个工作日 | 满足 |
| 预算口径 | AC 已超 BAC（15,800）594.90，超出批准预算 17,800 的部分由管理储备/应急储备覆盖 | 需 CCB 追认 | 见 §5.2 R-UAT-04 |

### 4.6 NPV 与投资回收期 — **基准满足，组合敏感性有残留项**

引用 `docs/01-business-case.md` §5.3/§5.4：

- 基准：NPV ≈ **+39,397.59**（> 0），回收期 **9.3 个月**（< 12 个月）→ 满足。
- 组合敏感性（B1/B2 同时下降 25%）：NPV +24,352.14 仍为正，但回收期 **12.6 个月**，超出 12 个月上限约 0.6 个月。该结果已在商业论证 §5.4 中作为条件 2 的残留项提交 CCB/客户代表核定，**未核定前不改变推荐方案**。
- 判定：成功标准"回收期 < 12 个月"在基准情形满足；敏感性情形需客户确认前置假设（B1 替代比例 ≥ 2/3、B2 ≥ 1 次/年）。

## 5 缺陷清单与遗留问题

### 5.1 缺陷清单

**无。** 本次 UAT 未发现产品缺陷（0 严重 / 0 一般 / 0 轻微产品级缺陷）。所有实测退出码（0/1/2/3/4）与 `05-architecture.md` §4/§5 契约一致，JSON 字段与 §4 一致。

### 5.2 遗留问题（引用 QA 各包观察项 + 本次 UAT 新增）

| ID | 等级 | 描述 | 来源 | 处置建议 |
|---|---|---|---|---|
| R-UAT-01 | 中 | 登录失败不清空既有会话：先 `admin` 登录成功，再以 `student1` 错误口令登录（退出码 1），会话文件仍为 `{"role":"admin"}`，随后 `audit list` 仍以 admin 身份成功执行 | OBS-WP1-01（本次 UAT 复现） | 契约 §1 未规定失败路径；建议 BA 明确"失败登录是否清会话"，再由 Dev 收口。单机 CLI 场景风险可控，但演示时易被误读 |
| R-UAT-02 | 低 | 不带时区的时间输入按 UTC 解释：`--from 2026-12-10T08:00` 与 `T08:00:00Z` 等价；客户按北京时间填写会差 8 小时 | 本次 UAT 新增 | README/演示镜头中明确"输入一律 UTC，或使用 `+08:00` 偏移" |
| R-UAT-03 | 低 | `TC-NFR-07-01` 无同名用例，NFR-07 仅由内联正则断言覆盖（§4.4 缺口） | 本次 UAT 新增 | BA 在 RTM 注明"由内联断言覆盖"，或 QA 补一条 `test_tc_nfr_07_01_*`（不改产品代码） |
| R-UAT-04 | 低 | EVM 显示 AC 已超 BAC 594.90、EAC 18,635.93 超批准预算 17,800 达 836 元，需动用管理/应急储备 | stage3-log「累计」「纠偏决策」 | 收尾前由 CCB 出具储备动用追认，写入最终报告 |
| R-UAT-05 | 低 | 组合敏感性下回收期 12.6 个月略超 12 个月（NPV 仍为正） | `01-business-case.md` §5.4 | 客户确认前置假设，或接受该偏差并记录为条件 |
| R-UAT-06 | 低 | 设备检索不支持按资产编号：`device search --name DEV-001` 返回 `{"items": []}`、退出码 0（`--name` 只匹配设备名） | 本次 UAT 新增 | 契约未要求（CRQ-02 只写"名称/类别/时段"）；二期可加 `--code`，本期在 README 注明"按设备名检索" |
| R-UAT-07 | 低 | 单机单会话：会话文件全局唯一，同一台机器上不能同时保持学生与管理员两个身份；无并发多用户能力 | 契约 §1 | MVP 范围内，演示与使用须知中说明 |
| OBS-WP2-01 | 观察 | 无时段时 `device search` 的 `available` 等价于"设备级可借"，`conflicts` 恒为 0 | qa-wp2 §3 | BA 在契约 §4 补一句口径 |
| OBS-WP2-03 | 观察 | 无会话调用 `device list` 仍会创建库文件与 5 张表（退出码正确为 3） | qa-wp2 §3 | 如需"零副作用"由 PM 决策 |
| OBS-WP2-04 | 观察 | 参数校验先于会话校验（先 2 后 3），契约两条规则的优先级未写明 | qa-wp2 §3 | BA 明确优先级，不影响安全 |
| OBS-WP3-01 | 观察 | 唯一冲突源为未还借出时，`conflicts[].end_at` 输出 `null`（本次实测 `start_at` 为 `checked_out_at`） | qa-wp3 §5、本次 UAT | 契约补"开放占用 `end_at` 输出 null" |
| OBS-WP5-01 | 观察 | `overbooked` 在正常流程下不可达（审批冲突判定保证利用率 ≤ 1） | qa-wp5 §5 | 保留字段即可，不影响正确性 |
| OBS-WP5-02 | 观察 | `audit list --action <未知值>` 返回空列表、退出码 0（契约未规定枚举） | qa-wp5 §5 | 可接受 |

等级说明：**中** = 客户使用时可能产生误解、建议收尾前处理；**低/观察** = 记录在案、不阻塞验收。以上均**未削弱任何既有测试断言**，也未修改产品代码。

### 5.3 验收结论：**有条件通过**

产品层面 16 条基线需求全部验收通过、73 条自动化测试全绿、成功标准 6 条中 5 条满足、1 条（追溯性）有 1 处文档级缺口；未发现产品缺陷，客户主流程可完整演示。建议按"有条件通过"签字，条件如下：

| 条件 | 内容 | 责任方 | 完成标志 |
|---|---|---|---|
| C1 | 补 `TC-NFR-07-01` 的追溯口径（RTM 注明覆盖方式或补 1 条用例），使 S4 无悬空项 | BA / QA | **已闭环**：新增 `tests/test_tc_nfr_07_01.py`（3 条，覆盖带/不带 Z 等价、四类时间输出格式、非法时间退出码 2）；全量 76 条通过 |
| C2 | 书面确认三条使用须知：时间一律 UTC（或带 `+08:00`）、单机单会话、按设备名检索 | PM / 客户 | **已写入** `README.md` §使用须知；客户签字栏 `【待填】` |
| C3 | 确认 R-UAT-04/05（储备动用、组合敏感性回收期）与 CRQ-10 延后至二期 | CCB / 客户代表 | **CCB 侧已闭环**（`docs/evidence/ccb-closeout.md`）；客户代表确认栏 `【待填】` |

## 6 客户签字栏

| 项 | 内容 |
|---|---|
| 验收结论 | 有条件通过（条件 C1–C3 见 §5.3） |
| 客户方（实验中心）代表签字 | 【待填】 |
| 签字日期 | 【待填】 |
| 项目方（PM）签字 | 【待填】 |
| 签字日期 | 【待填】 |
| 备注 | 【待填】 |

## 7 证据可复现清单

| # | 命令 | 期望 |
|---|---|---|
| 1 | `python scripts/demo.py --db <临时路径>\demo.db --force` | 退出码 0，摘要 20 设备 / 申请 1（approved 1）/ 借出 1（已还 1）/ 审计 6 |
| 2 | `python -m unittest discover -s tests` | `Ran 73 tests` / `OK`，退出码 0 |
| 3 | `device search --name 显微镜 --from <起> --to <止>` | 3 台显微镜，`available` 反映是否有已批准申请或未还借出 |
| 4 | `request submit` → `request approve`（重叠时段） | 退出码 4 + `time_conflict`，`request show` 仍为 pending |
| 5 | `request approve`（首尾相接） | 退出码 0 |
| 6 | `loan checkout` → `loan return` | `due_at` = 申请 `end_at`；逾期时 `overdue:true`、`days_late ≥ 1` |
| 7 | `stats usage --from/--to`、`stats overdue` | `overdue_rate`、`borrow_count`、`utilization` 与 `05-architecture.md` §6 公式一致 |
| 8 | `audit list --action <六类之一>` | 六类事件可查，时间均为 ISO 8601 `Z` |
| 9 | `Get-ChildItem data` 前后对比 | 两个文件 mtime 与大小不变（NFR-05） |

未执行项（如需补证）：真实网络环境、超过演示规模的数据量、并发多用户——均超出 MVP 验收范围（`04-scope.md` §2/§5）。

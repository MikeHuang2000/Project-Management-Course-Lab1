# QA5 验收记录：WP5 统计与审计 + 演示数据脚本（WBS 3.10）

| 项目 | 内容 |
|---|---|
| 验收对象 | WP5：`stats usage`、`stats overdue`、`audit list`、`scripts/demo.py` |
| 契约依据 | `docs/05-architecture.md` §4（参数与退出码）、§5（权限矩阵）、§6（统计口径公式）、§7（审计事件）；`docs/04-scope.md` §6 TC-CRQ-07-01 / TC-CRQ-08-01 / TC-NFR-06-01 / TC-NFR-05-01 |
| 被测代码 | `src/stats.py`、`src/audit.py`、`src/main.py`、`scripts/demo.py`（**只读**，未做任何改动） |
| 测试代码 | 新增 `tests/test_wp5_stats.py`（14 条，标准库 unittest，子进程调 CLI） |
| 数据隔离 | 全部使用 `tempfile` 临时库 + 临时会话文件；临时库路径形如 `%TEMP%\qa-wp5-*`；仓库 `data/` 未被改动（见 §4） |
| 日期 | 2026-10-23 |
| 结论 | **PASS**（0 条产品缺陷；2 条口径/实现观察见 §5） |

## 1 执行的命令与真实输出

### 1.1 本包测试（单文件）

```text
$ python -m unittest tests.test_wp5_stats -v
test_audit_list_rejects_bad_limit ... ok
test_audit_permission_matrix ... ok
test_tc_crq_08_01_audit_list_default_limit_and_order ... ok
test_tc_nfr_06_01_audit_filters ... ok
test_tc_nfr_05_01_demo_force_and_guard ... ok
test_overdue_list_returned_and_unreturned ... ok
test_overdue_range_filter ... ok
test_overdue_rate_formula ... ok
test_overdue_rate_zero_denominator ... ok
test_stats_permission_matrix ... ok
test_tc_crq_07_01_borrow_count_and_utilization ... ok
test_usage_empty_range_is_all_zero ... ok
test_usage_rejects_to_not_after_from ... ok
test_utilization_clamped_when_overbooked ... ok
----------------------------------------------------------------------
Ran 14 tests in 30.005s

OK
```

首轮（同命令）为 13 ok / 1 FAIL，失败是**测试自身断言写错**：权限用例在构造 5 条审计后依次让 3 个角色 login，login 本身也写审计，故 admin 看到 8 条而非 5 条。断言改为 `>= 5` 后复跑通过（非产品缺陷）。

### 1.2 全量回归（仓库根目录，一次，不带 `-v`）

```text
$ python -m unittest discover -s tests
..................................
[TC-NFR-02-01] search_devices elapsed = 0.0022s (20 devices / 50 requests / 25 loans)
.......................................
----------------------------------------------------------------------
Ran 73 tests in 105.080s

OK
EXIT=0
```

`Ran 73 tests` / `OK` → **73 passed, 0 failed, 0 skipped**（既有 59 + 本包 14）。

### 1.3 TC-CRQ-07-01 现场：`stats usage`（临时库，cwd 同临时目录）

造数（每行 `CMD 参数 | EXIT n | stdout`）：

```text
CMD seed | EXIT 0 | {"users": 8, "devices": 20, "requests": 0, "loans": 0}
CMD login --username student1 --password Passw0rd! | EXIT 0 | {"user_id": 1, ..., "role": "student"}
CMD request submit --device DEV-001 --from 2027-01-02T00:00:00Z --to 2027-01-02T12:00:00Z --purpose lab | EXIT 0 | {"request_id": 1, "status": "pending"}
CMD request submit --device DEV-002 --from 2026-12-31T22:00:00Z --to 2027-01-01T02:00:00Z --purpose cross | EXIT 0 | {"request_id": 2, "status": "pending"}
CMD request submit --device DEV-003 --from 2027-01-03T00:00:00Z --to 2027-01-04T00:00:00Z --purpose toreject | EXIT 0 | {"request_id": 3, "status": "pending"}
CMD login --username admin --password Passw0rd! | EXIT 0 | {"user_id": 7, ..., "role": "admin"}
CMD request approve --request-id 1 | EXIT 0 | {"request_id": 1, "status": "approved", "decided_at": "2026-10-23T14:58:01Z"}
CMD request approve --request-id 2 | EXIT 0 | {"request_id": 2, "status": "approved", "decided_at": "2026-10-23T14:58:02Z"}
CMD request reject --request-id 3 --reason schedule | EXIT 0 | {"request_id": 3, "status": "rejected", ...}
```

统计区间 `[2027-01-01T00:00:00Z, 2027-01-11T00:00:00Z)` = 864000 秒：

```text
CMD stats usage --from 2027-01-01T00:00:00Z --to 2027-01-11T00:00:00Z | EXIT 0 | devices=20 overdue_rate=0
    range={"from": "2027-01-01T00:00:00Z", "to": "2027-01-11T00:00:00Z"}
    devices[前 6 台，完整 20 台见测试断言]=[
      {"device_id": 1, "borrow_count": 1, "utilization": 0.05,   "overbooked": false},
      {"device_id": 2, "borrow_count": 0, "utilization": 0.0083, "overbooked": false},
      {"device_id": 3, "borrow_count": 0, "utilization": 0.0,    "overbooked": false},
      {"device_id": 4, "borrow_count": 0, "utilization": 0.0,    "overbooked": false},
      {"device_id": 5, "borrow_count": 0, "utilization": 0.0,    "overbooked": false},
      {"device_id": 6, "borrow_count": 0, "utilization": 0.0,    "overbooked": false}]
```

核对：DEV-001 12h/10d = 0.05、借 1 次；DEV-002 `start_at` 在区间外 → 借出次数 0，但区间内交集 2h/10d = 0.008333… 取 4 位 = 0.0083；DEV-003 的申请被拒 → 0。区间内无借出记录 → `overdue_rate=0`。

`>1` 截断（正常流程不可达：`request approve` 会拦截同一设备时段重叠，无法通过 CLI 造出重叠 approved 申请，故在**临时库**直接插入 2 条重叠 approved 申请）：

```text
SQL 直接插入 2 条重叠 approved(DEV-001: 7d+7d=14d) + 1 条吃满区间(DEV-002: 10d)
CMD stats usage --from 2027-01-01 --to 2027-01-11 | EXIT 0
    devices[1..3]=[{"device_id": 1, "borrow_count": 2, "utilization": 1.0, "overbooked": true},
                   {"device_id": 2, "borrow_count": 1, "utilization": 1.0, "overbooked": false},
                   {"device_id": 3, "borrow_count": 0, "utilization": 0.0, "overbooked": false}]
```

即 14d/10d = 1.4 → 输出 1.0 且 `overbooked=true`；恰好 10d/10d = 1.0 → `overbooked=false`。

`to <= from` → 2：

```text
CMD stats usage --from 2027-01-01T00:00:00Z --to 2027-01-01T00:00:00Z | EXIT 2 | {"error": "bad_args", "message": "结束时间必须晚于开始时间"}
```

参数校验先于会话校验（未登录 + `to<=from` 仍为 2），由 `test_usage_rejects_to_not_after_from` 断言；缺 `--to` → 2。

### 1.4 TC-CRQ-07-01 现场：逾期率与 `stats overdue`

借出/归还造数（相对真实当前时间；`late` 的 due 在 3.5 天前，`stillout` 的 due 在 1.5 天前未还，`ontime` 的 due 在 1.5 天后）：

```text
CMD loan checkout --request-id 4 | EXIT 0 | {"loan_id": 1, "request_id": 4, "due_at": "2026-10-20T02:58:02Z"}
CMD loan checkout --request-id 5 | EXIT 0 | {"loan_id": 2, "request_id": 5, "due_at": "2026-10-22T02:58:02Z"}
CMD loan checkout --request-id 6 | EXIT 0 | {"loan_id": 3, "request_id": 6, "due_at": "2026-10-26T02:58:02Z"}
CMD loan return --loan-id 1 | EXIT 0 | {"loan_id": 1, "returned_at": "2026-10-23T14:58:03Z", "overdue": true,  "days_late": 4}
CMD loan return --loan-id 3 | EXIT 0 | {"loan_id": 3, "returned_at": "2026-10-23T14:58:03Z", "overdue": false, "days_late": 0}
```

```text
CMD stats usage --from 2026-10-13T14:58:03Z --to 2026-11-02T14:58:03Z | EXIT 0 | devices=20 overdue_rate=0.5
CMD stats overdue | EXIT 0 | {"items": [
  {"loan_id": 1, "request_id": 4, "device_id": 4, "due_at": "2026-10-20T02:58:02Z",
   "returned_at": "2026-10-23T14:58:03Z", "days_late": 4},
  {"loan_id": 2, "request_id": 5, "device_id": 5, "due_at": "2026-10-22T02:58:02Z",
   "returned_at": null, "days_late": 2}]}
CMD stats overdue --from 2026-10-19T14:58:04Z --to 2026-10-20T14:58:04Z | EXIT 0 | {"items": [
  {"loan_id": 1, "request_id": 4, "device_id": 4, "due_at": "2026-10-20T02:58:02Z",
   "returned_at": "2026-10-23T14:58:03Z", "days_late": 4}]}
```

核对：已还 2 条（1 逾期 + 1 准时），`overdue_rate = 1/2 = 0.5`；未还且已逾期的 loan 2 **不进分母**，否则会是 0.6667（测试用 `assertNotAlmostEqual` 排除了这种实现）。逾期清单同时列出「已还逾期」(loan 1, `returned_at` 非空) 与「未还逾期」(loan 2, `returned_at: null`)；准时归还的 loan 3、未还但 due 在未来的记录均不出现。`days_late`：3.5 天 → 4（ceil）、1.5 天 → 2；未还逾期 60 秒的用例断言为 1（`max(1, ·)`）。`--from/--to` 按 `due_at ∈ [from, to)` 过滤，只命中 loan 1。

无已还记录时分母为 0：`test_overdue_rate_zero_denominator` 场景（2 条未还借出，其中 1 条已逾期）`stats usage` 退出码 0、`overdue_rate=0`，`stats overdue` 恰好返回 1 条。

### 1.5 权限矩阵（§5）

```text
# student1
CMD stats usage --from 2027-01-01T00:00:00Z --to 2027-01-11T00:00:00Z | EXIT 3 | {"error": "forbidden", "message": "仅管理员或主任可查看统计"}
CMD stats overdue | EXIT 3 | {"error": "forbidden", "message": "仅管理员或主任可查看统计"}
CMD audit list | EXIT 3 | {"error": "forbidden", "message": "仅管理员可查询审计日志"}
# director
CMD stats usage --from 2027-01-01T00:00:00Z --to 2027-01-11T00:00:00Z | EXIT 0 | devices=20 overdue_rate=0
CMD stats overdue | EXIT 0 | {"items": [...]}
CMD audit list | EXIT 3 | {"error": "forbidden", "message": "仅管理员可查询审计日志"}
# admin
CMD audit list --limit 3 | EXIT 0 | {"items": [...]}
# 删除临时会话文件（未登录）
CMD stats usage --from 2027-01-01T00:00:00Z --to 2027-01-11T00:00:00Z | EXIT 3 | {"error": "not_logged_in", "message": "请先登录"}
CMD stats overdue | EXIT 3 | {"error": "not_logged_in", "message": "请先登录"}
CMD audit list | EXIT 3 | {"error": "not_logged_in", "message": "请先登录"}
```

与 §5 完全一致：usage/overdue 为 student ✗3、admin ✓、director ✓（只读）；audit list 为 student ✗3、director ✗3、admin ✓；未登录一律 3。

### 1.6 TC-CRQ-08-01 / TC-NFR-06-01 现场：`audit list`

真实流程产生的审计（admin）：

```text
CMD audit list --limit 3 | EXIT 0 | {"items": [
  {"at": "2026-10-23T14:58:05Z", "actor_name": "admin",    "action": "login",           "target_type": "user",    "target_id": 7, "result": "ok"},
  {"at": "2026-10-23T14:58:04Z", "actor_name": "director", "action": "login",           "target_type": "user",    "target_id": 8, "result": "ok"},
  {"at": "2026-10-23T14:58:04Z", "actor_name": "student1", "action": "login",           "target_type": "user",    "target_id": 1, "result": "ok"}]}
CMD audit list --action loan_return | EXIT 0 | {"items": [
  {"at": "2026-10-23T14:58:03Z", "actor_name": "admin", "action": "loan_return", "target_type": "loan", "target_id": 3, "result": "ok"},
  {"at": "2026-10-23T14:58:03Z", "actor_name": "admin", "action": "loan_return", "target_type": "loan", "target_id": 1, "result": "ok"}]}
CMD audit list --user student1 --limit 2 | EXIT 0 | {"items": [
  {"at": "2026-10-23T14:58:04Z", "actor_name": "student1", "action": "login",          "target_type": "user",    "target_id": 1, "result": "ok"},
  {"at": "2026-10-23T14:58:02Z", "actor_name": "student1", "action": "request_submit", "target_type": "request", "target_id": 6, "result": "ok"}]}
CMD audit list --limit 0  | EXIT 2 | {"error": "bad_args", "message": "--limit 必须为正整数"}
CMD audit list --limit -1 | EXIT 2 | {"error": "bad_args", "message": "--limit 必须为正整数"}
```

默认 50 条上限与 `at` 倒序（CLI 写的 `at` 是秒级，同一秒内无法稳定断言排序，故在临时库插入 60 条 `at` 各异的记录——2030-01-01T00:00:00Z ~ 00:59:00Z，`i%3==0` 为 `login`、`i%2==0` 为 `student1`）：`test_tc_crq_08_01_audit_list_default_limit_and_order` 断言 `len(items)==50`、`ats == sorted(ats, reverse=True)`、首条 `at == 2030-01-01T00:59:00Z`、字段集合正是 `at/actor_name/action/target_type/target_id/result`，且查询后 `audit_log` 仍为 60 条。`test_tc_nfr_06_01_audit_filters` 断言 `--action login`→20 条且全为 login、`--user student1`→30 条且全为 student1、`--from 00:10 --to 00:20`→10 条且 `at ∈ [from,to)`、`--limit 5` 恰为默认结果的前 5 条、组合过滤 3 条全部命中。六类事件 `login / request_submit / request_approve / request_reject / loan_checkout / loan_return` 由既有 WP1–WP4 测试（`test_wp1_auth.py`…`test_wp4_loans.py`）逐条断言，本包回归全过。

### 1.7 TC-NFR-05-01 现场：演示脚本

```text
$ python scripts/demo.py --db <TEMP>\demo.db --force
... 逐步打印每条 CLI 命令与退出码，最后：
演示数据摘要 (C:\Users\Lenovo\AppData\Local\Temp\qa-wp5-ev3-e3vhpcwf\demo.db)
  设备数: 20
  申请数: 1（其中 approved: 1）
  借出数: 1（其中已归还: 1）
  审计条数: 6
  申请 ID: 1，借出 ID: 1
  时段: 2026-10-24T09:00:00Z ~ 2026-10-24T11:00:00Z
DEMO --force | EXIT 0

$ python scripts/demo.py --db <TEMP>\demo.db          # 不带 --force 重复执行
数据库已存在: C:\Users\Lenovo\AppData\Local\Temp\qa-wp5-ev3-e3vhpcwf\demo.db
如需重建请加 --force。
DEMO (no --force) | EXIT 2

$ python scripts/demo.py --db <TEMP>\demo.db --force  # 再次 --force
（同上摘要：approved 1 / 已归还 1 / 审计 6）
DEMO --force | EXIT 0
```

`test_tc_nfr_05_01_demo_force_and_guard` 断言退出码 0/2/0、stdout 含 `approved: 1` 与 `已归还: 1`，并在三次运行后读库核对 `users=8, devices=20, approved=1, loans=1, returned=1, audit>0`；第二次 `--force` 后计数与首次完全一致（重建而非累加），退出码 2 时库内容不变。会话文件为 `<db>.session.json`（与临时库同目录），未写 `data/`。

## 2 逐条 TC 结论

| TC | 验收点 | 对应测试 | 结论 |
|---|---|---|---|
| TC-CRQ-07-01 | 借用次数按 `start_at ∈ [from,to)` 且 approved 计；利用率 = 交集秒数/(to−from)，4 位小数；>1 截 1 且 `overbooked=true`；`to<=from`→2；无 approved → 全 0、`overdue_rate=0`；逾期率 = 已还逾期/已还总数，分母 0 返回 0；`stats overdue` 列出已还与未还逾期、`days_late=max(1,ceil(秒/86400))`、准时与未到期不列 | `test_tc_crq_07_01_borrow_count_and_utilization`、`test_utilization_clamped_when_overbooked`、`test_usage_empty_range_is_all_zero`、`test_usage_rejects_to_not_after_from`、`test_overdue_rate_formula`、`test_overdue_rate_zero_denominator`、`test_overdue_list_returned_and_unreturned`、`test_overdue_range_filter` | PASS |
| TC-CRQ-08-01 | `audit list` 默认 50 条、`at` 倒序、`--action/--user/--from/--to/--limit` 过滤、`--limit<=0`→2 | `test_tc_crq_08_01_audit_list_default_limit_and_order`、`test_tc_nfr_06_01_audit_filters`、`test_audit_list_rejects_bad_limit` | PASS |
| TC-NFR-06-01 | 六类关键操作可查、字段完整、权限仅 admin | 同上 + 既有 WP1–WP4 审计断言（全量回归 73 ok） | PASS |
| TC-NFR-05-01 | 演示数据脚本可用、可重复（`--force` 重建 / 否则 2）、数据不落仓库 | `test_tc_nfr_05_01_demo_force_and_guard` | PASS |
| §5 权限 | usage/overdue：student 3、admin/director 0；audit list：student/director 3、admin 0；未登录 3 | `test_stats_permission_matrix`、`test_audit_permission_matrix` | PASS |

## 3 §6 公式逐条核对

| # | 口径（契约原文） | 实现核对点 | 实测 | 一致 |
|---|---|---|---|---|
| 1 | 借用次数：`start_at ∈ [from,to)` 且 `status='approved'` | `start_dt <= req_start < end_dt`，SQL 已过滤 approved | 区间内 1 次；`start_at` 早于 from → 0 | ✓ |
| 2 | 利用率：Σ交集秒数 ÷ (to−from)，4 位小数 | `(min(end,to)−max(start,from)).total_seconds()` 求和后除以 span，`round(...,4)` | 0.05 / 0.0083 / 0.125 | ✓ |
| 3 | >1 截 1 且 `overbooked=true` | `min(raw,1.0)` + `raw > 1.0` | 1.4 → 1.0/true；1.0 → 1.0/false | ✓ |
| 4 | `to <= from` → 退出码 2 | main 校验 `end <= start` | EXIT 2 | ✓ |
| 5 | 逾期率 = 逾期归还数 ÷ `returned_at` 非空数；分母 0 → 0；未还逾期不进分母 | SQL `returned_at IS NOT NULL`，分子 `returned_at > due_at` | 1/2=0.5；分母 0 → 0 | ✓ |
| 6 | 逾期率取数范围 `due_at ∈ [from,to)` | SQL `due_at >= ? AND due_at < ?` | 区间过滤生效 | ✓ |
| 7 | `days_late = max(1, ceil(逾期秒数/86400))` | `max(1, math.ceil(seconds/86400))`，`seconds<=0` 返回 0（调用前已过滤） | 3.5d→4、1.5d→2、60s→1、准时 0 | ✓ |
| 8 | 逾期唯一口径：未还且当前 > due_at，或 returned_at > due_at | `overdue()` 分支 | 与 loan return 的 4/0 一致 | ✓ |

## 4 数据隔离（NFR-05 落地）

- 每次测试 `setUp` 新建 `%TEMP%\qa-wp5-*`，`--db` 指向临时库，`DEVICELOAN_SESSION`/`DEVICELOAN_DB` 从环境清除，cwd 设为临时目录，会话落在 `<tmp>\data\session.json`。
- 演示脚本以临时库为 `--db`，会话由脚本写入 `<db>.session.json`（同临时目录）。
- 运行后检查仓库 `data/`：`deviceloan.db`、`session.json` 的 mtime 均为 `2026-10-23 21:28:11`（早于本轮 QA 运行时刻 `22:59`），本轮未写入仓库运行期目录。

## 5 缺陷与观察项

**缺陷：无**（0 条；无严重缺陷，符合 S3）。

观察项（不影响判定，供 PM/BA 参考）：

1. **§6 逾期率的两处表述需合读**：表格行只写「逾期归还数 ÷ returned_at 非空数」，末行补「取数范围 `due_at ∈ [from,to)`」。实现把区间同时作用于分子与分母（`WHERE due_at ∈ [from,to) AND returned_at IS NOT NULL`），是唯一自洽的读法，实测与之一致。建议 v1.1 修订时把区间条件并入公式行，避免二次解读。
2. **`overbooked` 在正常流程下不可达**：`request approve` 的冲突判定保证同一设备的 approved 申请互不重叠，因此利用率恒 ≤ 1，`overbooked=true` 只在数据被外部写入时出现。本包按契约公式验证了截断分支（测试内直接插库），建议 PM 确认该字段是否仍需保留——保留不影响正确性，仅为契约口径完整性。
3. `audit list --action` 无取值校验：传未知 action 返回 `{"items": []}`、退出码 0（`CMD audit list --action no_such_action | EXIT 0 | {"items": []}`）。契约未规定该参数枚举，不判缺陷。
4. `scripts/demo.py` 的 stdout 是演示转录（含 `$ 命令`、中文摘要），不是单行 JSON；§4「不向 stdout 输出非 JSON 文本」约束的是 CLI 子命令，演示脚本不受此约束，但下游若需机读输出应改用 CLI。

## 6 结论

**PASS。** 统计口径（§6）逐条与实现一致，权限矩阵（§5）无越界，退出码 0/2/3 与契约一致，审计查询默认条数、排序与四类过滤正确，演示脚本三种运行路径符合预期。未发现产品缺陷；既有 59 条 + 新增 14 条共 73 条测试全过。

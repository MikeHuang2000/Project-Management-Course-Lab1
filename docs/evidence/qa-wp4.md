# QA4 验收记录：WP4 借出、归还与逾期（WBS 3.8）

| 项目 | 内容 |
|---|---|
| 验收对象 | WP4：`loan checkout`、`loan return`、`days_late` 逾期口径、借还权限与审计 |
| 契约依据 | `docs/05-architecture.md` §2/§4/§5/§6/§7；`docs/04-scope.md` §6 TC-CRQ-06-01；`docs/10-work-packages.md` WP4 |
| 被测代码 | 仓库 `src/loans.py`、`src/main.py`（**只读**，未做任何改动） |
| 测试代码 | 新增 `tests/test_wp4_loans.py`（10 条，标准库 unittest，子进程调 CLI） |
| 日期 | 2026-10-23 |
| 结论 | **PASS**（0 条产品缺陷；3 条契约未规定事项见 §5） |

## 1 执行的命令与真实输出

### 1.1 本包测试（单文件，带 `-v` 便于定位）

```text
$ python -m unittest tests.test_wp4_loans -v
test_checkout_missing_request ... ok
test_checkout_requires_approved_request ... ok
test_device_search_reflects_unreturned_loan ... ok
test_duplicate_checkout_rejected ... ok
test_duplicate_return_rejected ... ok
test_loan_permission_matrix ... ok
test_overdue_boundary_exact_due_at ... ok
test_return_missing_loan ... ok
test_return_overdue_days_late ... ok
test_tc_crq_06_01_checkout_and_return_on_time ... ok
----------------------------------------------------------------------
Ran 10 tests in 18.442s

OK
```

### 1.2 全量回归（仓库根目录，一次，不带 `-v`）

```text
$ python -m unittest discover -s tests
..................................
[TC-NFR-02-01] search_devices elapsed = 0.0022s (20 devices / 50 requests / 25 loans)
.........................
----------------------------------------------------------------------
Ran 59 tests in 68.783s

OK
EXIT=0
```

`Ran 59 tests` / `OK` → **59 passed, 0 failed, 0 skipped**（WP1 14 + WP2 21 + WP3 14 + 本包 10）。

### 1.3 TC-CRQ-06-01 现场（临时库 `<TEMP>\qa-wp4-demo-*\qa.db`，cwd 同临时目录）

```text
CMD seed --db <tmp>\qa.db | EXIT 0 | {"users": 8, "devices": 20, "requests": 0, "loans": 0}
CMD login --username student1 --password Passw0rd! | EXIT 0 | {"user_id": 1, "username": "student1", "role": "student"}
CMD request submit --device DEV-001 --from 2026-12-01T08:00:00Z --to 2026-12-01T12:00:00Z --purpose demo
  | EXIT 0 | {"request_id": 1, "status": "pending"}
CMD login --username admin --password Passw0rd! | EXIT 0 | {"user_id": 7, "username": "admin", "role": "admin"}
CMD request approve --request-id 1 | EXIT 0 | {"request_id": 1, "status": "approved", "decided_at": "2026-10-23T14:32:52Z"}
CMD loan checkout --request-id 1 | EXIT 0 | {"loan_id": 1, "request_id": 1, "due_at": "2026-12-01T12:00:00Z"}
CMD loan checkout --request-id 1 | EXIT 1 | {"error": "already_checked_out", "message": "该申请已登记借出，不能重复借出"}
SQL UPDATE loans SET due_at=2026-10-23T12:02:52Z WHERE id=1  (逾期约 2.5 小时)
CMD loan return --loan-id 1 | EXIT 0 | {"loan_id": 1, "returned_at": "2026-10-23T14:32:52Z", "overdue": true, "days_late": 1}
CMD loan return --loan-id 1 | EXIT 1 | {"error": "already_returned", "message": "该借出记录已归还"}
DB loans  [(1, 1, 1, 1, '2026-10-23T14:32:52Z', '2026-10-23T12:02:52Z', '2026-10-23T14:32:52Z')]
DB audit  [('loan_checkout', 'loan', 1, 'ok', '{"request_id": 1, "due_at": "2026-12-01T12:00:00Z"}', 'admin'),
           ('loan_return',   'loan', 1, 'ok', '{"returned_at": "2026-10-23T14:32:52Z", "overdue": true}', 'admin')]
DB ids    admin=(7,) student1=(1,) DEV-001=(1,)
```

- `due_at` = 申请 `end_at`；`loans.request_id/device_id/user_id` = 1/1/1，与申请一致。
- 重复借出 `EXIT 1` 且 `loans` 仍只有 1 行；重复归还 `EXIT 1` 且 `returned_at` 未被覆盖；两处都未新增 `ok` 审计。
- 逾期 2.5 小时 → `overdue=true, days_late=1`（`ceil(9000/86400)=1`，`max(1,·)` 生效）。
- 说明：控制台按 GBK 显示中文错误消息时会出现乱码，这是终端编码显示问题；测试以 UTF-8 解码 stdout，断言对象是 JSON 字段，不受影响。

### 1.4 数据隔离

测试一律 `cwd=tempfile.mkdtemp(prefix="qa-wp4-")`、显式 `--db <临时库>`，会话文件落在临时目录的 `data/session.json`（契约 §1）；§1.3 的演示同样在临时目录。

```text
data\deviceloan.db      mtime 2026-10-23 21:28:11
data\session.json       mtime 2026-10-23 21:28:11
now                     2026-10-23 22:33:16
```

两次测试运行（约 22:2x–22:33）未修改仓库 `data/` 下任何文件。

## 2 逐条验收结论（TC-CRQ-06-01）

| 验收点 | 用例 | 结论 |
|---|---|---|
| 对 approved 申请借出 → 0，返回 `loan_id/request_id/due_at` | `test_tc_crq_06_01_checkout_and_return_on_time` | PASS |
| `due_at` 等于申请 `end_at` | 同上 | PASS |
| `loans.device_id` / `user_id` 与申请一致，`returned_at` 初始为空，时间 ISO 8601 秒级 `Z` | 同上（查 `requests` 与 `loans` 双表比对） | PASS |
| 同一申请二次借出 → 1（`already_checked_out`），库中仍 1 行，不追加 `ok` 审计 | `test_duplicate_checkout_rejected` | PASS |
| 对 pending / rejected / cancelled 申请借出 → 1，不落库、无审计 | `test_checkout_requires_approved_request` | PASS |
| 不存在的 request-id → 1（`request_not_found`） | `test_checkout_missing_request` | PASS |
| 未登录借/还 → 3；student、director 借/还 → 3；越权调用不改数据、不写 `ok` | `test_loan_permission_matrix` | PASS |
| 正常归还 → 0，`overdue=false, days_late=0`，`returned_at` 落库且与响应一致 | `test_tc_crq_06_01_checkout_and_return_on_time` | PASS |
| 逾期约 1 分钟 → `days_late=1`（`max(1,·)` 生效） | `test_return_overdue_days_late` | PASS |
| 逾期 3.5 小时 → `days_late=1` | 同上 | PASS |
| 逾期 2 天 1 小时 → `days_late=3`（`ceil` 向上取整） | 同上 | PASS |
| 逾期 1 秒 → `days_late=1`；`returned_at == due_at` 与早 1 秒 → 不逾期 0；恰满 1 天 → 1；1 天 + 1 秒 → 2 | `test_overdue_boundary_exact_due_at`（调 `loans.overdue_days` 纯函数） | PASS |
| 二次归还 → 1（`already_returned`），`returned_at` 不变，不追加 `ok` 审计 | `test_duplicate_return_rejected` | PASS |
| 不存在的 loan-id → 1（`loan_not_found`），不误改既有记录 | `test_return_missing_loan` | PASS |
| 审计：checkout / return 各 1 条 `ok`，`target_type=loan`、`target_id=loan_id`，detail 含 `request_id/due_at` 与 `returned_at/overdue` | `test_tc_crq_06_01_checkout_and_return_on_time` | PASS |
| 联动：checkout 后 `device search` 在 2027-03-01、2030-01-01 两个后续时段均 `available=false, conflicts=1`；归还后恢复 `available=true, conflicts=0` | `test_device_search_reflects_unreturned_loan` | PASS |

## 3 缺陷清单

未发现产品缺陷（逾期天数、权限越界、审计缺失、重复借出四项均为 0 缺陷）。

| ID | 等级 | 位置 | 期望 | 实际 |
|---|---|---|---|---|
| — | — | — | — | 无 |

## 4 对已知情况（Dev 自检 / PM 转述）的复核

| 已知情况 | 复核结果 |
|---|---|
| 重复借出 1 | 一致：`already_checked_out`，`loans` 仍 1 行 |
| pending 申请借出 1 | 一致（rejected / cancelled 同样是 1） |
| 逾期天数向上取整 | 一致：3.5 小时→1、2 天 1 小时→3、1 秒→1、恰满 1 天→1 |
| `days_late = max(1, ceil(秒数/86400))` 且仅在 `returned_at > due_at` 生效 | 一致（`returned_at == due_at` → 0） |

## 5 契约未规定 / 需 PM-BA 记录的事项（不构成缺陷）

1. **逾期样本的构造方式**：契约 §4 的 `loan checkout` / `loan return` 都没有"指定借出/归还时间"的参数，逾期只能由"当前时间 vs `due_at`"决定。本次测试在**临时库**里改写 `loans.due_at` 来复现逾期场景（只改临时库，不动 `data/`）。若后续要做可重复的演示脚本，建议在演示脚本里用同样的方式，或由 CCB 决定是否加测试参数。
2. **`loan return` 的失败 error code 未写死**：契约 §4 只规定退出码 1，未规定"已归还再还"的 `error` 值（实现为 `already_returned`）。测试只断言退出码 1 与"数据不变"，不锁死该字符串；同理 `already_checked_out` / `request_not_found` / `loan_not_found` 只作记录。
3. **借出时是否复查设备状态未规定**：契约 §2 只写设备 `maintenance/retired` 不可借，未说明"申请已批准、之后设备转维护，`loan checkout` 是否要拦"。`src/loans.py` 未做该检查。契约未规定，本包不判定；若业务上需要拦，应走 CCB 补契约后再验收。

另：契约 §2 的"未还且超过 `due_at` 即逾期"在 `loan return` 之外没有可观测入口（逾期清单属 WP5 `stats overdue`），本包只验归还路径。

## 6 结论

TC-CRQ-06-01（借出→归还→逾期标记）在全量 59 条测试下通过，逾期天数与 §6 公式逐例手算一致，权限矩阵与 §7 审计均符合契约。**判定 PASS**。

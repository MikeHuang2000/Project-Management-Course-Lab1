# QA3 验收记录：WP3 申请审批与冲突阻止（WBS 3.6）

| 项目 | 内容 |
|---|---|
| 验收对象 | WP3：`request submit/cancel/list/show/approve/reject`、状态机、审批时冲突判定与回滚 |
| 契约依据 | `docs/05-architecture.md` §2/§3/§4/§5/§7；`docs/04-scope.md` §6；`docs/10-work-packages.md` WP3 |
| 被测代码 | `%TEMP%\qa3-snap\src`（WP3 完成时刻冻结快照，PM 提供），**不读仓库 `src/`** |
| 测试代码 | 仓库 `tests/test_wp3_requests.py`（新增）、`tests/test_wp1_auth.py`（修订 1 条陈旧用例 + 新增 1 条 NFR-04 端到端），复制进快照后运行 |
| 日期 | 2026-10-23 |
| 结论 | **PASS**（0 条严重缺陷；1 条契约未规定的输出细节见 §5） |

快照文件指纹（SHA-256 前 16 位）：

```text
20EC26C31DD6C4EB  audit.py        D32FD60329DA2AE0  auth.py
1170F4F23631C3D1  db.py           3490EB0EA2AB8D5F  devices.py
36E1B085642A2B7F  main.py         A47B9593DC038837  requests.py
37007A0D2A668161  test_wp1_auth.py   6F57EC905A988119  test_wp2_devices.py
708C7A94D9001EE0  test_wp3_requests.py
```

## 1 执行的命令与真实输出

### 1.1 全量回归（快照内，一次，不带 `-v`）

```text
$ python -m unittest discover -s "%TEMP%\qa3-snap\tests"
..................................
[TC-NFR-02-01] search_devices elapsed = 0.0023s (20 devices / 50 requests / 25 loans)
...............
----------------------------------------------------------------------
Ran 49 tests in 48.930s

OK
```

`Ran 49 tests`、`OK` → 49 passed, 0 failed, 0 skipped（WP1 14 条、WP2 21 条、WP3 新增 14 条）。

说明：`python -m unittest discover` 在快照的 `tests/` 下运行（该目录无 `__init__.py`，
需以 `tests` 自身为 start dir）。工作目录不影响结果——测试内部一律用临时目录做 cwd、
显式 `--db <临时库>`，会话文件落在临时目录的 `data/session.json`（契约 §1 运行期文件位置）。

### 1.2 首次全量运行的两条失败（均为测试侧问题，已修正；未改产品代码）

| 失败 | 原因 | 处理 |
|---|---|---|
| `test_wp1_unimplemented_commands_not_registered` 期望 2 实得 3 | 快照里仍是 WP1 时期的旧测试文件（复制被沙箱拦下，实际未复制成功） | 重新复制修订后的 `tests/test_wp1_auth.py` 进快照 |
| `test_terminal_states_are_immutable` 得 `duplicate_pending` | 我的新用例在同一学生 + 同一设备上连开 3 条 pending，触发契约 §2 的"同一 user 对同一 device 只允许一条 pending" | 三条申请改用 DEV-001/002/003 |

修正后再跑全量 → 上表 1.1 的 `OK`。产品代码未做任何改动。

### 1.3 TC-CRQ-05 冲突与回滚现场（快照 CLI，临时库）

```text
seed --db <tmp>\qa.db                                          EXIT 0  {"users": 8, "devices": 20, "requests": 0, "loans": 0}
login --username student1 --password Passw0rd!                 EXIT 0  {"user_id": 1, "username": "student1", "role": "student"}
request submit --device DEV-001 --from 2026-11-02T08:00:00Z --to 2026-11-02T12:00:00Z --purpose demo
                                                               EXIT 0  {"request_id": 1, "status": "pending"}
login --username admin                                         EXIT 0  {"user_id": 7, "username": "admin", "role": "admin"}
request approve --request-id 1                                 EXIT 0  {"request_id": 1, "status": "approved", "decided_at": "2026-10-23T14:21:26Z"}
login --username student2                                      EXIT 0  {"user_id": 2, ...}
request submit --device DEV-001 --from 2026-11-02T10:00:00Z --to 2026-11-02T14:00:00Z --purpose overlap
                                                               EXIT 0  {"request_id": 2, "status": "pending"}
request approve --request-id 2                                 EXIT 4  {"error": "time_conflict", "conflicts": [{"request_id": 1, "start_at": "2026-11-02T08:00:00Z", "end_at": "2026-11-02T12:00:00Z"}]}

库内复核：requests#2 = ('pending', None, None)          ← 状态/审批人/审批时间均未落库
          approved 条数 = 1
          audit_log 中 request_approve 的 target_id = [(1,)]   ← 回滚时未留 approve 审计

request submit --device DEV-001 --from 2026-11-02T12:00:00Z --to 2026-11-02T14:00:00Z --purpose back-to-back
                                                               EXIT 0  {"request_id": 3, "status": "pending"}
request approve --request-id 3                                 EXIT 0  {"request_id": 3, "status": "approved", ...}   ← 首尾相接放行
```

### 1.4 未归还 loan 的无限占位（快照 CLI，临时库）

```text
request approve --request-id 1  （DEV-001, 2026-11-10T08:00–12:00）      EXIT 0
[SQL] INSERT INTO loans(... request_id=1, checked_out_at='2026-11-10T08:00:00Z', returned_at=NULL)
request submit --device DEV-001 --from 2026-11-20T08:00:00Z --to 2026-11-20T12:00:00Z
                                                                        EXIT 0  {"request_id": 2, "status": "pending"}
request approve --request-id 2   ← 新时段完全在已批准申请结束之后
                                                                        EXIT 4  {"error": "time_conflict", "conflicts": [{"request_id": 1, "start_at": "2026-11-10T08:00:00Z", "end_at": null}]}
[SQL] UPDATE loans SET returned_at='2026-11-10T11:00:00Z' WHERE request_id=1
request approve --request-id 2                                          EXIT 0  {"request_id": 2, "status": "approved", ...}
库内复核：requests#2 = ('approved',)                                    ← 归还后占用立即解除
```

结论：未归还 loan 从 `checked_out_at` 起无限占位、归还后解除，符合契约 §3 第 3 条；
同一申请的"approved 申请行 + 未还 loan 行"合并为 1 条冲突（`GROUP BY request_id`），符合"只计 1 次"。

## 2 逐条验收结论

测试文件：`tests/test_wp3_requests.py`（14 条）、`tests/test_wp1_auth.py`（修订 1 条 + 新增 1 条）。

| TC | 契约要点 | 用例 | 结论 |
|---|---|---|---|
| TC-CRQ-03-01 | submit 落 pending，返回 `request_id/status`，时间归一化，submit 不做冲突判定 | `test_tc_crq_03_01_submit_creates_pending_request` | PASS |
| TC-CRQ-04-01（批准） | pending→approved，写 `decided_by/decided_at` | `test_tc_crq_04_01_approve_pending_request` | PASS |
| TC-CRQ-04-01（拒绝） | 拒绝必填原因并落库，返回 `reject_reason` | `test_tc_crq_04_01_reject_records_reason` | PASS |
| TC-CRQ-05-01 | 重叠 → 退出码 4，`{"error":"time_conflict","conflicts":[...]}`，整事务回滚（仍 pending、decided_* 为空、approved 数不变、无 approve 审计） | `test_tc_crq_05_01_overlap_returns_4_and_rolls_back` + §1.3 | PASS |
| TC-CRQ-05-02 | 首尾相接（前 end == 后 start）不冲突 → 0 | `test_tc_crq_05_02_back_to_back_allowed` | PASS |
| CRQ-05 补充 | pending / rejected / cancelled 不占位 | `test_pending_rejected_cancelled_do_not_occupy` | PASS |
| CRQ-05 补充 | 未还 loan 无限占位、归还后解除、申请+借出只计 1 次 | `test_unreturned_loan_blocks_later_slot_until_returned` + §1.4 | PASS |
| TC-CRQ-09-01 | 仅本人且 pending 可取消；他人取消 → 1；admin 取消 → 3；重复取消 → 1 | `test_tc_crq_09_01_cancel_only_own_pending` | PASS |
| 状态机 | 终态不可再变：approve/reject 作用于 approved/rejected/cancelled → 1 | `test_terminal_states_are_immutable` | PASS |
| TC-NFR-04-01 | student 不能 approve/reject（3）；director 不能 list/show（3）；admin 不能 submit（3）；student `--all` → 3 | `test_permission_matrix_role_checks` | PASS |
| TC-NFR-04-01 | student list 只见本人；看他人 show → 1；admin 见全部 | `test_tc_nfr_04_01_student_sees_only_own_requests` | PASS |
| TC-NFR-04-01（e2e） | student1 已登录后调 `request approve` → 3，库中 approved 数 0 | `test_wp1_auth.py::test_tc_nfr_04_01_student_calling_admin_command_exits_3` | PASS |
| 参数 | `from>to` / `from==to` / 非法时间格式 / purpose 空或全空白 → 2；reject 缺 `--reason` 或全空白 → 2；参数错误不落库 | `test_parameter_validation_and_missing_request` | PASS |
| 参数 | 不存在的 request-id：show/approve/reject/cancel → 1 | 同上 | PASS |
| 设备状态 | `maintenance`/`retired` 时 submit → 1 `device_unavailable`；提交后转 retired 再 approve → 1 且仍 pending、decided_* 为空 | `test_device_status_blocks_submit_and_approve` | PASS |
| 审计 §7 | `request_submit/approve/reject/cancel` 各写一条，`target_type=request`、`result=ok`、拒绝 detail 含原因 | `test_audit_events_for_request_actions` | PASS |
| WP1 陈旧用例修订 | WP3 后 `request list` 已注册，无会话 → 3（`not_logged_in`）；参数校验先于会话（缺 `--request-id` → 2） | `test_wp1_auth.py::test_wp1_wp3_commands_registered_and_require_session` | PASS |

## 3 缺陷清单

无严重缺陷（冲突未拦住、回滚不彻底、越权三类均未发现）。

| ID | 等级 | 位置 | 期望 | 实际 |
|---|---|---|---|---|
| — | — | — | — | 无产品缺陷 |

## 4 对已知情况的复核

| 已知情况 | 复核结果 |
|---|---|
| Dev 自检 A–O 全过，含冲突回滚（退出码 4、库内仍 pending）、首尾相接 0 冲突 | 复核一致（§1.3） |
| `maintenance/retired` 时 submit 与 approve 均返回 1（`device_unavailable`） | 一致，且 approve 被拒后申请仍 pending、`decided_by/decided_at` 为空 |
| 1 条 WP1 陈旧用例与新契约矛盾（`request list` 未注册 → 2） | 确认已按契约修订为"已注册、无会话 → 3"，并补 e2e 权限断言；未削弱其它断言 |

## 5 契约未规定 / 需 PM-BA 记录的事项（不构成缺陷）

1. **唯一冲突源为未还 loan 时，`conflicts[].end_at` 为 `null`**（§1.4 实测）。
   契约 §3 只写"未还 loan 是无结束时间的占用"，§4 的冲突 JSON 示例给了 `end_at` 字段但未说明
   开放占用如何取值；`null` 是诚实表达，建议下次改契约时明确一句"开放占用 end_at 输出 null"。
   当前测试只断言结构存在与去重，不锁死该值。
2. `request submit` 不做冲突判定（契约 §3 第 6 条明确要求），因此重叠的 pending 可以并存，
   只在 approve 兜底——这是设计口径，不是缺陷。
3. 冲突返回体按契约 §3 第 7 条只有 `error` 与 `conflicts`，没有 `message` 字段（与其它错误的
   `{"error","message"}` 形状不同）。本次按契约原样验收，未加断言要求 `message`。

## 6 结论

WP3 契约范围内的 TC-CRQ-03-01 / 04-01 / 05-01 / 05-02 / 09-01 与 NFR-04 端到端全部通过；
全量 49 条测试 0 失败。**判定 PASS**，可进入 WP4 验收。

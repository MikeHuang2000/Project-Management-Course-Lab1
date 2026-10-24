# QA-WP6 验证记录（CR-02 二期：候补队列）

| 项 | 内容 |
|---|---|
| WBS | WP6 / CR-02 二期 |
| 验收依据 | `docs/evidence/ccb-cr02.md` §1、§4（AC1–AC4） |
| 被测代码 | `src/waitlist.py`、`src/main.py`（`waitlist` 命令组）、`src/db.py`、`src/requests.py` |
| 测试文件 | `tests/test_wp6_waitlist.py`（新增 8 条）、`tests/test_wp1_auth.py`（`LOCAL_MODULES` 增补 `waitlist`） |
| 环境 | Windows / Python 3.11.9 / 标准库 unittest；每个用例独立临时目录与临时 DB，CLI 子进程 + 显式 `--db`，会话在 `<tmp>/data/session.json` |
| 结论 | **PASS**（AC1–AC4 全绿，未发现产品缺陷） |

## 1 AC 对照

| AC | 判定点 | 用例 | 结果 |
|---|---|---|---|
| AC1 | join 退出码 0；`waitlist_id`/`status=waiting`/`available_now=true`；库中 1 条 `waiting`；`waitlist_join` 审计 1 条；list 字段齐全 | `test_ac1_join_creates_waiting_row_and_audit` | PASS |
| AC2 | 同人同设备重叠 → 1 `duplicate_waitlist`、无新增；首尾相接 → 0；他人同时段 → 允许 | `test_ac2_overlap_duplicate_rejected_adjacent_and_other_user_allowed` | PASS |
| AC3 | 有 waiting 时 approve → 0/approved、无 `time_conflict`；后续重叠申请 approve 仍为 4；无 waiting 对照库结果一致 | `test_ac3_waitlist_does_not_affect_approve` | PASS |
| AC4 | student 仅见本人、`--all` → 3；admin 无 `--all` 为空、`--all` 见 2 条；`--device` 编码/编号等价；director list → 3；admin/director join → 3 | `test_ac4_visibility_and_role_matrix` | PASS |

## 2 边界与 NFR

| 项 | 用例 | 结果 |
|---|---|---|
| 非法时间 / start>=end / note 201 字符 → 2，不落库 | `test_boundary_validation_and_device_lookup` | PASS |
| 设备不存在 → 1 `device_not_found`，无审计 | 同上 | PASS |
| 设备已有批准申请占用 → join 成功但 `available_now=false` | `test_available_now_false_when_slot_occupied` | PASS |
| `seed --reset` 清空 `waitlists`，seed 输出字段不变（users/devices/requests/loans，8/20） | `test_seed_reset_clears_waitlists` | PASS |
| NFR：`src/` 仅 import 标准库与本地模块 | `test_nfr_src_imports_stdlib_or_local_only`、`test_wp1_auth.test_tc_nfr_01_01_no_third_party_imports` | PASS |

## 3 命令与统计

| 命令 | 结果 |
|---|---|
| `python tests/test_wp6_waitlist.py -v` | Ran 8 tests, OK（8 passed / 0 failed / 0 skipped） |
| `python -m unittest discover -s tests` | Ran 84 tests, exit 0, OK（原 76 + 新增 8；0 failed / 0 skipped） |
| `python -m unittest tests.test_wp1_auth.WP1CliTest.test_tc_nfr_01_01_no_third_party_imports -v` | Ran 1 test, OK（白名单修复生效） |

## 4 缺陷

none

## 5 备注

- `tests/test_wp1_auth.py` 的 `LOCAL_MODULES` 原为硬编码集合，新增 `src/waitlist.py` 后未同步，导致 NFR-01 误报；已加入 `"waitlist"`，属测试侧白名单维护，未改动任何断言。
- 二期契约见 `ccb-cr02.md`；`docs/05-architecture.md` 已由 PM 同步为 v1.1（新增 `waitlists` 表、`waitlist join/list`、`waitlist_join` 审计）。

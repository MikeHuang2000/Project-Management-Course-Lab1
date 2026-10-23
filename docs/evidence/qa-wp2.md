# QA 证据：WP2 设备目录与查询（QA2 / WBS 3.4）

| 项 | 内容 |
|---|---|
| 测试文件 | `tests/test_wp2_devices.py`（unittest，标准库，21 个用例） |
| 被测对象 | `src/devices.py`（91 行，SHA256 前 16 位 `EC84EA2BFD300D5F`）、`src/main.py`（225 行，`7F333EA59F4C8D58`）；只读，未修改 |
| 契约依据 | `05-architecture.md` §2/§3/§4/§5、`04-scope.md` §6（TC-CRQ-02-01、TC-NFR-02-01）、`10-work-packages.md` WP2 |
| 隔离方式 | `setUpClass` 在临时目录 `seed` 出基线库；每个用例复制一份到自己的临时库，CLI 以该临时目录为 cwd 并显式传 `--db`，会话文件因此落在 `<临时目录>/data/session.json`；`tearDown` 删除 |
| 日期 / 执行者 | 2026-10-23 / QA（DeepSeek V4.1 Flash Free） |

## 1 执行的命令与真实结果

### 1.1 全量测试（含 WP1 回归）

```
python -m unittest discover -s tests
EXIT=0
Ran 34 tests in 22.068s
OK
```

34 = WP1 的 13 条（`tests/test_wp1_auth.py`，全部仍通过）+ WP2 的 21 条。
定向运行 `python -m unittest tests.test_wp2_devices` 为 `Ran 21 tests / OK`。

### 1.2 性能实测（TC-NFR-02-01）

用例在临时库内构造 20 台设备、50 条 `approved` 申请、25 条未归还 `loans`，用
`time.perf_counter()` 只包住 `devices.search_devices()` 调用（不含解释器启动）：

```
[TC-NFR-02-01] search_devices elapsed = 0.0023s (20 devices / 50 requests / 25 loans)
```

三次运行的实测值：0.0038s / 0.0025s / 0.0023s，阈值 1 秒，余量充足。

### 1.3 CLI 走查（临时库，`src/main.py seed` 起）

| # | 命令 | 退出码 | stdout |
|---|---|---|---|
| — | `seed --db qa.db` | 0 | `{"users": 8, "devices": 20, "requests": 0, "loans": 0}` |
| A | `device list`（无会话） | 3 | `{"error": "not_logged_in", "message": "请先登录"}` |
| A | `device search --name 显微镜`（无会话） | 3 | 同上 |
| B | `login --username student1` | 0 | `{"user_id": 1, "username": "student1", "role": "student"}` |
| C | `device list` | 0 | `{"items": [{"id": 1, "code": "DEV-001", "name": "倒置金相显微镜", "category": "显微镜", "status": "available"}, …20 条…]}` |
| D | `device list --category 显微镜` | 0 | 3 条：`DEV-001/002/003` |
| E | `device list --status borrowed` | 2 | `{"error": "bad_args", "message": "argument --status: invalid choice: 'borrowed' (choose from 'available', 'maintenance', 'retired')"}` |
| F | `device search`（无条件） | 2 | `{"error": "bad_args", "message": "至少提供 --name、--category、--from/--to 之一"}` |
| G | `device search --from 2026-11-02T09:00:00Z` | 2 | `{"error": "bad_args", "message": "--from 与 --to 必须成对出现"}` |
| H | `device search --from 11:00 --to 09:00` | 2 | `{"error": "bad_args", "message": "结束时间必须晚于开始时间"}` |
| I | `device search --from "2026/11/02 09:00" --to …10:00` | 2 | `{"error": "bad_args", "message": "时间格式非法，应为 ISO 8601"}` |
| J | 调库插入 `approved [11-02 08:00,10:00)` 后查 `[09:00,11:00)` | 0 | `{"items": [{"id": 13, "code": "DEV-013", "name": "STM32 开发板", "category": "开发板", "available": false, "conflicts": 1}]}` |
| K | 同一数据查 `[10:00,11:00)`（首尾相接） | 0 | `{"items": [{"id": 13, …, "available": true, "conflicts": 0}]}` |

契约 §5 权限矩阵的补充走查（同一临时库）：

| 场景 | 退出码 |
|---|---|
| 无会话 `device list --status available` | 3 |
| 无会话 `device search --from … --to …`（参数合法） | 3 |
| `student1` 登录后 `device list` / `device search --category 显微镜` | 0 / 0 |
| `admin` 登录后 `device search --name 示波` | 0（3 条） |

### 1.4 "上一轮返工"复核：设备状态枚举

- 库层：`devices.status` 约束为 `CHECK IN ('available','maintenance','retired')`，不含 `borrowed`；`UPDATE … status='borrowed'` 抛 `sqlite3.IntegrityError`（用例已断言）。
- 命令层：`--status` 的 `choices` 就是这三档，`borrowed` / `AVAILABLE` / 空串 / `lost` 一律退出码 2。
- 语义层：`maintenance` 设备在 `device search` 中 `available=false`（契约 §2"维护/退役不可借"）。
- **结论：三种枚举，无 `borrowed`，返工有效。**

### 1.5 隔离与只读核对

- 仓库 `data/deviceloan.db`（40960 B）、`data/session.json`（76 B）的 `LastWriteTime` 在测试前后均为 `2026/10/23 21:28:11`；本次执行时间为 21:44–21:54，未写入。
- 所有测试库与日志落在 `%TEMP%\qa-wp2-*`，用例结束即删除。
- 未改动 `src/`：复核时 `devices.py`、`main.py` 的内容与首次读取一致（行数、逻辑、哈希见上表），本次只新增 `tests/test_wp2_devices.py` 与本文件。

## 2 逐条 TC 结论

| TC | 验证内容 | 对应用例 | 结论 |
|---|---|---|---|
| TC-CRQ-02-01（list） | 20 条、按 `code` 升序、字段集合、类别过滤、三种状态取值、非法状态 2 | `list_returns_20_devices_sorted_by_code`、`list_filters_by_category`、`list_accepts_three_status_values`、`list_rejects_illegal_status_with_exit_2` | **PASS** |
| TC-CRQ-02-01（search 条件） | 名称模糊、类别、时段、组合条件、无时段时 `available`/`conflicts` 结构 | `search_by_name_is_fuzzy`、`search_by_category`、`search_by_time_range_reports_available`、`search_combined_conditions` | **PASS** |
| TC-CRQ-02-01（参数错误） | 无条件→2；只给 `--from`→2；`--to` ≤ `--from`→2；非法 ISO→2 | `search_without_condition_exits_2`、`search_from_without_to_exits_2`、`search_to_before_from_exits_2`、`search_invalid_iso_exits_2` | **PASS** |
| 契约 §3（冲突判定，查询侧） | a) 重叠→`conflicts=1`/`available=false`；b) 首尾相接→0/true；c) `pending`/`rejected`/`cancelled` 不占；d) 未还 `loans` 占、已还不占；e) 同一申请+其未还 loan 只计 1 | `overlapping_approved_request_counts_as_conflict`、`adjacent_window_is_not_a_conflict`、`pending_rejected_cancelled_do_not_occupy_time`、`unreturned_loan_occupies_returned_loan_does_not`、`request_and_its_loan_counted_once` | **PASS** |
| 契约 §5（权限） | 两条命令无会话→3；`student` 可查；`admin` 可查 | `no_session_exits_3`、`student_can_query_devices`、`admin_can_query_devices` | **PASS** |
| TC-NFR-02-01 | 20 设备 / 50 申请 / 25 loan 下单次查询 < 1 秒 | `test_tc_nfr_02_01_search_under_one_second` | **PASS**（实测 0.0023–0.0038s） |

补充：契约 §3 第 6、7 条（只在 `approve` 时判定、事务回滚）属 WP3 的 `request approve`，
不在本包命令范围内，未测（见 §4）。

## 3 发现的问题

**产品缺陷：无（0 个）。**

| ID | 等级 | 描述 | 期望 vs 实际 | 归属 |
|---|---|---|---|---|
| OBS-WP2-01 | 观察（契约未规定） | 未给 `--from/--to` 时，`device search` 的 `available` 直接等于 `status == 'available'`，`conflicts` 恒为 0 | 契约 §4 只定义字段存在，未定义"无时段"时 `available` 的含义；当前实现是合理默认，但语义上是"设备级可借"而非"时段可借" | BA 可在 §4 补一句口径，不影响判定 |
| OBS-WP2-02 | 观察（契约未规定） | 未归还 `loans` 的占位区间取 `[checked_out_at, due_at)`。实测：`loan(due_at=11-02T10:00)` 未归还，查 `11-10` 时段得 `conflicts=0 / available=true` | 契约 §3-3 只写"该设备未归还的 `loans`"，未定义区间；按"还没还回来就该继续占着"的常识理解，未来时段可能应被挡住。当前口径是"按原计划区间占位" | 契约缺口，需 PM/BA 明确；若确认为缺陷，属 WP2 返工 |
| OBS-WP2-03 | 观察（契约未规定） | 无会话调用 `device list --db fresh.db` 时，仍会创建库文件并建 5 张表，随后返回 3（实测 `tables=['audit_log','devices','loans','requests','sqlite_sequence','users']`，`devices=0`，无会话文件） | 契约 §1 只写"缺少会话...不读业务表"，未禁止 DDL 副作用；退出码本身正确 | 契约未禁止，不计缺陷；如需严格"零副作用"由 PM 决策 |
| OBS-WP2-04 | 观察（契约歧义） | 无会话且参数非法时先报参数错误：`device search --from x` 无会话 → 2（`bad_args`），无会话但参数合法 → 3。`device list --status available` 无会话 → 3 | 契约 §1 说缺会话"一律返回退出码 3"，§4 说参数错误为 2，两条规则未定优先级；实现选择"先校验参数、再校验会话" | PM/BA 明确优先级即可，两种口径都不影响安全（两者都不读业务数据） |

另外，以下现象均为契约未规定，不计缺陷：
- `device list --category <不存在的类别>` 返回 0 + 空列表（契约只列 0/2/3，未规定空结果码）；
- `--from/--to` 带时区偏移（如 `+08:00`）会被 `normalize_iso` 折算成 UTC，契约 §2 只规定 UTC 存储格式，未规定输入的偏移写法（未做用例）。

## 4 未覆盖 / 超出本包

- `request approve` 的冲突退出码 4 与整事务回滚（TC-CRQ-05-01/02 的完整口径）：属 WP3 / QA3。
- 审计写入、统计口径、`seed --reset`：属 WP3/WP5。
- 并发、超过演示规模的数据量：不在 NFR-02 的验收口径内。
- `device search` 的 `conflicts` 计数在"同一设备多条重叠申请"下为 N（而非布尔），契约写的是 `conflicts:N`，未额外设用例。

## 5 结论

**PASS**

- WP2 退出标准核对：`--from/--to` 不成对 → 2 ✅；结果按 `code` 升序 ✅；`device list` 可按类别/状态过滤 ✅；20 台设备读取路径 ✅。
- 冲突判定查询侧与契约 §3 第 1–5 条逐条一致（含首尾相接不冲突、`pending/rejected/cancelled` 不占位、已还 loan 不占位、申请与其 loan 不重复计数）。
- 严重缺陷 0 个、一般缺陷 0 个；4 条契约缺口/歧义待 PM/BA 裁定，均不影响本包判定。
- QA 未修改任何产品代码，未触碰仓库 `data/`。

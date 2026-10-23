# QA 证据：WP1 账户与角色权限（QA1 / WBS 3.2）

| 项 | 内容 |
|---|---|
| 测试文件 | `tests/test_wp1_auth.py`（unittest，标准库，13 个用例） |
| 被测对象 | `src/main.py`、`src/db.py`、`src/auth.py`、`src/audit.py`（只读，未修改） |
| 契约依据 | `05-architecture.md` §1/§2/§4/§5、`04-scope.md` §6、`10-work-packages.md` WP1 |
| 隔离方式 | 每个用例建独立临时目录作为 cwd，CLI 显式传 `--db <临时库>`；会话文件因 cwd 隔离落在 `<临时目录>/data/session.json`（契约 §1 的相对路径），测试后 `shutil.rmtree` 清理 |
| 日期 / 执行者 | 2026-10-23 / QA（DeepSeek V4.1 Flash Free） |

## 1 执行的命令与真实结果

### 1.1 全量测试（唯一一次全量运行，不带 -v）

```
python -m unittest discover -s tests
```

实际输出：

```
.............
----------------------------------------------------------------------
Ran 13 tests in 8.762s

OK
EXIT=0
```

（首次带 `-v` 的定向运行同样 13 passed：`Ran 13 tests in 6.619s / OK`。）

### 1.2 手工复核 CLI 实际行为（临时库，不影响仓库 `data/`）

在临时目录内依次执行（`src/main.py` 绝对路径调用）：

| 命令 | 退出码 | stdout |
|---|---|---|
| `init-db --db qe.db` | 0 | `{"created": true, "db_path": "qe.db"}` |
| `init-db --db qe.db`（第二次） | 0 | `{"created": false, "db_path": "qe.db"}` |
| `seed --db qe.db` | 0 | `{"users": 8, "devices": 20, "requests": 0, "loans": 0}` |
| `seed --db qe.db`（第二次） | 1 | `{"error": "already_seeded", "message": "数据库已有数据，如需重建请使用 --reset"}` |
| `login --db qe.db --username student1 --password Passw0rd!` | 0 | `{"user_id": 1, "username": "student1", "role": "student"}` |
| `login ... --username student1 --password bad` | 1 | `{"error": "login_failed", "message": "用户名或口令错误"}` |
| `login ... --username ghost --password Passw0rd!` | 1 | `{"error": "login_failed", ...}` |
| `login --db qe.db --username admin`（缺 --password） | 2 | `{"error": "bad_args", "message": "the following arguments are required: --password"}` |
| `request list`（WP1 未注册） | 2 | `{"error": "bad_args", "message": "argument command: invalid choice: 'request' (choose from 'init-db', 'seed', 'login')"}` |

会话文件实际内容（登录 student1 后，`<临时目录>/data/session.json`）：

```json
{"username": "student1", "role": "student", "created_at": "2026-10-23T13:30:59Z"}
```

补充观察（`login` 成功 1 次 + 失败 1 次后的库内状态）：

```
audit rows: [(7,'admin','login','user',7,'ok'), (None,'student1','login',None,None,'denied')]
session after failed login: {'username': 'admin', 'role': 'admin', 'created_at': '2026-10-23T13:32:04Z'}
```

说明：PowerShell 控制台直显中文时出现乱码，但原始字节捕获为合法 UTF-8
（`b'{"error": "already_seeded", "message": "\xe6\x95\xb0... --reset"}'`），JSON 可正常解析，**不是**产品缺陷。

### 1.3 隔离核对

`data/deviceloan.db`（40960 B）与 `data/session.json`（76 B）的 `LastWriteTime` 在测试前后均为 `2026/10/23 21:28:11`，测试未触碰仓库运行期文件。`tests/__pycache__` 已在运行后清理。

## 2 逐条 TC 结论

| TC | 验证内容 | 对应用例 | 结论 |
|---|---|---|---|
| TC-CRQ-01-01 | 登录与角色分流 | `init_db_idempotent`、`seed_creates_8_users_20_devices`、`seed_twice_exits_1`、`login_returns_correct_role`（4 个用户）、`login_wrong_password_exits_1`、`login_unknown_user_exits_1`、`login_missing_args_exits_2`（3 种缺参）、`session_file_has_no_credentials` | **PASS** |
| TC-NFR-03-01 | 库中无明文口令 | `no_plaintext_password_in_db`：`password_hash`/`salt` 两列不含 `Passw0rd`；`qa.db`（含 `-wal`/`-journal`，实扫 1 个文件）字节扫描无 `b"Passw0rd"`；8 个盐互不相同、相同口令摘要互不相同；`auth.verify_password` 对正确口令 True、对 `Passw0rd!x` False；`iterations` 均 ≥ 100000 | **PASS** |
| TC-NFR-04-01 | student 调 admin 命令返回 3 | `student_denied_admin_actions`（单元：`auth.has_role(student,'admin')` False、`has_role(None,...)` False、`has_role(admin,'admin')` True、`has_role(director,'admin')` False / `has_role(director,'admin','director')` True）、`no_session_has_no_user`（`read_session()`/`current_user()` 返回 None） | **PASS（单元层面）** |
| TC-NFR-01-01 | 无第三方 import | `no_third_party_imports`：AST 解析 `src/` 下 4 个模块的 `Import`/`ImportFrom`，集合 ⊆ `sys.stdlib_module_names` ∪ `{main,db,auth,audit,devices,requests,loans,stats}`，差集为空 | **PASS** |

**TC-NFR-04-01 未做端到端验证的原因（契约所限，非 Dev 缺陷）**：WP1 卡片写明"未实现就不注册该子命令"，当前仅有 `init-db`/`seed`/`login` 三条命令，不存在 admin 专属命令可调。因此本包只在函数层锁定角色判定，`student 调 admin 命令 → 退出码 3` 的端到端回归**由 WP3 在注册 `request approve` 等命令后完成**（QA3 必测项）。

补充用例 `unimplemented_commands_not_registered`：验证 `request list` 当前不可调用（退出码 2，非 0），对应 WP1「不做什么」条款。

## 3 发现的问题

| ID | 等级 | 描述 | 期望 vs 实际 | 归属 |
|---|---|---|---|---|
| DEF-WP1-01 | 一般（契约冲突，非产品缺陷） | WP1 卡片退出标准写"无会话调 `request list` 退出码 3"，与同卡片"未实现就不注册该子命令"互相矛盾；`request` 子命令未注册时只能由 argparse 报参数错误 | 期望（退出标准）：3；实际：2 + `bad_args`。按"不注册"条款实现是唯一自洽解 | 需 PM/BA 裁定口径；若坚持 3，则 WP1 必须先注册受保护子命令（与"不做什么"冲突） |
| DEF-WP1-02 | 轻微（文档不一致） | `05-architecture.md` §4 的 `seed` 行"可能退出码"列写 `0, 2`，未列 `1`；实际重复 seed 返回 1（与 WP1 任务书要求一致，且符合全局"1=业务拒绝"定义） | 期望：文档与实现一致；实际：文档漏列 1 | BA 更新 §4 表格（建议补 1），不影响产品判定 |
| OBS-WP1-01 | 轻微（契约未规定） | 登录失败不清空既有会话文件：先以 admin 登录成功，再以 student1 错误口令登录（退出码 1），会话文件仍为 `admin` | 契约仅规定"login 直接覆盖写"（成功路径），未规定失败路径 | 契约未规定，不算缺陷；若 PM 认为需降权，作为 WP3 变更提出 |

其余均为契约未规定项，不计缺陷：
- 登录失败时 `audit_log.target_type/target_id` 为 NULL（§7 只要求记录 `result='denied'`，未规定失败时的 target）。
- `login` 在库无数据时返回 1（`login_failed`），契约未单列该场景，落在"1=登录失败"。
- 会话文件字段顺序 `username, role, created_at`（契约只规定字段集合）。

## 4 未覆盖 / 超出本包

- `seed --reset` 分支、`audit list` 查询、登录以外的审计事件：属 WP3/WP5 验收范围。
- `init-db` 对已存在但缺表的库的修复行为：契约未规定，未测。
- 性能（NFR-02）、时间格式全局一致性（NFR-07）：分属 WP2/WP5；本包仅顺带核对了 `devices.created_at` 与 `session.created_at` 的 `...Z` 格式。

## 5 结论

**PASS**（有 2 条文档/契约层面待 PM/BA 处理的事项，无产品级缺陷）。

- WP1 退出标准核对：`init-db`+`seed`+`login` 可跑通 ✅；错误口令退出码 1 ✅；"无会话调 `request list` 退出码 3" 因命令未注册无法成立（DEF-WP1-01，见上）。
- 严重缺陷 0 个，一般问题 1 个（契约冲突，非代码），轻微问题 2 个。
- QA 未修改任何产品代码；仅新增 `tests/test_wp1_auth.py` 与本证据文件。

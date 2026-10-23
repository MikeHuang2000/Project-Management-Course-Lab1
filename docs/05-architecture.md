# 架构与接口契约：DeviceLoan MVP

| 项目 | 内容 |
|---|---|
| 文档编号 / 版本 | 05-architecture v1.0 |
| 编制 | BA（DeepSeek V4.1 Flash Free） |
| 日期 | 2026-10-23 |
| 状态 | 待评审；一经 PM 批准即为 Dev 实现与 QA 测试的契约 |
| 上游依据 | `04-scope.md`、`00-customer-brief.md`、`02-charter.md` §7 |

技术基线：Python 3.11、标准库 + SQLite（`sqlite3`、`argparse`、`hashlib`、`json`、`datetime`）、命令行运行、零第三方依赖（NFR-01）。

## 1 文件布局（固定，Dev 必须照此实现）

| 文件 | 职责 | 边界（不做什么） | 工作包 |
|---|---|---|---|
| `src/main.py` | argparse 定义全部子命令、参数校验、分发、把结果统一序列化为 JSON 写到 stdout、退出码映射 | 不含 SQL、不含业务规则 | WP1 起，逐包加子命令 |
| `src/db.py` | 取连接、启用 `PRAGMA foreign_keys=ON`、建表 DDL、事务上下文 | 不含业务规则 | WP1 |
| `src/auth.py` | PBKDF2 口令哈希与校验、登录、会话文件读写、角色校验装饰器 | 不做审批 | WP1 |
| `src/devices.py` | 设备列表、按名称/类别检索、按时段判定可借 | 不写 `requests` 状态 | WP2 |
| `src/requests.py` | 提交、取消、列表、详情、批准、拒绝、**冲突判定** | 不改 `loans` | WP3 |
| `src/loans.py` | 借出、归还、逾期判定与逾期查询数据源 | 不改审批状态 | WP4 |
| `src/stats.py` | 借用次数、逾期率、设备利用率（口径见 §6） | 不写库 | WP5 |
| `src/audit.py` | 写审计记录、查询审计记录 | 不改业务数据 | WP5（表与写入在 WP1 即建立） |
| `tests/test_*.py` | unittest 测试，由 QA 编写 | Dev 不得代写测试 | 全部 |

运行期文件（不提交 git 亦可）：数据库 `data/deviceloan.db`（默认，`--db` 参数或环境变量 `DEVICELOAN_DB` 覆盖，QA 用独立库文件实现 NFR-05 隔离）；会话文件 `data/session.json`（登录后写入 `username`、`role`、`created_at`）。

会话判定规则（供 TC-CRQ-01-01 与权限矩阵的 `✗ 3` 使用）：会话无过期时间，`login` 直接覆盖写；除 `init-db`、`seed`、`login` 三条本地运维/登录命令外，缺少会话文件或会话角色与命令要求不符，一律返回退出码 3，不读业务表。参数校验先于会话校验：参数不合法（缺必填、取值不在枚举内、时间格式错误）一律返回 2，即使未登录。

依赖方向：`main.py` → 各业务模块 → `db.py`；`auth.py`、`audit.py` 被业务模块调用，不反向依赖 `main.py`。

## 2 数据模型

时间一律为 ISO 8601 UTC 字符串，秒级，形如 `2026-10-23T08:00:00Z`（NFR-07）。所有表主键为 `INTEGER PRIMARY KEY AUTOINCREMENT`。

**users**

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| username | TEXT | NOT NULL UNIQUE | 登录名 |
| password_hash | TEXT | NOT NULL | PBKDF2-HMAC-SHA256 十六进制摘要 |
| salt | TEXT | NOT NULL | 16 字节随机盐，十六进制 |
| iterations | INTEGER | NOT NULL DEFAULT 120000 | 迭代次数，不少于 100000（NFR-03） |
| role | TEXT | NOT NULL CHECK IN ('student','admin','director') | 教师按 student 处理（`04-scope.md` §5 假设） |
| display_name | TEXT | NOT NULL | 展示名，演示数据用虚构姓名 |
| created_at | TEXT | NOT NULL | |

**devices**

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| code | TEXT | NOT NULL UNIQUE | 资产编号，如 `DEV-001` |
| name | TEXT | NOT NULL | 如"STM32 开发板" |
| category | TEXT | NOT NULL | 如"开发板/测量仪器/便携设备" |
| status | TEXT | NOT NULL CHECK IN ('available','maintenance','retired') DEFAULT 'available' | 设备级状态；`maintenance/retired` 不可借 |
| note | TEXT | 可空 | |
| created_at | TEXT | NOT NULL | |

**requests**（状态机：`pending → approved | rejected | cancelled`，终态不可再变更）

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| device_id | INTEGER | NOT NULL REFERENCES devices(id) | |
| user_id | INTEGER | NOT NULL REFERENCES users(id) | 申请人 |
| purpose | TEXT | NOT NULL | 用途 |
| start_at | TEXT | NOT NULL | 半开区间左端 |
| end_at | TEXT | NOT NULL | 半开区间右端 |
| status | TEXT | NOT NULL CHECK IN ('pending','approved','rejected','cancelled') DEFAULT 'pending' | |
| reject_reason | TEXT | 可空；`rejected` 时必填（应用层校验） | |
| decided_by | INTEGER | 可空 REFERENCES users(id) | 审批人 |
| decided_at | TEXT | 可空 | |
| created_at | TEXT | NOT NULL | |

应用层约束：`end_at > start_at`；同一 `user_id` 对同一 `device_id` 只允许一条 `pending` 申请。

**loans**

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| request_id | INTEGER | NOT NULL UNIQUE REFERENCES requests(id) | 一条已批准申请只能借出一次 |
| device_id | INTEGER | NOT NULL REFERENCES devices(id) | 冗余，便于统计 |
| user_id | INTEGER | NOT NULL REFERENCES users(id) | 冗余，便于统计 |
| checked_out_at | TEXT | NOT NULL | 实际借出时间 |
| due_at | TEXT | NOT NULL | 应还时间，取对应申请的 `end_at` |
| returned_at | TEXT | 可空 | 空 = 未归还 |
| created_at | TEXT | NOT NULL | |

逾期判定（唯一口径）：`returned_at IS NULL AND 当前时间 > due_at`（未还逾期）或 `returned_at > due_at`（逾期归还）。

**audit_log**

| 列 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK | |
| at | TEXT | NOT NULL | 事件时间（UTC） |
| actor_id | INTEGER | 可空 REFERENCES users(id) | 系统事件或登录失败时可空 |
| actor_name | TEXT | NOT NULL | 冗余登录名，便于追溯 |
| action | TEXT | NOT NULL | 事件类型，见 §7 |
| target_type | TEXT | 可空 | `user / device / request / loan` |
| target_id | INTEGER | 可空 | |
| detail | TEXT | 可空 | JSON 字符串，如拒绝原因、冲突对象 id |
| result | TEXT | NOT NULL CHECK IN ('ok','denied','error') | |

**不建 waitlist 表**：CRQ-10 不在基线（`04-scope.md` §6）。

## 3 冲突规则（CRQ-05 唯一判定口径）

1. 时段按半开区间 `[start, end)` 判定。
2. 冲突条件：`new.start < existing.end AND new.end > existing.start`。
3. 只对同一 `device_id`、且状态为 `approved` 的 `requests`，以及该设备未归还的 `loans`（`returned_at IS NULL`）做判定。
   - `requests` 按申请自身的 `[start_at, end_at)` 占位。
   - **未归还的 `loans` 为无结束时间的占用**：只要 `new.end > checked_out_at` 即冲突（不看 `due_at`）。理由：设备没还回来，后续任何时段都不能再批准，否则会出现"已逾期未还却被再次批准"。归还后（`returned_at` 非空）该占用立即解除。
   - 同一条申请与其对应借出记录只计 1 次冲突。
4. `rejected` / `cancelled` 不占用时段；`pending` 不占用（多条 pending 可并存，由审批时兜底）。
5. 首尾相接（前一段 `end == 后一段 start`）**不算冲突**。
6. 只在 `request approve` 时判定；`request submit` 不做冲突判定，避免出现两套口径。
7. 审批在一个数据库事务内完成：先写 `status='approved'`、`decided_by`、`decided_at`，再复查冲突；冲突则整事务回滚、库中无任何变更、返回退出码 4，stdout 输出 `{"error":"time_conflict","conflicts":[{"request_id":..,"start_at":..,"end_at":..}]}`。

## 4 CLI 契约

统一约定：所有命令把结果以单行 JSON 写到 stdout，错误也写 `{"error":"<code>","message":"<中文说明>"}`；不向 stdout 输出非 JSON 文本；日志与诊断写 stderr。全局可选参数 `--db <path>`。

| 命令 | 参数（必填 / 可选） | stdout JSON 要点 | 可能退出码 |
|---|---|---|---|
| `init-db` | 无 | `{"created":true,"db_path":..}` | 0, 2 |
| `seed` | `--reset`（可选，清空后重建） | `{"users":8,"devices":20,"requests":N,"loans":M}` | 0, 1（已初始化）, 2 |
| `login` | `--username`、`--password`（必填） | `{"user_id":..,"username":..,"role":..}`，并写会话文件 | 0, 1, 2 |
| `device list` | `--category`、`--status`（可选） | `{"items":[{"id","code","name","category","status"}]}` | 0, 2, 3 |
| `device search` | `--name`、`--category`、`--from`、`--to`（至少给 1 个；`--from/--to` 必须成对） | `{"items":[{"id","code","name","category","available","conflicts":N}]}` | 0, 2, 3 |
| `request submit` | `--device`、`--from`、`--to`、`--purpose`（全必填） | `{"request_id":..,"status":"pending"}` | 0, 1, 2, 3 |
| `request cancel` | `--request-id`（必填） | `{"request_id":..,"status":"cancelled"}` | 0, 1, 2, 3 |
| `request list` | `--status`、`--all`（可选；`--all` 仅 admin） | `{"items":[{"request_id","device_id","user_id","start_at","end_at","status"}]}` | 0, 2, 3 |
| `request show` | `--request-id`（必填） | 单条完整字段 + `loan` 摘要（可空） | 0, 1, 2, 3 |
| `request approve` | `--request-id`（必填） | `{"request_id":..,"status":"approved","decided_at":..}` | 0, 1, 2, 3, 4 |
| `request reject` | `--request-id`、`--reason`（必填） | `{"request_id":..,"status":"rejected","reject_reason":..}` | 0, 1, 2, 3 |
| `loan checkout` | `--request-id`（必填） | `{"loan_id":..,"request_id":..,"due_at":..}` | 0, 1, 2, 3 |
| `loan return` | `--loan-id`（必填） | `{"loan_id":..,"returned_at":..,"overdue":bool,"days_late":N}` | 0, 1, 2, 3 |
| `stats usage` | `--from`、`--to`（必填） | `{"range":{..},"overdue_rate":x,"devices":[{"device_id","borrow_count","utilization","overbooked"}]}` | 0, 1, 2, 3 |
| `stats overdue` | `--from`、`--to`（可选，默认全期间） | `{"items":[{"loan_id","request_id","device_id","due_at","returned_at","days_late"}]}` | 0, 3 |
| `audit list` | `--action`、`--user`、`--from`、`--to`、`--limit`（可选，默认 50） | `{"items":[{"at","actor_name","action","target_type","target_id","result"}]}` | 0, 2, 3 |

退出码（全局统一，不得扩增）：`0` 成功；`1` 业务拒绝（无权限操作他人数据、状态不允许、重复借出、登录失败）；`2` 参数错误（缺参、时间格式非法、`end <= start`）；`3` 未登录或角色不符；`4` 时段冲突（仅 `request approve`）。

区分口径：`3` 看"你是谁"，`1` 看"这件事能不能做"，`4` 看"时段是否重叠"。

## 5 权限矩阵（NFR-04）

| 命令 | student | admin | director |
|---|---|---|---|
| `init-db`、`seed` | 本地运维命令，无需登录 | 同左 | 同左 |
| `login` | ✓ | ✓ | ✓ |
| `device list` / `device search` | ✓ | ✓ | ✓ |
| `request submit` | ✓（本人） | ✗ 3 | ✗ 3 |
| `request cancel` | ✓ 仅本人且 `pending`，否则 1 | ✗ 3 | ✗ 3 |
| `request list` / `request show` | ✓ 仅本人（他人 → 1） | ✓ 全部 | ✗ 3 |
| `request approve` / `request reject` | ✗ 3 | ✓ | ✗ 3 |
| `loan checkout` / `loan return` | ✗ 3 | ✓ | ✗ 3 |
| `stats usage` / `stats overdue` | ✗ 3 | ✓ | ✓（只读） |
| `audit list` | ✗ 3 | ✓ | ✗ 3 |

`--all` 仅 admin 可用；student 传 `--all` 视为角色不符，退出码 3。

## 6 统计口径（CRQ-07，公式写死）

统计区间 `[from, to)`，单位秒。

| 指标 | 公式 | 边界 |
|---|---|---|
| 借用次数（按设备） | 该设备 `start_at ∈ [from, to)` 且 `status='approved'` 的申请条数 | 按申请开始时间归属区间 |
| 逾期率 | 逾期归还的借出记录数 ÷ `returned_at` 非空的借出记录数 | 分母为 0 时返回 `0`；未归还但已超过 `due_at` 的记录不计入分母，只在 `stats overdue` 列出 |
| 设备利用率（按设备） | Σ（该设备每条 `approved` 申请的 `[start_at, end_at)` 与 `[from, to)` 的交集秒数）÷ (to − from) | 结果 > 1 时按 1 输出并置 `overbooked=true`；保留 4 位小数；`to <= from` 时退出码 2 |

`days_late = max(1, ceil(逾期秒数 / 86400))`（逾期秒数 = `returned_at` 或当前时间 − `due_at`，不足 1 天记 1 天）。

逾期率的取数范围：`due_at ∈ [from, to)` 的借出记录，保证同一区间可重复核对。

## 7 审计日志（CRQ-08）

必须记录的 6 类事件（`action` 取值固定）：

| action | 触发点 | target_type / target_id | detail 要点 |
|---|---|---|---|
| `login` | 登录成功（失败记 `result='denied'`） | user / 用户 id | 无 |
| `request_submit` | 提交申请成功 | request / 新 id | device_id、start_at、end_at |
| `request_approve` | 批准成功 | request / id | 无 |
| `request_reject` | 拒绝成功 | request / id | reason |
| `loan_checkout` | 借出登记成功 | loan / 新 id | request_id、due_at |
| `loan_return` | 归还登记成功 | loan / id | returned_at、overdue |

`request_cancel` 允许记录，但不在验收范围。审计写入与被审计的业务操作在同一事务内，业务失败时审计记录同样回滚（登录失败除外，单独提交）。

## 8 契约稳定性

- Dev 不得修改命令名、参数名、退出码、JSON 字段名与表结构；实现与本文不一致时以本文为准并报 PM。
- 需要变更（含新增命令、字段、CRQ-10 相关表）一律由 PM 提交 CCB；未批准前不得进入代码。
- 本文档版本随变更递增：v1.0 → v1.1 …；每次变更在文末留一行变更记录。

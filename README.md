# 实验室设备借用管理系统（DeviceLoan MVP）

命令行原型，Python 3.11 标准库 + SQLite，无第三方依赖。用于演示"登录—查询—申请—审批—借出—归还—统计—审计"的完整借用流程。

## 快速开始

```powershell
python src/main.py init-db --db data/deviceloan.db
python src/main.py seed --db data/deviceloan.db
python src/main.py login --username admin --password Passw0rd! --db data/deviceloan.db
python src/main.py device list --db data/deviceloan.db
```

候补队列（CR-02 二期）：

```powershell
# 学生登记候补
python src/main.py login --username student1 --password Passw0rd! --db data/deviceloan.db
python src/main.py waitlist join --device DEV-001 --from 2026-11-03T08:00:00Z --to 2026-11-03T12:00:00Z --note 课程实验 --db data/deviceloan.db
python src/main.py waitlist list --db data/deviceloan.db

# 管理员查看全部候补
python src/main.py login --username admin --password Passw0rd! --db data/deviceloan.db
python src/main.py waitlist list --all --db data/deviceloan.db
```

候补只做“登记 + 名单”，不做通知、自动递补、取消候补；候补记录不占用时段，不影响 `request approve` 的冲突判定。

一键生成演示数据（含一次完整的申请—批准—借出—归还）：

```powershell
python scripts/demo.py --db data/demo.db --force
```

运行测试：

```powershell
python -m unittest discover -s tests
```

## 使用须知（C2）

1. **时间一律按 UTC 解释**。`2026-11-03T08:00:00Z` 与 `2026-11-03T08:00:00` 等价；如果按北京时间填写，请显式写成 `2026-11-03T08:00:00+08:00` 或换算成 UTC，否则实际时段会相差 8 小时。
2. **单机单会话**。会话保存在本地 JSON 文件（默认 `data/session.json`，可用环境变量 `DEVICELOAN_SESSION` 指向别处），同一时刻只保留最近一次登录的身份；不是多用户并发系统。
3. **按设备名称检索**。`device search --name` 支持名称模糊匹配，输入 `DEV-001` 这类资产编号会返回空列表（编号精确查询不在本版范围，见遗留清单 R-UAT-06）。
4. **角色**：`student`（提交/取消自己的申请）、`admin`（审批、借出、归还、查看审计）、`director`（只读统计）。

## 目录

| 路径 | 内容 |
|---|---|
| `src/` | 实现（`db` / `auth` / `audit` / `devices` / `requests` / `waitlist` / `loans` / `stats` / `main`） |
| `tests/` | 84 条自动化测试（一期 76 + 二期候补 8） |
| `scripts/demo.py` | 演示数据脚本 |
| `docs/` | 过程文档（商业论证、章程、范围、架构、WBS、进度、成本、风险质量、工作包） |
| `docs/evidence/` | 各阶段收口记录、验收证据、变更与追认记录 |
| `plan/` | 计划与台账（任务、人日、完成度、EVM、甘特图） |
| `plan/tasks-cr02.csv` | 二期 CR-02 的 5 个任务（2.5 天，2026-11-30 起） |
| `plan/schedule-cr02.md` | 二期排期表（ES/EF/关键路径） |
| `plan/gantt-cr02.png` | 一期 + 二期组合甘特图（一期 18.75 天 + 二期 2.5 天） |
| `plan/track-cr02.png` | 二期追踪甘特图（CPI/SPI 1.00） |
| `wbs/wbs.xml` | 一期 30 任务详细 WBS（结构归档） |
| `wbs/wbs-msp.xml` | 一期整日版 WBS（MS Project 截图用，19.75 天） |
| `wbs/wbs-cr02-msp.xml` | 二期 WBS（MS Project 截图用，2.5 天） |
| `wbs/wbs-all-msp.xml` | 一期 + 二期合并 WBS（单张截图可选） |

## 已知限制

- 候补队列（CRQ-10）已按 CR-02 在二期交付：仅“登记 + 名单”，不含通知、自动递补、取消候补；一期 16 条基线与 EVM 不变。
- 逾期天数按自然日向上取整，最小记 1 天。
- 未登录时，参数错误优先于身份校验返回 2，其余返回 3。

"""QA5（WBS 3.10）验收测试：WP5 统计与审计 + 演示数据脚本。

契约依据：docs/05-architecture.md §4（stats usage / stats overdue / audit list 参数
与退出码）、§5（权限矩阵）、§6（统计口径公式）、§7（审计事件）；
docs/04-scope.md §6 TC-CRQ-07-01、TC-CRQ-08-01、TC-NFR-06-01、TC-NFR-05-01。

调用方式：子进程执行 CLI，cwd 为临时目录，显式传 --db <临时库>，会话文件落在
<临时目录>/data/session.json（契约 §1），不污染 data/。

两点数据构造说明：
1) 「利用率 > 1」在正常流程下不可达（approve 会拦截时段重叠，且 conflicts 判定
   保证同一设备 approved 申请互不重叠）。为验证 §6 的截断口径，本文件在**临时库**
   里直接插入重叠的 approved 申请，只改测试数据，不改产品代码。
2) 审计过滤测试需要 >50 条且 at 各异的记录；CLI 写审计的 at 为秒级，同一秒内多条
   无法稳定断言排序，故在临时库里直接插入构造好的 audit_log 行。
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "src", "main.py")
DEMO = os.path.join(ROOT, "scripts", "demo.py")

SEED_PASSWORD = "Passw0rd!"

# stats usage 的固定统计区间：2027-01-01 00:00 ~ 2027-01-11 00:00，共 10 天 = 864000 秒
RANGE_FROM = "2027-01-01T00:00:00Z"
RANGE_TO = "2027-01-11T00:00:00Z"


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_now(offset_seconds):
    """相对真实当前时间偏移（秒）的 ISO 时间；用于逾期相关用例。"""
    return iso(datetime.now(timezone.utc) + timedelta(seconds=offset_seconds))


class WP5TestBase(unittest.TestCase):
    """公共脚手架：临时库、临时会话文件、CLI 调用。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-wp5-")
        self.db = os.path.join(self.tmp, "qa.db")
        self.session_file = os.path.join(self.tmp, "data", "session.json")
        self.env = dict(os.environ)
        self.env.pop("DEVICELOAN_DB", None)
        self.env.pop("DEVICELOAN_SESSION", None)
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 基础设施 ----
    def cli(self, *args):
        return subprocess.run(
            [sys.executable, MAIN] + list(args),
            cwd=self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def payload(self, proc):
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, "stdout 应为单行 JSON，实际: %r" % proc.stdout)
        return json.loads(lines[0])

    def query(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def exec_sql(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def seed(self):
        proc = self.cli("seed", "--db", self.db)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.users = dict(self.query("SELECT username, id FROM users"))
        self.devices = dict(self.query("SELECT code, id FROM devices"))

    def login(self, username):
        proc = self.cli(
            "login", "--db", self.db, "--username", username, "--password", SEED_PASSWORD
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)

    def logout(self):
        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def submit(self, device, window, purpose="课程实验"):
        start, end = window
        return self.cli(
            "request", "submit", "--db", self.db,
            "--device", device, "--from", start, "--to", end, "--purpose", purpose,
        )

    def submitted(self, device, window, purpose="课程实验", user="student1"):
        self.login(user)
        proc = self.submit(device, window, purpose)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)["request_id"]

    def approve(self, request_id):
        return self.cli("request", "approve", "--db", self.db, "--request-id", str(request_id))

    def approved(self, device, window, user="student1"):
        rid = self.submitted(device, window, user=user)
        self.login("admin")
        proc = self.approve(rid)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return rid

    def checkout(self, request_id):
        return self.cli("loan", "checkout", "--db", self.db, "--request-id", str(request_id))

    def do_return(self, loan_id):
        return self.cli("loan", "return", "--db", self.db, "--loan-id", str(loan_id))

    def checked_out(self, device, window):
        """返回 (request_id, loan_id)，不归还。"""
        rid = self.approved(device, window)
        proc = self.checkout(rid)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return rid, self.payload(proc)["loan_id"]

    def returned(self, device, window):
        rid, loan_id = self.checked_out(device, window)
        proc = self.do_return(loan_id)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return rid, loan_id, self.payload(proc)

    def stats_usage(self, start=RANGE_FROM, end=RANGE_TO):
        return self.cli("stats", "usage", "--db", self.db, "--from", start, "--to", end)

    def stats_overdue(self, *extra):
        return self.cli("stats", "overdue", "--db", self.db, *extra)

    def audit_list(self, *extra):
        return self.cli("audit", "list", "--db", self.db, *extra)

    def usage_by_device(self, body):
        return {item["device_id"]: item for item in body["devices"]}

    def insert_approved_request(self, device, start, end, user="student1"):
        self.exec_sql(
            "INSERT INTO requests (device_id, user_id, purpose, start_at, end_at, status,"
            " decided_by, decided_at, created_at) VALUES (?, ?, '构造数据', ?, ?, 'approved', ?, ?, ?)",
            (
                self.devices[device],
                self.users[user],
                start,
                end,
                self.users["admin"],
                "2027-01-01T00:00:00Z",
                "2027-01-01T00:00:00Z",
            ),
        )

    def craft_audit(self, count=60):
        """清空审计表后插入 count 条 at 各异的记录（i%3==0 → login，i%2==0 → student1）。"""
        self.exec_sql("DELETE FROM audit_log")
        conn = sqlite3.connect(self.db)
        try:
            for i in range(count):
                at = "2030-01-01T00:%02d:00Z" % i
                action = "login" if i % 3 == 0 else "request_submit"
                actor = "student1" if i % 2 == 0 else "admin"
                conn.execute(
                    "INSERT INTO audit_log (at, actor_id, actor_name, action, target_type,"
                    " target_id, detail, result) VALUES (?, NULL, ?, ?, 'request', ?, NULL, 'ok')",
                    (at, actor, action, i),
                )
            conn.commit()
        finally:
            conn.close()


class StatsUsageTest(WP5TestBase):
    """TC-CRQ-07-01：借用次数、利用率（§6 公式逐条核对）。"""

    def test_tc_crq_07_01_borrow_count_and_utilization(self):
        self.seed()
        # DEV-001：整段落在区间内，12 小时
        self.approved("DEV-001", ("2027-01-02T00:00:00Z", "2027-01-02T12:00:00Z"))
        # DEV-002：start_at 在区间外（区间内取 2 小时），借出次数应为 0
        self.approved("DEV-002", ("2026-12-31T22:00:00Z", "2027-01-01T02:00:00Z"))
        # DEV-003：两条不重叠的 approved 申请
        self.approved("DEV-003", ("2027-01-05T00:00:00Z", "2027-01-06T00:00:00Z"))
        self.approved("DEV-003", ("2027-01-08T00:00:00Z", "2027-01-08T06:00:00Z"))
        # DEV-004 rejected / DEV-005 cancelled / DEV-006 pending：均不计入
        rid = self.submitted("DEV-004", ("2027-01-03T00:00:00Z", "2027-01-04T00:00:00Z"))
        self.login("admin")
        self.assertEqual(
            self.cli("request", "reject", "--db", self.db,
                     "--request-id", str(rid), "--reason", "时段已满").returncode,
            0,
        )
        rid = self.submitted("DEV-005", ("2027-01-03T00:00:00Z", "2027-01-04T00:00:00Z"))
        self.assertEqual(
            self.cli("request", "cancel", "--db", self.db, "--request-id", str(rid)).returncode, 0
        )
        self.submitted("DEV-006", ("2027-01-03T00:00:00Z", "2027-01-04T00:00:00Z"))

        self.login("admin")
        proc = self.stats_usage()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["range"], {"from": RANGE_FROM, "to": RANGE_TO})
        self.assertEqual(body["overdue_rate"], 0, "无借出记录时逾期率为 0")
        items = self.usage_by_device(body)
        self.assertEqual(len(body["devices"]), 20, "20 台设备应全部列出")

        span = 864000.0  # 10 天
        expect = {
            "DEV-001": (1, 43200 / span),        # 0.05
            "DEV-002": (0, 7200 / span),         # 0.008333… → 0.0083
            "DEV-003": (2, 108000 / span),       # 0.125
            "DEV-004": (0, 0.0),
            "DEV-005": (0, 0.0),
            "DEV-006": (0, 0.0),
        }
        for code, (count, util) in expect.items():
            item = items[self.devices[code]]
            self.assertEqual(item["borrow_count"], count, "%s borrow_count" % code)
            self.assertEqual(item["utilization"], round(util, 4), "%s utilization" % code)
            self.assertIs(item["overbooked"], False, "%s overbooked" % code)
        # 保留 4 位小数
        self.assertEqual(items[self.devices["DEV-002"]]["utilization"], 0.0083)
        self.assertEqual(items[self.devices["DEV-001"]]["utilization"], 0.05)
        for item in body["devices"]:
            self.assertEqual(item["utilization"], round(item["utilization"], 4))
            self.assertGreaterEqual(item["utilization"], 0)
            self.assertLessEqual(item["utilization"], 1)

    def test_utilization_clamped_when_overbooked(self):
        """§6：> 1 截为 1 且 overbooked=true；恰为 1 时 overbooked=false。"""
        self.seed()
        # 同设备两条重叠 approved 申请，合计 14 天占 10 天区间
        self.insert_approved_request(
            "DEV-001", "2027-01-01T00:00:00Z", "2027-01-08T00:00:00Z"
        )
        self.insert_approved_request(
            "DEV-001", "2027-01-03T00:00:00Z", "2027-01-10T00:00:00Z"
        )
        # 恰好吃满区间
        self.insert_approved_request(
            "DEV-002", "2027-01-01T00:00:00Z", "2027-01-11T00:00:00Z"
        )

        self.login("admin")
        proc = self.stats_usage()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.usage_by_device(self.payload(proc))

        over = items[self.devices["DEV-001"]]
        self.assertEqual(over["borrow_count"], 2)
        self.assertEqual(over["utilization"], 1.0, ">1 应截为 1")
        self.assertIs(over["overbooked"], True)

        exact = items[self.devices["DEV-002"]]
        self.assertEqual(exact["borrow_count"], 1)
        self.assertEqual(exact["utilization"], 1.0)
        self.assertIs(exact["overbooked"], False, "恰好 1 不算 overbooked")

    def test_usage_empty_range_is_all_zero(self):
        """区间内无 approved 申请、无借出记录 → 全 0，且 overdue_rate=0（不报错）。"""
        self.seed()
        self.approved("DEV-001", ("2027-01-02T00:00:00Z", "2027-01-02T12:00:00Z"))
        self.login("admin")
        proc = self.stats_usage("2025-01-01T00:00:00Z", "2025-01-11T00:00:00Z")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["overdue_rate"], 0)
        for item in body["devices"]:
            self.assertEqual(item["borrow_count"], 0, item)
            self.assertEqual(item["utilization"], 0.0, item)
            self.assertIs(item["overbooked"], False, item)

    def test_usage_rejects_to_not_after_from(self):
        """§6：to <= from → 退出码 2；参数校验先于会话校验。"""
        self.seed()
        cases = [
            ("to == from", ("2027-01-01T00:00:00Z", "2027-01-01T00:00:00Z")),
            ("to < from", ("2027-01-02T00:00:00Z", "2027-01-01T00:00:00Z")),
            ("非法时间格式", ("not-a-time", "2027-01-11T00:00:00Z")),
        ]
        for label, (start, end) in cases:
            with self.subTest(case=label, session="anon"):
                self.logout()
                proc = self.stats_usage(start, end)
                self.assertEqual(proc.returncode, 2, label + ": " + proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))
            with self.subTest(case=label, session="admin"):
                self.login("admin")
                proc = self.stats_usage(start, end)
                self.assertEqual(proc.returncode, 2, label + ": " + proc.stdout + proc.stderr)
        # 缺必填参数 → 2
        self.logout()
        proc = self.cli("stats", "usage", "--db", self.db, "--from", RANGE_FROM)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)


class OverdueStatsTest(WP5TestBase):
    """TC-CRQ-07-01：逾期率与逾期清单（§6）。"""

    def test_overdue_rate_formula(self):
        """逾期率 = 逾期归还数 ÷ 已还数；未归还但已逾期者不进分母。"""
        self.seed()
        # A：已归还且逾期（due 在 3.5 天前）
        _, a_loan, a_body = self.returned(
            "DEV-001", (iso_now(-5.5 * 86400), iso_now(-3.5 * 86400))
        )
        self.assertIs(a_body["overdue"], True)
        # B：已归还且准时（due 在未来）
        _, b_loan, b_body = self.returned(
            "DEV-002", (iso_now(1.5 * 86400), iso_now(2.5 * 86400))
        )
        self.assertIs(b_body["overdue"], False)
        # C：未归还但已逾期（只进逾期清单，不进分母）
        _, c_loan = self.checked_out(
            "DEV-003", (iso_now(-2.5 * 86400), iso_now(-1.5 * 86400))
        )

        self.login("admin")
        proc = self.stats_usage(iso_now(-10 * 86400), iso_now(10 * 86400))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["overdue_rate"], 0.5, "1 逾期 ÷ 2 已还 = 0.5: %r" % body)
        # 未归还记录不计入分母：若计入则为 2/3
        self.assertNotAlmostEqual(body["overdue_rate"], round(2 / 3, 4), places=4)

        rows = self.query(
            "SELECT id, returned_at FROM loans WHERE id IN (?, ?, ?) ORDER BY id",
            (a_loan, b_loan, c_loan),
        )
        self.assertEqual(len(rows), 3)
        self.assertIsNotNone(dict(rows)[a_loan])
        self.assertIsNotNone(dict(rows)[b_loan])
        self.assertIsNone(dict(rows)[c_loan])

    def test_overdue_rate_zero_denominator(self):
        """无已还记录 → 分母为 0 → 返回 0，不报错。"""
        self.seed()
        self.checked_out("DEV-001", (iso_now(-2.5 * 86400), iso_now(-1.5 * 86400)))
        self.checked_out("DEV-002", (iso_now(1.5 * 86400), iso_now(2.5 * 86400)))

        self.login("admin")
        proc = self.stats_usage(iso_now(-10 * 86400), iso_now(10 * 86400))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["overdue_rate"], 0)
        # 未还与已还的区分只体现在逾期清单里
        proc = self.stats_overdue()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(len(self.payload(proc)["items"]), 1, "只列未还且已逾期的 1 条")

    def test_overdue_list_returned_and_unreturned(self):
        """已还逾期与未还逾期都列出；准时归还、未到 due_at 的不列出；days_late 按 §6。"""
        self.seed()
        _, a_loan, _ = self.returned(
            "DEV-001", (iso_now(-5.5 * 86400), iso_now(-3.5 * 86400))
        )  # 逾期归还，约 3.5 天 → 4
        _, b_loan, _ = self.returned(
            "DEV-002", (iso_now(1.5 * 86400), iso_now(2.5 * 86400))
        )  # 准时归还
        _, c_loan = self.checked_out(
            "DEV-003", (iso_now(-2.5 * 86400), iso_now(-1.5 * 86400))
        )  # 未还逾期，约 1.5 天 → 2
        _, d_loan = self.checked_out(
            "DEV-004", (iso_now(1.5 * 86400), iso_now(2.5 * 86400))
        )  # 未还但未到 due_at
        _, e_loan = self.checked_out(
            "DEV-005", (iso_now(-1.5 * 86400), iso_now(-60))
        )  # 未还逾期 60 秒 → 不足 1 天记 1

        self.login("admin")
        proc = self.stats_overdue()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        by_loan = {item["loan_id"]: item for item in items}

        self.assertIn(a_loan, by_loan, "已还逾期必须列出")
        self.assertIn(c_loan, by_loan, "未还逾期必须列出")
        self.assertIn(e_loan, by_loan)
        self.assertNotIn(b_loan, by_loan, "准时归还不应出现")
        self.assertNotIn(d_loan, by_loan, "未还但未到 due_at 不应出现")

        self.assertEqual(by_loan[a_loan]["days_late"], 4, by_loan[a_loan])
        self.assertEqual(by_loan[c_loan]["days_late"], 2, by_loan[c_loan])
        self.assertEqual(by_loan[e_loan]["days_late"], 1, "不足 1 天记 1 天")
        self.assertIsNotNone(by_loan[a_loan]["returned_at"])
        self.assertIsNone(by_loan[c_loan]["returned_at"])
        # 字段齐备
        self.assertEqual(
            sorted(by_loan[a_loan].keys()),
            ["days_late", "device_id", "due_at", "loan_id", "request_id", "returned_at"],
        )

    def test_overdue_range_filter(self):
        """--from/--to 按 due_at ∈ [from, to) 过滤。"""
        self.seed()
        _, a_loan, _ = self.returned(
            "DEV-001", (iso_now(-5.5 * 86400), iso_now(-3.5 * 86400))
        )
        _, c_loan = self.checked_out(
            "DEV-003", (iso_now(-2.5 * 86400), iso_now(-1.5 * 86400))
        )

        self.login("admin")
        proc = self.stats_overdue(
            "--from", iso_now(-4 * 86400), "--to", iso_now(-3 * 86400)
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ids = [item["loan_id"] for item in self.payload(proc)["items"]]
        self.assertEqual(ids, [a_loan], "只应命中 due_at 落在区间内的记录")
        self.assertNotIn(c_loan, ids)


class StatsPermissionTest(WP5TestBase):
    """§5 权限矩阵：stats usage / overdue —— student ✗3，admin ✓，director ✓（只读）。"""

    def test_stats_permission_matrix(self):
        self.seed()
        self.approved("DEV-001", ("2027-01-02T00:00:00Z", "2027-01-02T12:00:00Z"))

        for username, expected in (("student1", 3), ("director", 0), ("admin", 0)):
            self.login(username)
            for label, proc in (
                ("usage", self.stats_usage()),
                ("overdue", self.stats_overdue()),
            ):
                with self.subTest(user=username, cmd=label):
                    self.assertEqual(proc.returncode, expected, label + ": " + proc.stdout)
                    body = self.payload(proc)
                    if expected == 3:
                        self.assertIn("error", body)
                    else:
                        self.assertNotIn("error", body)

        self.logout()
        for label, proc in (
            ("usage", self.stats_usage()),
            ("overdue", self.stats_overdue()),
        ):
            with self.subTest(user="anon", cmd=label):
                self.assertEqual(proc.returncode, 3, label + ": " + proc.stdout)
                self.assertIn("error", self.payload(proc))


class AuditListTest(WP5TestBase):
    """TC-CRQ-08-01 / TC-NFR-06-01：audit list 默认条数、倒序与过滤。"""

    def test_tc_crq_08_01_audit_list_default_limit_and_order(self):
        self.seed()
        self.login("admin")
        self.craft_audit(60)

        proc = self.audit_list()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(len(items), 50, "默认最多 50 条")
        ats = [item["at"] for item in items]
        self.assertEqual(ats, sorted(ats, reverse=True), "应按 at 倒序")
        self.assertEqual(ats[0], "2030-01-01T00:59:00Z", "首条应是最新记录")
        self.assertEqual(
            sorted(items[0].keys()),
            ["action", "actor_name", "at", "result", "target_id", "target_type"],
        )
        self.assertEqual(
            self.query("SELECT count(*) FROM audit_log")[0][0], 60, "查询不应改动审计表"
        )

    def test_tc_nfr_06_01_audit_filters(self):
        self.seed()
        self.login("admin")
        self.craft_audit(60)

        default_items = self.payload(self.audit_list())["items"]

        # --action
        proc = self.audit_list("--action", "login")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(len(items), 20, "i%3==0 共 20 条 login")
        self.assertTrue(all(item["action"] == "login" for item in items))

        # --user
        proc = self.audit_list("--user", "student1")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(len(items), 30, "i%2==0 共 30 条 student1")
        self.assertTrue(all(item["actor_name"] == "student1" for item in items))

        # --from / --to（[from, to)）
        proc = self.audit_list(
            "--from", "2030-01-01T00:10:00Z", "--to", "2030-01-01T00:20:00Z"
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(len(items), 10, "%r" % [i["at"] for i in items])
        self.assertTrue(
            all("2030-01-01T00:10:00Z" <= i["at"] < "2030-01-01T00:20:00Z" for i in items)
        )

        # --limit
        proc = self.audit_list("--limit", "5")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(len(items), 5)
        self.assertEqual(items, default_items[:5], "--limit 应取倒序后的前 N 条")

        # 组合过滤
        proc = self.audit_list("--action", "login", "--user", "student1", "--limit", "3")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertEqual((item["action"], item["actor_name"]), ("login", "student1"))

    def test_audit_list_rejects_bad_limit(self):
        self.seed()
        self.login("admin")
        self.craft_audit(5)
        for value in ("0", "-1"):
            with self.subTest(limit=value):
                proc = self.audit_list("--limit", value)
                self.assertEqual(proc.returncode, 2, value + ": " + proc.stdout)
                self.assertIn("error", self.payload(proc))

    def test_audit_permission_matrix(self):
        """§5：audit list 仅 admin；student/director → 3，未登录 → 3。"""
        self.seed()
        self.login("admin")
        self.craft_audit(5)

        for username, expected in (("student1", 3), ("director", 3), ("admin", 0)):
            self.login(username)
            with self.subTest(user=username):
                proc = self.audit_list()
                self.assertEqual(proc.returncode, expected, username + ": " + proc.stdout)
                body = self.payload(proc)
                if expected == 3:
                    self.assertIn("error", body)
                else:
                    # 期间各角色 login 也会写审计，故用 >= 构造条数
                    self.assertGreaterEqual(len(body["items"]), 5)

        self.logout()
        proc = self.audit_list()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("error", self.payload(proc))


class DemoScriptTest(WP5TestBase):
    """TC-NFR-05-01：演示数据脚本（临时库，不污染 data/）。"""

    def run_demo(self, *extra):
        return subprocess.run(
            [sys.executable, DEMO, "--db", self.db] + list(extra),
            cwd=self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def counts(self):
        conn = sqlite3.connect("file:%s?mode=ro" % self.db.replace("\\", "/"), uri=True)
        try:
            approved = conn.execute(
                "SELECT count(*) FROM requests WHERE status='approved'"
            ).fetchone()[0]
            loans = conn.execute("SELECT count(*) FROM loans").fetchone()[0]
            returned = conn.execute(
                "SELECT count(*) FROM loans WHERE returned_at IS NOT NULL"
            ).fetchone()[0]
            users = conn.execute("SELECT count(*) FROM users").fetchone()[0]
            devices = conn.execute("SELECT count(*) FROM devices").fetchone()[0]
            audits = conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]
        finally:
            conn.close()
        return {
            "approved": approved,
            "loans": loans,
            "returned": returned,
            "users": users,
            "devices": devices,
            "audit": audits,
        }

    def test_tc_nfr_05_01_demo_force_and_guard(self):
        # 首次生成
        proc = self.run_demo("--force")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        out = proc.stdout
        self.assertIn("approved: 1", out, "摘要应显示 1 条 approved")
        self.assertRegex(out, r"已归还[:：]\s*1", "摘要应显示 1 条已归还")
        first = self.counts()
        self.assertEqual(first["approved"], 1)
        self.assertEqual(first["loans"], 1)
        self.assertEqual(first["returned"], 1)
        self.assertEqual(first["devices"], 20)
        self.assertEqual(first["users"], 8)
        self.assertGreater(first["audit"], 0, "演示流程应产生审计记录")
        # 数据与会话都落在临时目录：库文件在 tmp，会话文件为 <db>.session.json
        self.assertTrue(os.path.exists(self.db))
        self.assertTrue(
            os.path.exists(self.db + ".session.json"),
            "演示脚本应使用与临时库同目录的会话文件",
        )

        # 重复执行且不带 --force → 2
        proc = self.run_demo()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("--force", proc.stdout, "应提示使用 --force")
        self.assertEqual(self.counts(), first, "退出码 2 时不得改动库内容")

        # 再次 --force → 0，重建而非累加
        proc = self.run_demo("--force")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("approved: 1", proc.stdout)
        self.assertEqual(self.counts(), first, "重建后计数应与首次一致")


if __name__ == "__main__":
    unittest.main()

"""QA2（WBS 3.4）验收测试：WP2 设备目录与查询。

契约依据：docs/05-architecture.md §2（devices/requests/loans 字段）、§3（冲突判定 7 条）、
§4（device list / device search 参数与退出码）、§5（权限矩阵）；
docs/04-scope.md §6（TC-CRQ-02-01、TC-NFR-02-01）；docs/10-work-packages.md WP2。

隔离方式：CLI 以临时目录为 cwd 并显式传 --db <临时库>，会话文件因此落在
<临时目录>/data/session.json（契约 §1 的相对路径），不触碰仓库 data/。
临时库由 setUp 从 setUpClass 生成的基线库（seed 结果）复制，保证用例互不干扰。
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
MAIN = os.path.join(SRC, "main.py")

SEED_PASSWORD = "Passw0rd!"
NOW = "2026-10-23T00:00:00Z"
STATUS_ENUM = ("available", "maintenance", "retired")


def iso(day, hh, mm):
    """2026-11-02 08:00 -> 2026-11-02T08:00:00Z（契约 §2：UTC、秒级）。"""
    return "%sT%02d:%02d:00Z" % (day, hh, mm)


class WP2Base(unittest.TestCase):
    """WP2 用例公共装置：基线库 + 临时库 + CLI 调用。"""

    @classmethod
    def setUpClass(cls):
        cls.base_dir = tempfile.mkdtemp(prefix="qa-wp2-base-")
        cls.base_db = os.path.join(cls.base_dir, "base.db")
        env = dict(os.environ)
        env.pop("DEVICELOAN_DB", None)
        env.pop("DEVICELOAN_SESSION", None)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, MAIN, "seed", "--db", cls.base_db],
            cwd=cls.base_dir,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.returncode == 0, "基线库 seed 失败: %s%s" % (proc.stdout, proc.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base_dir, ignore_errors=True)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-wp2-")
        self.db = os.path.join(self.tmp, "qa.db")
        self.session_file = os.path.join(self.tmp, "data", "session.json")
        shutil.copyfile(self.base_db, self.db)
        self.env = dict(os.environ)
        self.env.pop("DEVICELOAN_DB", None)       # 防止外部环境串库
        self.env.pop("DEVICELOAN_SESSION", None)  # 会话文件位置由 cwd 决定
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 辅助 ----
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
        """stdout 必须是单行 JSON（契约 §4 统一约定）。"""
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, "stdout 应为单行 JSON，实际: %r" % proc.stdout)
        return json.loads(lines[0])

    def login(self, username="student1", password=SEED_PASSWORD):
        proc = self.cli("login", "--db", self.db, "--username", username,
                        "--password", password)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)

    def query(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def execute(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def device_id(self, code):
        rows = self.query("SELECT id FROM devices WHERE code = ?", (code,))
        self.assertEqual(len(rows), 1, "演示数据缺少设备 %s" % code)
        return rows[0][0]

    def add_request(self, device_id, start, end, status="approved", user_id=1):
        """直接写库构造申请（绕过 WP3 命令，WP2 只做查询侧判定）。"""
        return self.execute(
            "INSERT INTO requests (device_id, user_id, purpose, start_at, end_at,"
            " status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (device_id, user_id, "qa-wp2", start, end, status, NOW),
        )

    def add_loan(self, request_id, device_id, checked_out_at, due_at,
                 returned_at=None, user_id=1):
        return self.execute(
            "INSERT INTO loans (request_id, device_id, user_id, checked_out_at,"
            " due_at, returned_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (request_id, device_id, user_id, checked_out_at, due_at, returned_at, NOW),
        )

    def search(self, *args):
        proc = self.cli("device", "search", "--db", self.db, *args)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)["items"]

    def list_cmd(self, *args):
        proc = self.cli("device", "list", "--db", self.db, *args)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)["items"]

    def item(self, items, code):
        for entry in items:
            if entry["code"] == code:
                return entry
        self.fail("结果中缺少设备 %s" % code)


class DeviceListTest(WP2Base):
    """契约 §4：device list 参数、输出、退出码；§2：devices 表与状态枚举。"""

    def test_tc_crq_02_01_list_returns_20_devices_sorted_by_code(self):
        self.login()
        proc = self.cli("device", "list", "--db", self.db)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]

        self.assertEqual(len(items), 20, "seed 后应有 20 台设备")
        codes = [item["code"] for item in items]
        self.assertEqual(codes, sorted(codes), "结果应按 code 升序稳定输出")
        self.assertEqual(codes[0], "DEV-001")
        self.assertEqual(codes[-1], "DEV-020")

        for item in items:
            self.assertEqual(
                set(item), {"id", "code", "name", "category", "status"},
                "device list 条目字段应严格为契约 §4 所列 5 个",
            )
            self.assertIsInstance(item["id"], int)
            self.assertTrue(item["name"] and item["category"], item["code"])
            # 契约 §2：设备状态只有三档，不含 borrowed
            self.assertIn(item["status"], STATUS_ENUM, item["code"])

    def test_tc_crq_02_01_list_filters_by_category(self):
        self.login()
        expected = [r[0] for r in self.query(
            "SELECT code FROM devices WHERE category = '显微镜' ORDER BY code")]
        self.assertEqual(len(expected), 3, "演示数据中显微镜应有 3 台")

        items = self.list_cmd("--category", "显微镜")
        self.assertEqual([i["code"] for i in items], expected)
        for item in items:
            self.assertEqual(item["category"], "显微镜")

        # 不存在的类别 -> 成功但空列表（契约只规定 0/2/3）
        proc = self.cli("device", "list", "--db", self.db, "--category", "不存在的类别")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["items"], [])

    def test_tc_crq_02_01_list_accepts_three_status_values(self):
        self.login()
        # 直接改库造出 maintenance / retired 场景（seed 全部为 available）
        self.execute("UPDATE devices SET status='maintenance' WHERE code IN ('DEV-002','DEV-005')")
        self.execute("UPDATE devices SET status='retired' WHERE code='DEV-007'")

        counts = {}
        for status in STATUS_ENUM:
            items = self.list_cmd("--status", status)
            counts[status] = len(items)
            for item in items:
                self.assertEqual(item["status"], status)
        self.assertEqual(counts, {"available": 17, "maintenance": 2, "retired": 1})

        # 不带 --status 时返回全部 20 台，状态取值为三档之一
        all_items = self.list_cmd()
        self.assertEqual(len(all_items), 20)
        self.assertTrue({i["status"] for i in all_items} <= set(STATUS_ENUM))

        # category + status 组合
        combo = self.list_cmd("--category", "显微镜", "--status", "maintenance")
        self.assertEqual([i["code"] for i in combo], ["DEV-002"])

        # maintenance / retired 不可借（契约 §2）-> search 的 available 为 false
        found = self.search("--name", "体视显微镜")
        self.assertFalse(self.item(found, "DEV-002")["available"])

    def test_tc_crq_02_01_list_rejects_illegal_status_with_exit_2(self):
        self.login()
        for status in ("borrowed", "AVAILABLE", "", "lost"):
            with self.subTest(status=status):
                proc = self.cli("device", "list", "--db", self.db, "--status", status)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))

        # 库层同样只允许三档（契约 §2 CHECK 约束）
        with self.assertRaises(sqlite3.IntegrityError):
            self.execute("UPDATE devices SET status='borrowed' WHERE code='DEV-001'")


class DeviceSearchConditionsTest(WP2Base):
    """契约 §4：device search 的四个参数与参数错误映射（退出码 2）。"""

    def test_tc_crq_02_01_search_by_name_is_fuzzy(self):
        self.login()
        items = self.search("--name", "显微镜")
        self.assertEqual([i["code"] for i in items], ["DEV-001", "DEV-002", "DEV-003"])
        for item in items:
            self.assertIn("显微镜", item["name"])
            self.assertEqual(
                set(item), {"id", "code", "name", "category", "available", "conflicts"})
            self.assertIsInstance(item["conflicts"], int)

        partial = self.search("--name", "STM32")
        self.assertEqual([i["code"] for i in partial], ["DEV-013"])

        proc = self.cli("device", "search", "--db", self.db, "--name", "无此设备")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["items"], [])

    def test_tc_crq_02_01_search_by_category(self):
        self.login()
        items = self.search("--category", "开发板")
        self.assertEqual([i["code"] for i in items], ["DEV-013", "DEV-014", "DEV-015"])
        for item in items:
            self.assertEqual(item["category"], "开发板")

    def test_tc_crq_02_01_search_by_time_range_reports_available(self):
        self.login()
        d = "2026-11-02"
        did = self.device_id("DEV-004")
        self.add_request(did, iso(d, 9, 0), iso(d, 10, 0), "approved")

        items = self.search("--from", iso(d, 9, 30), "--to", iso(d, 10, 30))
        self.assertEqual(len(items), 20, "只给时段时应返回全部设备")
        codes = [i["code"] for i in items]
        self.assertEqual(codes, sorted(codes), "search 结果同样应按 code 升序")
        busy = self.item(items, "DEV-004")
        self.assertEqual(busy["conflicts"], 1)
        self.assertFalse(busy["available"])
        free = self.item(items, "DEV-005")
        self.assertEqual(free["conflicts"], 0)
        self.assertTrue(free["available"])

    def test_tc_crq_02_01_search_combined_conditions(self):
        """TC-CRQ-02-01：名称 + 类别 + 时段组合条件命中。"""
        self.login()
        d = "2026-11-02"
        did = self.device_id("DEV-003")
        self.add_request(did, iso(d, 9, 0), iso(d, 10, 0), "approved")

        items = self.search("--name", "显微镜", "--category", "显微镜",
                            "--from", iso(d, 9, 30), "--to", iso(d, 10, 30))
        self.assertEqual([i["code"] for i in items], ["DEV-001", "DEV-002", "DEV-003"])
        self.assertEqual(self.item(items, "DEV-003")["conflicts"], 1)
        self.assertFalse(self.item(items, "DEV-003")["available"])
        self.assertTrue(self.item(items, "DEV-001")["available"])

        # 名称与类别互斥时不命中
        proc = self.cli("device", "search", "--db", self.db,
                        "--name", "显微镜", "--category", "开发板")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["items"], [])

    def test_tc_crq_02_01_search_without_condition_exits_2(self):
        self.login()
        proc = self.cli("device", "search", "--db", self.db)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))

    def test_tc_crq_02_01_search_from_without_to_exits_2(self):
        self.login()
        proc = self.cli("device", "search", "--db", self.db,
                        "--from", "2026-11-02T09:00:00Z")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))

    def test_tc_crq_02_01_search_to_before_from_exits_2(self):
        self.login()
        for lo, hi in (
            ("2026-11-02T11:00:00Z", "2026-11-02T09:00:00Z"),
            ("2026-11-02T09:00:00Z", "2026-11-02T09:00:00Z"),
        ):
            with self.subTest(from_=lo, to=hi):
                proc = self.cli("device", "search", "--db", self.db,
                                "--from", lo, "--to", hi)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))

    def test_tc_crq_02_01_search_invalid_iso_exits_2(self):
        self.login()
        cases = (
            ("--from", "2026/11/02 09:00", "--to", "2026-11-02T10:00:00Z"),
            ("--from", "2026-11-02T09:00:00Z", "--to", "not-a-time"),
            ("--from", "2026-13-45T09:00:00Z", "--to", "2026-13-45T10:00:00Z"),
        )
        for args in cases:
            with self.subTest(args=args):
                proc = self.cli("device", "search", "--db", self.db, *args)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))


class ConflictRuleTest(WP2Base):
    """契约 §3（CRQ-05 唯一判定口径）的查询侧验证。

    完整 TC-CRQ-05（approve 时退出码 4 且事务回滚）属 QA3/WP3；
    本包只验 device search 暴露的 conflicts / available 是否与 §3 一致。
    """

    def test_overlapping_approved_request_counts_as_conflict(self):
        """§3-1/§3-2/§3-3：半开区间重叠 -> conflicts=1、available=false。"""
        self.login()
        d = "2026-11-03"
        did = self.device_id("DEV-013")
        self.add_request(did, iso(d, 8, 0), iso(d, 10, 0), "approved")

        items = self.search("--from", iso(d, 9, 0), "--to", iso(d, 11, 0))
        target = self.item(items, "DEV-013")
        self.assertEqual(target["conflicts"], 1)
        self.assertFalse(target["available"])

    def test_adjacent_window_is_not_a_conflict(self):
        """§3-5：首尾相接（前段 end == 后段 start）不算冲突。"""
        self.login()
        d = "2026-11-03"
        did = self.device_id("DEV-014")
        self.add_request(did, iso(d, 8, 0), iso(d, 10, 0), "approved")

        items = self.search("--from", iso(d, 10, 0), "--to", iso(d, 11, 0))
        target = self.item(items, "DEV-014")
        self.assertEqual(target["conflicts"], 0)
        self.assertTrue(target["available"])

    def test_pending_rejected_cancelled_do_not_occupy_time(self):
        """§3-4：pending / rejected / cancelled 不占用时段。"""
        self.login()
        d = "2026-11-03"
        did = self.device_id("DEV-006")
        for status in ("pending", "rejected", "cancelled"):
            self.add_request(did, iso(d, 9, 0), iso(d, 10, 0), status)

        items = self.search("--from", iso(d, 9, 0), "--to", iso(d, 10, 0))
        target = self.item(items, "DEV-006")
        self.assertEqual(target["conflicts"], 0)
        self.assertTrue(target["available"])

    def test_unreturned_loan_occupies_returned_loan_does_not(self):
        """§3-3：未归还 loans 占时段；returned_at 非空的不占。"""
        self.login()
        d = "2026-11-03"

        # 未还：申请时段在窗口外，占位只可能来自 loan
        did = self.device_id("DEV-008")
        rid = self.add_request(did, iso(d, 20, 0), iso(d, 22, 0), "approved")
        self.add_loan(rid, did, iso(d, 9, 0), iso(d, 11, 0), None)

        # 已还：同样的时段关系，但 returned_at 非空
        did2 = self.device_id("DEV-009")
        rid2 = self.add_request(did2, iso(d, 20, 0), iso(d, 22, 0), "approved")
        self.add_loan(rid2, did2, iso(d, 9, 0), iso(d, 11, 0), iso(d, 10, 0))

        items = self.search("--from", iso(d, 9, 30), "--to", iso(d, 10, 30))
        open_loan = self.item(items, "DEV-008")
        self.assertEqual(open_loan["conflicts"], 1, "未归还的 loan 应占时段")
        self.assertFalse(open_loan["available"])

        closed_loan = self.item(items, "DEV-009")
        self.assertEqual(closed_loan["conflicts"], 0, "已归还的 loan 不应占时段")
        self.assertTrue(closed_loan["available"])

    def test_request_and_its_loan_counted_once(self):
        """同一笔 approved 申请 + 其对应未还 loan 只计 1 次冲突。"""
        self.login()
        d = "2026-11-04"
        did = self.device_id("DEV-010")
        rid = self.add_request(did, iso(d, 8, 0), iso(d, 10, 0), "approved")
        self.add_loan(rid, did, iso(d, 8, 0), iso(d, 10, 0), None)

        items = self.search("--from", iso(d, 9, 0), "--to", iso(d, 11, 0))
        target = self.item(items, "DEV-010")
        self.assertEqual(target["conflicts"], 1, "申请与其借出记录不应重复计数")
        self.assertFalse(target["available"])


class DevicePermissionTest(WP2Base):
    """契约 §5 权限矩阵：device list / device search 三种角色都可查；无会话退出码 3。"""

    def test_no_session_exits_3(self):
        for args in (
            ("device", "list", "--db", self.db),
            ("device", "search", "--db", self.db, "--name", "显微镜"),
            ("device", "search", "--db", self.db,
             "--from", "2026-11-02T09:00:00Z", "--to", "2026-11-02T10:00:00Z"),
        ):
            with self.subTest(args=args):
                self.assertFalse(os.path.exists(self.session_file))
                proc = self.cli(*args)
                self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))

    def test_student_can_query_devices(self):
        body = self.login("student1")
        self.assertEqual(body["role"], "student")
        for args in (
            ("device", "list", "--db", self.db),
            ("device", "search", "--db", self.db, "--category", "显微镜"),
        ):
            with self.subTest(args=args):
                proc = self.cli(*args)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertGreater(len(self.payload(proc)["items"]), 0)

    def test_admin_can_query_devices(self):
        body = self.login("admin")
        self.assertEqual(body["role"], "admin")
        proc = self.cli("device", "search", "--db", self.db, "--name", "示波")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(len(self.payload(proc)["items"]), 3)


class PerformanceTest(WP2Base):
    """TC-NFR-02-01：演示规模（20 台设备、50 条借用记录）下单次查询 < 1 秒。"""

    def test_tc_nfr_02_01_search_under_one_second(self):
        self.login()
        device_ids = [r[0] for r in self.query("SELECT id FROM devices ORDER BY code")]
        self.assertEqual(len(device_ids), 20)

        rows = []
        for n in range(50):
            did = device_ids[n % len(device_ids)]
            start_day = "2026-11-%02d" % (5 + n % 20)
            rows.append((did, 1, "qa-perf", iso(start_day, 8, 0),
                         iso(start_day, 10, 0), "approved", NOW))
        conn = sqlite3.connect(self.db)
        try:
            conn.executemany(
                "INSERT INTO requests (device_id, user_id, purpose, start_at, end_at,"
                " status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
            conn.commit()
            reqs = conn.execute(
                "SELECT id, device_id, start_at, end_at FROM requests"
                " WHERE purpose='qa-perf' ORDER BY id").fetchall()
            self.assertEqual(len(reqs), 50)
            loans = []
            for rid, did, start_at, end_at in reqs[:25]:
                loans.append((rid, did, 1, start_at, end_at, None, NOW))
            conn.executemany(
                "INSERT INTO loans (request_id, device_id, user_id, checked_out_at,"
                " due_at, returned_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", loans)
            conn.commit()
            total_req = conn.execute("SELECT count(*) FROM requests").fetchone()[0]
            total_loan = conn.execute("SELECT count(*) FROM loans").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(total_req, 50)
        self.assertEqual(total_loan, 25)

        sys.path.insert(0, SRC)
        try:
            import db as dbmod
            import devices as devmod
        finally:
            sys.path.remove(SRC)

        conn = dbmod.connect(self.db)
        try:
            started = time.perf_counter()
            items = devmod.search_devices(
                conn, category=None, start="2026-11-05T09:00:00Z",
                end="2026-11-25T11:00:00Z")
            elapsed = time.perf_counter() - started
        finally:
            conn.close()

        self.assertEqual(len(items), 20)
        self.assertGreater(sum(i["conflicts"] for i in items), 0, "计时用例应在有冲突的数据上运行")
        self.assertLess(elapsed, 1.0, "单次 device search 耗时 %.3fs，应 < 1s" % elapsed)
        print(
            "\n[TC-NFR-02-01] search_devices elapsed = %.4fs "
            "(20 devices / 50 requests / 25 loans)" % elapsed,
            file=sys.stderr,
        )


if __name__ == "__main__":
    unittest.main()

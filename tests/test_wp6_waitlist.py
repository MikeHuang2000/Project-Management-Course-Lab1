"""QA6（CR-02 二期）验收测试：候补队列登记与可见性。

契约依据：docs/evidence/ccb-cr02.md §4（AC1–AC4）、§1（做/不做边界）；
docs/05-architecture.md §4（waitlist join/list 命令）、§5（权限矩阵）。
调用方式同 test_wp3_requests.py：临时目录为 cwd、显式 --db <临时库>、
会话文件落在 <临时目录>/data/session.json。
"""

import ast
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
MAIN = os.path.join(SRC, "main.py")

SEED_PASSWORD = "Passw0rd!"

# 半开区间 [start, end)
A_START, A_END = "2026-11-02T08:00:00Z", "2026-11-02T12:00:00Z"   # 基准段
B_START, B_END = "2026-11-02T10:00:00Z", "2026-11-02T11:00:00Z"   # 与 A 重叠
C_START, C_END = "2026-11-02T12:00:00Z", "2026-11-02T14:00:00Z"   # 与 A 首尾相接

LIST_FIELDS = {"waitlist_id", "device_id", "user_id", "start_at", "end_at",
               "status", "created_at"}


class WP6WaitlistTest(unittest.TestCase):
    """CR-02 二期验收：waitlist join / list。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-wp6-")
        self.db = os.path.join(self.tmp, "qa.db")
        self.db2 = os.path.join(self.tmp, "ctrl.db")  # AC3 对照库
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

    def query(self, sql, params=(), db=None):
        conn = sqlite3.connect(db or self.db)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def seed(self, db=None, reset=False):
        args = ["seed", "--db", db or self.db] + (["--reset"] if reset else [])
        proc = self.cli(*args)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        rows = self.query("SELECT username, id FROM users", db=db)
        self.users = dict(rows)
        self.devices = dict(self.query("SELECT code, id FROM devices", db=db))
        return proc

    def login(self, username):
        proc = self.cli(
            "login", "--db", self.db, "--username", username, "--password", SEED_PASSWORD
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)

    def join(self, device="DEV-001", start=A_START, end=A_END, note=None):
        args = ["waitlist", "join", "--db", self.db, "--device", device,
                "--from", start, "--to", end]
        if note is not None:
            args += ["--note", note]
        return self.cli(*args)

    def joined(self, device="DEV-001", start=A_START, end=A_END, note=None):
        proc = self.join(device=device, start=start, end=end, note=note)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)

    def wlist(self, *extra):
        return self.cli("waitlist", "list", "--db", self.db, *extra)

    def wcount(self, status=None, db=None):
        if status:
            sql = "SELECT count(*) FROM waitlists WHERE status = ?"
            return self.query(sql, (status,), db=db)[0][0]
        return self.query("SELECT count(*) FROM waitlists", db=db)[0][0]

    def submit(self, device="DEV-001", start=A_START, end=A_END, purpose="课程实验"):
        return self.cli("request", "submit", "--db", self.db, "--device", device,
                        "--from", start, "--to", end, "--purpose", purpose)

    def submitted(self, **kw):
        proc = self.submit(**kw)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["status"], "pending")
        return self.payload(proc)["request_id"]

    def approve(self, request_id):
        return self.cli("request", "approve", "--db", self.db,
                        "--request-id", str(request_id))

    def audit_rows(self, action):
        return self.query(
            "SELECT target_type, target_id, result, detail FROM audit_log"
            " WHERE action = ? ORDER BY id", (action,)
        )

    # ---- AC1：登记成功 ----
    def test_ac1_join_creates_waiting_row_and_audit(self):
        self.seed()
        self.login("student1")

        proc = self.join(device="DEV-001", start=A_START, end=A_END, note="课程实验")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIsInstance(body["waitlist_id"], int)
        self.assertEqual(body["status"], "waiting")
        self.assertTrue(body["available_now"])

        rows = self.query(
            "SELECT device_id, user_id, start_at, end_at, status, note FROM waitlists"
        )
        self.assertEqual(len(rows), 1)
        device_id, user_id, start_at, end_at, status, note = rows[0]
        self.assertEqual(device_id, self.devices["DEV-001"])
        self.assertEqual(user_id, self.users["student1"])
        self.assertEqual((start_at, end_at), (A_START, A_END))
        self.assertEqual(status, "waiting")
        self.assertEqual(note, "课程实验")
        self.assertEqual(self.wcount("waiting"), 1)

        audits = self.audit_rows("waitlist_join")
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0][0], "waitlist")
        self.assertEqual(audits[0][1], body["waitlist_id"])
        self.assertEqual(audits[0][2], "ok")

        proc = self.wlist()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(set(items[0].keys()), LIST_FIELDS)
        self.assertEqual(items[0]["waitlist_id"], body["waitlist_id"])
        self.assertEqual(items[0]["status"], "waiting")
        self.assertEqual(items[0]["user_id"], self.users["student1"])

    # ---- AC2：重复登记 ----
    def test_ac2_overlap_duplicate_rejected_adjacent_and_other_user_allowed(self):
        self.seed()
        self.login("student1")
        self.joined(start=A_START, end=A_END)

        # 同人同设备重叠 10:00–11:00 → 1，库无新增
        proc = self.join(start=B_START, end=B_END)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["error"], "duplicate_waitlist")
        self.assertEqual(self.wcount(), 1)

        # 首尾相接 12:00–14:00 → 0
        proc = self.join(start=C_START, end=C_END)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.wcount(), 2)

        # 另一学生同设备同时段 → 允许
        self.login("student2")
        proc = self.join(start=A_START, end=A_END)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.wcount(), 3)

    # ---- AC3：候补不占位 ----
    def test_ac3_waitlist_does_not_affect_approve(self):
        self.seed()
        self.login("student2")
        with_wait = self.submitted(device="DEV-002", start=A_START, end=A_END)
        self.login("student1")
        self.joined(device="DEV-002", start=A_START, end=A_END)
        self.login("admin")

        proc = self.approve(with_wait)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["status"], "approved")
        self.assertNotIn("error", body)
        self.assertEqual(
            self.query("SELECT status FROM requests WHERE id = ?", (with_wait,))[0][0],
            "approved",
        )

        # 与已批准申请重叠的第二条 → 仍按原冲突逻辑 4
        self.login("student2")
        second = self.submitted(device="DEV-002", start=B_START, end=C_END)
        self.login("admin")
        proc = self.approve(second)
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["error"], "time_conflict")
        self.assertEqual([c["request_id"] for c in body["conflicts"]], [with_wait])
        self.assertEqual(
            self.query("SELECT status FROM requests WHERE id = ?", (second,))[0][0],
            "pending",
        )

        # 对照：无候补记录的库上，同一场景结果一致
        self.seed(db=self.db2)
        self.login("student2")
        proc = self.cli("request", "submit", "--db", self.db2, "--device", "DEV-002",
                        "--from", A_START, "--to", A_END, "--purpose", "课程实验")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ctrl_first = self.payload(proc)["request_id"]
        self.login("admin")
        proc = self.cli("request", "approve", "--db", self.db2,
                        "--request-id", str(ctrl_first))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["status"], "approved")

        self.login("student2")
        proc = self.cli("request", "submit", "--db", self.db2, "--device", "DEV-002",
                        "--from", B_START, "--to", C_END, "--purpose", "课程实验")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ctrl_second = self.payload(proc)["request_id"]
        self.login("admin")
        proc = self.cli("request", "approve", "--db", self.db2,
                        "--request-id", str(ctrl_second))
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        ctrl_body = self.payload(proc)
        self.assertEqual(ctrl_body["error"], "time_conflict")
        self.assertEqual([c["request_id"] for c in ctrl_body["conflicts"]], [ctrl_first])
        self.assertEqual(self.query("SELECT count(*) FROM waitlists", db=self.db2)[0][0], 0)

    # ---- AC4：可见性 ----
    def test_ac4_visibility_and_role_matrix(self):
        self.seed()
        self.login("student1")
        mine = self.joined(device="DEV-001", start=A_START, end=A_END)["waitlist_id"]
        self.login("student2")
        self.joined(device="DEV-002", start=A_START, end=A_END)

        # student 只看本人；--all → 3
        self.login("student1")
        proc = self.wlist()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual([it["waitlist_id"] for it in items], [mine])
        self.assertTrue(all(it["user_id"] == self.users["student1"] for it in items))

        proc = self.wlist("--all")
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))

        # admin 无 --all → 空列表；--all → 两条
        self.login("admin")
        proc = self.wlist()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["items"], [])

        proc = self.wlist("--all")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        all_items = self.payload(proc)["items"]
        self.assertEqual(len(all_items), 2)

        # 设备过滤：编码与编号等价
        proc = self.wlist("--all", "--device", "DEV-001")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        by_code = self.payload(proc)["items"]
        self.assertEqual([it["waitlist_id"] for it in by_code], [mine])

        proc = self.wlist("--all", "--device", str(self.devices["DEV-001"]))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual([it["waitlist_id"] for it in self.payload(proc)["items"]], [mine])

        # director 看名单 / 登记 → 3；admin 登记 → 3
        self.login("director")
        proc = self.wlist()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        proc = self.join()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(self.wcount(), 2)

        self.login("admin")
        proc = self.join()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(self.wcount(), 2)

    # ---- 边界：参数与设备 ----
    def test_boundary_validation_and_device_lookup(self):
        self.seed()
        self.login("student1")

        proc = self.join(start="2026-13-40T08:00:00Z", end=A_END)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        proc = self.join(start=A_END, end=A_START)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        proc = self.join(start=A_START, end=A_START)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        proc = self.join(note="长" * 201)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self.wcount(), 0, "参数错误不应落库")

        proc = self.join(device="DEV-999")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["error"], "device_not_found")
        self.assertEqual(self.wcount(), 0)
        self.assertEqual(len(self.audit_rows("waitlist_join")), 0)

    # ---- 边界：设备已被批准申请占用 ----
    def test_available_now_false_when_slot_occupied(self):
        self.seed()
        self.login("student2")
        rid = self.submitted(device="DEV-003", start=A_START, end=A_END)
        self.login("admin")
        self.assertEqual(self.approve(rid).returncode, 0)

        self.login("student1")
        proc = self.join(device="DEV-003", start=A_START, end=A_END)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["status"], "waiting")
        self.assertFalse(body["available_now"])
        self.assertEqual(self.wcount("waiting"), 1)

    # ---- 边界：seed --reset 清空候补且输出字段不变 ----
    def test_seed_reset_clears_waitlists(self):
        self.seed()
        self.login("student1")
        self.joined()
        self.assertEqual(self.wcount(), 1)

        proc = self.seed(db=self.db, reset=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(set(body.keys()), {"users", "devices", "requests", "loans"})
        self.assertEqual((body["users"], body["devices"]), (8, 20))
        self.assertEqual(self.wcount(), 0)
        self.assertEqual(len(self.audit_rows("waitlist_join")), 0)

    # ---- NFR：src/ 仅依赖标准库与本地模块 ----
    def test_nfr_src_imports_stdlib_or_local_only(self):
        allowed = set(sys.stdlib_module_names)
        allowed.update(
            name[:-3] for name in os.listdir(SRC) if name.endswith(".py")
        )
        for name in sorted(os.listdir(SRC)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(SRC, name)
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        imported.add(node.module.split(".")[0])
            with self.subTest(module=name):
                self.assertEqual(imported - allowed, set())


if __name__ == "__main__":
    unittest.main()

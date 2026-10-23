"""TC-NFR-07-01：时间统一 ISO 8601（UAT 条件 C1 补齐的 RTM 同名用例）。

契约依据：docs/05-architecture.md §4（--from/--to 接受 ISO 8601，带不带 Z 等价；
非法时间 -> 退出码 2）；§2（时间字段统一 UTC、秒级、以 Z 结尾）。

说明：request submit 的输出按契约只含 request_id / status，故 start_at / end_at
经 request show 读取 submit 实际落库的值后校验格式。

隔离方式：每个用例使用独立临时目录与临时库，--db 显式指向临时库，
DEVICELOAN_SESSION 指向临时目录内的会话文件，不触碰仓库 data/。
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, "src", "main.py")

SEED_PASSWORD = "Passw0rd!"
NOW = "2026-10-23T00:00:00Z"
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class TCNFR0701Test(unittest.TestCase):
    """NFR-07：对外暴露的时间参数与回显均为 ISO 8601（UTC，秒级，Z 结尾）。"""

    @classmethod
    def setUpClass(cls):
        cls.base_dir = tempfile.mkdtemp(prefix="qa-nfr07-base-")
        cls.base_db = os.path.join(cls.base_dir, "base.db")
        env = dict(os.environ)
        env.pop("DEVICELOAN_DB", None)
        env.pop("DEVICELOAN_SESSION", None)
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, MAIN, "seed", "--db", cls.base_db],
            cwd=cls.base_dir, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        assert proc.returncode == 0, "基线库 seed 失败: %s%s" % (proc.stdout, proc.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base_dir, ignore_errors=True)

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-nfr07-")
        self.db = os.path.join(self.tmp, "qa.db")
        shutil.copyfile(self.base_db, self.db)
        self.env = dict(os.environ)
        self.env.pop("DEVICELOAN_DB", None)
        self.env["DEVICELOAN_SESSION"] = os.path.join(self.tmp, "session.json")
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 辅助 ----
    def cli(self, *args):
        return subprocess.run(
            [sys.executable, MAIN] + list(args),
            cwd=self.tmp, env=self.env, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )

    def payload(self, proc):
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, "stdout 应为单行 JSON，实际: %r" % proc.stdout)
        return json.loads(lines[0])

    def ok(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)

    def login(self, username="student1", password=SEED_PASSWORD):
        return self.ok(self.cli("login", "--db", self.db, "--username", username,
                                "--password", password))

    def search(self, *args):
        return self.ok(self.cli("device", "search", "--db", self.db, *args))["items"]

    def device_id(self, code):
        conn = sqlite3.connect(self.db)
        try:
            rows = conn.execute("SELECT id FROM devices WHERE code = ?", (code,)).fetchall()
        finally:
            conn.close()
        self.assertEqual(len(rows), 1, "演示数据缺少设备 %s" % code)
        return rows[0][0]

    def add_approved_request(self, device_id, start, end):
        conn = sqlite3.connect(self.db)
        try:
            conn.execute(
                "INSERT INTO requests (device_id, user_id, purpose, start_at, end_at,"
                " status, created_at) VALUES (?, 1, 'qa-nfr-07', ?, ?, 'approved', ?)",
                (device_id, start, end, NOW),
            )
            conn.commit()
        finally:
            conn.close()

    # ---- 断言 1：--from/--to 带 Z 与不带 Z 语义一致 ----
    def test_tc_nfr_07_01_search_with_and_without_z_are_equivalent(self):
        self.login()
        did = self.device_id("DEV-004")
        self.add_approved_request(did, "2026-11-03T08:00:00Z", "2026-11-03T10:00:00Z")

        with_z = self.search("--from", "2026-11-03T08:00:00Z",
                             "--to", "2026-11-03T10:00:00Z")
        plain = self.search("--from", "2026-11-03T08:00:00",
                            "--to", "2026-11-03T10:00:00")

        self.assertEqual(len(with_z), 20)
        self.assertEqual(len(plain), 20)

        def view(items):
            return {i["code"]: (i["available"], i["conflicts"]) for i in items}

        self.assertEqual(view(with_z), view(plain),
                         "带 Z 与不带 Z 的同一时段应得到相同的 available/conflicts")
        target = view(with_z)["DEV-004"]
        self.assertEqual(target, (False, 1),
                         "用例应运行在有冲突的时段上，才能验证两种写法的等价性")
        self.assertEqual(view(with_z)["DEV-005"], (True, 0))

    # ---- 断言 2：申请与借还记录的时间回显均为 ISO 8601 UTC ----
    def test_tc_nfr_07_01_submit_checkout_return_echo_iso_utc(self):
        self.login("student1")
        submitted = self.ok(self.cli(
            "request", "submit", "--db", self.db,
            "--device", "DEV-005",
            "--from", "2026-11-04T09:00:00Z", "--to", "2026-11-04T11:00:00Z",
            "--purpose", "tc-nfr-07-01"))
        request_id = submitted["request_id"]
        self.assertEqual(submitted["status"], "pending")

        self.login("admin")
        detail = self.ok(self.cli("request", "show", "--db", self.db,
                                  "--request-id", str(request_id)))
        self.assertRegex(detail["start_at"], ISO_UTC)
        self.assertRegex(detail["end_at"], ISO_UTC)

        self.ok(self.cli("request", "approve", "--db", self.db,
                         "--request-id", str(request_id)))
        checkout = self.ok(self.cli("loan", "checkout", "--db", self.db,
                                    "--request-id", str(request_id)))
        self.assertRegex(checkout["due_at"], ISO_UTC)

        returned = self.ok(self.cli("loan", "return", "--db", self.db,
                                    "--loan-id", str(checkout["loan_id"])))
        self.assertRegex(returned["returned_at"], ISO_UTC)

    # ---- 断言 3：非法时间退出码为 2 ----
    def test_tc_nfr_07_01_illegal_time_exits_2(self):
        self.login()
        for bad in ("2026-13-01T00:00:00Z", "not-a-date"):
            with self.subTest(cmd="device search", value=bad):
                proc = self.cli("device", "search", "--db", self.db,
                                "--from", bad, "--to", "2026-11-03T10:00:00Z")
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))

            with self.subTest(cmd="request submit", value=bad):
                proc = self.cli("request", "submit", "--db", self.db,
                                "--device", "DEV-005",
                                "--from", bad, "--to", "2026-11-03T10:00:00Z",
                                "--purpose", "tc-nfr-07-01")
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))


if __name__ == "__main__":
    unittest.main()

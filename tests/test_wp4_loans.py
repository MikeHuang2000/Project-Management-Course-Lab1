"""QA4（WBS 3.8）验收测试：WP4 借出、归还与逾期。

契约依据：docs/05-architecture.md §2（loans 表：request_id UNIQUE、due_at 取申请
end_at、returned_at 空 = 未归还；逾期唯一口径）、§4（loan checkout / loan return
参数与退出码）、§5（仅 admin 可借还）、§6（days_late = max(1, ceil(秒数/86400))）、
§7（审计 loan_checkout / loan_return）；docs/04-scope.md §6 TC-CRQ-06-01；
docs/10-work-packages.md WP4 卡片。

调用方式：子进程执行 CLI，cwd 为临时目录，显式传 --db <临时库>，
会话文件落在 <临时目录>/data/session.json（契约 §1）。为使逾期可复现，测试在临时库中
改写 loans.due_at（产品代码无 --due-at 参数，契约也未要求；只改临时库，不污染 data/）。
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
SRC = os.path.join(ROOT, "src")
MAIN = os.path.join(SRC, "main.py")

SEED_PASSWORD = "Passw0rd!"
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# 申请时段全部落在将来（相对 2026-10-23），避免与"当前时间"相关的分支
W1 = ("2026-12-01T08:00:00Z", "2026-12-01T12:00:00Z")
W2 = ("2026-12-02T08:00:00Z", "2026-12-02T12:00:00Z")
W3 = ("2026-12-03T08:00:00Z", "2026-12-03T12:00:00Z")
W4 = ("2026-12-04T08:00:00Z", "2026-12-04T12:00:00Z")


def iso_now(offset_seconds=0):
    moment = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class WP4LoanTest(unittest.TestCase):
    """WP4 命令层验收：loan checkout / loan return 与逾期口径。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-wp4-")
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
        """删掉临时会话文件，模拟未登录。"""
        if os.path.exists(self.session_file):
            os.remove(self.session_file)

    def submit(self, device, window, purpose="课程实验"):
        start, end = window
        return self.cli(
            "request", "submit", "--db", self.db,
            "--device", device, "--from", start, "--to", end, "--purpose", purpose,
        )

    def submitted(self, device, window, purpose="课程实验"):
        proc = self.submit(device, window, purpose)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)["request_id"]

    def approve(self, request_id):
        return self.cli("request", "approve", "--db", self.db, "--request-id", str(request_id))

    def reject(self, request_id, reason="时段已满"):
        return self.cli(
            "request", "reject", "--db", self.db,
            "--request-id", str(request_id), "--reason", reason,
        )

    def cancel(self, request_id):
        return self.cli("request", "cancel", "--db", self.db, "--request-id", str(request_id))

    def checkout(self, request_id):
        return self.cli(
            "loan", "checkout", "--db", self.db, "--request-id", str(request_id)
        )

    def do_return(self, loan_id):
        return self.cli("loan", "return", "--db", self.db, "--loan-id", str(loan_id))

    def search(self, start="2027-03-01T08:00:00Z", end="2027-03-01T12:00:00Z",
               code="DEV-001", name="倒置金相"):
        proc = self.cli(
            "device", "search", "--db", self.db,
            "--name", name, "--from", start, "--to", end,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        matched = [it for it in items if it["code"] == code]
        self.assertEqual(len(matched), 1, "未命中设备 %s: %r" % (code, items))
        return matched[0]

    def approved_request(self, device="DEV-001", window=W1):
        """student1 提交、admin 批准，返回 request_id。"""
        self.login("student1")
        rid = self.submitted(device, window)
        self.login("admin")
        proc = self.approve(rid)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return rid

    def checked_out(self, device="DEV-001", window=W1):
        """已批准申请 + admin 登记借出，返回 (request_id, loan_id)。"""
        rid = self.approved_request(device, window)
        proc = self.checkout(rid)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return rid, self.payload(proc)["loan_id"]

    def loan_row(self, loan_id):
        rows = self.query(
            "SELECT request_id, device_id, user_id, checked_out_at, due_at, returned_at"
            " FROM loans WHERE id = ?",
            (loan_id,),
        )
        self.assertEqual(len(rows), 1, "借出记录 %s 不存在" % loan_id)
        return rows[0]

    def request_row(self, request_id):
        rows = self.query(
            "SELECT device_id, user_id, end_at, status FROM requests WHERE id = ?",
            (request_id,),
        )
        self.assertEqual(len(rows), 1, "申请 %s 不存在" % request_id)
        return rows[0]

    def set_due_at(self, loan_id, due_iso):
        self.exec_sql("UPDATE loans SET due_at = ? WHERE id = ?", (due_iso, loan_id))

    def audit_rows(self, action):
        return self.query(
            "SELECT target_type, target_id, result, detail, actor_name FROM audit_log"
            " WHERE action = ? ORDER BY id",
            (action,),
        )

    def ok_audit_count(self, action):
        return self.query(
            "SELECT count(*) FROM audit_log WHERE action = ? AND result = 'ok'", (action,)
        )[0][0]

    # ---- TC-CRQ-06-01 主线：借出 → 归还 ----
    def test_tc_crq_06_01_checkout_and_return_on_time(self):
        self.seed()
        rid = self.approved_request("DEV-001", W1)
        req_device, req_user, req_end, req_status = self.request_row(rid)
        self.assertEqual(req_status, "approved")

        proc = self.checkout(rid)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["request_id"], rid)
        self.assertIsInstance(body["loan_id"], int)
        loan_id = body["loan_id"]
        # due_at 取申请 end_at
        self.assertEqual(body["due_at"], req_end)
        self.assertEqual(body["due_at"], W1[1])

        # 数据一致性：loans.device_id / user_id 与申请一致，returned_at 初始为空
        request_id, device_id, user_id, checked_out_at, due_at, returned_at = self.loan_row(loan_id)
        self.assertEqual(request_id, rid)
        self.assertEqual(device_id, req_device)
        self.assertEqual(user_id, req_user)
        self.assertEqual(device_id, self.devices["DEV-001"])
        self.assertEqual(user_id, self.users["student1"])
        self.assertEqual(due_at, req_end)
        self.assertIsNone(returned_at)
        self.assertRegex(checked_out_at, ISO_RE)

        # checkout 审计：1 条 ok，target=loan/loan_id，detail 含 request_id 与 due_at
        rows = self.audit_rows("loan_checkout")
        self.assertEqual(len(rows), 1, "loan_checkout 审计应恰好 1 条: %r" % (rows,))
        target_type, target_id, result, detail, actor = rows[0]
        self.assertEqual((target_type, target_id, result), ("loan", loan_id, "ok"))
        self.assertEqual(actor, "admin")
        self.assertIn('"request_id"', detail)
        self.assertIn(str(rid), detail)
        self.assertIn(req_end, detail)

        # 正常归还（due_at 在未来）：overdue=false, days_late=0
        proc = self.do_return(loan_id)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["loan_id"], loan_id)
        self.assertIs(body["overdue"], False)
        self.assertEqual(body["days_late"], 0)
        self.assertRegex(body["returned_at"], ISO_RE)

        _, _, _, _, _, returned_at = self.loan_row(loan_id)
        self.assertEqual(returned_at, body["returned_at"])

        # return 审计：1 条 ok，detail 含 returned_at 与 overdue
        rows = self.audit_rows("loan_return")
        self.assertEqual(len(rows), 1, "loan_return 审计应恰好 1 条: %r" % (rows,))
        target_type, target_id, result, detail, actor = rows[0]
        self.assertEqual((target_type, target_id, result), ("loan", loan_id, "ok"))
        self.assertEqual(actor, "admin")
        self.assertIn("returned_at", detail)
        self.assertIn("overdue", detail)
        self.assertIn('"overdue": false', detail)

    # ---- 重复借出同一申请 → 1，且不再写 ok 审计 ----
    def test_duplicate_checkout_rejected(self):
        self.seed()
        rid, loan_id = self.checked_out("DEV-001", W1)

        proc = self.checkout(rid)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIn("error", body)
        self.assertEqual(body["error"], "already_checked_out")

        self.assertEqual(self.query("SELECT count(*) FROM loans")[0][0], 1)
        self.assertEqual(self.loan_row(loan_id)[0], rid)
        # 失败路径不得追加 ok 审计
        self.assertEqual(len(self.audit_rows("loan_checkout")), 1)
        self.assertEqual(self.ok_audit_count("loan_checkout"), 1)

    # ---- 只允许对 approved 申请借出 ----
    def test_checkout_requires_approved_request(self):
        self.seed()
        self.login("student1")
        pending = self.submitted("DEV-001", W1)
        to_reject = self.submitted("DEV-002", W2)
        to_cancel = self.submitted("DEV-003", W3)
        self.login("admin")
        self.assertEqual(self.reject(to_reject).returncode, 0)
        self.login("student1")
        self.assertEqual(self.cancel(to_cancel).returncode, 0)
        self.login("admin")

        cases = [
            ("pending", pending),
            ("rejected", to_reject),
            ("cancelled", to_cancel),
        ]
        for label, rid in cases:
            with self.subTest(status=label):
                proc = self.checkout(rid)
                self.assertEqual(proc.returncode, 1, label + ": " + proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))
        self.assertEqual(self.query("SELECT count(*) FROM loans")[0][0], 0, "失败路径不应落库")
        self.assertEqual(len(self.audit_rows("loan_checkout")), 0)

    # ---- 不存在的 request-id → 1 ----
    def test_checkout_missing_request(self):
        self.seed()
        self.login("admin")
        proc = self.checkout(999999)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["error"], "request_not_found")
        self.assertEqual(self.query("SELECT count(*) FROM loans")[0][0], 0)
        self.assertEqual(len(self.audit_rows("loan_checkout")), 0)

    # ---- 权限矩阵：借还仅 admin；未登录 → 3 ----
    def test_loan_permission_matrix(self):
        self.seed()
        self.login("student1")
        rid_a = self.submitted("DEV-001", W1)
        rid_b = self.submitted("DEV-002", W2)
        self.login("admin")
        self.assertEqual(self.approve(rid_a).returncode, 0)
        proc = self.checkout(rid_a)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        loan_id = self.payload(proc)["loan_id"]

        # 未登录 → 3（checkout / return 都算）
        self.logout()
        for label, proc in (
            ("anon checkout", self.checkout(rid_b)),
            ("anon return", self.do_return(loan_id)),
        ):
            with self.subTest(case=label):
                self.assertEqual(proc.returncode, 3, label + ": " + proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))

        # student / director → 3
        for username in ("student1", "director"):
            self.login(username)
            for label, proc in (
                ("checkout", self.checkout(rid_b)),
                ("return", self.do_return(loan_id)),
            ):
                with self.subTest(case=username + " " + label):
                    self.assertEqual(proc.returncode, 3, label + ": " + proc.stdout + proc.stderr)
                    self.assertIn("error", self.payload(proc))

        # 越权调用未改动数据、未写 ok 审计
        self.assertEqual(self.query("SELECT count(*) FROM loans")[0][0], 1)
        self.assertIsNone(self.loan_row(loan_id)[5], "学生的归还调用不应生效")
        self.assertEqual(self.ok_audit_count("loan_checkout"), 1)
        self.assertEqual(self.ok_audit_count("loan_return"), 0)

        # admin 仍可正常归还
        self.login("admin")
        proc = self.do_return(loan_id)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIsNotNone(self.loan_row(loan_id)[5])

    # ---- 逾期天数：ceil 向上取整 + 不足 1 天记 1 ----
    def test_return_overdue_days_late(self):
        self.seed()
        cases = [
            # (标签, 申请设备/时段, due_at 相对当前秒数, 期望 days_late)
            ("逾期约1分钟", "DEV-001", W1, -60, 1),
            ("逾期3.5小时", "DEV-002", W2, -int(3.5 * 3600), 1),
            ("逾期2天1小时", "DEV-003", W3, -(2 * 86400 + 3600), 3),
        ]
        for label, device, window, offset, expected in cases:
            with self.subTest(case=label):
                rid, loan_id = self.checked_out(device, window)
                self.set_due_at(loan_id, iso_now(offset))
                proc = self.do_return(loan_id)
                self.assertEqual(proc.returncode, 0, label + ": " + proc.stdout + proc.stderr)
                body = self.payload(proc)
                self.assertIs(body["overdue"], True, label)
                self.assertEqual(body["days_late"], expected, label + ": " + json.dumps(body))
                self.assertEqual(
                    self.query(
                        "SELECT count(*) FROM audit_log WHERE action='loan_return'"
                        " AND target_id=? AND result='ok'",
                        (loan_id,),
                    )[0][0],
                    1,
                )

    # ---- 边界：returned_at == due_at 不算逾期；1 秒即算逾期且记 1 天 ----
    def test_overdue_boundary_exact_due_at(self):
        sys.path.insert(0, SRC)
        try:
            import loans as loans_module
        finally:
            sys.path.remove(SRC)

        self.assertEqual(loans_module.overdue_days(W1[1], W1[1]), (False, 0))
        one_second_before = "2026-12-01T11:59:59Z"
        self.assertEqual(loans_module.overdue_days(one_second_before, W1[1]), (False, 0))
        # 逾期 1 秒：ceil(1/86400)=1，max(1,·) 保证不足 1 天记 1 天
        self.assertEqual(loans_module.overdue_days("2026-12-01T12:00:01Z", W1[1]), (True, 1))
        # 恰满 1 天仍是 1 天，多 1 秒进到 2 天
        self.assertEqual(loans_module.overdue_days("2026-12-02T12:00:00Z", W1[1]), (True, 1))
        self.assertEqual(loans_module.overdue_days("2026-12-02T12:00:01Z", W1[1]), (True, 2))

        # CLI 层：due_at 在未来 → overdue=false, days_late=0
        self.seed()
        rid, loan_id = self.checked_out("DEV-001", W1)
        self.set_due_at(loan_id, iso_now(3600))
        proc = self.do_return(loan_id)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIs(body["overdue"], False)
        self.assertEqual(body["days_late"], 0)

    # ---- 重复归还 → 1，且不再写 ok 审计、returned_at 不变 ----
    def test_duplicate_return_rejected(self):
        self.seed()
        rid, loan_id = self.checked_out("DEV-001", W1)

        first = self.do_return(loan_id)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        first_returned_at = self.payload(first)["returned_at"]
        audit_before = len(self.audit_rows("loan_return"))

        proc = self.do_return(loan_id)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["error"], "already_returned")

        self.assertEqual(self.loan_row(loan_id)[5], first_returned_at, "重复归还不得覆盖 returned_at")
        self.assertEqual(len(self.audit_rows("loan_return")), audit_before)
        self.assertEqual(self.ok_audit_count("loan_return"), 1)

    # ---- 不存在的 loan-id → 1 ----
    def test_return_missing_loan(self):
        self.seed()
        rid, loan_id = self.checked_out("DEV-001", W1)
        missing = loan_id + 1000
        proc = self.do_return(missing)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["error"], "loan_not_found")
        self.assertIsNone(self.loan_row(loan_id)[5], "非法调用不应归还既有记录")
        self.assertEqual(len(self.audit_rows("loan_return")), 0)

    # ---- 联动：未归还的借出占位，归还后立即解除 ----
    def test_device_search_reflects_unreturned_loan(self):
        self.seed()
        rid, loan_id = self.checked_out("DEV-001", W1)

        # 申请时段（2026-12-01）之外的后续任意时段，仍应因未归还借出而不可借
        for start, end in (
            ("2027-03-01T08:00:00Z", "2027-03-01T12:00:00Z"),
            ("2030-01-01T00:00:00Z", "2030-01-01T01:00:00Z"),
        ):
            with self.subTest(window=start):
                item = self.search(start, end)
                self.assertIs(item["available"], False)
                self.assertGreaterEqual(item["conflicts"], 1)
                self.assertEqual(item["conflicts"], 1, "同一申请与其借出记录只计 1 次: %r" % item)
                self.assertEqual(item["id"], self.devices["DEV-001"])

        proc = self.do_return(loan_id)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        for start, end in (
            ("2027-03-01T08:00:00Z", "2027-03-01T12:00:00Z"),
            ("2030-01-01T00:00:00Z", "2030-01-01T01:00:00Z"),
        ):
            with self.subTest(window=start, after="return"):
                item = self.search(start, end)
                self.assertIs(item["available"], True)
                self.assertEqual(item["conflicts"], 0)


if __name__ == "__main__":
    unittest.main()

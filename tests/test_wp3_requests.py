"""QA3（WBS 3.6）验收测试：WP3 申请审批与冲突阻止。

契约依据：docs/05-architecture.md §2（requests/loans 表与状态机）、§3（冲突规则）、
§4（request 6 条命令）、§5（权限矩阵）、§7（审计事件）；docs/04-scope.md §6
TC-CRQ-03-01 / 04-01 / 05-01 / 05-02 / 09-01、TC-NFR-04-01；
docs/10-work-packages.md WP3 卡片。

调用方式：子进程执行 CLI，cwd 为临时目录，显式传 --db <临时库>，
会话文件落在 <临时目录>/data/session.json（契约 §1 运行期文件位置）。
"""

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

# 半开区间 [start, end)，取值全部落在将来，避免与"当前时间"相关的分支
A_START, A_END = "2026-11-02T08:00:00Z", "2026-11-02T12:00:00Z"
B_START, B_END = "2026-11-02T10:00:00Z", "2026-11-02T14:00:00Z"  # 与 A 重叠
C_START, C_END = "2026-11-02T12:00:00Z", "2026-11-02T14:00:00Z"  # 与 A 首尾相接


class WP3RequestTest(unittest.TestCase):
    """WP3 命令层验收：submit / cancel / list / show / approve / reject。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-wp3-")
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
        users = dict(self.query("SELECT username, id FROM users"))
        devices = dict(self.query("SELECT code, id FROM devices"))
        self.users, self.devices = users, devices

    def login(self, username):
        proc = self.cli(
            "login", "--db", self.db, "--username", username, "--password", SEED_PASSWORD
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)

    def submit(self, device="DEV-001", start=A_START, end=A_END, purpose="课程实验"):
        return self.cli(
            "request", "submit", "--db", self.db,
            "--device", device, "--from", start, "--to", end, "--purpose", purpose,
        )

    def submitted(self, device="DEV-001", start=A_START, end=A_END, purpose="课程实验"):
        proc = self.submit(device=device, start=start, end=end, purpose=purpose)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["status"], "pending")
        return body["request_id"]

    def approve(self, request_id):
        return self.cli("request", "approve", "--db", self.db, "--request-id", str(request_id))

    def reject(self, request_id, reason="时段已满"):
        return self.cli(
            "request", "reject", "--db", self.db,
            "--request-id", str(request_id), "--reason", reason,
        )

    def cancel(self, request_id):
        return self.cli("request", "cancel", "--db", self.db, "--request-id", str(request_id))

    def request_row(self, request_id):
        rows = self.query(
            "SELECT status, decided_by, decided_at, reject_reason FROM requests WHERE id = ?",
            (request_id,),
        )
        self.assertEqual(len(rows), 1, "申请 %s 不存在" % request_id)
        return rows[0]

    def approved_count(self):
        return self.query("SELECT count(*) FROM requests WHERE status='approved'")[0][0]

    def audit_rows(self, action):
        return self.query(
            "SELECT target_type, target_id, result, detail FROM audit_log WHERE action = ?"
            " ORDER BY id",
            (action,),
        )

    def set_device_status(self, code, status):
        self.exec_sql("UPDATE devices SET status = ? WHERE code = ?", (status, code))

    # ---- TC-CRQ-03-01：提交申请 ----
    def test_tc_crq_03_01_submit_creates_pending_request(self):
        self.seed()
        self.login("student1")

        proc = self.submit(device="DEV-001", start=A_START, end=A_END, purpose="嵌入式课程实验")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIsInstance(body["request_id"], int)
        self.assertEqual(body["status"], "pending")
        rid = body["request_id"]

        rows = self.query(
            "SELECT device_id, user_id, purpose, start_at, end_at, status,"
            " decided_by, decided_at FROM requests WHERE id = ?", (rid,)
        )
        self.assertEqual(len(rows), 1)
        device_id, user_id, purpose, start_at, end_at, status, decided_by, decided_at = rows[0]
        self.assertEqual(device_id, self.devices["DEV-001"])
        self.assertEqual(user_id, self.users["student1"])
        self.assertEqual(purpose, "嵌入式课程实验")
        self.assertEqual(start_at, A_START)  # NFR-07 归一化
        self.assertEqual(end_at, A_END)
        self.assertEqual(status, "pending")
        self.assertIsNone(decided_by)
        self.assertIsNone(decided_at)

        # 提交后立即可查：本人 list / show
        proc = self.cli("request", "list", "--db", self.db)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual([it["request_id"] for it in items], [rid])
        self.assertEqual(items[0]["status"], "pending")

        proc = self.cli("request", "show", "--db", self.db, "--request-id", str(rid))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        shown = self.payload(proc)
        self.assertEqual(shown["purpose"], "嵌入式课程实验")
        self.assertIsNone(shown["loan"])

    # ---- TC-CRQ-04-01：批准 ----
    def test_tc_crq_04_01_approve_pending_request(self):
        self.seed()
        self.login("student1")
        rid = self.submitted()
        self.login("admin")

        proc = self.approve(rid)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["request_id"], rid)
        self.assertEqual(body["status"], "approved")
        self.assertTrue(body["decided_at"])

        status, decided_by, decided_at, _ = self.request_row(rid)
        self.assertEqual(status, "approved")
        self.assertEqual(decided_by, self.users["admin"])
        self.assertEqual(decided_at, body["decided_at"])
        self.assertEqual(self.approved_count(), 1)

    # ---- TC-CRQ-04-01：拒绝必须带原因 ----
    def test_tc_crq_04_01_reject_records_reason(self):
        self.seed()
        self.login("student1")
        rid = self.submitted()
        self.login("admin")

        proc = self.reject(rid, reason="同一时段已批给其他课程")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["status"], "rejected")
        self.assertEqual(body["reject_reason"], "同一时段已批给其他课程")

        status, decided_by, decided_at, reason = self.request_row(rid)
        self.assertEqual(status, "rejected")
        self.assertEqual(decided_by, self.users["admin"])
        self.assertTrue(decided_at)
        self.assertEqual(reason, "同一时段已批给其他课程")

    # ---- TC-CRQ-09-01：取消 ----
    def test_tc_crq_09_01_cancel_only_own_pending(self):
        self.seed()
        self.login("student1")
        rid = self.submitted()

        # 他人（student2）取消 → 1，数据不变
        self.login("student2")
        proc = self.cancel(rid)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))
        self.assertEqual(self.request_row(rid)[0], "pending")

        # admin 取消 → 3（权限矩阵：cancel ✗ 3）
        self.login("admin")
        proc = self.cancel(rid)
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertEqual(self.request_row(rid)[0], "pending")

        # 本人取消 → 0
        self.login("student1")
        proc = self.cancel(rid)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["status"], "cancelled")
        self.assertEqual(self.request_row(rid)[0], "cancelled")

        # 已取消再取消 → 1
        proc = self.cancel(rid)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    # ---- 终态不可再变 ----
    def test_terminal_states_are_immutable(self):
        self.seed()
        self.login("student1")
        approved_id = self.submitted(device="DEV-001", start=A_START, end=A_END)
        rejected_id = self.submitted(device="DEV-002", start="2026-11-03T08:00:00Z",
                                     end="2026-11-03T12:00:00Z")
        cancelled_id = self.submitted(device="DEV-003", start="2026-11-04T08:00:00Z",
                                      end="2026-11-04T12:00:00Z")
        self.login("admin")
        self.assertEqual(self.approve(approved_id).returncode, 0)
        self.assertEqual(self.reject(rejected_id).returncode, 0)
        self.login("student1")
        self.assertEqual(self.cancel(cancelled_id).returncode, 0)
        self.login("admin")

        cases = [
            ("approve approved", self.approve(approved_id)),
            ("approve rejected", self.approve(rejected_id)),
            ("approve cancelled", self.approve(cancelled_id)),
            ("reject approved", self.reject(approved_id)),
            ("reject rejected", self.reject(rejected_id)),
            ("reject cancelled", self.reject(cancelled_id)),
        ]
        for label, proc in cases:
            with self.subTest(case=label):
                self.assertEqual(proc.returncode, 1, label + ": " + proc.stdout + proc.stderr)
        self.assertEqual(self.request_row(approved_id)[0], "approved")
        self.assertEqual(self.request_row(rejected_id)[0], "rejected")
        self.assertEqual(self.request_row(cancelled_id)[0], "cancelled")
        self.assertEqual(self.approved_count(), 1)

    # ---- TC-CRQ-05-01：重叠 → 4 且整事务回滚 ----
    def test_tc_crq_05_01_overlap_returns_4_and_rolls_back(self):
        self.seed()
        self.login("student1")
        first = self.submitted(start=A_START, end=A_END)
        self.login("admin")
        self.assertEqual(self.approve(first).returncode, 0)
        audit_before = len(self.audit_rows("request_approve"))

        self.login("student2")
        second = self.submitted(start=B_START, end=B_END)  # 10:00–14:00 与 08:00–12:00 重叠
        self.login("admin")
        proc = self.approve(second)
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["error"], "time_conflict")
        self.assertIn("conflicts", body)
        self.assertEqual([c["request_id"] for c in body["conflicts"]], [first])

        # 回滚：申请仍是 pending，审批人/时间为空，无新增 approved
        status, decided_by, decided_at, reason = self.request_row(second)
        self.assertEqual(status, "pending")
        self.assertIsNone(decided_by)
        self.assertIsNone(decided_at)
        self.assertIsNone(reason)
        self.assertEqual(self.approved_count(), 1)
        # 冲突回滚不留 approve 审计
        self.assertEqual(len(self.audit_rows("request_approve")), audit_before)
        self.assertEqual(
            self.query(
                "SELECT count(*) FROM audit_log WHERE action='request_approve' AND target_id=?",
                (second,),
            )[0][0],
            0,
        )

    # ---- TC-CRQ-05-02：首尾相接不算冲突 ----
    def test_tc_crq_05_02_back_to_back_allowed(self):
        self.seed()
        self.login("student1")
        first = self.submitted(start=A_START, end=A_END)
        self.login("admin")
        self.assertEqual(self.approve(first).returncode, 0)

        self.login("student2")
        second = self.submitted(start=C_START, end=C_END)  # 12:00 起，与第一段首尾相接
        self.login("admin")
        proc = self.approve(second)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["status"], "approved")
        self.assertEqual(self.request_row(second)[0], "approved")
        self.assertEqual(self.approved_count(), 2)

    # ---- pending / rejected / cancelled 不占位 ----
    def test_pending_rejected_cancelled_do_not_occupy(self):
        self.seed()
        # pending 不占位：两条重叠的 pending 可先后被处理，先批的不被后一条影响
        self.login("student1")
        self.submitted(start=A_START, end=A_END)
        self.login("student2")
        overlap_pending = self.submitted(start=A_START, end=A_END)
        self.login("admin")
        proc = self.approve(overlap_pending)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        # rejected 不占位
        self.login("student3")
        rejected_slot = self.submitted(start="2026-11-03T08:00:00Z", end="2026-11-03T12:00:00Z")
        self.login("admin")
        self.assertEqual(self.reject(rejected_slot).returncode, 0)
        self.login("student4")
        after_reject = self.submitted(start="2026-11-03T08:00:00Z", end="2026-11-03T12:00:00Z")
        self.login("admin")
        proc = self.approve(after_reject)
        self.assertEqual(proc.returncode, 0, "rejected 不应占位: " + proc.stdout + proc.stderr)

        # cancelled 不占位
        self.login("student5")
        cancelled_slot = self.submitted(start="2026-11-04T08:00:00Z", end="2026-11-04T12:00:00Z")
        self.assertEqual(self.cancel(cancelled_slot).returncode, 0)
        self.login("student6")
        after_cancel = self.submitted(start="2026-11-04T08:00:00Z", end="2026-11-04T12:00:00Z")
        self.login("admin")
        proc = self.approve(after_cancel)
        self.assertEqual(proc.returncode, 0, "cancelled 不应占位: " + proc.stdout + proc.stderr)
        self.assertEqual(self.approved_count(), 3)

    # ---- 未归还 loan 从 checked_out_at 起无限占位 ----
    def test_unreturned_loan_blocks_later_slot_until_returned(self):
        self.seed()
        self.login("student1")
        borrowed = self.submitted(start="2026-11-10T08:00:00Z", end="2026-11-10T12:00:00Z")
        self.login("admin")
        self.assertEqual(self.approve(borrowed).returncode, 0)

        # 直接造一条未归还借出记录（WP4 命令未实现，按契约 §2 loans 表插入）
        self.exec_sql(
            "INSERT INTO loans (request_id, device_id, user_id, checked_out_at, due_at,"
            " returned_at, created_at) VALUES (?, ?, ?, ?, ?, NULL, ?)",
            (
                borrowed, self.devices["DEV-001"], self.users["student1"],
                "2026-11-10T08:00:00Z", "2026-11-10T12:00:00Z", "2026-11-10T08:00:00Z",
            ),
        )

        # 后续时段完全在已批准申请结束之后 → 仍因未归还 loan 冲突
        self.login("student2")
        later = self.submitted(start="2026-11-20T08:00:00Z", end="2026-11-20T12:00:00Z")
        self.login("admin")
        proc = self.approve(later)
        self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["error"], "time_conflict")
        same_request = [c for c in body["conflicts"] if c["request_id"] == borrowed]
        self.assertEqual(len(same_request), 1, "申请与其借出记录只应计 1 次冲突: %r" % body)
        self.assertEqual(self.request_row(later)[0], "pending")

        # 归还后占用立即解除
        self.exec_sql(
            "UPDATE loans SET returned_at = '2026-11-10T11:00:00Z' WHERE request_id = ?",
            (borrowed,),
        )
        proc = self.approve(later)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.request_row(later)[0], "approved")

    # ---- 权限矩阵 ----
    def test_permission_matrix_role_checks(self):
        self.seed()
        self.login("student1")
        rid = self.submitted()

        self.login("student2")
        for label, proc in (
            ("student approve", self.approve(rid)),
            ("student reject", self.reject(rid)),
        ):
            with self.subTest(case=label):
                self.assertEqual(proc.returncode, 3, label + ": " + proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))

        self.login("director")
        for label, proc in (
            ("director list", self.cli("request", "list", "--db", self.db)),
            ("director show", self.cli("request", "show", "--db", self.db,
                                       "--request-id", str(rid))),
            ("director approve", self.approve(rid)),
        ):
            with self.subTest(case=label):
                self.assertEqual(proc.returncode, 3, label + ": " + proc.stdout + proc.stderr)

        # admin 不能提交申请（权限矩阵 request submit ✗ 3）
        self.login("admin")
        proc = self.submit()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)

        # student 传 --all → 3；admin 可 --all
        self.login("student1")
        proc = self.cli("request", "list", "--db", self.db, "--all")
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.login("admin")
        proc = self.cli("request", "list", "--db", self.db, "--all")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(len(self.payload(proc)["items"]), 1)

        # 申请仍是 pending，未被任何越权调用改动
        self.assertEqual(self.request_row(rid)[0], "pending")

    # ---- NFR-04：学生只见本人申请 ----
    def test_tc_nfr_04_01_student_sees_only_own_requests(self):
        self.seed()
        self.login("student1")
        mine = [self.submitted(device="DEV-001"), self.submitted(device="DEV-002")]
        self.login("student2")
        theirs = self.submitted(device="DEV-003")

        self.login("student1")
        proc = self.cli("request", "list", "--db", self.db)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        items = self.payload(proc)["items"]
        self.assertEqual(sorted(it["request_id"] for it in items), sorted(mine))
        self.assertTrue(all(it["user_id"] == self.users["student1"] for it in items))

        # 看他人详情 → 1（业务拒绝，不是 3）
        proc = self.cli("request", "show", "--db", self.db, "--request-id", str(theirs))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))

        # admin 可见全部
        self.login("admin")
        proc = self.cli("request", "list", "--db", self.db)
        self.assertEqual(len(self.payload(proc)["items"]), 3)
        proc = self.cli("request", "show", "--db", self.db, "--request-id", str(theirs))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    # ---- 参数校验 → 2；不存在的 request-id → 1 ----
    def test_parameter_validation_and_missing_request(self):
        self.seed()
        self.login("student1")
        rid = self.submitted()

        proc = self.submit(start=A_END, end=A_START)  # from > to
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))
        proc = self.submit(start=A_START, end=A_START)  # from == to
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        proc = self.submit(start="2026-13-40T08:00:00Z", end=A_END)  # 非法时间
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        for purpose in ("", "   "):
            with self.subTest(purpose=repr(purpose)):
                proc = self.submit(purpose=purpose)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(len(self.query("SELECT id FROM requests")), 1, "参数错误不应落库")

        self.login("admin")
        proc = self.cli("request", "reject", "--db", self.db, "--request-id", str(rid))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        proc = self.reject(rid, reason="   ")
        self.assertEqual(proc.returncode, 2, "空原因应视为缺参: " + proc.stdout + proc.stderr)
        self.assertEqual(self.request_row(rid)[0], "pending")

        missing = max(self.query("SELECT max(id) FROM requests")[0][0], 999) + 1
        for label, proc in (
            ("show", self.cli("request", "show", "--db", self.db,
                             "--request-id", str(missing))),
            ("approve", self.approve(missing)),
            ("reject", self.reject(missing)),
        ):
            with self.subTest(case=label):
                self.assertEqual(proc.returncode, 1, label + ": " + proc.stdout + proc.stderr)
        self.login("student1")
        proc = self.cancel(missing)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    # ---- 设备状态 maintenance / retired ----
    def test_device_status_blocks_submit_and_approve(self):
        self.seed()
        self.login("student1")
        for status in ("maintenance", "retired"):
            with self.subTest(status=status):
                self.set_device_status("DEV-001", status)
                proc = self.submit(device="DEV-001")
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(self.payload(proc)["error"], "device_unavailable")
        self.assertEqual(self.query("SELECT count(*) FROM requests")[0][0], 0)

        # 提交时可用，审批前转 retired → approve 返回 1，申请仍 pending
        self.set_device_status("DEV-002", "available")
        rid = self.submitted(device="DEV-002")
        self.set_device_status("DEV-002", "retired")
        self.login("admin")
        proc = self.approve(rid)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(self.payload(proc)["error"], "device_unavailable")
        status, decided_by, decided_at, _ = self.request_row(rid)
        self.assertEqual(status, "pending")
        self.assertIsNone(decided_by)
        self.assertIsNone(decided_at)

    # ---- 审计：4 类事件各一条 ----
    def test_audit_events_for_request_actions(self):
        self.seed()
        self.login("student1")
        to_approve = self.submitted(device="DEV-001")
        to_reject = self.submitted(device="DEV-002")
        to_cancel = self.submitted(device="DEV-003")
        self.assertEqual(self.cancel(to_cancel).returncode, 0)
        self.login("admin")
        self.assertEqual(self.approve(to_approve).returncode, 0)
        self.assertEqual(self.reject(to_reject).returncode, 0)

        expected = {"request_submit": 3, "request_approve": 1,
                    "request_reject": 1, "request_cancel": 1}
        for action, count in expected.items():
            with self.subTest(action=action):
                rows = self.audit_rows(action)
                self.assertEqual(len(rows), count, "%s 审计条数不符" % action)
                for target_type, target_id, result, detail in rows:
                    self.assertEqual(target_type, "request")
                    self.assertEqual(result, "ok")
                    self.assertIn(target_id, (to_approve, to_reject, to_cancel))

        approve_target = self.audit_rows("request_approve")[0][1]
        self.assertEqual(approve_target, to_approve)
        reject_detail = self.audit_rows("request_reject")[0][3]
        self.assertIsNotNone(reject_detail)
        self.assertIn("时段已满", reject_detail)
        submit_detail = self.audit_rows("request_submit")[0][3]
        self.assertIn("device_id", submit_detail)


if __name__ == "__main__":
    unittest.main()

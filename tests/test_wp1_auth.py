"""QA1（WBS 3.2）验收测试：WP1 账户与角色权限。

契约依据：docs/05-architecture.md §1/§2/§4/§5、docs/04-scope.md §6、docs/10-work-packages.md WP1。
隔离方式：所有 CLI 调用以临时目录为 cwd 并显式传 --db <临时路径>，
因此会话文件落在 <临时目录>/data/session.json（契约 §1 的相对路径），不触碰仓库的 data/。
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
TABLES = {"users", "devices", "requests", "loans", "audit_log"}
# src/ 内部模块（架构 §1 文件布局），不属于第三方依赖
LOCAL_MODULES = {
    "main", "db", "auth", "audit", "devices", "requests", "loans", "stats", "waitlist",
}


class WP1CliTest(unittest.TestCase):
    """WP1 的 CLI 层验收（init-db / seed / login）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-wp1-")
        self.db = os.path.join(self.tmp, "qa.db")
        self.session_file = os.path.join(self.tmp, "data", "session.json")
        self.env = dict(os.environ)
        # 显式用 --db 指定库、用 cwd 决定会话文件位置，避免两个环境变量干扰
        self.env.pop("DEVICELOAN_DB", None)
        self.env.pop("DEVICELOAN_SESSION", None)
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 辅助 ----
    def cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, MAIN] + list(args),
            cwd=cwd or self.tmp,
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

    def query(self, sql, params=()):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def seed(self):
        proc = self.cli("seed", "--db", self.db)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return self.payload(proc)

    # ---- TC-CRQ-01-01：init-db ----
    def test_tc_crq_01_01_init_db_idempotent(self):
        proc = self.cli("--db", self.db, "init-db")  # 全局位置传 --db
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIs(body["created"], True)
        self.assertEqual(os.path.abspath(body["db_path"]), os.path.abspath(self.db))
        names = {r[0] for r in self.query("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(TABLES.issubset(names), "缺少表: %s" % (TABLES - names))

        # 第二次执行：不得报错，created 应为 false
        proc = self.cli("init-db", "--db", self.db)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIs(self.payload(proc)["created"], False)
        names = {r[0] for r in self.query("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(TABLES.issubset(names))

    # ---- TC-CRQ-01-01：seed 规模 ----
    def test_tc_crq_01_01_seed_creates_8_users_20_devices(self):
        body = self.seed()
        self.assertEqual(body["users"], 8)
        self.assertEqual(body["devices"], 20)
        self.assertEqual(body["requests"], 0)
        self.assertEqual(body["loans"], 0)

        self.assertEqual(self.query("SELECT count(*) FROM users")[0][0], 8)
        self.assertEqual(self.query("SELECT count(*) FROM devices")[0][0], 20)

        roles = dict(self.query("SELECT role, count(*) FROM users GROUP BY role"))
        self.assertEqual(roles, {"student": 6, "admin": 1, "director": 1})

        rows = self.query("SELECT username, password_hash, salt, iterations FROM users")
        names = {r[0] for r in rows}
        self.assertEqual(
            names,
            {"student1", "student2", "student3", "student4", "student5", "student6",
             "admin", "director"},
        )
        for username, pw_hash, salt, iterations in rows:
            self.assertGreaterEqual(iterations, 100000, username)  # NFR-03
            self.assertEqual(len(salt), 32, "盐应为 16 字节十六进制: %s" % username)
            int(salt, 16)
            self.assertEqual(len(pw_hash), 64, "SHA-256 摘要应为 64 位十六进制: %s" % username)
            int(pw_hash, 16)

        for code, name, category, status, note, created_at in self.query(
            "SELECT code, name, category, status, note, created_at FROM devices"
        ):
            self.assertTrue(code.startswith("DEV-"), code)
            self.assertTrue(name and category, code)
            self.assertEqual(status, "available", code)
            self.assertRegex(created_at, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")  # NFR-07

    # ---- seed 重复执行（WP1 任务书：退出码 1）----
    def test_tc_crq_01_01_seed_twice_exits_1(self):
        self.seed()
        proc = self.cli("seed", "--db", self.db)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIn("error", body)
        self.assertEqual(self.query("SELECT count(*) FROM users")[0][0], 8)
        self.assertEqual(self.query("SELECT count(*) FROM devices")[0][0], 20)

    # ---- TC-CRQ-01-01：login 成功与角色 ----
    def test_tc_crq_01_01_login_returns_correct_role(self):
        self.seed()
        for username, role in (
            ("student1", "student"),
            ("student6", "student"),
            ("admin", "admin"),
            ("director", "director"),
        ):
            with self.subTest(username=username):
                proc = self.cli(
                    "login", "--db", self.db, "--username", username,
                    "--password", SEED_PASSWORD,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                body = self.payload(proc)
                self.assertEqual(body["username"], username)
                self.assertEqual(body["role"], role)
                self.assertIsInstance(body["user_id"], int)
                self.assertTrue(os.path.exists(self.session_file), "login 应写会话文件")

    # ---- 错误口令 / 不存在用户 → 1 ----
    def test_tc_crq_01_01_login_wrong_password_exits_1(self):
        self.seed()
        proc = self.cli(
            "login", "--db", self.db, "--username", "student1", "--password", "wrong-pass",
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIn("error", body)
        self.assertNotIn("user_id", body)

    def test_tc_crq_01_01_login_unknown_user_exits_1(self):
        self.seed()
        proc = self.cli(
            "login", "--db", self.db, "--username", "nobody", "--password", SEED_PASSWORD,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))

    # ---- 缺参数 → 2 ----
    def test_tc_crq_01_01_login_missing_args_exits_2(self):
        self.seed()
        for args in (
            ("login", "--db", self.db, "--username", "student1"),
            ("login", "--db", self.db, "--password", SEED_PASSWORD),
            ("login",),
        ):
            with self.subTest(args=args):
                proc = self.cli(*args)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertIn("error", self.payload(proc))

    # ---- 会话文件内容 ----
    def test_tc_crq_01_01_session_file_has_no_credentials(self):
        self.seed()
        proc = self.cli(
            "login", "--db", self.db, "--username", "admin", "--password", SEED_PASSWORD,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(self.session_file, encoding="utf-8") as fh:
            raw = fh.read()
        session = json.loads(raw)
        self.assertEqual(session["username"], "admin")
        self.assertEqual(session["role"], "admin")
        self.assertIn("created_at", session)
        for key in session:
            self.assertNotIn("pass", key.lower(), "会话文件不得含口令字段: %s" % key)
            self.assertNotIn("salt", key.lower())
            self.assertNotIn("hash", key.lower())
        self.assertNotIn(SEED_PASSWORD, raw)
        self.assertNotIn("Passw0rd", raw)

    # ---- TC-NFR-03-01：库中无明文口令 ----
    def test_tc_nfr_03_01_no_plaintext_password_in_db(self):
        self.seed()
        for column in ("password_hash", "salt"):
            values = [r[0] for r in self.query("SELECT %s FROM users" % column)]
            self.assertEqual(len(values), 8)
            for value in values:
                self.assertNotIn("Passw0rd", value)
                self.assertNotIn(SEED_PASSWORD, value)

        rows = self.query("SELECT username, password_hash, salt, iterations FROM users")
        self.assertEqual(len({r[2] for r in rows}), 8, "每个用户的盐必须不同")
        self.assertEqual(len({r[1] for r in rows}), 8, "相同口令＋不同盐应得到不同摘要")

        # 摘要确实是该口令的 PBKDF2 结果（不是明文、也不是空串）
        sys.path.insert(0, SRC)
        try:
            import auth
        finally:
            sys.path.remove(SRC)
        for username, pw_hash, salt, iterations in rows:
            self.assertTrue(
                auth.verify_password(SEED_PASSWORD, salt, pw_hash, iterations),
                "口令校验失败: %s" % username,
            )
            self.assertFalse(
                auth.verify_password(SEED_PASSWORD + "x", salt, pw_hash, iterations),
                "错误口令不应通过: %s" % username,
            )

        # 对库文件（含可能存在的 -wal / -journal）做一次字节扫描
        scanned = 0
        for suffix in ("", "-wal", "-journal"):
            path = self.db + suffix
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    blob = fh.read()
                scanned += 1
                self.assertNotIn(b"Passw0rd", blob, "库文件 %s 中出现明文口令" % path)
        self.assertGreaterEqual(scanned, 1)

    # ---- TC-NFR-04-01（单元部分）：角色判定 ----
    def test_tc_nfr_04_01_student_denied_admin_actions(self):
        """WP1 未注册 admin 专属子命令，故直接验证 auth.has_role 的角色判定。

        端到端（student 调 admin 命令 → 退出码 3）由 WP3 在注册 request/loan/stats
        子命令后完成；此处只锁定 WP1 交付的角色判定函数本身。
        """
        sys.path.insert(0, SRC)
        try:
            import auth  # noqa: F401  (需 src 在 sys.path 上)
        finally:
            sys.path.remove(SRC)

        self.seed()
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        try:
            student = conn.execute(
                "SELECT * FROM users WHERE username='student1'").fetchone()
            admin = conn.execute("SELECT * FROM users WHERE username='admin'").fetchone()
            director = conn.execute(
                "SELECT * FROM users WHERE username='director'").fetchone()
        finally:
            conn.close()

        self.assertEqual(student["role"], "student")
        # 权限矩阵 §5：student 对 approve/reject/loan/audit/--all 均为 ✗ 3
        self.assertFalse(auth.has_role(student, "admin"))
        self.assertFalse(auth.has_role(student, "admin", "director"))
        self.assertTrue(auth.has_role(student, "student"))
        # 无会话视为角色不符（架构 §1 会话判定规则）
        self.assertFalse(auth.has_role(None, "admin"))
        self.assertFalse(auth.has_role(None, "student", "admin", "director"))
        # 正向：admin 可审批，director 可看统计、不可审批
        self.assertTrue(auth.has_role(admin, "admin"))
        self.assertTrue(auth.has_role(director, "admin", "director"))  # stats usage
        self.assertFalse(auth.has_role(director, "admin"))              # approve / audit

    def test_tc_nfr_04_01_no_session_has_no_user(self):
        """无会话文件时 current_user() 返回 None —— 受保护命令据此映射为退出码 3。"""
        sys.path.insert(0, SRC)
        try:
            import auth
        finally:
            sys.path.remove(SRC)
        saved = os.environ.get("DEVICELOAN_SESSION")
        os.environ["DEVICELOAN_SESSION"] = self.session_file
        try:
            self.assertFalse(os.path.exists(self.session_file))
            self.assertIsNone(auth.read_session())
            self.assertIsNone(auth.current_user(None))
        finally:
            if saved is None:
                os.environ.pop("DEVICELOAN_SESSION", None)
            else:
                os.environ["DEVICELOAN_SESSION"] = saved

    # ---- TC-NFR-01-01：无第三方依赖 ----
    def test_tc_nfr_01_01_no_third_party_imports(self):
        stdlib = set(sys.stdlib_module_names)
        allowed = stdlib | LOCAL_MODULES
        seen = set()
        for name in sorted(os.listdir(SRC)):
            if not name.endswith(".py"):
                continue
            seen.add(name)
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
            extra = imported - allowed
            self.assertEqual(extra, set(), "%s 引入非标准库/非本项目模块: %s" % (name, extra))
        wp1_files = {"main.py", "db.py", "auth.py", "audit.py"}
        self.assertTrue(wp1_files.issubset(seen), "WP1 模块未被扫描到: %s" % (wp1_files - seen))

    # ---- 命令注册：WP3 之后 request list 已注册，无会话 → 3 ----
    def test_wp1_wp3_commands_registered_and_require_session(self):
        """WP3 已完成，`request list` 按契约 §4 注册；无会话调用走会话判定 → 3。

        WP1 时期的旧断言（未注册 → 2）与被测契约矛盾，已在 QA3 修订为契约口径。
        """
        proc = self.cli("request", "list")
        self.assertEqual(proc.returncode, 3, "无会话应退出码 3: " + proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertIn("error", body)
        self.assertEqual(body["error"], "not_logged_in")

        # 参数校验先于会话校验（契约 §1 末段）：缺 --request-id → 2，即使未登录
        proc = self.cli("request", "approve", "--db", self.db)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("error", self.payload(proc))

    # ---- TC-NFR-04-01 端到端：student 调 admin 命令 → 3 ----
    def test_tc_nfr_04_01_student_calling_admin_command_exits_3(self):
        self.seed()
        login = self.cli(
            "login", "--db", self.db, "--username", "student1",
            "--password", SEED_PASSWORD,
        )
        self.assertEqual(login.returncode, 0, login.stdout + login.stderr)

        proc = self.cli("request", "approve", "--db", self.db, "--request-id", "1")
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        body = self.payload(proc)
        self.assertEqual(body["error"], "forbidden")
        self.assertEqual(self.query("SELECT count(*) FROM requests WHERE status='approved'")[0][0], 0)


if __name__ == "__main__":
    unittest.main()

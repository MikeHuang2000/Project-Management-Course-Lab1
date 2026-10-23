"""演示数据脚本：调用项目 CLI 生成一套可演示数据，并打印统计摘要。"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src" / "main.py"
SEED_PASSWORD = "Passw0rd!"
DEVICE = "DEV-001"
STUDENT = "student1"
ADMIN = "admin"


def iso_at(day_offset, hour):
    day = datetime.now(timezone.utc).date() + timedelta(days=day_offset)
    return "%sT%02d:00:00Z" % (day.isoformat(), hour)


class Runner:
    def __init__(self, db):
        self.db = db
        self.env = dict(os.environ)
        self.env["DEVICELOAN_SESSION"] = os.path.abspath(db) + ".session.json"
        self.env["PYTHONIOENCODING"] = "utf-8"

    def run(self, *args):
        cmd = [sys.executable, str(MAIN), "--db", self.db] + [str(a) for a in args]
        print("$ " + " ".join(cmd))
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if stdout:
            print("  输出: " + stdout)
        print("  退出码: %d" % proc.returncode)
        if proc.returncode != 0:
            if stderr:
                print("  错误: " + stderr)
            print("步骤失败，终止演示数据生成。")
            sys.exit(proc.returncode)
        return stdout

    def run_json(self, *args):
        stdout = self.run(*args)
        try:
            return json.loads(stdout.splitlines()[-1])
        except (IndexError, ValueError):
            print("无法解析命令输出为 JSON: %r" % stdout)
            sys.exit(1)


def clean(path):
    for suffix in ("", "-wal", "-shm", ".session.json"):
        target = path + suffix
        if os.path.exists(target):
            os.remove(target)


def summary(db):
    uri = "file:%s?mode=ro" % Path(db).resolve().as_posix()
    conn = sqlite3.connect(uri, uri=True)
    try:
        devices = conn.execute("SELECT count(*) FROM devices").fetchone()[0]
        requests = conn.execute("SELECT count(*) FROM requests").fetchone()[0]
        approved = conn.execute(
            "SELECT count(*) FROM requests WHERE status = 'approved'"
        ).fetchone()[0]
        loans = conn.execute("SELECT count(*) FROM loans").fetchone()[0]
        returned = conn.execute(
            "SELECT count(*) FROM loans WHERE returned_at IS NOT NULL"
        ).fetchone()[0]
        audits = conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]
    finally:
        conn.close()
    return {
        "devices": devices,
        "requests": requests,
        "approved": approved,
        "loans": loans,
        "returned": returned,
        "audit": audits,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="生成设备借用管理系统的演示数据")
    parser.add_argument("--db", default=os.path.join("data", "demo.db"), help="数据库文件路径")
    parser.add_argument("--force", action="store_true", help="数据库已存在时删除重建")
    args = parser.parse_args()

    db = os.path.abspath(args.db)
    if os.path.exists(db):
        if not args.force:
            print("数据库已存在: %s" % db)
            print("如需重建请加 --force。")
            return 2
        clean(db)
        print("已删除旧数据库: %s" % db)
    else:
        os.makedirs(os.path.dirname(db), exist_ok=True)

    runner = Runner(db)
    start_at = iso_at(1, 9)
    end_at = iso_at(1, 11)

    runner.run("init-db")
    runner.run("seed")
    runner.run_json("login", "--username", STUDENT, "--password", SEED_PASSWORD)
    created = runner.run_json(
        "request",
        "submit",
        "--device",
        DEVICE,
        "--from",
        start_at,
        "--to",
        end_at,
        "--purpose",
        "课程实验测量演示",
    )
    request_id = created["request_id"]
    runner.run_json("login", "--username", ADMIN, "--password", SEED_PASSWORD)
    runner.run_json("request", "approve", "--request-id", request_id)
    loan = runner.run_json("loan", "checkout", "--request-id", request_id)
    loan_id = loan["loan_id"]
    runner.run_json("loan", "return", "--loan-id", loan_id)

    result = summary(db)
    print("")
    print("演示数据摘要 (%s)" % db)
    print("  设备数: %d" % result["devices"])
    print("  申请数: %d（其中 approved: %d）" % (result["requests"], result["approved"]))
    print("  借出数: %d（其中已归还: %d）" % (result["loans"], result["returned"]))
    print("  审计条数: %d" % result["audit"])
    print("  申请 ID: %d，借出 ID: %d" % (request_id, loan_id))
    print("  时段: %s ~ %s" % (start_at, end_at))
    return 0


if __name__ == "__main__":
    sys.exit(main())

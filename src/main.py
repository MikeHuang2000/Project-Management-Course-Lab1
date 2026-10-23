"""CLI 入口：子命令定义、统一 JSON 输出与退出码映射。"""

import argparse
import json
import sqlite3
import sys

import audit
import auth
import db

SEED_PASSWORD = "Passw0rd!"

SEED_USERS = [
    ("student1", "student", "陈晓"),
    ("student2", "student", "李雷"),
    ("student3", "student", "王芳"),
    ("student4", "student", "赵敏"),
    ("student5", "student", "周杰"),
    ("student6", "student", "吴静"),
    ("admin", "admin", "设备管理员"),
    ("director", "director", "实验中心主任"),
]

SEED_DEVICES = [
    ("DEV-001", "倒置金相显微镜", "显微镜", "含 10x/40x 物镜"),
    ("DEV-002", "体视显微镜", "显微镜", None),
    ("DEV-003", "荧光显微镜", "显微镜", "需提前预热"),
    ("DEV-004", "数字示波器 DS-200", "示波器", None),
    ("DEV-005", "四通道示波器", "示波器", "带宽 100MHz"),
    ("DEV-006", "手持示波表", "示波器", None),
    ("DEV-007", "激光投影仪", "投影仪", "阶梯教室用"),
    ("DEV-008", "便携投影仪", "投影仪", None),
    ("DEV-009", "高清投影仪", "投影仪", None),
    ("DEV-010", "商务笔记本 T14", "笔记本", None),
    ("DEV-011", "图形工作站笔记本", "笔记本", "含独立显卡"),
    ("DEV-012", "轻薄笔记本", "笔记本", None),
    ("DEV-013", "STM32 开发板", "开发板", "含下载器"),
    ("DEV-014", "FPGA 开发板", "开发板", None),
    ("DEV-015", "树莓派套件", "开发板", "含外壳与电源"),
    ("DEV-016", "数字万用表", "测量仪器", None),
    ("DEV-017", "函数信号发生器", "测量仪器", None),
    ("DEV-018", "可编程直流电源", "测量仪器", None),
    ("DEV-019", "热成像仪", "测量仪器", None),
    ("DEV-020", "便携频谱仪", "测量仪器", "需押金"),
]


class CLIError(Exception):
    def __init__(self, code, error, message):
        super().__init__(message)
        self.code = code
        self.error = error
        self.message = message


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail(2, "bad_args", message)
        sys.exit(2)


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False))


def fail(code, error, message):
    emit({"error": error, "message": message})


def cmd_init_db(args):
    conn = db.connect(args.db)
    created = db.init_db(conn)
    conn.close()
    return {"created": created, "db_path": db.db_path(args.db)}


def cmd_seed(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    with db.transaction(conn):
        count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
        if count and not args.reset:
            raise CLIError(1, "already_seeded", "数据库已有数据，如需重建请使用 --reset")
        if args.reset:
            for table in ("loans", "requests", "audit_log", "devices", "users"):
                conn.execute("DELETE FROM %s" % table)
        now = db.now_iso()
        for username, role, display_name in SEED_USERS:
            salt, pw_hash, iterations = auth.hash_password(SEED_PASSWORD)
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, iterations, role, display_name, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (username, pw_hash, salt, iterations, role, display_name, now),
            )
        for code, name, category, note in SEED_DEVICES:
            conn.execute(
                "INSERT INTO devices (code, name, category, status, note, created_at)"
                " VALUES (?, ?, ?, 'available', ?, ?)",
                (code, name, category, note, now),
            )
        users = conn.execute("SELECT count(*) FROM users").fetchone()[0]
        devices = conn.execute("SELECT count(*) FROM devices").fetchone()[0]
        requests = conn.execute("SELECT count(*) FROM requests").fetchone()[0]
        loans = conn.execute("SELECT count(*) FROM loans").fetchone()[0]
    conn.close()
    return {"users": users, "devices": devices, "requests": requests, "loans": loans}


def cmd_login(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    user = auth.authenticate(conn, args.username, args.password)
    if user is None:
        with db.transaction(conn):
            audit.log(conn, args.username, "login", None, "denied", None)
        conn.close()
        raise CLIError(1, "login_failed", "用户名或口令错误")
    with db.transaction(conn):
        audit.log(conn, user, "login", ("user", user["id"]), "ok", None)
    auth.write_session(user)
    result = {"user_id": user["id"], "username": user["username"], "role": user["role"]}
    conn.close()
    return result


def build_parser():
    parser = Parser(prog="deviceloan", description="设备借用管理系统")
    parser.add_argument("--db", dest="db", default=None, help="数据库文件路径")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-db", help="建库建表")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    p.set_defaults(handler=cmd_init_db)

    p = sub.add_parser("seed", help="写入演示数据")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    p.add_argument("--reset", action="store_true", help="清空后重建")
    p.set_defaults(handler=cmd_seed)

    p = sub.add_parser("login", help="登录并写会话文件")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.set_defaults(handler=cmd_login)

    return parser


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        payload = args.handler(args)
    except CLIError as exc:
        fail(exc.code, exc.error, exc.message)
        return exc.code
    except sqlite3.Error as exc:
        fail(1, "db_error", str(exc))
        return 1
    emit(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())

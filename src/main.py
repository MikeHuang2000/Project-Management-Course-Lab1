"""CLI 入口：子命令定义、统一 JSON 输出与退出码映射。"""

import argparse
import json
import sqlite3
import sys

import audit
import auth
import db
import devices
import loans
import requests
import stats
import waitlist

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
            for table in ("loans", "waitlists", "requests", "audit_log", "devices", "users"):
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


def require_session(conn):
    user = auth.current_user(conn)
    if user is None:
        raise CLIError(3, "not_logged_in", "请先登录")
    return user


def cmd_device_list(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    require_session(conn)
    items = devices.list_devices(conn, category=args.category, status=args.status)
    conn.close()
    return {"items": items}


def cmd_device_search(args):
    if bool(args.from_) != bool(args.to_):
        raise CLIError(2, "bad_args", "--from 与 --to 必须成对出现")
    if not (args.name or args.category or args.from_ or args.to_):
        raise CLIError(2, "bad_args", "至少提供 --name、--category、--from/--to 之一")
    start = devices.normalize_iso(args.from_)
    end = devices.normalize_iso(args.to_)
    if (args.from_ and start is None) or (args.to_ and end is None):
        raise CLIError(2, "bad_args", "时间格式非法，应为 ISO 8601")
    if start and end and end <= start:
        raise CLIError(2, "bad_args", "结束时间必须晚于开始时间")
    conn = db.connect(args.db)
    db.init_db(conn)
    require_session(conn)
    items = devices.search_devices(
        conn, name=args.name, category=args.category, start=start, end=end
    )
    conn.close()
    return {"items": items}


def cmd_request_submit(args):
    start = devices.normalize_iso(args.from_)
    end = devices.normalize_iso(args.to_)
    if start is None or end is None:
        raise CLIError(2, "bad_args", "时间格式非法，应为 ISO 8601")
    if start >= end:
        raise CLIError(2, "bad_args", "结束时间必须晚于开始时间")
    purpose = args.purpose.strip()
    if not purpose:
        raise CLIError(2, "bad_args", "用途不能为空")
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return requests.submit(conn, user, args.device, start, end, purpose)
    finally:
        conn.close()


def cmd_request_cancel(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return requests.cancel(conn, user, args.request_id)
    finally:
        conn.close()


def cmd_request_list(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        items = requests.list_requests(
            conn, user, status=args.status, show_all=args.all
        )
    finally:
        conn.close()
    return {"items": items}


def cmd_request_show(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return requests.show(conn, user, args.request_id)
    finally:
        conn.close()


def cmd_request_approve(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return requests.approve(conn, user, args.request_id)
    finally:
        conn.close()


def cmd_request_reject(args):
    reason = args.reason.strip()
    if not reason:
        raise CLIError(2, "bad_args", "拒绝原因不能为空")
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return requests.reject(conn, user, args.request_id, reason)
    finally:
        conn.close()


def cmd_waitlist_join(args):
    start = devices.normalize_iso(args.from_)
    end = devices.normalize_iso(args.to_)
    if start is None or end is None:
        raise CLIError(2, "bad_args", "时间格式非法，应为 ISO 8601")
    if start >= end:
        raise CLIError(2, "bad_args", "结束时间必须晚于开始时间")
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return waitlist.join(conn, user, args.device, start, end, args.note)
    finally:
        conn.close()


def cmd_waitlist_list(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        items = waitlist.list_waitlists(
            conn, user, show_all=args.all, device_ref=args.device, status=args.status
        )
    finally:
        conn.close()
    return {"items": items}


def cmd_loan_checkout(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return loans.checkout(conn, user, args.request_id)
    finally:
        conn.close()


def cmd_loan_return(args):
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        return loans.return_loan(conn, user, args.loan_id)
    finally:
        conn.close()


def cmd_stats_usage(args):
    start = devices.normalize_iso(args.from_)
    end = devices.normalize_iso(args.to_)
    if start is None or end is None:
        raise CLIError(2, "bad_args", "时间格式非法，应为 ISO 8601")
    if end <= start:
        raise CLIError(2, "bad_args", "结束时间必须晚于开始时间")
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        if user["role"] not in ("admin", "director"):
            raise CLIError(3, "forbidden", "仅管理员或主任可查看统计")
        return stats.usage(conn, start, end)
    finally:
        conn.close()


def cmd_stats_overdue(args):
    start = devices.normalize_iso(args.from_)
    end = devices.normalize_iso(args.to_)
    if (args.from_ and start is None) or (args.to_ and end is None):
        raise CLIError(2, "bad_args", "时间格式非法，应为 ISO 8601")
    if start and end and end <= start:
        raise CLIError(2, "bad_args", "结束时间必须晚于开始时间")
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        if user["role"] not in ("admin", "director"):
            raise CLIError(3, "forbidden", "仅管理员或主任可查看统计")
        return stats.overdue(conn, start, end)
    finally:
        conn.close()


def cmd_audit_list(args):
    start = devices.normalize_iso(args.from_)
    end = devices.normalize_iso(args.to_)
    if (args.from_ and start is None) or (args.to_ and end is None):
        raise CLIError(2, "bad_args", "时间格式非法，应为 ISO 8601")
    if start and end and end <= start:
        raise CLIError(2, "bad_args", "结束时间必须晚于开始时间")
    if args.limit < 1:
        raise CLIError(2, "bad_args", "--limit 必须为正整数")
    conn = db.connect(args.db)
    db.init_db(conn)
    try:
        user = require_session(conn)
        if user["role"] != "admin":
            raise CLIError(3, "forbidden", "仅管理员可查询审计日志")
        items = audit.list_entries(
            conn,
            action=args.action,
            user=args.user,
            start=start,
            end=end,
            limit=args.limit,
        )
    finally:
        conn.close()
    return {"items": items}


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

    p = sub.add_parser("device", help="设备目录查询")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    dsub = p.add_subparsers(dest="device_command", required=True)

    d = dsub.add_parser("list", help="设备列表")
    d.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    d.add_argument("--category")
    d.add_argument(
        "--status", choices=("available", "maintenance", "retired")
    )
    d.set_defaults(handler=cmd_device_list)

    d = dsub.add_parser("search", help="按名称/类别/时段检索")
    d.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    d.add_argument("--name")
    d.add_argument("--category")
    d.add_argument("--from", dest="from_")
    d.add_argument("--to", dest="to_")
    d.set_defaults(handler=cmd_device_search)

    p = sub.add_parser("request", help="借用申请")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    rsub = p.add_subparsers(dest="request_command", required=True)

    r = rsub.add_parser("submit", help="提交申请")
    r.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    r.add_argument("--device", required=True)
    r.add_argument("--from", dest="from_", required=True)
    r.add_argument("--to", dest="to_", required=True)
    r.add_argument("--purpose", required=True)
    r.set_defaults(handler=cmd_request_submit)

    r = rsub.add_parser("cancel", help="取消本人待审批申请")
    r.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    r.add_argument("--request-id", dest="request_id", type=int, required=True)
    r.set_defaults(handler=cmd_request_cancel)

    r = rsub.add_parser("list", help="申请列表")
    r.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    r.add_argument(
        "--status", choices=("pending", "approved", "rejected", "cancelled")
    )
    r.add_argument("--all", action="store_true", help="查看全部（仅管理员）")
    r.set_defaults(handler=cmd_request_list)

    r = rsub.add_parser("show", help="申请详情")
    r.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    r.add_argument("--request-id", dest="request_id", type=int, required=True)
    r.set_defaults(handler=cmd_request_show)

    r = rsub.add_parser("approve", help="批准申请")
    r.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    r.add_argument("--request-id", dest="request_id", type=int, required=True)
    r.set_defaults(handler=cmd_request_approve)

    r = rsub.add_parser("reject", help="拒绝申请")
    r.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    r.add_argument("--request-id", dest="request_id", type=int, required=True)
    r.add_argument("--reason", required=True)
    r.set_defaults(handler=cmd_request_reject)

    p = sub.add_parser("waitlist", help="候补队列")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    wsub = p.add_subparsers(dest="waitlist_command", required=True)

    w = wsub.add_parser("join", help="登记候补")
    w.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    w.add_argument("--device", required=True)
    w.add_argument("--from", dest="from_", required=True)
    w.add_argument("--to", dest="to_", required=True)
    w.add_argument("--note")
    w.set_defaults(handler=cmd_waitlist_join)

    w = wsub.add_parser("list", help="候补名单")
    w.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    w.add_argument("--all", action="store_true", help="查看全部（仅管理员）")
    w.add_argument("--device")
    w.add_argument("--status", choices=("waiting", "cancelled"))
    w.set_defaults(handler=cmd_waitlist_list)

    p = sub.add_parser("loan", help="借出与归还")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    lsub = p.add_subparsers(dest="loan_command", required=True)

    l = lsub.add_parser("checkout", help="登记借出")
    l.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    l.add_argument("--request-id", dest="request_id", type=int, required=True)
    l.set_defaults(handler=cmd_loan_checkout)

    l = lsub.add_parser("return", help="登记归还")
    l.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    l.add_argument("--loan-id", dest="loan_id", type=int, required=True)
    l.set_defaults(handler=cmd_loan_return)

    p = sub.add_parser("stats", help="借用统计")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    ssub = p.add_subparsers(dest="stats_command", required=True)

    s = ssub.add_parser("usage", help="借用次数、逾期率与利用率")
    s.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    s.add_argument("--from", dest="from_", required=True)
    s.add_argument("--to", dest="to_", required=True)
    s.set_defaults(handler=cmd_stats_usage)

    s = ssub.add_parser("overdue", help="逾期清单")
    s.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    s.add_argument("--from", dest="from_")
    s.add_argument("--to", dest="to_")
    s.set_defaults(handler=cmd_stats_overdue)

    p = sub.add_parser("audit", help="审计日志")
    p.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    asub = p.add_subparsers(dest="audit_command", required=True)

    a = asub.add_parser("list", help="查询审计记录")
    a.add_argument("--db", dest="db", default=argparse.SUPPRESS)
    a.add_argument("--action")
    a.add_argument("--user")
    a.add_argument("--from", dest="from_")
    a.add_argument("--to", dest="to_")
    a.add_argument("--limit", type=int, default=50)
    a.set_defaults(handler=cmd_audit_list)

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
    except requests.TimeConflict as exc:
        emit({"error": "time_conflict", "conflicts": exc.conflicts})
        return 4
    except requests.RequestError as exc:
        fail(exc.code, exc.error, exc.message)
        return exc.code
    except loans.LoanError as exc:
        fail(exc.code, exc.error, exc.message)
        return exc.code
    except waitlist.WaitlistError as exc:
        fail(exc.code, exc.error, exc.message)
        return exc.code
    except sqlite3.Error as exc:
        fail(1, "db_error", str(exc))
        return 1
    emit(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())

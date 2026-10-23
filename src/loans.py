"""借出登记、归还登记与逾期判定。"""

import math
from datetime import datetime, timezone

import audit
from db import now_iso, transaction


class LoanError(Exception):
    def __init__(self, code, error, message):
        super().__init__(message)
        self.code = code
        self.error = error
        self.message = message


def parse_utc(text):
    value = text.strip()
    if value[-1:] in ("Z", "z"):
        value = value[:-1] + "+00:00"
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def overdue_days(returned_at, due_at):
    seconds = (parse_utc(returned_at) - parse_utc(due_at)).total_seconds()
    if seconds <= 0:
        return False, 0
    return True, max(1, math.ceil(seconds / 86400))


def get_loan(conn, loan_id):
    return conn.execute(
        "SELECT id, request_id, device_id, user_id, checked_out_at, due_at, returned_at"
        " FROM loans WHERE id = ?",
        (loan_id,),
    ).fetchone()


def checkout(conn, user, request_id):
    if user["role"] != "admin":
        raise LoanError(3, "forbidden", "仅管理员可登记借出")
    request = conn.execute(
        "SELECT id, device_id, user_id, end_at, status FROM requests WHERE id = ?",
        (request_id,),
    ).fetchone()
    if request is None:
        raise LoanError(1, "request_not_found", "申请不存在")
    if request["status"] != "approved":
        raise LoanError(1, "bad_status", "只能对已批准的申请登记借出")
    existing = conn.execute(
        "SELECT id FROM loans WHERE request_id = ?", (request_id,)
    ).fetchone()
    if existing is not None:
        raise LoanError(1, "already_checked_out", "该申请已登记借出，不能重复借出")
    device = conn.execute(
        "SELECT status FROM devices WHERE id = ?", (request["device_id"],)
    ).fetchone()
    if device is None or device["status"] != "available":
        raise LoanError(1, "device_unavailable", "设备当前不可借")
    checked_out_at = now_iso()
    with transaction(conn):
        cursor = conn.execute(
            "INSERT INTO loans (request_id, device_id, user_id, checked_out_at, due_at, returned_at, created_at)"
            " VALUES (?, ?, ?, ?, ?, NULL, ?)",
            (
                request_id,
                request["device_id"],
                request["user_id"],
                checked_out_at,
                request["end_at"],
                checked_out_at,
            ),
        )
        loan_id = cursor.lastrowid
        audit.log(
            conn,
            user,
            "loan_checkout",
            ("loan", loan_id),
            "ok",
            {"request_id": request_id, "due_at": request["end_at"]},
        )
    return {"loan_id": loan_id, "request_id": request_id, "due_at": request["end_at"]}


def return_loan(conn, user, loan_id):
    if user["role"] != "admin":
        raise LoanError(3, "forbidden", "仅管理员可登记归还")
    loan = get_loan(conn, loan_id)
    if loan is None:
        raise LoanError(1, "loan_not_found", "借出记录不存在")
    if loan["returned_at"] is not None:
        raise LoanError(1, "already_returned", "该借出记录已归还")
    returned_at = now_iso()
    overdue, days_late = overdue_days(returned_at, loan["due_at"])
    with transaction(conn):
        conn.execute(
            "UPDATE loans SET returned_at = ? WHERE id = ? AND returned_at IS NULL",
            (returned_at, loan_id),
        )
        audit.log(
            conn,
            user,
            "loan_return",
            ("loan", loan_id),
            "ok",
            {"returned_at": returned_at, "overdue": overdue},
        )
    return {
        "loan_id": loan_id,
        "returned_at": returned_at,
        "overdue": overdue,
        "days_late": days_late,
    }

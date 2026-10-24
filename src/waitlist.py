"""候补队列：登记与查询。"""

import audit
import requests
from db import now_iso, transaction

WAITLIST_FIELDS = (
    "SELECT id, device_id, user_id, start_at, end_at, status, created_at FROM waitlists"
)


class WaitlistError(Exception):
    def __init__(self, code, error, message):
        super().__init__(message)
        self.code = code
        self.error = error
        self.message = message


def join(conn, user, device_ref, start, end, note=None):
    if user["role"] != "student":
        raise WaitlistError(3, "forbidden", "仅学生可登记候补")
    device = requests.find_device(conn, device_ref)
    if device is None:
        raise WaitlistError(1, "device_not_found", "设备不存在")
    note = (note or "").strip()
    if len(note) > 200:
        raise WaitlistError(2, "bad_args", "备注不能超过 200 字符")
    duplicate = conn.execute(
        "SELECT id FROM waitlists WHERE user_id = ? AND device_id = ?"
        " AND status = 'waiting' AND start_at < ? AND end_at > ?",
        (user["id"], device["id"], end, start),
    ).fetchone()
    if duplicate is not None:
        raise WaitlistError(1, "duplicate_waitlist", "该设备该时段已有候补登记")
    conflicts = requests.find_conflicts(conn, device["id"], 0, start, end)
    available_now = device["status"] == "available" and not conflicts
    with transaction(conn):
        cursor = conn.execute(
            "INSERT INTO waitlists (device_id, user_id, start_at, end_at, status, note, created_at)"
            " VALUES (?, ?, ?, ?, 'waiting', ?, ?)",
            (device["id"], user["id"], start, end, note or None, now_iso()),
        )
        waitlist_id = cursor.lastrowid
        audit.log(
            conn,
            user,
            "waitlist_join",
            ("waitlist", waitlist_id),
            "ok",
            {"device_id": device["id"], "start_at": start, "end_at": end},
        )
    return {
        "waitlist_id": waitlist_id,
        "status": "waiting",
        "available_now": available_now,
    }


def list_waitlists(conn, user, show_all=False, device_ref=None, status=None):
    role = user["role"]
    if role == "director":
        raise WaitlistError(3, "forbidden", "主任无权查看候补名单")
    if show_all and role != "admin":
        raise WaitlistError(3, "forbidden", "--all 仅管理员可用")
    clauses = []
    params = []
    if role != "admin" or not show_all:
        clauses.append("user_id = ?")
        params.append(user["id"])
    if device_ref is not None:
        device = requests.find_device(conn, device_ref)
        if device is None:
            return []
        clauses.append("device_id = ?")
        params.append(device["id"])
    if status:
        clauses.append("status = ?")
        params.append(status)
    sql = WAITLIST_FIELDS
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "waitlist_id": row["id"],
            "device_id": row["device_id"],
            "user_id": row["user_id"],
            "start_at": row["start_at"],
            "end_at": row["end_at"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]

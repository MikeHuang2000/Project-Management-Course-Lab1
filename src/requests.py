"""借用申请：提交、取消、列表、详情、批准、拒绝与冲突判定。"""

import audit
from db import now_iso, transaction

REQUEST_FIELDS = (
    "SELECT r.id, r.device_id, r.user_id, r.purpose, r.start_at, r.end_at,"
    " r.status, r.reject_reason, r.decided_by, r.decided_at, r.created_at,"
    " d.code AS device_code, d.name AS device_name"
    " FROM requests r JOIN devices d ON d.id = r.device_id"
)

CONFLICT_SQL = (
    "SELECT request_id, min(start_at) AS start_at, max(end_at) AS end_at FROM ("
    " SELECT r.id AS request_id, r.start_at AS start_at, r.end_at AS end_at"
    " FROM requests r"
    " WHERE r.device_id = ? AND r.status = 'approved' AND r.id <> ?"
    " AND r.start_at < ? AND r.end_at > ?"
    " UNION"
    " SELECT l.request_id, l.checked_out_at, NULL FROM loans l"
    " WHERE l.device_id = ? AND l.returned_at IS NULL AND l.request_id <> ?"
    " AND l.checked_out_at < ?"
    ") GROUP BY request_id ORDER BY start_at"
)


class RequestError(Exception):
    def __init__(self, code, error, message):
        super().__init__(message)
        self.code = code
        self.error = error
        self.message = message


class TimeConflict(Exception):
    def __init__(self, conflicts):
        super().__init__("time_conflict")
        self.conflicts = conflicts


def find_device(conn, ref):
    text = str(ref).strip()
    row = conn.execute(
        "SELECT id, code, name, status FROM devices WHERE code = ?", (text,)
    ).fetchone()
    if row is None and text.isdigit():
        row = conn.execute(
            "SELECT id, code, name, status FROM devices WHERE id = ?", (int(text),)
        ).fetchone()
    return row


def get_request(conn, request_id):
    return conn.execute(REQUEST_FIELDS + " WHERE r.id = ?", (request_id,)).fetchone()


def find_conflicts(conn, device_id, request_id, start, end):
    rows = conn.execute(
        CONFLICT_SQL, (device_id, request_id, end, start, device_id, request_id, end)
    ).fetchall()
    return [
        {"request_id": row["request_id"], "start_at": row["start_at"], "end_at": row["end_at"]}
        for row in rows
    ]


def submit(conn, user, device_ref, start, end, purpose):
    if user["role"] != "student":
        raise RequestError(3, "forbidden", "仅学生可提交借用申请")
    device = find_device(conn, device_ref)
    if device is None:
        raise RequestError(1, "device_not_found", "设备不存在")
    if device["status"] != "available":
        raise RequestError(1, "device_unavailable", "设备当前不可借")
    duplicate = conn.execute(
        "SELECT id FROM requests WHERE user_id = ? AND device_id = ? AND status = 'pending'",
        (user["id"], device["id"]),
    ).fetchone()
    if duplicate is not None:
        raise RequestError(1, "duplicate_pending", "该设备已有待审批申请")
    with transaction(conn):
        cursor = conn.execute(
            "INSERT INTO requests (device_id, user_id, purpose, start_at, end_at, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (device["id"], user["id"], purpose, start, end, now_iso()),
        )
        request_id = cursor.lastrowid
        audit.log(
            conn,
            user,
            "request_submit",
            ("request", request_id),
            "ok",
            {"device_id": device["id"], "start_at": start, "end_at": end},
        )
    return {"request_id": request_id, "status": "pending"}


def cancel(conn, user, request_id):
    if user["role"] != "student":
        raise RequestError(3, "forbidden", "仅学生可取消申请")
    row = get_request(conn, request_id)
    if row is None:
        raise RequestError(1, "request_not_found", "申请不存在")
    if row["user_id"] != user["id"]:
        raise RequestError(1, "not_owner", "只能取消本人的申请")
    if row["status"] != "pending":
        raise RequestError(1, "bad_status", "只能取消待审批的申请")
    with transaction(conn):
        conn.execute(
            "UPDATE requests SET status = 'cancelled' WHERE id = ? AND status = 'pending'",
            (request_id,),
        )
        audit.log(conn, user, "request_cancel", ("request", request_id), "ok", None)
    return {"request_id": request_id, "status": "cancelled"}


def list_requests(conn, user, status=None, show_all=False):
    role = user["role"]
    if role == "director":
        raise RequestError(3, "forbidden", "主任无权查看申请列表")
    if show_all and role != "admin":
        raise RequestError(3, "forbidden", "--all 仅管理员可用")
    clauses = []
    params = []
    if role != "admin":
        clauses.append("r.user_id = ?")
        params.append(user["id"])
    if status:
        clauses.append("r.status = ?")
        params.append(status)
    sql = REQUEST_FIELDS
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY r.id"
    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "request_id": row["id"],
            "device_id": row["device_id"],
            "user_id": row["user_id"],
            "start_at": row["start_at"],
            "end_at": row["end_at"],
            "status": row["status"],
        }
        for row in rows
    ]


def show(conn, user, request_id):
    if user["role"] == "director":
        raise RequestError(3, "forbidden", "主任无权查看申请详情")
    row = get_request(conn, request_id)
    if row is None:
        raise RequestError(1, "request_not_found", "申请不存在")
    if user["role"] != "admin" and row["user_id"] != user["id"]:
        raise RequestError(1, "not_owner", "只能查看本人的申请")
    loan = conn.execute(
        "SELECT id, checked_out_at, due_at, returned_at FROM loans WHERE request_id = ?",
        (request_id,),
    ).fetchone()
    return {
        "request_id": row["id"],
        "device_id": row["device_id"],
        "device_code": row["device_code"],
        "device_name": row["device_name"],
        "user_id": row["user_id"],
        "purpose": row["purpose"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "status": row["status"],
        "reject_reason": row["reject_reason"],
        "decided_by": row["decided_by"],
        "decided_at": row["decided_at"],
        "created_at": row["created_at"],
        "loan": None
        if loan is None
        else {
            "loan_id": loan["id"],
            "checked_out_at": loan["checked_out_at"],
            "due_at": loan["due_at"],
            "returned_at": loan["returned_at"],
        },
    }


def approve(conn, user, request_id):
    if user["role"] != "admin":
        raise RequestError(3, "forbidden", "仅管理员可审批")
    row = get_request(conn, request_id)
    if row is None:
        raise RequestError(1, "request_not_found", "申请不存在")
    if row["status"] != "pending":
        raise RequestError(1, "bad_status", "只能审批待审批的申请")
    device = conn.execute(
        "SELECT status FROM devices WHERE id = ?", (row["device_id"],)
    ).fetchone()
    if device is None or device["status"] != "available":
        raise RequestError(1, "device_unavailable", "设备当前不可借")
    decided_at = now_iso()
    with transaction(conn):
        conn.execute(
            "UPDATE requests SET status = 'approved', decided_by = ?, decided_at = ?"
            " WHERE id = ? AND status = 'pending'",
            (user["id"], decided_at, request_id),
        )
        conflicts = find_conflicts(conn, row["device_id"], request_id, row["start_at"], row["end_at"])
        if conflicts:
            raise TimeConflict(conflicts)
        audit.log(conn, user, "request_approve", ("request", request_id), "ok", None)
    return {"request_id": request_id, "status": "approved", "decided_at": decided_at}


def reject(conn, user, request_id, reason):
    if user["role"] != "admin":
        raise RequestError(3, "forbidden", "仅管理员可审批")
    row = get_request(conn, request_id)
    if row is None:
        raise RequestError(1, "request_not_found", "申请不存在")
    if row["status"] != "pending":
        raise RequestError(1, "bad_status", "只能审批待审批的申请")
    with transaction(conn):
        conn.execute(
            "UPDATE requests SET status = 'rejected', reject_reason = ?, decided_by = ?, decided_at = ?"
            " WHERE id = ? AND status = 'pending'",
            (reason, user["id"], now_iso(), request_id),
        )
        audit.log(conn, user, "request_reject", ("request", request_id), "ok", {"reason": reason})
    return {"request_id": request_id, "status": "rejected", "reject_reason": reason}

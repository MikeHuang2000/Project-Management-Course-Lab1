"""设备目录：列表、按名称/类别检索与按时段判定可借。"""

from datetime import datetime, timezone

DEVICE_SELECT = "SELECT id, code, name, category, status FROM devices"


def normalize_iso(value):
    if value is None:
        return None
    text = value.strip()
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_devices(conn, category=None, status=None):
    clauses = []
    params = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if status:
        clauses.append("status = ?")
        params.append(status)
    sql = DEVICE_SELECT
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY code"
    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "id": row["id"],
            "code": row["code"],
            "name": row["name"],
            "category": row["category"],
            "status": row["status"],
        }
        for row in rows
    ]


def conflict_counts(conn, start, end):
    rows = conn.execute(
        "SELECT device_id, count(*) FROM ("
        " SELECT id AS request_id, device_id FROM requests"
        " WHERE status = 'approved' AND start_at < ? AND end_at > ?"
        " UNION"
        " SELECT request_id, device_id FROM loans"
        " WHERE returned_at IS NULL AND checked_out_at < ?"
        ") GROUP BY device_id",
        (end, start, end),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def search_devices(conn, name=None, category=None, start=None, end=None):
    clauses = []
    params = []
    if name:
        clauses.append("name LIKE ?")
        params.append("%" + name + "%")
    if category:
        clauses.append("category = ?")
        params.append(category)
    sql = DEVICE_SELECT
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY code"
    rows = conn.execute(sql, params).fetchall()
    counts = conflict_counts(conn, start, end) if start and end else {}
    items = []
    for row in rows:
        conflicts = counts.get(row["id"], 0)
        items.append(
            {
                "id": row["id"],
                "code": row["code"],
                "name": row["name"],
                "category": row["category"],
                "available": row["status"] == "available" and conflicts == 0,
                "conflicts": conflicts,
            }
        )
    return items

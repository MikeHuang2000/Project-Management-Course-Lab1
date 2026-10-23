"""借用统计：借用次数、逾期率、设备利用率与逾期清单（口径见契约 §6）。"""

import math
from datetime import datetime, timezone

from db import now_iso


def parse_utc(text):
    value = text.strip()
    if value[-1:] in ("Z", "z"):
        value = value[:-1] + "+00:00"
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def days_late(reference, due_at):
    seconds = (parse_utc(reference) - parse_utc(due_at)).total_seconds()
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 86400))


def overdue_rate(conn, start, end):
    row = conn.execute(
        "SELECT count(*), sum(CASE WHEN returned_at > due_at THEN 1 ELSE 0 END)"
        " FROM loans WHERE due_at >= ? AND due_at < ? AND returned_at IS NOT NULL",
        (start, end),
    ).fetchone()
    total = row[0] or 0
    if total == 0:
        return 0
    return round((row[1] or 0) / total, 4)


def usage(conn, start, end):
    start_dt = parse_utc(start)
    end_dt = parse_utc(end)
    span = (end_dt - start_dt).total_seconds()
    rows = conn.execute(
        "SELECT device_id, start_at, end_at FROM requests WHERE status = 'approved'"
    ).fetchall()
    borrowed = {}
    occupied = {}
    for row in rows:
        device_id = row["device_id"]
        req_start = parse_utc(row["start_at"])
        req_end = parse_utc(row["end_at"])
        if start_dt <= req_start < end_dt:
            borrowed[device_id] = borrowed.get(device_id, 0) + 1
        seconds = (min(req_end, end_dt) - max(req_start, start_dt)).total_seconds()
        if seconds > 0:
            occupied[device_id] = occupied.get(device_id, 0.0) + seconds
    items = []
    for row in conn.execute("SELECT id FROM devices ORDER BY id").fetchall():
        device_id = row["id"]
        raw = occupied.get(device_id, 0.0) / span
        items.append(
            {
                "device_id": device_id,
                "borrow_count": borrowed.get(device_id, 0),
                "utilization": round(min(raw, 1.0), 4),
                "overbooked": raw > 1.0,
            }
        )
    return {
        "range": {"from": start, "to": end},
        "overdue_rate": overdue_rate(conn, start, end),
        "devices": items,
    }


def overdue(conn, start=None, end=None, now=None):
    current = now or now_iso()
    rows = conn.execute(
        "SELECT id, request_id, device_id, due_at, returned_at FROM loans"
        " ORDER BY due_at, id"
    ).fetchall()
    items = []
    for row in rows:
        if start and row["due_at"] < start:
            continue
        if end and row["due_at"] >= end:
            continue
        returned_at = row["returned_at"]
        if returned_at is None:
            if current <= row["due_at"]:
                continue
            reference = current
        else:
            if returned_at <= row["due_at"]:
                continue
            reference = returned_at
        items.append(
            {
                "loan_id": row["id"],
                "request_id": row["request_id"],
                "device_id": row["device_id"],
                "due_at": row["due_at"],
                "returned_at": returned_at,
                "days_late": days_late(reference, row["due_at"]),
            }
        )
    return {"items": items}

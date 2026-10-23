"""审计日志写入与查询。"""

import json

from db import now_iso


def log(conn, actor, action, target, result, detail=None):
    actor_id = None
    actor_name = "system"
    if isinstance(actor, str):
        actor_name = actor
    elif actor is not None:
        actor_id = actor["id"]
        actor_name = actor["username"]
    target_type, target_id = target if target else (None, None)
    if isinstance(detail, (dict, list)):
        detail = json.dumps(detail, ensure_ascii=False)
    conn.execute(
        "INSERT INTO audit_log (at, actor_id, actor_name, action, target_type, target_id, detail, result)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (now_iso(), actor_id, actor_name, action, target_type, target_id, detail, result),
    )


def list_entries(conn, action=None, user=None, start=None, end=None, limit=50):
    clauses = []
    params = []
    if action:
        clauses.append("action = ?")
        params.append(action)
    if user:
        clauses.append("actor_name = ?")
        params.append(user)
    if start:
        clauses.append("at >= ?")
        params.append(start)
    if end:
        clauses.append("at < ?")
        params.append(end)
    sql = (
        "SELECT at, actor_name, action, target_type, target_id, result FROM audit_log"
    )
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY at DESC, id DESC LIMIT ?"
    params.append(limit)
    return [
        {
            "at": row["at"],
            "actor_name": row["actor_name"],
            "action": row["action"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "result": row["result"],
        }
        for row in conn.execute(sql, params).fetchall()
    ]

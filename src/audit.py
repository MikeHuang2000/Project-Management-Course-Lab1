"""审计日志写入（查询由 WP5 实现）。"""

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

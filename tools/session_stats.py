"""Collect per-session tool/token/timing stats from opencode's local DB (v2 schema).

Reads ~/.local/share/opencode/opencode.db read-only.
New schema: sessions live in `session_v2`, messages/parts are JSON rows in `session_message`.

Usage:
  python tools/session_stats.py                    # children of current session (by cwd)
  python tools/session_stats.py --session ses_xxx
  python tools/session_stats.py --children --json
  python tools/session_stats.py --details
"""

import argparse
import json
import os
import sqlite3
import sys

DEFAULT_DB = os.path.expanduser("~/.local/share/opencode/opencode.db")


def connect(path):
    return sqlite3.connect("file:" + path + "?mode=ro", uri=True)


def resolve_current(conn, cwd):
    row = conn.execute(
        "select id from session_v2 where parent_id is null and directory=? "
        "order by time_updated desc limit 1",
        (cwd.replace("\\", "/"),),
    ).fetchone()
    return row[0] if row else None


def session_row(conn, sid):
    cols = ("id", "parent_id", "agent", "title", "time_created", "time_updated",
            "tokens_input", "tokens_output", "tokens_reasoning",
            "tokens_cache_read", "tokens_cache_write", "cost")
    row = conn.execute("select %s from session_v2 where id=?" % ",".join(cols), (sid,)).fetchone()
    return dict(zip(cols, row)) if row else None


def scan_messages(conn, sid):
    tools, by_tool, model_ms, tool_ms, msgs = [], {}, 0, 0, 0
    for (data,) in conn.execute(
            "select data from session_message where session_id=? and type='assistant'", (sid,)):
        obj = json.loads(data)
        msgs += 1
        t = obj.get("time") or {}
        if t.get("completed") and t.get("created"):
            model_ms += t["completed"] - t["created"]
        for part in obj.get("content") or []:
            if part.get("type") != "tool":
                continue
            st = part.get("state") or {}
            meta = st.get("metadata") or {}
            exit_code = meta.get("exit")
            outcome = "failed" if (st.get("status") == "error"
                                   or (st.get("status") == "completed"
                                       and exit_code not in (None, 0))) else "ok"
            pt = part.get("time") or {}
            dur = (pt.get("completed") or 0) - (pt.get("ran") or pt.get("created") or 0)
            tool_ms += max(dur, 0)
            name = part.get("name", "?")
            tools.append({"name": name, "outcome": outcome, "exit": exit_code,
                          "ms": max(dur, 0)})
            agg = by_tool.setdefault(name, {"calls": 0, "failed": 0, "ms": 0})
            agg["calls"] += 1
            agg["ms"] += max(dur, 0)
            if outcome == "failed":
                agg["failed"] += 1
    return tools, by_tool, model_ms, tool_ms, msgs


def stats(conn, sid):
    s = session_row(conn, sid)
    if not s:
        return None
    tools, by_tool, model_ms, tool_ms, msgs = scan_messages(conn, sid)
    total = len(tools)
    failed = sum(1 for t in tools if t["outcome"] == "failed")
    return {
        "id": sid,
        "agent": s["agent"],
        "title": s["title"],
        "wall_ms": (s["time_updated"] or 0) - (s["time_created"] or 0),
        "model_ms": model_ms,
        "tool_ms": tool_ms,
        "assistant_messages": msgs,
        "tools_total": total,
        "tools_failed": failed,
        "fail_rate": round(failed / total, 4) if total else 0.0,
        "tokens": {
            "input": s["tokens_input"], "output": s["tokens_output"],
            "reasoning": s["tokens_reasoning"],
            "cache_read": s["tokens_cache_read"], "cache_write": s["tokens_cache_write"],
            "total": sum(s[k] for k in ("tokens_input", "tokens_output", "tokens_reasoning",
                                        "tokens_cache_read", "tokens_cache_write")),
        },
        "by_tool": by_tool,
        "tools": tools,
    }


def fmt_row(r):
    return ("%-38s %-12s %5d %5d %6.1f%% %8.1fs %8.1fs" % (
        r["id"], r["agent"], r["tools_total"], r["tools_failed"],
        100 * r["fail_rate"], r["wall_ms"] / 1000, r["tool_ms"] / 1000))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("OPENCODE_DB", DEFAULT_DB))
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--session")
    ap.add_argument("--task")
    ap.add_argument("--children", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--details", action="store_true")
    a = ap.parse_args()
    sid = a.task or a.session
    conn = connect(a.db)
    if not sid:
        sid = resolve_current(conn, a.cwd)
    if not sid:
        sys.exit("无法定位会话，请用 --session 指定")
    if a.children:
        kids = [r[0] for r in conn.execute(
            "select id from session_v2 where parent_id=? order by time_created", (sid,))]
        rows = [stats(conn, k) for k in kids]
        rows = [r for r in rows if r]
    else:
        r = stats(conn, sid)
        if not r:
            sys.exit("会话不存在: " + sid)
        rows = [r]
    if a.json:
        out = rows if (a.children or a.task or len(rows) > 1) else rows[0]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    print("%-38s %-12s %5s %5s %7s %9s %9s" % ("session", "agent", "calls", "fail", "rate", "wall", "tool"))
    for r in rows:
        print(fmt_row(r))
    if a.details:
        for r in rows:
            print("\n# %s  %s" % (r["id"], r["title"]))
            for name, v in sorted(r["by_tool"].items(), key=lambda kv: -kv[1]["calls"]):
                print("  %-10s calls=%3d fail=%2d avg=%.0fms" % (
                    name, v["calls"], v["failed"], v["ms"] / max(v["calls"], 1)))
            for t in r["tools"]:
                if t["outcome"] == "failed":
                    print("  FAILED %-10s exit=%s" % (t["name"], t["exit"]))


if __name__ == "__main__":
    main()

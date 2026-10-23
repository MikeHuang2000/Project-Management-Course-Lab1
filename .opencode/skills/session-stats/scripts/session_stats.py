#!/usr/bin/env python3
"""Report token usage, cost, timing and tool-call statistics for an opencode session.

The data comes from opencode's local SQLite database, opened read-only.
Subagents are stored as child sessions, so a Task tool `task_id` can be queried
directly with --task.

Examples:
    python session_stats.py
    python session_stats.py --session ses_abc123
    python session_stats.py --task ses_child123 --details
    python session_stats.py --children --json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_DATA_HOME = Path.home() / ".local" / "share"
TOKEN_KEYS = ("input", "output", "reasoning", "cache_read", "cache_write")


def _reconfigure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def default_db_path() -> Path:
    explicit = os.environ.get("OPENCODE_DB")
    if explicit:
        return Path(explicit).expanduser()
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home).expanduser() if data_home else DEFAULT_DATA_HOME
    return base / "opencode" / "opencode.db"


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise SystemExit(
            f"opencode database not found: {db_path}\n"
            "Pass --db PATH or set OPENCODE_DB."
        )
    uri = db_path.resolve().as_uri() + "?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=10.0)
    except sqlite3.Error as exc:
        raise SystemExit(f"cannot open database {db_path}: {exc}") from exc
    con.row_factory = sqlite3.Row
    return con


def normalize_dir(value: str | None) -> str:
    return (value or "").replace("\\", "/").rstrip("/").casefold()


def fetch_session(con: sqlite3.Connection, session_id: str) -> sqlite3.Row:
    row = con.execute("SELECT * FROM session WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise SystemExit(f"session not found: {session_id}")
    return row


def resolve_session(
    con: sqlite3.Connection,
    session_id: str | None,
    task_id: str | None,
    cwd: str | None,
) -> sqlite3.Row:
    if session_id and task_id:
        raise SystemExit("use either --session or --task, not both")
    if task_id:
        return fetch_session(con, task_id)
    if session_id:
        return fetch_session(con, session_id)

    target = normalize_dir(cwd or os.getcwd())
    candidates = con.execute(
        "SELECT * FROM session WHERE parent_id IS NULL ORDER BY time_updated DESC"
    ).fetchall()
    for row in candidates:
        if normalize_dir(row["directory"]) == target:
            return row
    if candidates:
        eprint(
            f"warning: no primary session for {cwd or os.getcwd()}; "
            f"falling back to most recent session {candidates[0]['id']}"
        )
        return candidates[0]
    raise SystemExit("no sessions found in the database")


def parse_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def model_label(raw: str | None) -> str:
    data = parse_json(raw)
    if not data:
        return "unknown"
    provider = data.get("providerID") or data.get("provider") or "?"
    model = data.get("id") or data.get("modelID") or "?"
    label = f"{provider}/{model}"
    variant = data.get("variant")
    if variant and variant not in ("default", ""):
        label += f" ({variant})"
    return label


def load_messages(con: sqlite3.Connection, session_id: str) -> list[dict]:
    rows = con.execute(
        "SELECT id, data, time_created, time_updated FROM message "
        "WHERE session_id = ? ORDER BY time_created",
        (session_id,),
    ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "data": parse_json(row["data"]),
                "time_created": row["time_created"],
                "time_updated": row["time_updated"],
            }
        )
    return result


def _short_error(state: dict, metadata: dict) -> str:
    error = state.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip().splitlines()[-1][:300]
    output = metadata.get("output") or state.get("output") or ""
    if isinstance(output, str):
        lines = [line for line in output.splitlines() if line.strip()]
        if lines:
            return lines[-1][:300]
    return ""


def load_tool_calls(con: sqlite3.Connection, session_id: str) -> list[dict]:
    try:
        rows = con.execute(
            "SELECT id, message_id, data, time_created FROM part "
            "WHERE session_id = ? AND json_extract(data, '$.type') = 'tool' "
            "ORDER BY time_created",
            (session_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = con.execute(
            "SELECT id, message_id, data, time_created FROM part "
            "WHERE session_id = ? ORDER BY time_created",
            (session_id,),
        ).fetchall()
    calls = []
    for row in rows:
        data = parse_json(row["data"])
        if data.get("type") != "tool":
            continue
        state = data.get("state") or {}
        metadata = state.get("metadata") or {}
        status = state.get("status") or "unknown"

        exit_code = metadata.get("exit")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            exit_code = None

        timing = state.get("time") or {}
        start = timing.get("start")
        end = timing.get("end")
        start = start if isinstance(start, int) else None
        end = end if isinstance(end, int) else None
        duration = end - start if start is not None and end is not None and end >= start else None

        failed = status == "error" or (
            status == "completed" and exit_code is not None and exit_code != 0
        )
        if status == "running":
            outcome = "running"
        elif status == "pending":
            outcome = "pending"
        elif failed:
            outcome = "failed"
        elif status == "completed":
            outcome = "ok"
        else:
            outcome = "unknown"

        calls.append(
            {
                "part_id": row["id"],
                "message_id": row["message_id"],
                "tool": data.get("tool") or "?",
                "call_id": data.get("callID") or "",
                "status": status,
                "outcome": outcome,
                "failed": failed,
                "exit_code": exit_code,
                "duration_ms": duration,
                "start": start,
                "end": end,
                "title": (state.get("title") or "").strip(),
                "error": _short_error(state, metadata) if failed else "",
            }
        )
    return calls


def token_totals_from_messages(messages: list[dict]) -> dict:
    totals = {key: 0 for key in TOKEN_KEYS}
    cost = 0.0
    for message in messages:
        data = message["data"]
        if data.get("role") != "assistant":
            continue
        tokens = data.get("tokens") or {}
        cache = tokens.get("cache") or {}
        totals["input"] += int(tokens.get("input") or 0)
        totals["output"] += int(tokens.get("output") or 0)
        totals["reasoning"] += int(tokens.get("reasoning") or 0)
        totals["cache_read"] += int(cache.get("read") or 0)
        totals["cache_write"] += int(cache.get("write") or 0)
        try:
            cost += float(data.get("cost") or 0)
        except (TypeError, ValueError):
            pass
    return {"tokens": totals, "cost": cost}


def summarize(
    session: sqlite3.Row,
    messages: list[dict],
    calls: list[dict],
    children: list[dict] | None = None,
    include_calls: bool = False,
) -> dict:
    session_id = session["id"]
    created = int(session["time_created"] or 0)
    updated = int(session["time_updated"] or created)

    tokens = {
        key: int(session[f"tokens_{key}"] or 0) for key in TOKEN_KEYS
    }
    tokens["total"] = sum(tokens.values())
    cost = float(session["cost"] or 0.0)
    token_source = "session"
    message_totals = token_totals_from_messages(messages)
    if tokens["total"] == 0 and sum(message_totals["tokens"].values()) > 0:
        tokens = message_totals["tokens"]
        tokens["total"] = sum(tokens.values())
        cost = message_totals["cost"]
        token_source = "messages"

    user_messages = 0
    assistant_messages = 0
    incomplete_assistant = 0
    model_ms = 0
    first_activity = created
    last_activity = updated

    for message in messages:
        data = message["data"]
        role = data.get("role")
        if role == "user":
            user_messages += 1
        elif role == "assistant":
            assistant_messages += 1

        timing = data.get("time") or {}
        started = timing.get("created")
        completed = timing.get("completed")
        if isinstance(started, int):
            first_activity = min(first_activity, started)
            last_activity = max(last_activity, started)
        if isinstance(completed, int):
            last_activity = max(last_activity, completed)
        if role == "assistant" and isinstance(started, int):
            if isinstance(completed, int) and completed >= started:
                model_ms += completed - started
            else:
                incomplete_assistant += 1

    for call in calls:
        if call["end"] is not None:
            last_activity = max(last_activity, call["end"])
        elif call["start"] is not None:
            last_activity = max(last_activity, call["start"])

    wall_ms = max(0, last_activity - first_activity)
    tool_ms = sum(c["duration_ms"] for c in calls if c["duration_ms"] is not None)
    timed_calls = sum(1 for c in calls if c["duration_ms"] is not None)

    by_tool: dict[str, dict] = defaultdict(
        lambda: {
            "calls": 0,
            "ok": 0,
            "failed": 0,
            "running": 0,
            "pending": 0,
            "unknown": 0,
            "duration_ms": 0,
            "timed_calls": 0,
        }
    )
    for call in calls:
        group = by_tool[call["tool"]]
        group["calls"] += 1
        group[call["outcome"]] = group.get(call["outcome"], 0) + 1
        if call["duration_ms"] is not None:
            group["duration_ms"] += call["duration_ms"]
            group["timed_calls"] += 1

    tool_rows = []
    for name in sorted(by_tool, key=lambda item: (-by_tool[item]["calls"], item)):
        group = by_tool[name]
        avg = (
            group["duration_ms"] / group["timed_calls"]
            if group["timed_calls"]
            else None
        )
        tool_rows.append(
            {
                "tool": name,
                "calls": group["calls"],
                "ok": group.get("ok", 0),
                "failed": group.get("failed", 0),
                "running": group.get("running", 0),
                "pending": group.get("pending", 0),
                "unknown": group.get("unknown", 0),
                "duration_ms": group["duration_ms"],
                "avg_ms": avg,
            }
        )

    outcomes = {
        "ok": sum(1 for c in calls if c["outcome"] == "ok"),
        "failed": sum(1 for c in calls if c["outcome"] == "failed"),
        "running": sum(1 for c in calls if c["outcome"] == "running"),
        "pending": sum(1 for c in calls if c["outcome"] == "pending"),
        "unknown": sum(1 for c in calls if c["outcome"] == "unknown"),
    }

    report = {
        "session": {
            "id": session_id,
            "parent_id": session["parent_id"],
            "title": session["title"],
            "agent": session["agent"] or "unknown",
            "model": model_label(session["model"]),
            "directory": (session["directory"] or "").replace("\\", "/"),
            "created_at_ms": created,
            "last_activity_ms": last_activity,
        },
        "tokens": {
            **tokens,
            "cost": round(cost, 8),
            "source": token_source,
        },
        "messages": {
            "total": len(messages),
            "user": user_messages,
            "assistant": assistant_messages,
            "assistant_incomplete": incomplete_assistant,
        },
        "timing": {
            "wall_ms": wall_ms,
            "model_ms": model_ms,
            "tool_ms": tool_ms,
            "timed_tool_calls": timed_calls,
        },
        "tools": {
            "total": len(calls),
            **outcomes,
            "by_tool": tool_rows,
        },
        "failures": [
            {
                "tool": c["tool"],
                "call_id": c["call_id"],
                "status": c["status"],
                "exit_code": c["exit_code"],
                "duration_ms": c["duration_ms"],
                "title": c["title"][:160],
                "error": c["error"],
            }
            for c in calls
            if c["failed"]
        ],
    }
    if include_calls:
        report["calls"] = [
            {
                "tool": c["tool"],
                "call_id": c["call_id"],
                "outcome": c["outcome"],
                "status": c["status"],
                "exit_code": c["exit_code"],
                "duration_ms": c["duration_ms"],
                "start_ms": c["start"],
                "title": c["title"][:160],
                "error": c["error"],
            }
            for c in calls
        ]
    if children is not None:
        report["children"] = children
    return report


def summarize_child(con: sqlite3.Connection, row: sqlite3.Row) -> dict:
    calls = load_tool_calls(con, row["id"])
    tokens = {key: int(row[f"tokens_{key}"] or 0) for key in TOKEN_KEYS}
    total = sum(tokens.values())
    return {
        "id": row["id"],
        "agent": row["agent"] or "unknown",
        "model": model_label(row["model"]),
        "title": row["title"],
        "tokens_total": total,
        "cost": round(float(row["cost"] or 0.0), 8),
        "wall_ms": max(0, int(row["time_updated"] or 0) - int(row["time_created"] or 0)),
        "tools_total": len(calls),
        "tools_failed": sum(1 for c in calls if c["failed"]),
    }


def fmt_int(value: int | float | None) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}"


def fmt_ms(ms: int | float | None) -> str:
    if ms is None:
        return "-"
    ms = int(ms)
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000.0
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, seconds = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def fmt_ts(ms: int | float | None) -> str:
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def print_report(report: dict) -> None:
    session = report["session"]
    tokens = report["tokens"]
    messages = report["messages"]
    timing = report["timing"]
    tools = report["tools"]

    role = "subagent" if session["parent_id"] else "primary"
    print(f"Session {session['id']}  [{role}]")
    if session["parent_id"]:
        print(f"  parent: {session['parent_id']}")
    print(f"  title:  {session['title']}")
    print(f"  agent:  {session['agent']}    model: {session['model']}")
    print(f"  dir:    {session['directory']}")
    print(
        f"  start:  {fmt_ts(session['created_at_ms'])}"
        f"    last activity: {fmt_ts(session['last_activity_ms'])}"
    )

    print()
    print("Tokens")
    print(
        f"  input {fmt_int(tokens['input'])}   "
        f"output {fmt_int(tokens['output'])}   "
        f"reasoning {fmt_int(tokens['reasoning'])}"
    )
    print(
        f"  cache read {fmt_int(tokens['cache_read'])}   "
        f"cache write {fmt_int(tokens['cache_write'])}"
    )
    source = " (from assistant messages)" if tokens["source"] == "messages" else ""
    print(
        f"  total {fmt_int(tokens['total'])}   "
        f"cost ${tokens['cost']:.6f}{source}"
    )
    print(
        f"  messages {fmt_int(messages['total'])}"
        f" (user {fmt_int(messages['user'])}, assistant {fmt_int(messages['assistant'])})"
    )

    print()
    print("Timing")
    print(f"  wall clock:  {fmt_ms(timing['wall_ms'])}  (session start -> last activity)")
    model_note = (
        f"; {messages['assistant_incomplete']} assistant turn still in progress"
        if messages["assistant_incomplete"]
        else ""
    )
    print(f"  model time:  {fmt_ms(timing['model_ms'])}  (sum of completed assistant turns{model_note})")
    print(
        f"  tool time:   {fmt_ms(timing['tool_ms'])}  "
        f"({timing['timed_tool_calls']}/{tools['total']} calls have timing)"
    )

    print()
    print("Tools")
    print(
        f"  total {tools['total']}   ok {tools['ok']}   failed {tools['failed']}   "
        f"running {tools['running']}   pending {tools['pending']}"
        + (f"   unknown {tools['unknown']}" if tools["unknown"] else "")
    )
    if tools["by_tool"]:
        header = f"  {'tool':<22}{'calls':>6}{'ok':>6}{'failed':>8}{'running':>9}{'total':>10}{'avg':>9}"
        print(header)
        for row in tools["by_tool"]:
            name = row["tool"][:22]
            print(
                f"  {name:<22}{row['calls']:>6}{row['ok']:>6}{row['failed']:>8}"
                f"{row['running']:>9}{fmt_ms(row['duration_ms']):>10}{fmt_ms(row['avg_ms']):>9}"
            )

    print()
    print("Failures")
    if not report["failures"]:
        print("  none")
    else:
        for failure in report["failures"]:
            exit_note = f" exit={failure['exit_code']}" if failure["exit_code"] is not None else ""
            detail = failure["error"] or failure["title"] or failure["status"]
            print(
                f"  - {failure['tool']} ({failure['call_id'] or '-'})"
                f"{exit_note} {fmt_ms(failure['duration_ms'])}: {detail[:160]}"
            )

    if "calls" in report:
        print()
        print("All tool calls")
        for call in report["calls"]:
            exit_note = f" exit={call['exit_code']}" if call["exit_code"] is not None else ""
            detail = call["error"] or call["title"]
            print(
                f"  [{call['outcome']:<7}] {call['tool']:<14} {fmt_ms(call['duration_ms']):>8}"
                f"  {call['call_id'] or '-'}{exit_note}  {detail[:100]}"
            )

    if "children" in report:
        print()
        print("Subagent sessions (children)")
        if not report["children"]:
            print("  none")
        else:
            print(
                f"  {'session':<34}{'agent':<10}{'tokens':>10}{'failed':>8}{'wall':>9}"
            )
            for child in report["children"]:
                print(
                    f"  {child['id']:<34}{child['agent'][:10]:<10}"
                    f"{fmt_int(child['tokens_total']):>10}{child['tools_failed']:>8}"
                    f"{fmt_ms(child['wall_ms']):>9}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Token, cost, timing and tool-call statistics for an opencode session or subagent."
    )
    parser.add_argument("--session", help="session id to inspect")
    parser.add_argument("--task", help="subagent task_id (child session id) to inspect")
    parser.add_argument("--db", help="path to opencode.db (default: ~/.local/share/opencode/opencode.db)")
    parser.add_argument("--cwd", help="project directory used to resolve the current session")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--details", action="store_true", help="include every tool call")
    parser.add_argument("--children", action="store_true", help="include direct subagent child sessions")
    args = parser.parse_args()

    con = connect(Path(args.db).expanduser() if args.db else default_db_path())
    try:
        session = resolve_session(con, args.session, args.task, args.cwd)
        messages = load_messages(con, session["id"])
        calls = load_tool_calls(con, session["id"])
        children = None
        if args.children:
            child_rows = con.execute(
                "SELECT * FROM session WHERE parent_id = ? ORDER BY time_created",
                (session["id"],),
            ).fetchall()
            children = [summarize_child(con, row) for row in child_rows]
        report = summarize(
            session,
            messages,
            calls,
            children=children,
            include_calls=args.details,
        )
    finally:
        con.close()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    _reconfigure_stdio()
    sys.exit(main())

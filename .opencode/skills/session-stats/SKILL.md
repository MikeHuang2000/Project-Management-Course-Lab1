---
name: session-stats
description: Use when the user asks for a session's or a subagent's token usage, cost, elapsed time, tool-call counts, or success/failure breakdown (查询本会话/子代理的 Token 消耗、耗时、工具调用次数、失败次数、子会话列表). Reads opencode's local SQLite database in read-only mode via a bundled Python script.
---

# Session & Subagent Stats

Report token usage, cost, timing, and tool-call statistics for the **current
session** or for a **subagent** (identified by its `task_id`), straight from
opencode's local SQLite database.

## When to use

- "这个会话用了多少 token / 花了多少时间 / 调用了哪些工具"
- "有多少次工具调用失败了"
- "某个子代理（task_id = ses_...）消耗了多少 token / 调用了多少次工具"
- "这个会话开了哪些子代理"

## Data source

- Database: `~/.local/share/opencode/opencode.db` (override with `--db` or the
  `OPENCODE_DB` env var).
- Opened **read-only** (`file:...?mode=ro`); the skill never writes to the DB
  and never modifies the project.
- Tokens/cost come from the `session` row (per-session aggregate). If that is
  all zeros, the script falls back to summing assistant-message token data.
- Subagents are stored as **child sessions**: `session.parent_id` points at the
  parent. The `task` tool's returned `task_id` **is** the child session id.

## Usage

Run from the project root. Python 3.8+ (stdlib only).

```bash
# Current session (resolved by matching the working directory)
python .opencode/skills/session-stats/scripts/session_stats.py

# Explicit session, or a subagent by task_id
python .opencode/skills/session-stats/scripts/session_stats.py --session ses_abc123
python .opencode/skills/session-stats/scripts/session_stats.py --task ses_child123

# Extra views
python .opencode/skills/session-stats/scripts/session_stats.py --details     # every tool call
python .opencode/skills/session-stats/scripts/session_stats.py --children    # direct subagents
python .opencode/skills/session-stats/scripts/session_stats.py --json        # machine-readable
python .opencode/skills/session-stats/scripts/session_stats.py --cwd D:/path/to/project
```

Flags: `--session`, `--task`, `--db`, `--cwd`, `--json`, `--details`,
`--children` (`--session` and `--task` are mutually exclusive).

## What the output means

**Tokens** - `input`, `output`, `reasoning`, `cache_read`, `cache_write`.
`total` is the sum of all five (matching opencode's own `tokens.total`).
`source` notes whether numbers came from the session row or message fallback.

**Timing** (all millisecond-based)

- `wall clock`: session start -> last activity (includes user think time).
- `model time`: sum of `completed - created` across finished assistant turns;
  the in-progress turn is reported separately and excluded.
- `tool time`: sum of tool `state.time.end - state.time.start` for calls that
  have timing (running calls have no end yet).

**Tools** - `total`, plus `ok` / `failed` / `running` / `pending` and a
per-tool breakdown (calls, ok, failed, running, total time, average).

Success/failure classification:

| Condition                                             | Outcome  |
| ----------------------------------------------------- | -------- |
| `state.status == "error"`                             | failed   |
| `state.status == "completed"` and `metadata.exit != 0`| failed   |
| `state.status == "completed"` (exit 0 or no exit)     | ok       |
| `state.status == "running"` / `"pending"`             | in progress |

So a shell command that ran but exited non-zero counts as a failure, with its
`exit_code` shown. Failures list includes tool, `call_id`, exit code, duration,
and a one-line error excerpt.

**Children** (`--children`) - direct subagent sessions with id, agent, model,
total tokens, cost, wall time, and tool failure count.

## Caveats

- **Self-inclusive**: when the current session is queried, the script's own
  `bash` call is part of that session, so it appears in the counts (often as
  `running`). Subtract one if you want the caller's view.
- Current-session resolution picks the most recently updated **primary**
  session whose `directory` matches the cwd. If it picks the wrong one, pass
  `--session ses_...` (or `--cwd`).
- Subagent sessions record their own `agent` and `model`; older rows may have
  them empty and will print `unknown`.
- Adding or editing this skill requires **restarting opencode** for the skill
  to be loaded.

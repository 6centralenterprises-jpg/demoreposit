#!/usr/bin/env python3
"""Task dispatcher: every couple of seconds, hand each idle agent its next task.

Agents are the subfolders of agents/. Each runs at most one task at a time.
A task is claimed (set to in_progress) BEFORE its agent is started, so a task
can never be fired twice. Agents report back through the Mission Control API
(POST /tasks/<id>/complete); if an agent exits without doing that, the task is
marked failed or blocked so it never stays claimed forever.
"""
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("ECOSYSTEM_HOME") or Path(__file__).resolve().parent.parent)
DB_PATH = HOME / "tasks" / "queue.db"
LIMITS_PATH = HOME / "tasks" / "limits.json"
SCHEMA_PATH = HOME / "schema.sql"
AGENTS_DIR = HOME / "agents"
OPENCLAW = os.environ.get("OPENCLAW_BIN") or shutil.which("openclaw") or "openclaw"
POLL_SECONDS = float(os.environ.get("DISPATCH_INTERVAL", "2"))
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "600"))
# Hard kill a little after openclaw's own --timeout, in case it hangs.
KILL_AFTER = AGENT_TIMEOUT + 60
OUTPUT_KEEP = 4000  # characters of agent output saved on the task

running = {}  # agent name -> {"proc", "task_id", "started", "log"}
stopping = False


def log(msg):
    print(f"{datetime.now().isoformat(timespec='seconds')} {msg}", flush=True)


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    # Own the schema too, so boot order with the API never matters.
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def event(conn, task_id, name, msg=None, meta=None):
    conn.execute(
        "INSERT INTO events (task_id, event, msg, meta) VALUES (?, ?, ?, ?)",
        (task_id, name, msg, json.dumps(meta) if meta is not None else None),
    )


def recover(conn):
    """Crash recovery: anything left in_progress by a dead run goes back to pending."""
    rows = conn.execute("SELECT id FROM tasks WHERE status = 'in_progress'").fetchall()
    for row in rows:
        conn.execute("UPDATE tasks SET status = 'pending', started_at = NULL WHERE id = ?", (row["id"],))
        event(conn, row["id"], "recovered", "reset to pending after dispatcher restart")
    if rows:
        log(f"recovered {len(rows)} stuck task(s) back to pending")


def known_agents():
    if not AGENTS_DIR.is_dir():
        return []
    return sorted(
        p.name for p in AGENTS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".") and not (p / "PAUSED").exists()
    )


def spend_cap_reached(conn):
    try:
        cap = float(json.loads(LIMITS_PATH.read_text())["daily_total_spend_cap"])
    except (OSError, ValueError, KeyError):
        return False
    spent = conn.execute(
        "SELECT COALESCE(SUM(cost_actual), 0) FROM tasks WHERE date(completed_at) = date('now')"
    ).fetchone()[0]
    return spent >= cap


def claim(conn, agent):
    """Atomically flip this agent's next task to in_progress. Returns its id or None."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        busy = conn.execute(
            "SELECT 1 FROM tasks WHERE assignee = ? AND status = 'in_progress' LIMIT 1", (agent,)
        ).fetchone()
        row = None if busy else conn.execute(
            """SELECT id FROM tasks WHERE assignee = ? AND status IN ('pending', 'assigned')
               ORDER BY priority DESC, id ASC LIMIT 1""",
            (agent,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', started_at = datetime('now') WHERE id = ?",
                (row["id"],),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return row["id"] if row else None


def fire(conn, agent, task_id):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    cmd = [
        OPENCLAW, "agent", "--agent", agent,
        "--message", f"task #{task_id} assigned, see /tasks/{task_id}",
        "--session-id", f"task-{task_id}-{stamp}",  # fresh session per task, never reused
        "--timeout", str(AGENT_TIMEOUT), "--json",
    ]
    log_dir = AGENTS_DIR / agent / "reports"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / f"task-{task_id}.log", "w+")
    kwargs = {"stdout": log_file, "stderr": subprocess.STDOUT, "cwd": str(AGENTS_DIR / agent)}
    if os.name == "nt":  # never flash a console window on Windows
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = 0
        kwargs.update(creationflags=0x08000000, startupinfo=info)
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as err:
        log_file.close()
        finish(conn, task_id, "failed", f"could not start openclaw: {err}")
        log(f"task #{task_id} ({agent}) failed to start: {err}")
        return
    running[agent] = {"proc": proc, "task_id": task_id, "started": time.monotonic(), "log": log_file}
    event(conn, task_id, "fired", agent, {"session": cmd[7]})
    log(f"fired task #{task_id} -> {agent}")


def finish(conn, task_id, status, note, output=None):
    """Close a task the agent left open. Never overwrites a result the agent reported."""
    conn.execute(
        """UPDATE tasks SET status = ?, completed_at = datetime('now'),
               notes = COALESCE(notes || char(10), '') || ?,
               result = COALESCE(result, ?)
           WHERE id = ? AND status = 'in_progress'""",
        (status, note, output, task_id),
    )
    event(conn, task_id, status, note)


def reap(conn):
    for agent, run in list(running.items()):
        proc, task_id = run["proc"], run["task_id"]
        code = proc.poll()
        if code is None and time.monotonic() - run["started"] > KILL_AFTER:
            proc.kill()
            code = proc.wait()
            note = f"killed after {KILL_AFTER}s"
        elif code is None:
            continue
        else:
            note = f"openclaw exited with code {code}"
        run["log"].seek(0)
        output = run["log"].read()[-OUTPUT_KEEP:]
        run["log"].close()
        del running[agent]
        status = conn.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if status and status["status"] == "in_progress":
            # The agent did not report back through the API. Exit 0 means it ran but
            # left no verdict, so a person should look (blocked); anything else failed.
            finish(conn, task_id, "blocked" if code == 0 else "failed",
                   note + ("; agent did not report a result" if code == 0 else ""), output)
        else:
            event(conn, task_id, "agent_exited", note)
        log(f"task #{task_id} ({agent}) finished: {note}")


def handle_stop(signum, frame):
    global stopping
    stopping = True


def main():
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    conn = connect()
    recover(conn)
    log(f"dispatcher up: home={HOME} openclaw={OPENCLAW} every {POLL_SECONDS}s")
    cap_logged = False
    while not stopping:
        try:
            reap(conn)
            if spend_cap_reached(conn):
                if not cap_logged:
                    log("daily spend cap reached; no new tasks start until tomorrow (UTC)")
                    event(conn, None, "spend_cap_reached")
                    cap_logged = True
            else:
                cap_logged = False
                for agent in known_agents():
                    if agent in running:
                        continue
                    task_id = claim(conn, agent)
                    if task_id is not None:
                        fire(conn, agent, task_id)
        except sqlite3.OperationalError as err:  # e.g. a brief lock; try again next tick
            log(f"database busy, retrying: {err}")
        time.sleep(POLL_SECONDS)
    log("stopping; any task still running goes back to pending on next start")
    return 0


if __name__ == "__main__":
    sys.exit(main())

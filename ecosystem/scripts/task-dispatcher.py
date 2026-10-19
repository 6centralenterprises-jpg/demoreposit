#!/usr/bin/env python3
"""Task dispatcher: fires agents for pending tasks in tasks/queue.db.

Every POLL_SECONDS it walks the agents (every subfolder of agents/) and, for
each agent with nothing running, claims its next task (flips it to
in_progress first), then runs:

  openclaw agent --agent <name> --message "task #<id> assigned, see /tasks/<id>"
    --session-id "task-<id>-<timestamp>" --timeout 600 --json

One task per agent at a time. A fresh session id per task, always.
Standard library only. Paths are relative to the ecosystem folder
(override with ECOSYSTEM_ROOT).
"""
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("ECOSYSTEM_ROOT") or Path(__file__).resolve().parent.parent)
AGENTS_DIR = ROOT / "agents"
DB_PATH = ROOT / "tasks" / "queue.db"
SCHEMA_PATH = ROOT / "tasks" / "schema.sql"
LOG_DIR = ROOT / "logs" / "tasks"
POLL_SECONDS = float(os.environ.get("DISPATCH_POLL_SECONDS", "2"))
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT_SECONDS", "600"))
# Hard kill a little after openclaw's own timeout, in case it hangs.
KILL_AFTER = AGENT_TIMEOUT + 60
OPENCLAW = os.environ.get("OPENCLAW_BIN", "openclaw")
CLAIMABLE = ("pending", "assigned")

running = {}  # agent name -> {"proc", "task_id", "started", "log"}
stopping = False


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    # Own the schema too, so boot order with the API never matters.
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def event(conn, task_id, name, msg=None, meta=None):
    conn.execute(
        "INSERT INTO events (task_id, event, msg, meta) VALUES (?, ?, ?, ?)",
        (task_id, name, msg, json.dumps(meta) if meta is not None else None),
    )


def recover_stuck(conn):
    """A task left in_progress at startup lost its agent; put it back in line."""
    rows = conn.execute("SELECT id FROM tasks WHERE status = 'in_progress'").fetchall()
    for r in rows:
        conn.execute("UPDATE tasks SET status = 'pending', started_at = NULL WHERE id = ?", (r["id"],))
        event(conn, r["id"], "recovered", "dispatcher restarted; reset in_progress to pending")
    if rows:
        log(f"recovered {len(rows)} stuck task(s): {[r['id'] for r in rows]}")


def known_agents():
    if not AGENTS_DIR.is_dir():
        return []
    return sorted(p.name for p in AGENTS_DIR.iterdir()
                  if p.is_dir() and not p.name.startswith((".", "_")))


def claim(conn, agent):
    """Atomically take the agent's next task. Returns the task id or None."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        busy = conn.execute(
            "SELECT 1 FROM tasks WHERE assignee = ? AND status = 'in_progress' LIMIT 1", (agent,)
        ).fetchone()
        row = None if busy else conn.execute(
            f"SELECT id FROM tasks WHERE assignee = ? AND status IN ({','.join('?' * len(CLAIMABLE))})"
            " ORDER BY priority DESC, id ASC LIMIT 1",
            (agent, *CLAIMABLE),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', started_at = datetime('now'),"
                " assigned_at = COALESCE(assigned_at, datetime('now')) WHERE id = ?",
                (row["id"],),
            )
            event(conn, row["id"], "claimed", f"dispatcher claimed for {agent}")
        conn.execute("COMMIT")
        return row["id"] if row else None
    except Exception:
        conn.execute("ROLLBACK")
        raise


def fire(conn, agent, task_id, openclaw_path):
    session = f"task-{task_id}-{int(time.time())}"
    cmd = [openclaw_path, "agent", "--agent", agent,
           "--message", f"task #{task_id} assigned, see /tasks/{task_id}",
           "--session-id", session, "--timeout", str(AGENT_TIMEOUT), "--json"]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{session}.log"
    kwargs = {}
    if os.name == "nt":
        # Never flash a console window on Windows.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        kwargs = {"creationflags": 0x08000000, "startupinfo": si}  # CREATE_NO_WINDOW
    out = open(log_path, "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                cwd=str(AGENTS_DIR / agent), **kwargs)
    except OSError as e:
        out.close()
        conn.execute("UPDATE tasks SET status = 'failed', completed_at = datetime('now'), notes = ? WHERE id = ?",
                     (f"could not start openclaw: {e}", task_id))
        event(conn, task_id, "failed", f"could not start openclaw: {e}")
        log(f"task #{task_id} ({agent}) failed to start: {e}")
        return
    running[agent] = {"proc": proc, "task_id": task_id, "started": time.time(), "log": log_path, "out": out}
    event(conn, task_id, "fired", f"openclaw agent {agent}", {"session_id": session, "log": str(log_path)})
    log(f"task #{task_id} -> {agent} (session {session})")


def reap(conn):
    """Check running agents; settle any task the agent left open."""
    for agent, run in list(running.items()):
        proc, task_id = run["proc"], run["task_id"]
        rc = proc.poll()
        if rc is None and time.time() - run["started"] > KILL_AFTER:
            proc.kill()
            rc = proc.wait()
            event(conn, task_id, "killed", f"no exit after {KILL_AFTER}s")
        if rc is None:
            continue
        run["out"].close()
        del running[agent]
        tail = run["log"].read_text(encoding="utf-8", errors="replace")[-4000:]
        row = conn.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row and row["status"] == "in_progress":
            # The agent didn't report back through the API; record the outcome for it.
            if rc == 0:
                conn.execute("UPDATE tasks SET status = 'done', completed_at = datetime('now'), result = ?,"
                             " notes = COALESCE(notes, 'completed by dispatcher on clean exit') WHERE id = ?",
                             (tail, task_id))
            else:
                conn.execute("UPDATE tasks SET status = 'failed', completed_at = datetime('now'), result = ?,"
                             " notes = ? WHERE id = ?", (tail, f"openclaw exited with code {rc}", task_id))
        event(conn, task_id, "exited", f"openclaw exit code {rc}", {"log": str(run["log"])})
        log(f"task #{task_id} ({agent}) finished, exit {rc}")


def handle_stop(signum, frame):
    global stopping
    stopping = True


def main():
    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)
    conn = connect()
    recover_stuck(conn)
    log(f"dispatcher up: root={ROOT}, polling every {POLL_SECONDS}s")
    last_warn = 0.0
    while not stopping:
        try:
            reap(conn)
            openclaw_path = shutil.which(OPENCLAW)
            agents = known_agents()
            if not openclaw_path:
                # Leave tasks pending rather than fail them while the runtime is missing.
                if agents and time.time() - last_warn > 60:
                    log(f"'{OPENCLAW}' not found on PATH; not dispatching (set OPENCLAW_BIN or finish Step 2)")
                    last_warn = time.time()
            else:
                for agent in agents:
                    if agent in running:
                        continue
                    task_id = claim(conn, agent)
                    if task_id:
                        fire(conn, agent, task_id, openclaw_path)
        except sqlite3.OperationalError as e:
            log(f"database busy, retrying: {e}")
        time.sleep(POLL_SECONDS)
    # Shutting down: let running agents finish on their own; the next start
    # resets their tasks to pending if they never reported back.
    log(f"dispatcher stopping ({len(running)} agent(s) still running)")
    conn.close()


if __name__ == "__main__":
    sys.exit(main())

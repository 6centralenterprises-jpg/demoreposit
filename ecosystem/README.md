# Agent Ecosystem Backbone

*A 6 Central Enterprises shared-services system*

The home base every AI agent plugs into: a SQLite task queue, a small API
that reads and writes it, and a dispatcher that fires OpenClaw agents for
queued tasks. It sits idle and costs nothing until a task arrives.

```
agents/                      one folder per agent (IDENTITY.md, PLAYBOOK.md, MEMORY.md, data/, reports/)
tasks/queue.db               the queue (created on first run, never committed)
tasks/schema.sql             the queue schema; both services apply it at startup
tasks/limits.json            spend caps
scripts/task-dispatcher.py   the daemon that fires agents (Python standard library only)
mission-control-api/         Express API on http://127.0.0.1:3001
ecosystem.config.js          pm2 config (Mac / Windows)
services/                    systemd units + installers for Linux, Mac and Windows
```

## Where to put it

Copy this `ecosystem/` folder to a plain local path **outside any
cloud-synced folder** (OneDrive, Dropbox, iCloud, Google Drive). Sync tools
grab the database mid-write and corrupt it.

| Machine | Path | Install |
|---|---|---|
| Linux / VPS | `/root/ecosystem` | `sudo bash services/install-linux.sh` (systemd) |
| Mac | `~/ecosystem` | `bash services/install-mac.sh` (pm2 + launchd) |
| Windows | `C:\Ecosystem` | `powershell -ExecutionPolicy Bypass -File services\windows\install-windows.ps1` (pm2 + logon task) |

Needs Node 18+, Python 3.9+ and `openclaw` on the PATH (Step 2). Nothing
hardcodes the path; set `ECOSYSTEM_ROOT` to override.

## How it works

- **A task** is a row in `tasks`. Create one with `POST /tasks` and set
  `assignee` to an agent's folder name.
- **The dispatcher** checks every 2 seconds. An agent is any subfolder of
  `agents/` (names starting with `.` or `_` are skipped). For each agent with
  nothing running, it takes the agent's next `pending` or `assigned` task
  (highest `priority`, then oldest), flips it to `in_progress`, and runs
  `openclaw agent --agent <name> --message "task #<id> assigned, see /tasks/<id>" --session-id task-<id>-<timestamp> --timeout 600 --json`.
  It runs one task per agent at a time, with a fresh session every time.
- **Agents report back** with `POST /tasks/:id/complete` (`{result, cost_actual}`)
  or `/reject` (`{reason}`). If an agent exits without reporting, the
  dispatcher marks the task `done` (exit 0) or `failed` (anything else)
  and saves the tail of the output. Each run's full output is in `logs/tasks/`.
- **Crash recovery:** on startup the dispatcher resets any `in_progress` task to
  `pending`. If `openclaw` is missing, tasks wait instead of failing.
- **Limits:** `POST /tasks` returns HTTP 429 when a task's `cost_estimate`
  is over `single_task_cost_max`, or when today's spend or task count would
  pass the daily caps. Today's spend counts each task's actual cost once
  known, otherwise its estimate. Days are UTC.
- **Dedupe:** a `dedupe_key` blocks a second *open* task with the same key
  (HTTP 409). Finished tasks never block a new one.

## API

| Method | Path | Does |
|---|---|---|
| GET | `/tasks?status=&assignee=&limit=` | List tasks, newest first |
| POST | `/tasks` | Create (enforces limits and dedupe) |
| GET | `/tasks/stats` | `{total, byStatus, today}` |
| GET / PATCH | `/tasks/limits` | Read / change caps |
| GET | `/tasks/:id` | One task with its event history |
| PATCH | `/tasks/:id` | Partial update |
| POST | `/tasks/:id/assign` · `/start` · `/complete` · `/reject` | Status changes with timestamps |

The API has no login, so it listens on `127.0.0.1` only. Don't expose port
3001 to the internet. Put an authenticated proxy in front if you ever need
remote access.

## Check it's healthy

```bash
curl http://localhost:3001/tasks/stats        # Windows: Invoke-RestMethod http://localhost:3001/tasks/stats
systemctl status task-dispatcher              # Mac/Windows: pm2 ls
```

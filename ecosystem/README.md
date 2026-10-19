# Agent Ecosystem Backbone

*A 6 Central Enterprises shared-services system*

This is the base layer that every agent plugs into. It costs nothing while idle.
An agent only runs, and only spends, when a task is waiting for it.

```
agents/                      one folder per agent (see agents/README.md)
tasks/queue.db               the SQLite task queue (created on first run)
tasks/limits.json            spend caps
schema.sql                   the queue schema (both services apply it on startup)
scripts/task-dispatcher.py   hands each idle agent its next task through OpenClaw
mission-control-api/         Express API on 127.0.0.1:3001 that reads and writes the queue
systemd/                     service files (filled in by install.sh)
install.sh                   installs or updates everything on a Linux VPS
```

## Install on the VPS

Do Step 2 first (Node 20+, Python 3, OpenClaw, gateway running). Then, inside tmux:

```bash
git clone https://github.com/6centralenterprises-jpg/demoreposit.git /root/demoreposit
cd /root/demoreposit && git checkout claude/elegant-newton-n5i6ps   # until this is merged
sudo bash ecosystem/install.sh
```

This puts the live system in `/root/ecosystem`, outside the git checkout. To update
later, run `git pull` and then `install.sh` again. Your queue, limits and agents are
never overwritten.

## Check it

```bash
systemctl status mission-control-api task-dispatcher
curl http://127.0.0.1:3001/tasks/stats        # JSON counts, not a 404
openclaw gateway status
journalctl -u task-dispatcher -f              # live dispatcher log (Ctrl+C to exit)
```

## How a task flows

1. Something creates a task: `POST /tasks` with `assignee`, `type`, `payload`, `cost_estimate`.
2. The dispatcher sees it within about 2 seconds. If that agent is idle, it marks the
   task `in_progress` and runs
   `openclaw agent --agent <name> --message "task #<id> assigned, see /tasks/<id>" --session-id task-<id>-<time> --timeout 600 --json`.
3. The agent reads `GET /tasks/<id>`, does the work, and calls `POST /tasks/<id>/complete`
   with `{result, cost_actual}`, or `POST /tasks/<id>/reject` with `{reason}`.
4. If the agent exits without reporting, the task becomes `blocked` (exit 0, so a person
   should look) or `failed` (error). It never stays claimed forever. The agent's output
   is saved on the task and in `agents/<name>/reports/task-<id>.log`.

## API

| Route | What it does |
|---|---|
| `GET /tasks?status=&assignee=` | List tasks (newest first) |
| `POST /tasks` | Create a task. Returns 429 if it breaks a limit, 409 if an open task has the same `dedupe_key` |
| `GET /tasks/stats` | `{total, byStatus, spendToday}` |
| `GET /tasks/limits`, `PATCH /tasks/limits` | Read or change the caps |
| `GET /tasks/:id`, `PATCH /tasks/:id` | Read or partly update one task |
| `POST /tasks/:id/assign` · `start` · `complete` · `reject` | Move a task along |
| `GET /events?task_id=` | The audit log |

## Safety rails

- **Spend caps** (`tasks/limits.json`): a task over `single_task_cost_max`, or one that
  would push today past `daily_total_spend_cap` or `daily_new_tasks_cap`, is refused.
  The dispatcher also stops starting tasks once today's actual spend reaches the daily cap.
  These caps only count what agents report. Also set a hard limit on your AI key at the
  provider (for example, OpenRouter's per-key credit limit).
- **One task per agent at a time**, and a fresh OpenClaw session for every task.
- **Crash recovery:** on restart, tasks left `in_progress` go back to `pending`.
- **Pause an agent:** create `agents/<name>/PAUSED`. Delete it to resume.
- **Private API:** it listens on 127.0.0.1 only and has no password, so do not open
  port 3001 to the internet. To view it from your own computer, use an SSH tunnel:
  `ssh -L 3001:127.0.0.1:3001 root@YOUR_SERVER_IP`, then open http://localhost:3001/tasks/stats.

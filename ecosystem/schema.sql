-- Task queue schema. The API and the dispatcher both run this on startup,
-- so either one can boot first.
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  created_by TEXT, assignee TEXT, type TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','assigned','in_progress','done','failed','rejected','cancelled','blocked')),
  payload TEXT, result TEXT,
  cost_estimate REAL DEFAULT 0, cost_actual REAL DEFAULT 0,
  priority INTEGER DEFAULT 0, parent_id INTEGER,
  dedupe_key TEXT, notes TEXT, kill_criteria TEXT,
  assigned_at TEXT, started_at TEXT, completed_at TEXT
);
-- Dedupe blocks duplicate OPEN tasks only. Status is deliberately not part of the
-- key: finishing a task drops it out of the index, so it can never collide.
CREATE UNIQUE INDEX IF NOT EXISTS ux_tasks_dedupe ON tasks(dedupe_key)
  WHERE dedupe_key IS NOT NULL AND status IN ('pending','assigned','in_progress');
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime('now')),
  task_id INTEGER, event TEXT, msg TEXT, meta TEXT
);

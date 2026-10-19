// Mission Control API: reads and writes the task queue (tasks/queue.db).
// Paths are relative to the ecosystem folder, so it runs from wherever that
// folder lives. Override with ECOSYSTEM_ROOT if needed.
const fs = require('fs');
const path = require('path');
const express = require('express');
const Database = require('better-sqlite3');

const ROOT = process.env.ECOSYSTEM_ROOT || path.resolve(__dirname, '..');
const TASKS_DIR = path.join(ROOT, 'tasks');
const DB_PATH = path.join(TASKS_DIR, 'queue.db');
const LIMITS_PATH = path.join(TASKS_DIR, 'limits.json');
const PORT = Number(process.env.PORT || 3001);
// Local only by default: this API has no login, so it must not face the internet.
const HOST = process.env.HOST || '127.0.0.1';

const STATUSES = ['pending', 'assigned', 'in_progress', 'done', 'failed', 'rejected', 'cancelled', 'blocked'];
const EDITABLE = ['created_by', 'assignee', 'type', 'status', 'payload', 'result', 'cost_estimate',
  'cost_actual', 'priority', 'parent_id', 'dedupe_key', 'notes', 'kill_criteria',
  'assigned_at', 'started_at', 'completed_at'];
const DEFAULT_LIMITS = { single_task_cost_max: 5.0, daily_total_spend_cap: 10.0, daily_new_tasks_cap: 50 };

fs.mkdirSync(TASKS_DIR, { recursive: true });
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('busy_timeout = 5000');
db.exec(fs.readFileSync(path.join(TASKS_DIR, 'schema.sql'), 'utf8'));

function readLimits() {
  try {
    return { ...DEFAULT_LIMITS, ...JSON.parse(fs.readFileSync(LIMITS_PATH, 'utf8')) };
  } catch {
    return { ...DEFAULT_LIMITS };
  }
}

// Payload and result are stored as text; objects are saved as JSON.
function asText(v) {
  if (v === undefined || v === null) return v;
  return typeof v === 'string' ? v : JSON.stringify(v);
}

function logEvent(taskId, event, msg, meta) {
  db.prepare('INSERT INTO events (task_id, event, msg, meta) VALUES (?, ?, ?, ?)')
    .run(taskId, event, msg ?? null, asText(meta) ?? null);
}

const getTask = (id) => db.prepare('SELECT * FROM tasks WHERE id = ?').get(id);

const app = express();
app.use(express.json({ limit: '2mb' }));

// Literal routes first: /tasks/:id would otherwise swallow "stats" and "limits".
app.get('/tasks/stats', (req, res) => {
  const rows = db.prepare('SELECT status, COUNT(*) AS n FROM tasks GROUP BY status').all();
  const byStatus = Object.fromEntries(STATUSES.map((s) => [s, 0]));
  let total = 0;
  for (const r of rows) { byStatus[r.status] = r.n; total += r.n; }
  const today = db.prepare(`SELECT COUNT(*) AS created, COALESCE(SUM(cost_actual), 0) AS spent
    FROM tasks WHERE date(created_at) = date('now')`).get();
  res.json({ total, byStatus, today });
});

app.get('/tasks/limits', (req, res) => res.json(readLimits()));

app.patch('/tasks/limits', (req, res) => {
  const next = readLimits();
  for (const key of Object.keys(DEFAULT_LIMITS)) {
    if (req.body[key] === undefined) continue;
    const n = Number(req.body[key]);
    if (!Number.isFinite(n) || n < 0) return res.status(400).json({ error: `${key} must be a number >= 0` });
    next[key] = n;
  }
  fs.writeFileSync(LIMITS_PATH, JSON.stringify(next, null, 2) + '\n');
  logEvent(null, 'limits_updated', null, next);
  res.json(next);
});

app.get('/tasks', (req, res) => {
  const where = [];
  const args = [];
  if (req.query.status) { where.push('status = ?'); args.push(req.query.status); }
  if (req.query.assignee) { where.push('assignee = ?'); args.push(req.query.assignee); }
  const limit = Math.min(Number(req.query.limit) || 200, 1000);
  const sql = `SELECT * FROM tasks ${where.length ? 'WHERE ' + where.join(' AND ') : ''}
    ORDER BY id DESC LIMIT ${limit}`;
  res.json(db.prepare(sql).all(...args));
});

app.post('/tasks', (req, res) => {
  const b = req.body || {};
  const limits = readLimits();
  const estimate = Number(b.cost_estimate || 0);
  if (!Number.isFinite(estimate) || estimate < 0) return res.status(400).json({ error: 'cost_estimate must be a number >= 0' });
  if (b.status && !STATUSES.includes(b.status)) return res.status(400).json({ error: `status must be one of ${STATUSES.join(', ')}` });

  if (estimate > limits.single_task_cost_max) {
    return res.status(429).json({ error: `cost_estimate $${estimate} exceeds single_task_cost_max $${limits.single_task_cost_max}` });
  }
  // Today's spend counts the actual cost once known, otherwise the estimate.
  const today = db.prepare(`SELECT COUNT(*) AS n,
      COALESCE(SUM(CASE WHEN cost_actual > 0 THEN cost_actual ELSE cost_estimate END), 0) AS spend
    FROM tasks WHERE date(created_at) = date('now')`).get();
  if (today.n + 1 > limits.daily_new_tasks_cap) {
    return res.status(429).json({ error: `daily_new_tasks_cap reached (${limits.daily_new_tasks_cap} tasks today)` });
  }
  if (today.spend + estimate > limits.daily_total_spend_cap) {
    return res.status(429).json({ error: `would exceed daily_total_spend_cap $${limits.daily_total_spend_cap} (today so far $${today.spend.toFixed(2)})` });
  }

  try {
    const info = db.prepare(`INSERT INTO tasks
      (created_by, assignee, type, status, payload, cost_estimate, priority, parent_id, dedupe_key, notes, kill_criteria)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
      b.created_by ?? null, b.assignee ?? null, b.type ?? null, b.status ?? 'pending', asText(b.payload) ?? null,
      estimate, Number(b.priority || 0), b.parent_id ?? null, b.dedupe_key ?? null, b.notes ?? null,
      asText(b.kill_criteria) ?? null);
    logEvent(info.lastInsertRowid, 'created', `by ${b.created_by || 'unknown'} for ${b.assignee || 'unassigned'}`);
    res.status(201).json(getTask(info.lastInsertRowid));
  } catch (err) {
    if (String(err.code).startsWith('SQLITE_CONSTRAINT_UNIQUE')) {
      const open = db.prepare(`SELECT id FROM tasks WHERE dedupe_key = ?
        AND status IN ('pending','assigned','in_progress')`).get(b.dedupe_key);
      return res.status(409).json({ error: 'an open task with this dedupe_key already exists', existing_id: open?.id });
    }
    throw err;
  }
});

app.get('/tasks/:id', (req, res) => {
  const task = getTask(req.params.id);
  if (!task) return res.status(404).json({ error: 'task not found' });
  task.events = db.prepare('SELECT * FROM events WHERE task_id = ? ORDER BY id').all(task.id);
  res.json(task);
});

app.patch('/tasks/:id', (req, res) => {
  if (!getTask(req.params.id)) return res.status(404).json({ error: 'task not found' });
  const fields = Object.keys(req.body || {}).filter((k) => EDITABLE.includes(k));
  if (!fields.length) return res.status(400).json({ error: `nothing to update; editable fields: ${EDITABLE.join(', ')}` });
  if (req.body.status && !STATUSES.includes(req.body.status)) return res.status(400).json({ error: `status must be one of ${STATUSES.join(', ')}` });
  const values = fields.map((k) => (k === 'payload' || k === 'result' || k === 'kill_criteria' ? asText(req.body[k]) : req.body[k]));
  try {
    db.prepare(`UPDATE tasks SET ${fields.map((k) => `${k} = ?`).join(', ')} WHERE id = ?`).run(...values, req.params.id);
  } catch (err) {
    if (String(err.code).startsWith('SQLITE_CONSTRAINT')) return res.status(409).json({ error: err.message });
    throw err;
  }
  logEvent(Number(req.params.id), 'updated', fields.join(', '));
  res.json(getTask(req.params.id));
});

// Status transitions. Each stamps its timestamp and logs an event.
function transition(route, status, stampColumn, extra) {
  app.post(`/tasks/:id/${route}`, (req, res) => {
    if (!getTask(req.params.id)) return res.status(404).json({ error: 'task not found' });
    const sets = ['status = ?'];
    const args = [status];
    if (stampColumn) sets.push(`${stampColumn} = datetime('now')`);
    const more = extra ? extra(req.body || {}) : {};
    for (const [k, v] of Object.entries(more)) { sets.push(`${k} = ?`); args.push(v); }
    db.prepare(`UPDATE tasks SET ${sets.join(', ')} WHERE id = ?`).run(...args, req.params.id);
    logEvent(Number(req.params.id), route, more.notes || null);
    res.json(getTask(req.params.id));
  });
}
transition('assign', 'assigned', 'assigned_at', (b) => (b.assignee ? { assignee: b.assignee } : {}));
transition('start', 'in_progress', 'started_at');
transition('complete', 'done', 'completed_at', (b) => {
  const out = {};
  if (b.result !== undefined) out.result = asText(b.result);
  if (b.cost_actual !== undefined) out.cost_actual = Number(b.cost_actual) || 0;
  return out;
});
transition('reject', 'rejected', 'completed_at', (b) => (b.reason ? { notes: String(b.reason) } : {}));

app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: err.message });
});

app.listen(PORT, HOST, () => console.log(`mission-control-api listening on http://${HOST}:${PORT} (db: ${DB_PATH})`));

// Mission Control API: reads and writes the task queue (tasks/queue.db).
// Listens on 127.0.0.1 only. Nothing on the internet can reach it; use an
// SSH tunnel to look at it from your own computer.
const fs = require('fs');
const path = require('path');
const express = require('express');
const Database = require('better-sqlite3');

const HOME = process.env.ECOSYSTEM_HOME || path.resolve(__dirname, '..');
const DB_PATH = path.join(HOME, 'tasks', 'queue.db');
const LIMITS_PATH = path.join(HOME, 'tasks', 'limits.json');
const SCHEMA_PATH = path.join(HOME, 'schema.sql');
const PORT = Number(process.env.PORT || 3001);
const HOST = process.env.HOST || '127.0.0.1';

fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('busy_timeout = 5000');
db.exec(fs.readFileSync(SCHEMA_PATH, 'utf8'));

const FIELDS = ['created_by', 'assignee', 'type', 'status', 'payload', 'result',
  'cost_estimate', 'cost_actual', 'priority', 'parent_id', 'dedupe_key', 'notes',
  'kill_criteria', 'assigned_at', 'started_at', 'completed_at'];
const LIMIT_KEYS = ['single_task_cost_max', 'daily_total_spend_cap', 'daily_new_tasks_cap'];

const readLimits = () => JSON.parse(fs.readFileSync(LIMITS_PATH, 'utf8'));
// Objects (like a JSON payload) are stored as JSON text.
const toCell = (v) => (v !== null && typeof v === 'object' ? JSON.stringify(v) : v);
const getTask = (id) => db.prepare('SELECT * FROM tasks WHERE id = ?').get(id);
const logEvent = (taskId, event, msg, meta) =>
  db.prepare('INSERT INTO events (task_id, event, msg, meta) VALUES (?, ?, ?, ?)')
    .run(taskId, event, msg ?? null, meta == null ? null : JSON.stringify(meta));

// Turns SQLite constraint errors into a clear HTTP answer instead of a crash.
function sqlError(res, err) {
  if (String(err.code).startsWith('SQLITE_CONSTRAINT_UNIQUE')) {
    return res.status(409).json({ error: 'an open task with this dedupe_key already exists' });
  }
  if (String(err.code).startsWith('SQLITE_CONSTRAINT')) {
    return res.status(400).json({ error: err.message });
  }
  throw err;
}

const app = express();
app.use(express.json({ limit: '1mb' }));

app.get('/health', (req, res) => res.json({ ok: true }));

app.get('/tasks', (req, res) => {
  const where = [];
  const args = [];
  for (const key of ['status', 'assignee']) {
    if (req.query[key]) { where.push(`${key} = ?`); args.push(req.query[key]); }
  }
  const limit = Math.min(Number(req.query.limit) || 200, 1000);
  const sql = `SELECT * FROM tasks ${where.length ? 'WHERE ' + where.join(' AND ') : ''}
               ORDER BY id DESC LIMIT ${limit}`;
  res.json(db.prepare(sql).all(...args));
});

app.post('/tasks', (req, res) => {
  const body = req.body || {};
  const limits = readLimits();
  const cost = Number(body.cost_estimate || 0);
  if (!Number.isFinite(cost) || cost < 0) {
    return res.status(400).json({ error: 'cost_estimate must be a number >= 0' });
  }
  if (cost > limits.single_task_cost_max) {
    return res.status(429).json({ error: `cost_estimate ${cost} exceeds single_task_cost_max ${limits.single_task_cost_max}` });
  }
  const today = db.prepare(`SELECT COUNT(*) AS n, COALESCE(SUM(cost_estimate), 0) AS spend
                            FROM tasks WHERE date(created_at) = date('now')`).get();
  if (today.n + 1 > limits.daily_new_tasks_cap) {
    return res.status(429).json({ error: `daily_new_tasks_cap ${limits.daily_new_tasks_cap} reached` });
  }
  if (today.spend + cost > limits.daily_total_spend_cap) {
    return res.status(429).json({ error: `daily_total_spend_cap ${limits.daily_total_spend_cap} would be exceeded (today ${today.spend.toFixed(2)} + ${cost})` });
  }
  const cols = FIELDS.filter((f) => body[f] !== undefined && !f.endsWith('_at'));
  try {
    const info = db.prepare(`INSERT INTO tasks (${cols.join(', ')}) VALUES (${cols.map(() => '?').join(', ')})`)
      .run(...cols.map((c) => toCell(body[c])));
    logEvent(info.lastInsertRowid, 'created', `by ${body.created_by || 'unknown'}`);
    res.status(201).json(getTask(info.lastInsertRowid));
  } catch (err) { sqlError(res, err); }
});

// Literal routes go BEFORE /tasks/:id, or ":id" swallows "stats" and "limits".
app.get('/tasks/stats', (req, res) => {
  const rows = db.prepare('SELECT status, COUNT(*) AS n FROM tasks GROUP BY status').all();
  const byStatus = Object.fromEntries(rows.map((r) => [r.status, r.n]));
  const total = rows.reduce((sum, r) => sum + r.n, 0);
  const spend = db.prepare(`SELECT COALESCE(SUM(cost_actual), 0) AS today FROM tasks
                            WHERE date(completed_at) = date('now')`).get();
  res.json({ total, byStatus, spendToday: spend.today });
});

app.get('/tasks/limits', (req, res) => res.json(readLimits()));

app.patch('/tasks/limits', (req, res) => {
  const limits = readLimits();
  for (const key of LIMIT_KEYS) {
    if (req.body[key] === undefined) continue;
    const value = Number(req.body[key]);
    if (!Number.isFinite(value) || value < 0) {
      return res.status(400).json({ error: `${key} must be a number >= 0` });
    }
    limits[key] = value;
  }
  fs.writeFileSync(LIMITS_PATH, JSON.stringify(limits, null, 2) + '\n');
  logEvent(null, 'limits_changed', null, limits);
  res.json(limits);
});

app.get('/events', (req, res) => {
  const limit = Math.min(Number(req.query.limit) || 100, 1000);
  const sql = req.query.task_id
    ? 'SELECT * FROM events WHERE task_id = ? ORDER BY id DESC LIMIT ' + limit
    : 'SELECT * FROM events ORDER BY id DESC LIMIT ' + limit;
  res.json(req.query.task_id ? db.prepare(sql).all(req.query.task_id) : db.prepare(sql).all());
});

app.get('/tasks/:id', (req, res) => {
  const task = getTask(req.params.id);
  task ? res.json(task) : res.status(404).json({ error: 'task not found' });
});

app.patch('/tasks/:id', (req, res) => {
  if (!getTask(req.params.id)) return res.status(404).json({ error: 'task not found' });
  const cols = FIELDS.filter((f) => req.body[f] !== undefined);
  if (!cols.length) return res.status(400).json({ error: 'no known fields to update' });
  try {
    db.prepare(`UPDATE tasks SET ${cols.map((c) => `${c} = ?`).join(', ')} WHERE id = ?`)
      .run(...cols.map((c) => toCell(req.body[c])), req.params.id);
    logEvent(Number(req.params.id), 'updated', cols.join(', '));
    res.json(getTask(req.params.id));
  } catch (err) { sqlError(res, err); }
});

// Status transitions: each sets a status, stamps a time and saves fields from the body.
function transition(route, status, stampCol, bodyCols) {
  app.post(`/tasks/:id/${route}`, (req, res) => {
    if (!getTask(req.params.id)) return res.status(404).json({ error: 'task not found' });
    const body = req.body || {};
    const sets = ['status = ?'];
    const args = [status];
    if (stampCol) sets.push(`${stampCol} = datetime('now')`);
    for (const [bodyKey, col] of bodyCols) {
      if (body[bodyKey] !== undefined) { sets.push(`${col} = ?`); args.push(toCell(body[bodyKey])); }
    }
    try {
      db.prepare(`UPDATE tasks SET ${sets.join(', ')} WHERE id = ?`).run(...args, req.params.id);
      logEvent(Number(req.params.id), route, body.reason || null);
      res.json(getTask(req.params.id));
    } catch (err) { sqlError(res, err); }
  });
}
transition('assign', 'assigned', 'assigned_at', [['assignee', 'assignee']]);
transition('start', 'in_progress', 'started_at', []);
transition('complete', 'done', 'completed_at', [['result', 'result'], ['cost_actual', 'cost_actual']]);
transition('reject', 'rejected', 'completed_at', [['reason', 'notes']]);

app.listen(PORT, HOST, () => console.log(`mission-control-api listening on http://${HOST}:${PORT} (db ${DB_PATH})`));

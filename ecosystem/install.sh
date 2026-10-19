#!/usr/bin/env bash
# Installs (or updates) the agent backbone on a Linux VPS:
#   mission-control-api  (Express, 127.0.0.1:3001)
#   task-dispatcher      (Python, fires agents through OpenClaw)
# both as systemd services. Safe to re-run after `git pull`: code is updated,
# but the queue (tasks/queue.db), limits.json and agents/ are never overwritten.
#
#   sudo bash ecosystem/install.sh            # installs to /root/ecosystem
#   ECOSYSTEM_HOME=/srv/eco sudo -E bash ecosystem/install.sh
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${ECOSYSTEM_HOME:-/root/ecosystem}"

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)."; exit 1; }
command -v systemctl >/dev/null || { echo "systemd not found; this script is for a Linux VPS."; exit 1; }
for bin in node npm python3; do
  command -v "$bin" >/dev/null || { echo "Missing $bin. Finish Step 2 first."; exit 1; }
done
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
[ "$NODE_MAJOR" -ge 20 ] || { echo "Node $NODE_MAJOR is too old; need 20 or newer."; exit 1; }
OPENCLAW_BIN="$(command -v openclaw || true)"
[ -n "$OPENCLAW_BIN" ] || echo "WARNING: openclaw not found on PATH. The dispatcher will start, but agents can't run until it is installed."

echo "==> Installing to $DEST"
mkdir -p "$DEST"/{agents,tasks,scripts,mission-control-api}
cp "$SRC/schema.sql" "$DEST/schema.sql"
cp "$SRC/scripts/task-dispatcher.py" "$DEST/scripts/"
cp "$SRC/mission-control-api/server.js" "$SRC/mission-control-api/package.json" \
   "$SRC/mission-control-api/package-lock.json" "$DEST/mission-control-api/"
[ -f "$DEST/tasks/limits.json" ] || cp "$SRC/tasks/limits.json" "$DEST/tasks/limits.json"
[ -f "$DEST/agents/README.md" ] || cp "$SRC/agents/README.md" "$DEST/agents/README.md"

echo "==> Installing API dependencies"
(cd "$DEST/mission-control-api" && npm ci --omit=dev --no-audit --no-fund)
(cd "$DEST/mission-control-api" && node -e "require('better-sqlite3')(':memory:')") \
  || { echo "better-sqlite3 did not install correctly (native module). Try: apt install -y build-essential, then re-run."; exit 1; }

echo "==> Writing systemd services"
PATH_LINE="PATH=$(dirname "$(command -v node)"):${OPENCLAW_BIN:+$(dirname "$OPENCLAW_BIN"):}/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
for unit in mission-control-api task-dispatcher; do
  sed -e "s|@DEST@|$DEST|g" -e "s|@PATH@|$PATH_LINE|g" \
      -e "s|@NODE@|$(command -v node)|g" -e "s|@PYTHON@|$(command -v python3)|g" \
      -e "s|@OPENCLAW@|${OPENCLAW_BIN:-openclaw}|g" \
      "$SRC/systemd/$unit.service" > "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload
systemctl enable mission-control-api task-dispatcher >/dev/null
systemctl restart mission-control-api task-dispatcher

echo "==> Checking"
sleep 2
systemctl is-active mission-control-api task-dispatcher
curl -fsS http://127.0.0.1:3001/tasks/stats && echo
echo "Done. Logs: journalctl -u task-dispatcher -f   |   journalctl -u mission-control-api -f"

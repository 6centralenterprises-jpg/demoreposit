#!/usr/bin/env bash
# Linux/VPS: install deps and run the API + dispatcher under systemd.
# Run as root from anywhere: bash services/install-linux.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/mission-control-api" && npm install --omit=dev --foreground-scripts
# Point the units at this folder and at the PATH that has openclaw right now.
OC_DIR="$(dirname "$(command -v openclaw || echo /usr/local/bin/openclaw)")"
NODE_DIR="$(dirname "$(command -v node)")"
for unit in mission-control-api task-dispatcher; do
  sed -e "s#/root/ecosystem#$ROOT#g" \
      -e "s#^Environment=PATH=#Environment=PATH=$OC_DIR:$NODE_DIR:#" \
      "$ROOT/services/systemd/$unit.service" > "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload
systemctl enable --now mission-control-api task-dispatcher
systemctl --no-pager status mission-control-api task-dispatcher | head -20

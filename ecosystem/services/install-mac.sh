#!/usr/bin/env bash
# Mac: install deps and run the API + dispatcher under pm2 (launchd at boot).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
case "$ROOT" in
  *"/Library/Mobile Documents/"*|*/Desktop/*|*/Documents/*|*Dropbox*|*"Google Drive"*|*OneDrive*)
    echo "Warning: $ROOT looks cloud-synced. Move the folder to ~/ecosystem first." >&2; exit 1;;
esac
command -v pm2 >/dev/null || npm install -g pm2
cd "$ROOT/mission-control-api" && npm install --omit=dev --foreground-scripts
cd "$ROOT" && pm2 start ecosystem.config.js && pm2 save
echo "Now run the 'sudo env PATH=...' line that 'pm2 startup' prints, so services survive a reboot:"
pm2 startup

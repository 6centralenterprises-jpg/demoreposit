// pm2 config for Mac and Windows: pm2 start ecosystem.config.js && pm2 save
const path = require('path');
const isWin = process.platform === 'win32';

module.exports = {
  apps: [
    {
      name: 'mission-control-api',
      cwd: path.join(__dirname, 'mission-control-api'),
      script: 'server.js',
      autorestart: true,
      restart_delay: 3000,
      windowsHide: true,
    },
    {
      name: 'task-dispatcher',
      cwd: __dirname,
      script: path.join('scripts', 'task-dispatcher.py'),
      interpreter: isWin ? 'python' : 'python3',
      interpreter_args: '-u',
      autorestart: true,
      restart_delay: 3000,
      windowsHide: true,
    },
  ],
};

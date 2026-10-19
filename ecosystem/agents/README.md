# Agents

One folder per agent. The dispatcher treats every subfolder here as an agent,
so the folder name must match the agent's name in OpenClaw.

```
agents/<name>/
  IDENTITY.md   who the agent is
  PLAYBOOK.md   how it does its job
  MEMORY.md     what it has learned
  data/
  reports/
```

To pause an agent without deleting it, create an empty file named `PAUSED`
in its folder. The dispatcher skips it until the file is removed.

# 6C Command Deck

A video-game-style AI crew station for 6 Central Enterprises, modeled on StarNet's
"Agents, teams & voice" docs. It is one self-contained page: `index.html`.

Agents run on Claude through the claude.ai artifact runtime (`sample`), and the
station's state saves privately per viewer (`db` + `user`), with localStorage as a fallback.
Opened outside claude.ai, building, quests and the dossier still work, but agents can't run.

## What's in it
- **Station floor (canvas):** desks (bays), inboxes, outboxes, belts, signposts
  (FILTER, SPLITTER, JOINER, MERGER, LOOP), and shared gear (CONSOLE, INTEL CAB, CORE,
  WORKBENCH, STUDIO, DISH). Live checks such as `NO AGENT — CLICK` and `LOOP! — BREAK THE CIRCLE`.
- **Refit (build mode):** tools 0–9, five ready-made lines, undo/redo, Esc to step back.
- **Crew:** Recruitment Bay with nine classes plus custom, a recruitment interview, a model tier
  per agent, skins, a memory core with fading trust, and CONFIDENCE / RELIABILITY / PRACTICE meters.
- **Real tool use:** files, memory, sandboxed JS (needs approval), and SVG images. Agents walk to
  the gear a tool call actually uses.
- **Delegation:** the Overseer and Allocator can dispatch, spawn temporary clones, and summon new
  crew (summon needs approval). The TASKS tab lets you list, inspect, interrupt and resume workers.
- **COMMS:** streaming chat, slash commands, clarifying questions with choice chips, and approvals.
- **Dossier:** beliefs in nine dimensions that you can keep, edit or strike. Rated work proposes new
  beliefs, and struck beliefs are never proposed again.
- **Quests & XP:** a goal becomes a 3–5 step milestone tree. XP comes only from ▲ NAILED IT.
  Levels follow 25·n·(n−1) and gate nothing.
- **Autonomy:** INITIATIVE, REACH and PACE settings; focus and rule-out lists; six gates; an
  append-only decision log; a morning report; drafts kept for review.
- **Repeat:** skills (dormant when their gear is missing), a Skill Market, recipes and scheduled routines.
- **Voice:** reads answers aloud with the browser's built-in speech. The microphone is blocked inside the claude.ai viewer.

## Known limits (truthful telemetry)
- No web access yet, so the DISH shows as dormant and agents are told not to invent facts.
- Autonomy and routines run only while the page is open in a tab.
- Costs bill to the viewer's Claude plan, so the ledger tracks calls, time and output size, not dollars.

---
description: Decompose the current milestone into a queue of task packets in PROGRESS.md
argument-hint: "[milestone id, e.g. M2 — defaults to the current milestone]"
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

Plan milestone: **$ARGUMENTS** (empty means the current milestone in `PROGRESS.md`).

Run at a milestone boundary only. First check `PROGRESS.md`:

- If the task queue is **not empty**, stop and report what is still queued. Re-planning a live
  queue throws away work and costs a session. The human decides whether to clear it.
- If a packet is **in progress**, stop. Finish or park it first.

Then run `"${STUDIO_CORE:-../studio-core}/scripts/layout.sh" .` and hand its output to the
**planner** agent along with the milestone id. It reads `GAME_PLAN.md`, `DECISIONS.md` and
`PROGRESS.md`, and writes ordered task packets to the queue in the shape defined by the
`state-files` skill — `scope` paths drawn from the layout, not guessed.

When the planner returns, run `verify.sh --no-engine .` so `check-progress.py` validates the
queue. A packet it rejects goes back to the planner once; a second rejection is reported.

Report back: the milestone, the number of packets, their ids and goals, and anything recorded
under **Blockers**. Do not start executing a packet — that is `/next-task`.

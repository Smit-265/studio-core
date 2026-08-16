# PROGRESS — {{GAME_NAME}}

> The single source of session state. **Read this first, every session. Write it before every
> session ends.** A session that ends without updating this file has wasted its tokens,
> because the next one cannot resume cheaply.
>
> Written by: planner (rewrites the queue), builder (moves one packet through it).
> Exact rules: `state-files` skill. Do not freehand prose where a packet belongs.

**Last updated:** {{DATE}} · **Updated by:** {{agent or human}}
**Harness:** _not yet recorded — run `verify.sh`_

---

## Current milestone

**{{M1 — name}}** — see `GAME_PLAN.md` §5 for exit criteria.

Progress: {{n}}/{{total}} tasks done.

---

## In progress

Exactly one task packet, or the word `none`. Same shape as a queue entry — a packet moves
between sections unchanged except for `base_sha` and `attempts`. If a packet is here at
session start, resume it rather than pulling a new one.

none

<!-- When active, the section holds one packet in exactly this shape:

```yaml
id: T-007
goal: Add a pause menu that suspends the game tree.
scope:
  - scenes/ui/pause_menu.tscn
  - scripts/ui/pause_menu.gd
acceptance:
  - Pressing ui_cancel toggles the menu and sets get_tree().paused
  - verify.sh exits 0
tools: []
base_sha: 4f2a1c9e8b7d6a5c4b3a2918f7e6d5c4b3a29187
attempts: 1
```
-->

---

## Task queue

Ordered; the top packet is next. Every entry is a task packet — the same shape the builder
consumes, with `base_sha: ""` and `attempts: 0` until a builder picks it up. A task that will
not fit this shape was decomposed badly; say so rather than writing prose instead.

```yaml
id: T-001
goal: {{one sentence — what is true when this is done}}
scope:
  - {{path/that/may/be/touched}}
acceptance:
  - {{observable outcome a script or a human can check}}
  - verify.sh exits 0
tools: []
base_sha: ""
attempts: 0
```

```yaml
id: T-002
goal: {{one sentence}}
scope:
  - {{path}}
acceptance:
  - {{outcome}}
  - verify.sh exits 0
tools: []
base_sha: ""
attempts: 0
```

---

## Completed

Newest first. One line each — enough to know it happened, not enough to cost tokens
re-reading. Detail lives in git history; `scripts/session-report.sh` recovers it when needed.

| Task | Goal | Done | Commit |
|---|---|---|---|
| T-000 | {{example — delete this row}} | {{date}} | `{{sha}}` |

---

## Blockers

Anything stopping work. A blocker needing a human decision must say so plainly, so the next
session opens with the question rather than rediscovering it.

| # | Blocker | Blocks | Needs | Raised |
|---|---|---|---|---|
| — | none | — | — | — |

---

## Notes for next session

Free text, short. Things a cold session cannot infer from the packets and tables above. Clear
these out once acted upon — stale notes cost tokens on every read.

- {{note}}

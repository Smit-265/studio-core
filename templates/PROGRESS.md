# PROGRESS — {{GAME_NAME}}

> The single source of session state. **Read this first, every session. Write it before every
> session ends.** A session that ends without updating this file has wasted its tokens,
> because the next one cannot resume cheaply.
>
> Written by: planner (rewrites the queue), builder (moves one task through the queue).
> Format rules: `state-files` skill.

**Last updated:** {{DATE}} · **Updated by:** {{agent or human}}

---

## Current milestone

**{{M1 — name}}** — see `GAME_PLAN.md` §5 for exit criteria.

Progress: {{n}}/{{total}} tasks done.

---

## In progress

Exactly one task, or "none". If a task is here at session start, resume it rather than
pulling a new one.

```
none
```

<!-- When active, use this shape:

### T-007 — {{title}}
- **Scope:** `path/one.gd`, `path/two.tscn`   (files this task may touch — nothing else)
- **Started:** {{date}}
- **State:** {{what is done, what remains — enough for a cold session to continue}}
- **Next step:** {{the single next action}}
-->

---

## Task queue

Ordered. Top of the list is next. Each task names its file scope, its acceptance criteria, and
the tool or asset source it uses — drawn only from the approved list in `DECISIONS.md`.

### T-001 — {{title}}

- **Scope:** `{{path}}`
- **Tool/source:** {{from DECISIONS.md, or "none"}}
- **Acceptance:**
  - [ ] {{checkable outcome}}
  - [ ] `verify.sh` exits 0

### T-002 — {{title}}

- **Scope:** `{{path}}`
- **Tool/source:** {{…}}
- **Acceptance:**
  - [ ] {{…}}
  - [ ] `verify.sh` exits 0

---

## Completed

Newest first. One line each — enough to know it happened, not enough to cost tokens re-reading.
Detail lives in git history; use `scripts/session-report.sh` to recover it when needed.

| Task | Title | Done | Commit |
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

Free text, short. Things a cold session cannot infer from the tables above. Clear this out
once acted upon — stale notes cost tokens on every read.

- {{note}}

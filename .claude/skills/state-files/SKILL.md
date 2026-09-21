---
name: state-files
description: Exact format and update rules for the four state files, and the task packet shape that planner writes and builder consumes. Load before writing state for the first time in a session.
---

# state-files

**This file is capped at 150 lines.** A loaded skill sits on-context for the rest of the
session, so the same discipline applies here as to `CLAUDE.md`. Overflow goes in a reference
file beside this one, loaded only when its case comes up.

State lives in the **game repo**, never in studio-core. Four files, plus one generated view.

| File | Written by | When |
|---|---|---|
| `GAME_PLAN.md` | human | rarely — a deliberate act |
| `PROGRESS.md` | planner (queue), builder (one packet) | every session |
| `DECISIONS.md` | human | append-only |
| `assets.yaml` | asset-pipeline | on acquisition |
| `ASSET_MANIFEST.md` | `gen-manifest.py` | **generated — never hand-edit** |

---

## The task packet

The unit of work. **Queue entries and the in-progress slot use the same shape**, so a packet
moves between sections unchanged apart from `base_sha` and `attempts`. There is no translation
step, and no second format to keep in sync.

```yaml
id: T-007                      # T-nnn, unique for the life of the repo, never reused
goal: >                        # ONE sentence, stating what is true when this is done
  Add a pause menu that suspends the game tree.
scope:                         # explicit files and directories this task may touch.
  - scenes/ui/pause_menu.tscn  # Nothing outside this list. A directory means its contents.
  - scripts/ui/pause_menu.gd
acceptance:                    # how verify PROVES it done - observable, not "looks right"
  - Pressing ui_cancel toggles the menu and sets get_tree().paused
  - verify.sh exits 0
tools: []                      # names drawn ONLY from DECISIONS.md §1/§2. [] means none.
agent: builder                 # builder | asset-pipeline. Who /next-task delegates to.
base_sha: ""                   # empty until a builder starts. Then HEAD at that moment.
attempts: 0                    # incremented on each verify.sh failure. Never reset.
```

Eight fields. No more, no fewer, no free-text additions. `check-progress.py` enforces this
inside `verify.sh`: field set, unique ids, clean queue, approved `tools`, one in-progress slot.
`agent` is `asset-pipeline` when `scope` is under `assets/` plus `assets.yaml`; else `builder`.

**If a task will not fit this shape, the planner decomposed it badly.** Say so and re-decompose.
Do not write prose in place of a packet, and do not smuggle detail into `goal` as a paragraph.
Common symptoms: `scope` you cannot enumerate (task too broad), `acceptance` that no script or
human can check (goal too vague), `tools` not in `DECISIONS.md` (needs a human decision first).

### base_sha

Set by the **builder**, once, to `git rev-parse HEAD` at the moment it starts the task — before
touching a file. It is the review base, so it must be recorded before any work exists.

Never set by the planner. Never edited afterwards. Never guessed.

### attempts

Starts at `0`. The builder increments it on **each `verify.sh` failure**, writing the packet
back to `PROGRESS.md` immediately.

This field, not the conversation, is what the **two-strike rule** reads:

- `attempts >= 2` on arrival → **do not attempt a fix.** Stop and report to the human with the
  last error output.
- The count lives in the file precisely so it survives a session boundary. A fresh session
  finding `attempts: 2` must not reset it to zero and start looping again. A loop on a failing
  gate is the most expensive thing an agent can do.

### Resetting attempts

`attempts` returns to `0` in exactly one circumstance: **a human amends the packet's `goal`,
`scope` or `acceptance`.** The task changed, so the count against the old task no longer applies.

It does **not** reset on a session boundary, a retry, a rebase, or because an agent judged the
earlier failures unrelated. No agent resets it. A human may amend a packet **without** resetting
— a clarification, not a new task — and an agent finding `attempts: 2` treats it as 2.

---

## Reviewer diff base

The reviewer diffs **`base_sha..HEAD`, and nothing else.** Not the working tree, not the whole
repo, not `HEAD~1`. **If `base_sha` is empty or missing, the reviewer stops and reports** — a
missing base means the builder skipped a step; a guessed base reviews unrelated commits.

### After a reviewer FAIL

`attempts` counts `verify.sh` failures only; a reviewer FAIL does not touch it. The packet is
already in **Completed** with its commit. The human chooses one of:

- **Fix packet.** Queue a new packet (new id) whose `goal` is the finding and whose `scope` is
  the files it names. `base_sha` is stamped fresh. This is the default.
- **Accept.** Findings were warnings or a recorded decision; nothing to do.
- **Revert.** `git revert <commit>`, then re-queue the original goal under a new id.

No agent picks; `/next-task` reports and stops.

---

## PROGRESS.md

Sections, in order: current milestone · in progress · task queue · completed · blockers · notes.

- **In progress** holds exactly one packet, or the literal word `none`. Never two.
- **Task queue** is ordered; the top packet is next.
- Moving a packet: cut it from the queue, paste it into in-progress, add `base_sha`. On success,
  add a row to **Completed** and delete the packet. The packet is not archived — git has it.
- **Completed** rows are one line: task id, goal, date, commit sha.
- **Blockers** needing a human decision must say so in the `Needs` column.
- Clear **Notes** once acted upon. Stale notes cost tokens on every read.

Update the `Last updated` line every time. No session ends without this file reflecting reality.

## DECISIONS.md

**Append-only.** To reverse a decision, append a new entry that supersedes it and mark the old
one `SUPERSEDED BY D-nnn`. Never delete, never rewrite, never re-litigate what is recorded.
Anything absent is an escalation to the human, not a judgement call.

## GAME_PLAN.md

Read at milestone boundaries, or when a packet's intent is genuinely unclear. Agents do not
edit it; proposing a change to scope or non-goals is an escalation.

## assets.yaml and ASSET_MANIFEST.md

`assets.yaml` is the source of truth; append one entry per acquisition. Then run
`gen-manifest.py` — the markdown is generated and hand edits are both overwritten and invisible
to `check-licences.py`. Field-level rules are in the `asset-import` skill.

---

## Session end

1. Update the in-progress packet: current `attempts`, and what remains if unfinished.
2. Move anything finished to **Completed**.
3. Record new blockers; delete resolved ones.
4. Write **Notes for next session** — only what the packets do not already say.
5. `session-report.sh --mark` — writes the `**Session boundary:**` line into `PROGRESS.md` —
   **then** commit, so the marker travels with the repo to the other machine.

---
description: Walk the current milestone's exit criteria with the human, tick them in GAME_PLAN.md, and advance PROGRESS.md to the next milestone
argument-hint: "[milestone id, e.g. M1 — defaults to the current milestone in PROGRESS.md]"
allowed-tools: Read, Edit, Bash
---

Close milestone: **$ARGUMENTS** (empty means the current milestone in `PROGRESS.md`).

This runs **in the main thread**, with the human. A milestone boundary is a judgement, not a
script result, and `/plan-milestone` trusts that this was done honestly.

Preconditions — stop and say which one failed:

- **Task queue** in `PROGRESS.md` is empty. Queued work means the milestone is not done.
- **In progress** is `none`. Finish or park it first.
- `verify.sh` exits 0 right now. Run it; do not take a past green run on trust.

Then read the milestone's block in `GAME_PLAN.md` §6 and go through its **Exit criteria** one
by one. For each, ask the human to confirm it is observably true — a script result, a thing they
looked at, a playtest they ran. Tick `- [x]` only on a confirmed yes. A criterion nobody can
confirm stays `- [ ]`, and the milestone stays open: either queue the packet that closes it, or
the human amends the criterion in `GAME_PLAN.md` and says why in the commit message.

When every criterion is ticked:

1. In `GAME_PLAN.md` §6, add `**Closed:** <date>` under the milestone's goal line. Append only;
   never rewrite the criteria that were met.
2. In `PROGRESS.md`, set **Current milestone** to the next `M<n>` in §6 if one exists, else to
   `none — run /design-milestone`. Reset the `Progress:` counter.
3. Note under **Notes for next session** anything this milestone taught that the next slice
   should know — one or two lines, not a retrospective.
4. Update `Last updated`, commit.

Report: the milestone id, which criteria were confirmed and by what, and the next command —
`/plan-milestone` if a next milestone exists, `/design-milestone` if not.

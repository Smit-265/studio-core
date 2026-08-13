---
description: Work out the next vertical slice with the human and append it to GAME_PLAN.md as a milestone the planner can decompose
argument-hint: "[optional focus for this slice, e.g. 'first playable' or 'the pause system']"
allowed-tools: Read, Edit, Write
---

Define the next milestone. Focus, if given: **$ARGUMENTS**

Load the `game-design` skill first and follow it. This runs **in the main thread**, as a
conversation — not a subagent.

Read `GAME_PLAN.md` for the pitch, core loop, art constraint and target scope, and `PROGRESS.md`
for what is already done and what the last milestone actually taught. If the plan's early
sections are empty, stop and point at `/design-game` — a milestone cut from a plan that does not
exist is a guess.

Work out **one vertical slice** with the human: a thin cut through the whole game that is
playable on its own. Not a layer, not a system in isolation. "Movement, one room, one
interaction, one way to lose" is a slice; "the inventory system" is a layer.

Interrogate it before writing:

- What can the player *do* at the end of this milestone that they cannot do now?
- What does this slice prove, or disprove, about whether the game is fun?
- What is the smallest version that still answers that question?
- What is explicitly **not** in it, that someone would reasonably assume is?

Then propose **2–3 candidate slices with tradeoffs** — different things to prove first, at
different costs. The human picks.

When agreed, append to the **Milestones** list in `GAME_PLAN.md`, in this shape:

```
### M<n> — <name>

**Goal:** one sentence.
**Proves:** what this slice answers about the design.

**Exit criteria:**
- [ ] <observable, checkable outcome>
- [ ] <observable, checkable outcome>
- [ ] `verify.sh` exits 0

**Not in this milestone:** <the reasonable assumptions this slice does not cover>
```

Exit criteria must be checkable by a script or by a human looking at one specific thing. "Feels
good" is not exit criteria. The planner decomposes this milestone and nothing else, so anything
vague here becomes a vague task packet later.

Append only — never rewrite an existing milestone. Do not decompose into tasks; that is
`/plan-milestone`, run separately once this is agreed.

Report the milestone name, its exit criteria, and what was deliberately left out.

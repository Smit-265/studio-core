---
description: Design the game with the human, interactively, and fill in an empty GAME_PLAN.md section by section
argument-hint: "[optional starting idea — a sentence is plenty, or nothing at all]"
allowed-tools: Read, Edit, Write
---

Design the game. Starting point, if any: **$ARGUMENTS**

Load the `game-design` skill first and follow it. This runs **in the main thread**, as a
conversation — do not delegate it to a subagent. Subagents fire and return; design is
back-and-forth.

First, read `GAME_PLAN.md`. If it already has content beyond the empty scaffold, stop and say
so: this command is for a new or empty plan. Filling in the next milestone of an existing plan
is `/design-milestone`.

Work through the sections in this order, because each one constrains the next:

1. **Pitch** — one paragraph. What it is, who it is for, why it is worth building.
2. **Core loop** — the player does X, which produces Y, which makes them want to do X again.
3. **Art direction constraint** — one line, enforceable. asset-pipeline reads it as a filter.
4. **World / map structure** — how space is organised and how the player moves through it.
5. **Target scope** — platform, engine, session length, total content, and what "shippable"
   concretely means.
6. **Non-goals** — explicit, with reasons. Everything rejected along the way lands here.

Milestones are **not** part of this command. Once the plan is agreed, `/design-milestone`
defines the first vertical slice.

Rules that matter more than speed:

- **Interview before proposing.** Ask what the player feels and why they return, before any
  mechanic talk.
- **Never accept a genre label as an answer.** Push until it is specific.
- **Offer 2–3 options with tradeoffs**, never a single answer. The human decides.
- **Push back on scope.** Name what to cut. Say when something is expensive and offer the
  cheaper version that keeps the intent.
- **Write nothing until the human confirms that section**, then write only that section.
- Mark anything unresolved as `UNDECIDED:` and ask. Never invent a decision by silence.

Finish by reporting which sections are written, which are still open, and the single next
question worth answering.

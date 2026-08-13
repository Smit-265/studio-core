# GAME_PLAN — {{GAME_NAME}}

> Vision, scope and milestones. Written with the human through `/design-game` and
> `/design-milestone`, never filled in by an agent working alone.
>
> **This is the only source of milestones.** The planner reads a milestone from §6 and nowhere
> else, then decomposes it into task packets in `PROGRESS.md`.
>
> Changes rarely — an edit here is a deliberate act. Session-level state lives in `PROGRESS.md`.

**Last reviewed:** {{DATE}} · **Status:** not yet designed

---

## 1. Pitch

One paragraph. What the game is, who it is for, and why it is worth building. If this cannot be
written in one paragraph, the scope is not decided yet.

_Not yet designed — run `/design-game`._

---

## 2. Core loop

One sentence, testable: **the player does X, which produces Y, which makes them want to do X
again.** If that sentence cannot be written, the loop does not exist yet.

"Atmospheric", "immersive" and "emergent" are results, not loops. Name what the player *does*.

_Not yet designed — run `/design-game`._

---

## 3. Art direction constraint

**One line, and enforceable.** asset-pipeline reads this as a filter when sourcing, so it has to
be something an asset can be measured against.

Enforceable: "Low-poly, untextured, three-colour palette." Not enforceable: "Moody."

Numeric limits derived from this line live in `DECISIONS.md` §4 and `config/budgets.yaml`.

_Not yet designed — run `/design-game`._

---

## 4. World / map structure

How space is organised, and how the player moves through it. Hub and spokes, linear levels, one
continuous space, procedural rooms — and what that choice costs to build.

_Not yet designed — run `/design-game`._

---

## 5. Target scope

What shipping means, concretely, decided now while it is cheap to be honest.

| | |
|---|---|
| Platform(s) | |
| Engine + version | Godot 4.7.1.stable (`DECISIONS.md` D-002) |
| Session length | |
| Total content | |

**Shippable means:**

_Not yet designed — run `/design-game`._

---

## 6. Milestones

Ordered, one active at a time. Appended by `/design-milestone`, one vertical slice each — a thin
cut through the whole game that is playable on its own, not a layer or a system in isolation.

A milestone is done when its exit criteria are met and `verify.sh` exits 0 — not when it feels
done. Exit criteria must be checkable by a script or by a human looking at one specific thing,
because the planner turns them into task packet acceptance criteria verbatim.

_No milestones yet — run `/design-milestone` once §1–§5 are agreed._

<!-- Appended milestones use exactly this shape:

### M1 — <name>

**Goal:** one sentence.
**Proves:** what this slice answers about the design.

**Exit criteria:**
- [ ] <observable, checkable outcome>
- [ ] <observable, checkable outcome>
- [ ] `verify.sh` exits 0

**Not in this milestone:** <the reasonable assumptions this slice does not cover>
-->

---

## 7. Non-goals

Explicit, with reasons. This section exists to be quoted back at anyone — human or agent —
proposing work that is out of scope. Every idea rejected during design lands here, so it does
not return in three months as a new idea.

_Not yet designed — run `/design-game`._

---

## 8. Risks

Optional, and worth keeping short. A risk with no mitigation is a non-goal that has not admitted
it yet.

| Risk | Impact | Mitigation |
|---|---|---|
| | | |

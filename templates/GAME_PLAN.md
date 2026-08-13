# GAME_PLAN — {{GAME_NAME}}

> Vision, scope, and milestones. Changes rarely — treat an edit here as a deliberate act, not
> a session-by-session update. Session-level state belongs in `PROGRESS.md`.
>
> Read by: planner (always), builder and reviewer (only when a task's intent is unclear).

**Last reviewed:** {{DATE}}

---

## 1. Vision

One paragraph. What the game is, who it is for, and what makes it worth building. If this
cannot be written in one paragraph, the scope is not yet decided.

---

## 2. Pillars

Three to five. Every task should serve at least one; a task serving none is scope creep.

1. **{{Pillar}}** — one line on what it means in practice.
2. **{{Pillar}}** — …
3. **{{Pillar}}** — …

---

## 3. Scope

### In scope

- {{Feature or system}}
- {{Feature or system}}

### Target

| | |
|---|---|
| Platform(s) | {{platform}} |
| Engine + version | {{engine}} |
| Session length | {{how long a player plays in one sitting}} |
| Total content | {{levels / hours / runs}} |

---

## 4. Non-goals

Explicit. This section exists to be quoted back at anyone — human or agent — proposing work
that is not in scope. Add to it whenever a tempting idea is rejected.

- Not building {{thing}}. Reason: {{reason}}.
- Not supporting {{thing}}. Reason: {{reason}}.
- No {{system}} until {{condition}}.

---

## 5. Milestones

Ordered. One active at a time. A milestone is done when its exit criteria are met and
`verify.sh` exits 0 — not when it feels done.

### M1 — {{name}}

**Goal:** one sentence.

**Exit criteria:**

- [ ] {{Observable, checkable outcome}}
- [ ] {{Observable, checkable outcome}}
- [ ] `verify.sh` exits 0

**Explicitly deferred to a later milestone:** {{list}}

### M2 — {{name}}

**Goal:**

**Exit criteria:**

- [ ] …

### M3 — {{name}}

**Goal:**

**Exit criteria:**

- [ ] …

---

## 6. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| {{risk}} | {{high/med/low}} | {{what we do about it}} |

---

## 7. Definition of done (whole game)

What "shippable" means, concretely. Written now, while it is cheap to be honest.

- {{criterion}}
- {{criterion}}

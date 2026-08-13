# studio-core — Build Brief

Hand this file to Claude Code as the spec for the first build. Read it fully before writing anything.

---

## 1. Mission

Build `studio-core`: a reusable, game-agnostic agent harness for a two-person game studio with no employees. It orchestrates AI agents to do production work (code, tooling, asset pipeline, verification) across **multiple games over multiple years**. It is not tied to any single game.

The first tenant will be a Godot 4.x 3D horror game, but nothing game-specific belongs in this repo.

---

## 2. Hard constraints

These are not preferences. Violating them makes the system unusable.

**Budget: one Claude Pro seat, ~$23/month.** Usage is a shared pool across chat and Claude Code, governed by a rolling 5-hour session limit and a weekly limit. Every design decision must minimise token burn.

Consequences:

- **Sequential only.** Never design for parallel sub-agents. One agent works at a time.
- **Deterministic-first.** If a bash script, a linter, or a CI job can do it, an LLM must not do it. Agents are for judgment, not for work a script can perform. Target roughly 90% of verification as plain scripts.
- **Context is the meter.** `CLAUDE.md` ships with every request. Hard cap: **200 lines**. Anything longer belongs in a skill that loads on demand.
- **Narrow scope per task.** Agents must never be pointed at the whole project. Every agent definition must state its file scope.
- **Sonnet by default.** Opus is reserved for architecture decisions and hard debugging only.
- **Cheap session resume.** A new session must be able to reconstruct state by reading state files, not by re-reading the codebase.

---

## 3. Repository structure to create

```
studio-core/
├── CLAUDE.md                     # ≤200 lines, hard limit
├── README.md                     # human-facing: what this is, how to use it
├── .claude/
│   ├── agents/
│   │   ├── planner.md
│   │   ├── builder.md
│   │   ├── reviewer.md
│   │   └── asset-pipeline.md
│   ├── commands/
│   │   ├── plan-milestone.md
│   │   ├── next-task.md
│   │   ├── verify.md
│   │   └── session-end.md
│   └── skills/
│       ├── godot-conventions/SKILL.md
│       ├── asset-import/SKILL.md
│       └── state-files/SKILL.md
├── scripts/
│   ├── verify.sh
│   ├── new-project.sh
│   ├── check-budgets.py
│   ├── check-licences.py
│   └── session-report.sh
├── templates/
│   ├── GAME_PLAN.md
│   ├── PROGRESS.md
│   ├── DECISIONS.md
│   ├── ASSET_MANIFEST.md
│   └── game-CLAUDE.md            # template for a per-game CLAUDE.md
└── .github/workflows/
    ├── verify.yml
    └── build.yml
```

A per-game repo (`game-<name>`) stays thin: the Godot project, the four state files, and a `CLAUDE.md` that references studio-core rather than duplicating it.

---

## 4. File specifications

### 4.1 `CLAUDE.md` (≤200 lines)

Must contain only what is needed on *every* request:

- One-paragraph description of the studio and the system.
- The token discipline rules from §2, stated as rules an agent must follow.
- Where state lives and the requirement to read state before acting and write state before ending.
- Pointers to skills by name — not their contents.
- The escalation rule: stop and ask the human rather than guessing on scope, architecture, or anything costing significant tokens.

Do not put engine conventions, asset rules, or coding style in here. Those go in skills.

### 4.2 Agents (`.claude/agents/*.md`)

Each agent definition must specify: purpose, file scope it may touch, tools it may use, what it must read before starting, what it must write when finished, and explicit non-goals.

- **planner** — Decomposes a milestone into a task queue with acceptance criteria per task. Names the tool/asset source for each task, drawn only from the approved list in `DECISIONS.md`. Writes the queue to `PROGRESS.md`. Never writes code. Runs at milestone boundaries only.
- **builder** — Executes one queued task. Narrow file scope. Runs `verify.sh` before declaring done. Never refactors beyond the task.
- **reviewer** — Reads diffs only, never the whole repo. Checks correctness, scope creep, and convention adherence. Outputs a pass/fail with specific findings.
- **asset-pipeline** — Sources CC0/free assets, checks style constraints and budgets, sets import settings, appends to `ASSET_MANIFEST.md` with source and licence. Never generates art.

### 4.3 Scripts (`scripts/`)

All must run standalone with no LLM involvement, exit non-zero on failure, and print actionable messages.

- **`verify.sh`** — Orchestrates: Godot headless compile/import check, GDScript parse errors, unit tests if a test framework is present, `check-budgets.py`, `check-licences.py`. Must degrade gracefully with a clear message if Godot is not installed or no project is present. Accepts a project path argument, defaults to cwd.
- **`check-budgets.py`** — Reads thresholds from a config file (poly counts, texture dimensions, file sizes, total build size). Walks the asset directory, reports violations. Thresholds configurable per game, with defaults in studio-core.
- **`check-licences.py`** — Cross-references files in the asset directory against `ASSET_MANIFEST.md`. Fails on any asset with no manifest entry or no licence recorded. This is a ship-blocker check; treat it as such.
- **`new-project.sh`** — Scaffolds a new `game-<name>` repo from `templates/`, wiring its `CLAUDE.md` to studio-core.
- **`session-report.sh`** — Summarises git activity since last session for cheap state reconstruction.

### 4.4 Skills (`.claude/skills/*/SKILL.md`)

Load-on-demand reference. Keep each focused.

- **godot-conventions** — GDScript style, node naming, scene organisation, signal patterns, resource layout.
- **asset-import** — Import settings per asset type, naming rules, directory layout, style-constraint enforcement, manifest entry format.
- **state-files** — Exact format and update rules for the four state files, so every agent writes them consistently.

### 4.5 Templates (`templates/`)

- **`GAME_PLAN.md`** — Vision, scope, milestones, explicit non-goals. Changes rarely.
- **`PROGRESS.md`** — Current milestone, task queue, in-progress task, completed log, blockers. Changes every session.
- **`DECISIONS.md`** — Approved tool/MCP/asset-source list, architecture decisions with rationale, style constraints. Append-only. Agents must not re-litigate what is recorded here.
- **`ASSET_MANIFEST.md`** — Every asset: path, source, author, licence, date added.

### 4.6 CI (`.github/workflows/`)

- **`verify.yml`** — Runs `verify.sh` on push and PR. Free tier, consumes no Claude quota. This is the primary verification path.
- **`build.yml`** — Godot headless export on tag. May be a documented stub if export presets are game-specific.

---

## 5. Build order

Build in phases. **Stop after each phase and report** — do not run all four in one session.

1. **Phase 1 — Skeleton.** Directory structure, `CLAUDE.md`, `README.md`, all four templates. Stop and report.
2. **Phase 2 — Scripts.** All five scripts, working and tested against an empty scaffold. Stop and report.
3. **Phase 3 — Agents and skills.** All agent definitions, all skills, all commands. Stop and report.
4. **Phase 4 — CI and dogfood.** Workflows, then run `new-project.sh` to scaffold a throwaway test game and confirm `verify.sh` passes end to end. Report results.

---

## 6. Acceptance criteria

- `CLAUDE.md` is ≤200 lines. Verify with `wc -l`.
- `verify.sh` runs clean on a freshly scaffolded empty project and exits 0.
- `verify.sh` exits non-zero when given a project with a deliberate GDScript syntax error.
- `check-licences.py` fails when an asset exists with no manifest entry.
- `new-project.sh` produces a working game repo in one command.
- No game-specific content anywhere in studio-core — no horror, no monster, no specific mechanics.
- Every agent definition states its file scope and its non-goals.

---

## 7. Non-goals — do not do these

- Do not install or configure MCP servers. List candidates in `DECISIONS.md` as recommendations only; installation is a human decision.
- Do not add agents beyond the four specified.
- Do not build anything requiring a paid API key.
- Do not write game code, game assets, or game design.
- Do not exceed the `CLAUDE.md` line limit "just this once".
- Do not build parallel or concurrent agent execution.
- Do not invent tooling not listed here without asking first.

---

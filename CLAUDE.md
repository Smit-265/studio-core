# studio-core

Game-agnostic agent harness for a two-person studio with no employees. It orchestrates AI
agents to do production work — code, tooling, asset pipeline, verification — across multiple
games over multiple years. studio-core holds the harness; each game lives in its own thin
`game-<name>` repo that references this one. Nothing game-specific belongs in studio-core.

## Budget reality

One Claude Pro seat, ~$23/month, shared across chat and Claude Code, governed by a rolling
5-hour session limit and a weekly limit. Token burn is the binding constraint on this studio.
The rules below are not preferences.

## Rules

1. **Sequential only.** One agent works at a time. Never spawn parallel or concurrent
   sub-agents. If a task seems to want parallelism, split it into ordered steps instead.
2. **Deterministic-first.** If a bash script, a linter, or a CI job can do it, do not use an
   LLM for it. Agents are for judgment, not for work a script can perform. Verification is
   ~90% plain scripts; run `scripts/verify.sh` rather than reading files to check correctness.
3. **Narrow scope.** Never work against the whole project. Every task names its file scope;
   stay inside it. Touching files outside scope is scope creep — stop and report instead.
4. **Cheap reads.** Prefer state files, `git diff`, and script output over reading source.
   Read whole files only when you are about to change them.
5. **No re-litigating.** Decisions recorded in `DECISIONS.md` are settled. Follow them or
   escalate to the human; do not quietly pick something else.
6. **Two-strike rule.** If `verify.sh` fails, you get at most two fix attempts. On the second
   failure, stop and report with the error output. Do not keep iterating — a loop on a failing
   gate is the most expensive thing you can do. The count lives in the task packet's `attempts`
   field, so it survives a session boundary; arriving at `attempts: 2` means stop, not restart.
7. **This file is capped at 200 lines.** Anything longer belongs in a skill. No exceptions.

## State

State lives in the game repo, not here. Four files:

| File | Holds | Changes |
|---|---|---|
| `GAME_PLAN.md` | Vision, scope, milestones, non-goals | Rarely |
| `PROGRESS.md` | Current milestone, task queue, in-progress task, completed log, blockers | Every session |
| `DECISIONS.md` | Approved tools/MCPs/asset sources, architecture decisions, style constraints | Append-only |
| `assets.yaml` | Asset provenance: path, source, author, SPDX licence, date | On asset add |

`ASSET_MANIFEST.md` is a **generated** view of `assets.yaml` — never hand-edit it; append to
`assets.yaml` and run `gen-manifest.py`. Budget thresholds live in `config/budgets.yaml`, never
in a script: studio-core's copy holds the defaults, the game repo's copy holds only that
game's overrides, and the game's values win on merge.

**`config/budgets.yaml` is asset budgets only** — triangles, texture dimensions, file sizes.
Gameplay numbers (drain rates, speeds, damage, timers) live in `tuning/game_tuning.tres`, a
Godot Resource editable in the inspector between playtests. A gameplay value in `budgets.yaml`
fails `check-budgets.py` at exit 2 and is unreadable from Godot at runtime. See D-004 and the
`godot-conventions` skill.

studio-core itself is found via `$STUDIO_CORE`, else the sibling directory `../studio-core`.

Work is carried in **task packets** — one YAML shape, written by planner and consumed by
builder or asset-pipeline, identical in the queue and in the in-progress slot. Fields: `id`,
`goal`, `scope`, `acceptance`, `tools`, `agent`, `base_sha`, `attempts`. Work that will not fit
the shape was decomposed badly; say so rather than writing prose instead. `check-progress.py`
validates every packet inside `verify.sh`. Full rules: `state-files` skill.

**Read state before acting.** At session start, read `PROGRESS.md` first, then `DECISIONS.md`
if the task involves tool or architecture choices. Reconstruct context from these files and
`scripts/session-report.sh` — not by re-reading the codebase.

**Write state before ending.** No session ends without `PROGRESS.md` updated: what got done,
what is in flight, what is blocked. A session that ends without this has wasted its tokens,
because the next session cannot resume cheaply.

Exact formats and update rules are in the `state-files` skill. Load it before writing state
for the first time in a session.

## Guards

The rules above are also **hooks** in every game repo (`.claude/settings.json`, generated from
studio-core): an `Edit`/`Write` outside the in-progress packet's `scope` is refused; a second
concurrent agent is refused; `git` rooted outside the game repo is refused; ending a session
with changes but an untouched `PROGRESS.md` is refused once. A refusal is the rule working —
report it, do not route around it. `STUDIO_GUARD=off` is a human's decision, outside a session.

## Agents

Four, no more. Each has a fixed file scope and explicit non-goals in its definition.

- `planner` — milestone → task queue with acceptance criteria. Never writes code.
- `builder` — executes one queued task. Runs `verify.sh` before declaring done.
- `reviewer` — reads diffs only. Pass/fail with specific findings.
- `asset-pipeline` — sources CC0/free assets, checks budgets, records licences. Never generates art.

## Skills

Load on demand, by name. Do not preload; do not inline their contents here.

- `game-design` — how to be a design partner: interview first, options not answers, push back.
- `godot-conventions` — GDScript style, node naming, scene organisation, signals, resources.
- `asset-import` — import settings per asset type, naming, directory layout, manifest format.
- `state-files` — exact format and update rules for the four state files.

## Scripts

Run these instead of reasoning about correctness.

- `scripts/verify.sh [project-path]` — the verification gate. Compile/import check, GDScript
  parse errors, tests, budgets, licences. Must exit 0 before any task is declared done.
- `scripts/check-budgets.py` — asset budgets, from `config/budgets.yaml` merged with the
  game's override.
- `scripts/check-licences.py` — validates `assets.yaml` against the filesystem. **Ship-blocker.**
- `scripts/gen-manifest.py` — regenerates `ASSET_MANIFEST.md` from `assets.yaml`.
- `scripts/check-plan.py` — warns when `GAME_PLAN.md` §3 states a limit the merged budget
  config does not enforce. Warning-only; always exits 0.
- `scripts/check-progress.py` — task packets honour the contract. Runs inside `verify.sh`.
- `scripts/layout.sh` — directory shape and script/scene names, for the planner's `scope`.
- `scripts/new-project.sh <name>` — scaffold a new game repo.
- `scripts/session-report.sh` — git activity since last session, for cheap resume.
  `--mark` writes the boundary into `PROGRESS.md`; run it **before** the final commit.

## Escalation

Stop and ask the human. Do not guess, and do not "just try it", when:

- Scope is ambiguous, or the task appears to need files outside its stated scope.
- An architecture decision is required that is not already in `DECISIONS.md`.
- A new tool, MCP server, dependency, or asset source would be introduced.
- The work would consume significant tokens — large refactors, broad searches, whole-repo reads.
- `verify.sh` fails in a way not obviously caused by the current change.
- A constraint in this file appears to block the task.

Asking costs a few hundred tokens. Guessing wrong costs a session.

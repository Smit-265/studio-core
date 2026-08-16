# studio-core

A reusable, game-agnostic agent harness for a two-person game studio with no employees.

studio-core is the machinery: agent definitions, slash commands, load-on-demand skills,
verification scripts, state-file templates, and CI workflows. It is not a game, and it is not
tied to one. Games live in their own thin `game-<name>` repos that reference this one.

## Why it exists

The studio runs on a single Claude Pro seat, ~$23/month, with a rolling 5-hour session limit
and a weekly limit shared across chat and Claude Code. That budget is the binding constraint
on everything here. The harness is built to spend as few tokens as possible per unit of
shipped work:

- **Sequential, never parallel.** One agent at a time.
- **Deterministic-first.** Roughly 90% of verification is plain scripts and CI, which cost no
  Claude quota. Agents are reserved for judgment.
- **Small context.** `CLAUDE.md` ships with every request and is hard-capped at 200 lines.
  Everything else loads on demand as a skill.
- **Narrow file scope.** No agent is ever pointed at the whole project.
- **Cheap session resume.** State is reconstructed from four state files, not by re-reading
  the codebase.

## Layout

```
studio-core/
├── CLAUDE.md                 # ships with every request — ≤200 lines, hard limit
├── README.md
├── VERSION                   # harness semver — see "Versioning the harness"
├── .claude/
│   ├── agents/               # planner, builder, reviewer, asset-pipeline
│   ├── commands/             # design-game, design-milestone, plan-milestone,
│   │                         # next-task, verify, session-end
│   └── skills/               # game-design, godot-conventions, asset-import, state-files
├── config/
│   └── budgets.yaml          # default asset thresholds; games override per-repo
├── scripts/                  # verify.sh, new-project.sh, check-budgets.py,
│                             # check-licences.py, gen-manifest.py, session-report.sh,
│                             # check-loaders.py, sync-loaders.sh, check-plan.py
│                             # _resolve.sh, _sclib.py — sourced/imported, not run
├── templates/                # state files, assets.yaml, budgets override, game CLAUDE.md
└── .github/workflows/        # verify.yml, build.yml
```

## The two-repo split

| | studio-core | `game-<name>` |
|---|---|---|
| Holds | Harness: agents, skills, commands, scripts, CI | Engine project, four state files, thin `CLAUDE.md` |
| Game-specific content | None, ever | All of it |
| Changes | Rarely, deliberately | Constantly |

A game repo's `CLAUDE.md` references studio-core rather than duplicating it. When the harness
improves, every game gets the improvement without a copy-paste migration.

## Starting a new game

```sh
scripts/new-project.sh <name>
```

Scaffolds `game-<name>` from `templates/`, wires its `CLAUDE.md` to studio-core, and drops in
the four state files ready to fill.

Then, in the new repo:

1. `/design-game` — design the game with the agent as a partner, not a scribe. It interviews
   before proposing, offers options with tradeoffs rather than single answers, pushes back on
   scope, and writes `GAME_PLAN.md` one section at a time, only once you confirm each.
2. `/design-milestone` — work out the first vertical slice and append it to the plan.
3. `/plan-milestone` — decompose that milestone into task packets.
4. `/next-task` — execute one packet at a time.

Design runs in the main thread rather than as an agent, because it is a conversation and
subagents cannot converse. Fill in `DECISIONS.md` as tool and asset-source choices come up;
agents treat it as settled and escalate on anything absent.

## The four state files

Held in each game repo. They are the entire memory of the project between sessions.

- **`GAME_PLAN.md`** — vision, scope, milestones, non-goals. Changes rarely.
- **`PROGRESS.md`** — current milestone, task queue, in-progress task, completed log,
  blockers. Changes every session.
- **`DECISIONS.md`** — approved tool/MCP/asset-source list, architecture decisions with
  rationale, style constraints. Append-only; agents must not re-litigate what is recorded.
- **`assets.yaml`** — machine-readable asset provenance: path, source URL, author, SPDX
  licence, date added, modifications, plus a rejected list. Agents append here.
  `check-licences.py` validates it against the filesystem and fails the build on any asset
  with no entry or no licence.
- **`ASSET_MANIFEST.md`** — human-readable view, **generated** from `assets.yaml` by
  `gen-manifest.py`. Never hand-edited; edits are overwritten and invisible to the checker.

Two files, one fact: the markdown exists to be read by people, the YAML to be parsed by
scripts. Regex over a markdown table is fragile and agents drift the format, so the parsed
source of truth is the YAML.

## Verification

`scripts/verify.sh [project-path]` is the gate. It runs the engine's headless compile and
import check, catches script parse errors, runs unit tests if a framework is present, then
`check-budgets.py` and `check-licences.py`. It exits non-zero on any failure and prints
actionable messages. It degrades gracefully with a clear message if the engine is not
installed or no project is present.

Budget thresholds come from `config/budgets.yaml`, deep-merged with the game repo's own
`config/budgets.yaml` if present. No script hardcodes a number.

`config/budgets.yaml` covers **assets only** — triangles, texture dimensions, file sizes.
Gameplay numbers live in the game's `tuning/game_tuning.tres`, a Godot Resource that scaffolds
with every new project and is editable in the inspector between playtests. The two are not
interchangeable: `check-budgets.py` exits 2 on a key it does not know, and Godot cannot read
YAML at runtime.

`check-plan.py` then reconciles `GAME_PLAN.md` §3 against the merged budget config and warns
when the prose states a limit the config does not enforce. It is **warning-only and always
exits 0** — §3 is written with a human during design, and a hard gate there would fire on
phrasing rather than substance. The fix is always the same: put the number in the config and
have the plan point at it.

CI runs the same script on push and PR via `.github/workflows/verify.yml`, on the free tier.
That is the primary verification path and it consumes no Claude quota — prefer it to asking an
agent whether something works.

## The four agents

No more will be added.

- **planner** — decomposes a milestone into a task queue with acceptance criteria per task,
  naming the tool or asset source for each from the approved list in `DECISIONS.md`. Writes
  the queue to `PROGRESS.md`. Never writes code. Runs at milestone boundaries only.
- **builder** — executes exactly one queued task within a narrow file scope. Runs `verify.sh`
  before declaring done. Never refactors beyond the task.
- **reviewer** — reads diffs only, never the whole repo. Checks correctness, scope creep, and
  convention adherence. Outputs pass/fail with specific findings.
- **asset-pipeline** — sources CC0/free assets, checks style constraints and budgets, sets
  import settings, appends to `ASSET_MANIFEST.md` with source and licence. Never generates art.

## Conventions

MCP servers are never installed by an agent. `DECISIONS.md` may list candidates as
recommendations; installing one is a human decision.

### Model policy — a human operating rule

**Sonnet by default. Opus only for architecture decisions and hard debugging.**

This one is on you, not on the agent. Model selection happens at invocation, so an instruction
inside `CLAUDE.md` cannot act on it — by the time the model reads the rule, the choice is
already made and already billed. It is therefore stated here and encoded as the declared model
in each agent definition, not carried as a runtime rule.

### How agents reach a game repo

A game repo's `.claude/` holds **loaders**, not copies. Each loader carries its own frontmatter
and one instruction: resolve studio-core, read the real definition there, follow it exactly. No
behaviour lives in a loader — if you find yourself writing instructions into one, that content
belongs upstream.

This keeps the working directory in the **game repo**, which matters because the builder stamps
`base_sha` from `git rev-parse HEAD` and the reviewer diffs `base_sha..HEAD`. Both must target
the game's history, and a git call silently rooted in the wrong tree is a whole bug class.

Loaders are generated by `sync-loaders.sh` and checked by `check-loaders.py`, which runs inside
`verify.sh`. A missing loader, an extra one, or any drift in frontmatter or body fails the
build — copies fork, so drift is made a build failure rather than a matter of discipline.

### Finding studio-core from a game repo

Game repo scripts locate this repo in a fixed order:

1. `$STUDIO_CORE`, if set — the escape hatch for non-standard layouts. `.env.example` in every
   scaffolded game repo shows the variable.
2. `../studio-core` — the sibling-directory convention. `new-project.sh` scaffolds game repos
   as siblings of studio-core so this works with no configuration.
3. Otherwise: fail with a message naming both.

Games track studio-core's head; there is no version pinning. The accepted consequence is that a
studio-core change can break an existing game repo — `verify.sh` is what catches it. Once a
game ships, pin it by converting studio-core to a git submodule in that repo; the resolution
order above already accommodates a submodule path via `$STUDIO_CORE`.

### Versioning the harness

`VERSION` at this repo's root holds a semver string. It is the harness's version, not any
game's.

| Bump | When |
|---|---|
| **minor** (`0.1.0` → `0.2.0`) | An agent definition, a skill contract, or a script interface changes. Anything a game repo depends on by name or by shape: an agent's scope or non-goals, a skill's rules, a script's arguments, exit codes or output format, the task packet fields, a state-file template's structure. |
| **patch** (`0.1.0` → `0.1.1`) | A fix that changes no contract. Bug fixes inside a script, wording, added examples, tightened checks that accept the same inputs. |
| **major** | Reserved. Nothing is `1.0.0` until a game has shipped against it. |

Bump `VERSION` in the same commit as the change, and tag that commit `v<version>`.

Games track head rather than pinning (D-001), so the version exists to answer a question after
the fact: *which harness was this game working against when it broke?* `verify.sh` records the
version and short SHA into the game's `PROGRESS.md` on every run — with `-dirty` appended when
studio-core has uncommitted edits, because an uncommitted harness is not the SHA it claims to
be. `session-report.sh` reads that stamp back and flags it when studio-core has moved since.

## Build status

Built in phases. Current phase and what remains are tracked in `PROGRESS.md` of this repo's
own working notes; see `STUDIO_CORE_BRIEF.md` for the original specification.

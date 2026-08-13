# {{GAME_NAME}}

Game repo. The harness — agents, skills, commands, verification scripts — lives in
**studio-core**. This file stays thin and does not duplicate it. Read studio-core's
`CLAUDE.md` for the operating rules; they apply here in full.

**Finding studio-core:** `$STUDIO_CORE` if set, else `../studio-core`, else the scripts fail
with a message naming both. At scaffold time it was `{{STUDIO_CORE_PATH}}`. See `.env.example`
to set the variable, and `DECISIONS.md` D-001 for why it is a convention rather than a pin.
This repo tracks studio-core's head — a harness change can break it, and `verify.sh` is what
catches that.

**Same 200-line cap applies to this file.** Game detail belongs in the state files below,
which load only when needed, not here, which ships with every request.

## Non-negotiables, restated

- Sequential only — one agent at a time, never parallel.
- Deterministic-first — if a script can check it, do not ask an LLM to.
- Stay inside the task's file scope. Outside it is scope creep; stop and report.
- Read state before acting; write `PROGRESS.md` before ending.
- Escalate rather than guess on scope, architecture, new tools, or anything token-expensive.

## State files

In this repo, at the root. These are the project's entire memory between sessions.

| File | Read when | Written by |
|---|---|---|
| `PROGRESS.md` | **Every session, first** | planner, builder |
| `DECISIONS.md` | Before any tool, dependency, or asset choice | human (append-only) |
| `GAME_PLAN.md` | At milestone boundaries, or when intent is unclear | human |
| `assets.yaml` | Before touching assets | asset-pipeline (append-only) |

`ASSET_MANIFEST.md` is generated from `assets.yaml` — never hand-edit it.

Format and update rules: `state-files` skill in studio-core.

## This game

<!-- Fill these in once. Keep to a few lines each; detail goes in GAME_PLAN.md. -->

- **Engine:** {{engine + version}}
- **Platform(s):** {{platforms}}
- **One-line pitch:** {{pitch}}
- **Current milestone:** see `PROGRESS.md`

## Project layout

<!-- Only the directories an agent needs to navigate. Not a full tree. -->

```
{{res://scenes/}}      {{what lives here}}
{{res://scripts/}}     {{what lives here}}
{{res://assets/}}      {{what lives here — covered by ASSET_MANIFEST.md}}
{{tests/}}             {{test framework, if present}}
```

## Verification

```sh
{{STUDIO_CORE_PATH}}/scripts/verify.sh .
```

Must exit 0 before any task is declared done. CI runs the same script on push and PR, on the
free tier — prefer reading its output to reasoning about whether something works.

Budget overrides for this game: `config/budgets.yaml` (merged over studio-core's defaults).

## Game-specific overrides

Only things that genuinely differ from studio-core defaults. Every entry here is a cost paid on
every request — if the list grows past a handful of lines, the difference probably belongs in
`DECISIONS.md` instead.

- {{override, and why}}

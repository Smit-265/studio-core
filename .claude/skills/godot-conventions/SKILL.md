---
name: godot-conventions
description: GDScript style, node and scene naming, scene organisation, signal patterns and resource layout for Godot 4.7.1. Load before writing or reviewing GDScript or scene files.
---

# godot-conventions

**Capped at 150 lines** — a loaded skill sits on-context all session. Overflow lives in
`reference/`, beside this file in studio-core; read one only when its case comes up.

Written against **Godot 4.7.1.stable** (pinned — see `DECISIONS.md` D-002). Do not apply Godot 3
idioms; they are silently wrong more often than they are loudly broken.

## Naming

| Thing | Convention | Example |
|---|---|---|
| Script file | `snake_case.gd` | `pause_menu.gd` |
| Scene file | `snake_case.tscn` | `pause_menu.tscn` |
| Node in a scene | `PascalCase` | `PauseMenu`, `HealthBar` |
| Class (`class_name`) | `PascalCase` | `class_name PauseMenu` |
| Function, variable | `snake_case` | `apply_damage`, `move_speed` |
| Private member | leading underscore | `_cached_target` |
| Constant, enum value | `SCREAMING_SNAKE_CASE` | `MAX_HEALTH` |
| Signal | `snake_case`, **past tense** | `died`, `health_changed` |
| Autoload / singleton | `PascalCase` | `GameState` |

A script's filename matches its `class_name` in snake_case. A scene's root node matches the
scene filename in PascalCase. Divergence here is the single most common source of "which file
is this?" churn.

---

## Script structure

Fixed order, and reviewers check it — write it this way the first time:

`class_name` · `extends` · docstring · signals · enums · constants · `@export` · public vars ·
private vars · `@onready` · `_init` · `_ready` · other engine callbacks · public methods ·
private methods · signal handlers.

Worked example with the reasoning and the usual mistakes: `reference/script-structure.md`.

## Typing

**Static types everywhere.** `var speed := 5.0`, `func apply(amount: int) -> void:`. Untyped
GDScript is slower and defers real errors to runtime, where they cost a session to find rather
than a `verify.sh` run.

- Always annotate function parameters and return types. `-> void` is not optional.
- Prefer `:=` inference to a bare `var x = ...`.
- `@onready` vars get an explicit type: `@onready var _panel: Panel = $Panel`.

## Signals over polling

Connect in code, in `_ready`, not in the editor — connections made in the editor are invisible
to `git diff` and to the reviewer.

```gdscript
func _ready() -> void:
	_button.pressed.connect(_on_resume_pressed)
	health_changed.connect(_hud.update_health)
```

- Signal handler names: `_on_<source>_<signal>`.
- Emit with `health_changed.emit(current)`. No `emit_signal("...")` string form.
- A node signals **upward** and calls **downward**. A child never reaches for a parent by
  `get_parent()` or by absolute path; it emits and lets the parent decide.
- Disconnect in `_exit_tree` only when the other end outlives this node.

## Node access

- `$Child/Grandchild` for nodes inside the same scene, via an `@onready` var, never inline in
  a hot path.
- `%UniqueName` for a node deep in the scene, when the path would otherwise be brittle.
- **Never** `get_node("../../Something")`. Crossing scene boundaries by path is how a scene
  becomes unmovable. Use an `@export` reference or a signal.
- `get_tree().get_first_node_in_group("player")` for the rare genuine global lookup, and only
  for a group recorded as a convention.

## Scene organisation

- One scene = one responsibility, and it must be openable and runnable on its own.
- A scene's root node type is the narrowest that works: `Control` for UI, `Node2D`/`Node3D` for
  world objects, plain `Node` for logic with no transform.
- Composition over inheritance. Prefer a child node that adds behaviour to a subclass of a
  subclass.
- Instance children with `PackedScene` `@export` vars rather than `load()` on a string path, so
  a rename is caught by the editor rather than at runtime.

## Directory layout

```
scenes/        one directory per feature area, mirroring scripts/
scripts/       .gd files, mirroring scenes/
assets/        art, audio, fonts - see the asset-import skill
tuning/        game_tuning.gd + .tres - gameplay values, see below
tests/         test scripts, named test_<thing>.gd
```

`scenes/ui/pause_menu.tscn` pairs with `scripts/ui/pause_menu.gd`. Keep the mirror exact; it is
what makes a task's `scope` list short and enumerable.

## Resources

- Custom data types are `Resource` subclasses with `class_name` and `@export` fields, saved as
  `.tres` (text) — **never `.res`**, which is binary and unreviewable in a diff.
- Load with `preload()` for a constant path known at compile time, `load()` only when the path
  is genuinely dynamic.
- Resources are shared by reference. Call `.duplicate()` before mutating one at runtime, or two
  instances will quietly share state.

## Gameplay tuning

Gameplay numbers — drain rates, speeds, damage, timers, spawn counts — live in
`tuning/game_tuning.tres`, an instance of the `GameTuning` Resource declared in
`tuning/game_tuning.gd`. Each game carries this as `DECISIONS.md` D-004.

**Never `config/budgets.yaml`.** That is the asset budget schema — triangles, texture
dimensions, file sizes. `check-budgets.py` exits 2 on a key it does not know, so a gameplay
value there breaks the budget gate outright, and Godot cannot read YAML at runtime regardless.

```gdscript
const TUNING: GameTuning = preload("res://tuning/game_tuning.tres")

func _process(delta: float) -> void:
	_charge -= TUNING.battery_drain_per_second * delta
```

- Typed `@export`s with defaults, `@export_range` wherever a range exists, units in the name:
  `fade_time_seconds`, not `fade_time`.
- Read `TUNING.x` at the point of use. Never copy one into a local `const` — a second source of
  truth, and the local copy wins silently.
- Read-only at runtime. Seed a `var` from it; do not write back through it.

Defining, grouping, splitting per system, mutation: `reference/tuning-resource.md`.

## Things that fail verify

- An autoload's script must **not** declare `class_name X` matching the autoload name. Godot
  rejects it: `Parse Error: Class "X" hides an autoload singleton.` Autoload scripts declare
  `extends Node` and nothing more; the autoload name is already the global identifier.
- Godot 4.4+ writes a `.gd.uid` beside every script. **Commit it**, and make sure the task
  packet's `scope` lists it — otherwise the reviewer correctly flags it as scope creep.
- Tabs, not spaces. Godot's formatter and the parser both assume tabs.
- No `print()` left in committed code; use `print_debug()` behind a flag, or delete it.
- Every `.gd` file must parse under `--check-only`. `verify.sh` checks each one individually.
- A `.tscn` referencing a script or resource that no longer exists fails the import step.

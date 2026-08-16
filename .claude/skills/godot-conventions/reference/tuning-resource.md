# The tuning resource

Loaded on demand from the `godot-conventions` skill. `SKILL.md` states the rule; this file is
how you actually define, load and use it.

Gameplay numbers live in `tuning/game_tuning.tres`. `config/budgets.yaml` is the asset budget
schema and holds none of them — `check-budgets.py` exits 2 on an unknown key, and Godot cannot
read YAML at runtime anyway. This is recorded per game as `DECISIONS.md` D-004.

## The two files

`tuning/game_tuning.gd` declares the shape:

```gdscript
class_name GameTuning
extends Resource
## Gameplay tuning. One instance: tuning/game_tuning.tres.

@export_group("Torch")
@export_range(0.0, 10.0, 0.05) var battery_drain_per_second: float = 1.5
@export_range(0.0, 1.0, 0.01) var battery_low_warning_fraction: float = 0.2

@export_group("Player")
@export_range(0.0, 20.0, 0.1) var move_speed: float = 4.0
@export_range(0.0, 20.0, 0.1) var sprint_speed: float = 7.0
@export var starting_lives: int = 3
```

`tuning/game_tuning.tres` is the instance, and is what the inspector edits:

```
[gd_resource type="Resource" script_class="GameTuning" load_steps=2 format=3]

[ext_resource type="Script" path="res://tuning/game_tuning.gd" id="1_tuning"]

[resource]
script = ExtResource("1_tuning")
battery_drain_per_second = 1.8
move_speed = 4.5
```

Values equal to the export's default are omitted by Godot when it saves. That is correct and
not drift: the default in the `.gd` is the value.

## Declaring values

- **Always a typed `@export` with a default.** An untyped export shows as a bare Variant in the
  inspector and cannot be range-limited.
- **`@export_range` wherever a sane range exists.** It turns the inspector into a slider, which
  is what makes a playtest-to-playtest tweak fast, and it stops a typo'd `50.0` where `5.0` was
  meant.
- **Units in the name**, not in a comment: `battery_drain_per_second`, `fade_time_seconds`,
  `spawn_interval_seconds`. `drain_rate` invites the next reader to guess.
- **`@export_group`** once past roughly eight values. The inspector is the interface here;
  an ungrouped wall of thirty floats is unusable.
- No methods. `GameTuning` is data. A number derived from two others is computed by the system
  that needs it, not cached here.

## Reading it from a script

Preload a const at the top of the consumer:

```gdscript
class_name Torch
extends Node3D

const TUNING: GameTuning = preload("res://tuning/game_tuning.tres")

var _charge := 1.0

func _process(delta: float) -> void:
	_charge -= TUNING.battery_drain_per_second * delta / 100.0
	if _charge <= TUNING.battery_low_warning_fraction:
		battery_low.emit()
```

- `preload`, not `load` — the path is constant, so resolve it at compile time and let a rename
  fail the import rather than the playthrough.
- **Never copy a tuning value into a local `const`.** `const DRAIN := 1.5` beside a
  `TUNING.battery_drain_per_second` is two sources of truth, and the local one wins silently.
- Read through `TUNING.x` at the point of use. Caching it into a `var` in `_ready` freezes the
  value, which defeats editing it while the game runs.

## When a system needs its own tuning

One resource for the whole game is right until it is not. Past roughly forty values, split by
system — `tuning/torch_tuning.tres`, `tuning/enemy_tuning.tres`, each with its own script — and
keep `game_tuning.tres` for values that genuinely span systems. Do not nest tuning resources
inside one another to fake the split; a nested resource is a separate inspector page with none
of the benefit.

## Mutation

Resources are shared by reference. A script that writes to `TUNING.move_speed` changes it for
every consumer, and if the game is running from the editor it can write back to disk. Tuning is
**read-only at runtime**. A value that genuinely changes during play (current speed, remaining
charge) is state and belongs on the node, initialised *from* tuning:

```gdscript
var _speed := TUNING.move_speed     # state, seeded from tuning
```

If a system must hold a modified copy, `TUNING.duplicate()` first.

## Verification

- `verify.sh` imports the project, so a `.tres` pointing at a deleted script or a renamed
  `@export` fails the gate rather than the playtest.
- A removed `@export` silently drops that line from the `.tres` on next save. Check the diff.
- The `.tres` is text and must stay text. Never save tuning as `.res`.

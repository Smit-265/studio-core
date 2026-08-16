# Script structure — the annotated example

Loaded on demand from the `godot-conventions` skill. The declaration order in `SKILL.md` is the
rule; this file is the worked example and the reasoning behind it.

```gdscript
class_name PauseMenu
extends Control
## One-line summary of what this node is responsible for.
##
## A second paragraph only if the responsibility is not obvious from the name.
## Docstrings use `##`, not `#` — only `##` reaches the editor's help panel.

signal resumed

enum State { CLOSED, OPENING, OPEN }

const FADE_TIME := 0.2

@export var start_hidden: bool = true
@export var fade_curve: Curve

var is_open := false           # public state, read by others

var _state: State = State.CLOSED   # private state, nobody else's business

@onready var _panel: Panel = $Panel
@onready var _resume_button: Button = %ResumeButton

func _init() -> void:
	# Runs before the node is in the tree. No $ or % access here — children do
	# not exist yet. Only pure setup belongs in _init.
	pass

func _ready() -> void:
	# Connections live here, in code, so they show up in a diff.
	_resume_button.pressed.connect(_on_resume_button_pressed)
	visible = not start_hidden

func _process(delta: float) -> void:
	pass

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		toggle()
		get_viewport().set_input_as_handled()

func toggle() -> void:
	# Public API next: what other nodes are allowed to call.
	if is_open:
		close()
	else:
		open()

func open() -> void:
	is_open = true
	_set_state(State.OPEN)

func close() -> void:
	is_open = false
	_set_state(State.CLOSED)
	resumed.emit()

func _set_state(next: State) -> void:
	# Private helpers after the public API.
	_state = next
	_panel.visible = _state != State.CLOSED

func _on_resume_button_pressed() -> void:
	# Signal handlers last, named _on_<source>_<signal>.
	close()
```

## Why this order

Reading a script top to bottom should answer questions in the order they get asked: *what is
this* (`class_name`, `extends`, docstring), *what does it tell the world* (signals), *what can
be configured* (constants, `@export`), *what does it hold* (vars), *what does it do* (methods).

- **Signals before everything else** because they are the node's public contract. A reader
  deciding whether to use this node needs them first.
- **`@export` before plain vars** because exports are the inspector-facing surface — the part a
  designer touches without opening the script.
- **`@onready` last among vars** because they depend on the tree existing, which is a different
  lifecycle stage from everything above them.
- **Engine callbacks before public methods** because they are the entry points; the public
  methods exist to be called from them or from outside.
- **Signal handlers last** because they are leaves. Nothing calls them but the engine.

## Common mistakes

- Using `#` where a docstring is meant. Only `##` is picked up as documentation.
- `$Child` access inside `_init`. The tree is not built yet; this returns `null`.
- Declaring `@onready` for a node in a *different* scene. `@onready` resolves a path in this
  scene only; cross-scene references are `@export` or a signal.
- A `var` that is only ever set in `_ready` from an export — collapse it into the export.
- Handlers named `_on_pressed`. The source belongs in the name: two buttons in one scene make
  the shorter form ambiguous immediately.

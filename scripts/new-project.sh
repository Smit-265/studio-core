#!/usr/bin/env bash
# new-project.sh - scaffold a game repo from templates/, wired to studio-core.
#
#     new-project.sh <name> [--parent DIR] [--no-git] [--force]
#
#       <name>        lowercase, digits and dashes. Produces game-<name>/
#       --parent DIR  where to create it. Default: studio-core's parent, so the
#                     ../studio-core sibling convention works with no setup.
#       --no-git      skip git init and the initial commit
#       --force       write into an existing empty directory
#
# One command produces a repo that verify.sh passes: state files, config,
# an empty Godot project, and a CLAUDE.md that points back here.
#
# Exit: 0 created | 2 refused.

set -uo pipefail

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=/dev/null
. "$SELF_DIR/_resolve.sh"

NAME=""
PARENT=""
DO_GIT=1
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --parent) PARENT="${2:-}"; shift ;;
    --no-git) DO_GIT=0 ;;
    --force)  FORCE=1 ;;
    -h|--help) sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) sc_die "unknown option $1 (see --help)" ;;
    *)  [ -n "$NAME" ] && sc_die "more than one name given"; NAME="$1" ;;
  esac
  shift
done

[ -n "$NAME" ] || sc_die "usage: new-project.sh <name> [--parent DIR] [--no-git] [--force]"

# Directory name becomes a git remote and a Godot project name; keep it boring.
printf '%s' "$NAME" | grep -Eq '^[a-z0-9][a-z0-9-]*$' \
  || sc_die "name must be lowercase letters, digits and dashes, starting alphanumeric.
       Got: '$NAME'"

TEMPLATES="$STUDIO_CORE/templates"
[ -d "$TEMPLATES" ] || sc_die "no templates/ in $STUDIO_CORE"

[ -n "$PARENT" ] || PARENT=$(dirname "$STUDIO_CORE")
PARENT=$(sc_abspath "$PARENT") || sc_die "parent directory does not exist: $PARENT"
TARGET="$PARENT/game-$NAME"

if [ -e "$TARGET" ]; then
  [ -d "$TARGET" ] || sc_die "$TARGET exists and is not a directory"
  if [ "$FORCE" -eq 0 ]; then
    sc_die "$TARGET already exists. Use --force to write into it (it must be empty)."
  fi
  if [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
    sc_die "$TARGET is not empty. Refusing to overwrite an existing project."
  fi
fi

TODAY=$(date +%Y-%m-%d)

# STUDIO_CORE_PATH is recorded for humans; resolution at runtime is
# $STUDIO_CORE then ../studio-core. See DECISIONS.md D-001.
if [ "$(dirname "$STUDIO_CORE")" = "$PARENT" ]; then
  SC_PATH_NOTE="../studio-core (sibling)"
else
  SC_PATH_NOTE="$STUDIO_CORE"
fi

# Substitute only the three scaffold placeholders. Every other {{...}} in the
# templates is a prompt for the human and must survive.
# The game's CI checks studio-core out by name, so derive owner/repo from this
# checkout's origin. Left as a placeholder when there is no remote yet - a
# workflow that names a repo nobody can resolve should say so, not guess.
SC_REPO=$(git -C "$STUDIO_CORE" remote get-url origin 2>/dev/null \
  | sed -e 's|^git@[^:]*:||' -e 's|^https\{0,1\}://[^/]*/||' -e 's|\.git$||')
[ -n "$SC_REPO" ] || SC_REPO="<owner>/studio-core"

fill() {
  sed -e "s|{{GAME_NAME}}|game-$NAME|g" \
      -e "s|{{DATE}}|$TODAY|g" \
      -e "s|{{STUDIO_CORE_PATH}}|$SC_PATH_NOTE|g" \
      -e "s|{{STUDIO_CORE_REPO}}|$SC_REPO|g" \
      "$1" > "$2"
}

sc_section "scaffolding game-$NAME"

mkdir -p "$TARGET/assets" "$TARGET/config" "$TARGET/scenes" "$TARGET/scripts" "$TARGET/tests" \
  "$TARGET/tuning" "$TARGET/.github/workflows" || sc_die "could not create $TARGET"

fill "$TEMPLATES/game-CLAUDE.md"  "$TARGET/CLAUDE.md"
fill "$TEMPLATES/GAME_PLAN.md"    "$TARGET/GAME_PLAN.md"
fill "$TEMPLATES/PROGRESS.md"     "$TARGET/PROGRESS.md"
fill "$TEMPLATES/DECISIONS.md"    "$TARGET/DECISIONS.md"
fill "$TEMPLATES/assets.yaml"     "$TARGET/assets.yaml"
fill "$TEMPLATES/budgets.yaml"    "$TARGET/config/budgets.yaml"
fill "$TEMPLATES/game-verify.yml"  "$TARGET/.github/workflows/verify.yml"
sc_ok "state files, CLAUDE.md, config/budgets.yaml, CI workflow"
if [ "$SC_REPO" = "<owner>/studio-core" ]; then
  sc_warn "studio-core has no origin remote - .github/workflows/verify.yml names"
  sc_info "<owner>/studio-core as a placeholder. Fill it in before pushing."
fi

# Keep otherwise-empty scaffold directories in git.
for d in assets scenes scripts tests; do : > "$TARGET/$d/.gitkeep"; done

cat > "$TARGET/.env.example" <<EOF
# Copy to .env and adjust, or export these in your shell.
#
# studio-core is resolved as: \$STUDIO_CORE, then ../studio-core, then failure.
# Leave STUDIO_CORE unset if this repo sits beside studio-core, which is how
# new-project.sh scaffolds it. See DECISIONS.md D-001.
STUDIO_CORE=$STUDIO_CORE

# Optional: path to the Godot 4.x executable, if it is not on PATH as \`godot\`.
#GODOT_BIN=
EOF
sc_ok ".env.example"

cat > "$TARGET/.gitignore" <<'EOF'
# Godot
.godot/
.import/
export_presets.cfg
*.translation

# builds
build/
export/
dist/

# local environment
.env
.studio/
EOF

cp "$STUDIO_CORE/.gitattributes" "$TARGET/.gitattributes" 2>/dev/null || true

# Minimal, empty Godot project. Not game content - without it the engine has
# nothing to import and verify.sh can only ever skip its main step.
cat > "$TARGET/project.godot" <<EOF
; Engine configuration for game-$NAME. Scaffolded by studio-core/new-project.sh.
; Set config/features to the Godot version this project targets.

config_version=5

[application]

config/name="game-$NAME"
config/features=PackedStringArray("4.3")

[rendering]

renderer/rendering_method="forward_plus"
EOF
sc_ok "project.godot, .gitignore, .gitattributes"

# Gameplay tuning. Scaffolded empty and deliberately: without a defined home,
# gameplay numbers end up in config/budgets.yaml, which is the asset-budget
# schema - check-budgets.py rejects keys it does not know, and Godot cannot read
# YAML at runtime regardless. See DECISIONS.md D-004.
#
# The comments live in the .gd, not the .tres: Godot rewrites a .tres whenever
# the resource is saved from the editor and does not preserve comments in it.
cat > "$TARGET/tuning/game_tuning.gd" <<EOF
class_name GameTuning
extends Resource
## Gameplay tuning for game-$NAME. One instance: tuning/game_tuning.tres.
##
## Gameplay numbers live here - drain rates, speeds, damage, timers, spawn
## counts, thresholds. NOT in config/budgets.yaml, which is the asset budget
## schema (triangles, texture dimensions, file sizes) and nothing else.
##
## The point of a Resource is that tuning/game_tuning.tres opens in the
## inspector and is editable between playtests with no rebuild. A value that
## needs a code change to adjust is not tunable, so put it here rather than
## writing a const in the script that consumes it.
##
## Adding a value: declare an @export below, then open the .tres and set it.
## Read it from a script with a preloaded const - see the godot-conventions
## skill, reference/tuning-resource.md.

# No values yet. Delete this block as real ones arrive. Examples of the shape:
#
# @export_range(0.0, 10.0) var battery_drain_per_second: float = 1.5
# @export_range(0.0, 20.0) var player_move_speed: float = 4.0
# @export var starting_lives: int = 3
EOF

cat > "$TARGET/tuning/game_tuning.tres" <<'EOF'
[gd_resource type="Resource" script_class="GameTuning" load_steps=2 format=3]

[ext_resource type="Script" path="res://tuning/game_tuning.gd" id="1_tuning"]

[resource]
script = ExtResource("1_tuning")
EOF
sc_ok "tuning/game_tuning.gd, tuning/game_tuning.tres (gameplay values go here)"

sc_require_python
$SC_PYTHON "$SC_SCRIPTS/gen-manifest.py" "$TARGET" --name "game-$NAME" >/dev/null \
  && sc_ok "ASSET_MANIFEST.md generated from assets.yaml"

# Loaders, not copies: each file points back at the definition in studio-core so
# the harness stays single-sourced, while agents still run rooted in this repo.
# See DECISIONS.md D-003.
$SC_PYTHON "$SC_SCRIPTS/check-loaders.py" "$TARGET" --write >/dev/null \
  && sc_ok ".claude/ loaders generated from studio-core"

if [ "$DO_GIT" -eq 1 ] && sc_have git; then
  (
    cd "$TARGET" || exit 1
    git init -q -b main >/dev/null 2>&1 || git init -q >/dev/null 2>&1
    git add -A >/dev/null 2>&1
    if git -c advice.detachedHead=false commit -q -m "chore: scaffold game-$NAME from studio-core" >/dev/null 2>&1; then
      exit 0
    fi
    exit 3
  )
  case $? in
    0) sc_ok "git repo initialised with an initial commit" ;;
    3) sc_warn "git repo initialised but the commit failed - set user.name and user.email, then commit" ;;
    *) sc_warn "git init failed; the files are all there, version them yourself" ;;
  esac
elif [ "$DO_GIT" -eq 1 ]; then
  sc_warn "git not found on PATH - skipping repo init"
fi

sc_section "next"
cat <<EOF
  $TARGET

  next step:  cd "$TARGET" && run /design-game

  GAME_PLAN.md is scaffolded with its sections present and empty. /design-game
  fills them in with you, one section at a time - pitch, core loop, art
  direction, world structure, scope, non-goals. Then:

  1. /design-milestone      - work out the first vertical slice
  2. /plan-milestone        - decompose it into task packets
  3. /next-task             - execute one packet at a time
  4. Verify any time:       $STUDIO_CORE/scripts/verify.sh "$TARGET"

  DECISIONS.md already carries D-001 to D-003. Add approved tools and asset
  sources there before the asset-pipeline needs them.

  studio-core resolves as $SC_PATH_NOTE from this repo.
EOF

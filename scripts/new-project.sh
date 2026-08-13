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
fill() {
  sed -e "s|{{GAME_NAME}}|game-$NAME|g" \
      -e "s|{{DATE}}|$TODAY|g" \
      -e "s|{{STUDIO_CORE_PATH}}|$SC_PATH_NOTE|g" \
      "$1" > "$2"
}

sc_section "scaffolding game-$NAME"

mkdir -p "$TARGET/assets" "$TARGET/config" "$TARGET/scenes" "$TARGET/scripts" "$TARGET/tests" \
  || sc_die "could not create $TARGET"

fill "$TEMPLATES/game-CLAUDE.md"  "$TARGET/CLAUDE.md"
fill "$TEMPLATES/GAME_PLAN.md"    "$TARGET/GAME_PLAN.md"
fill "$TEMPLATES/PROGRESS.md"     "$TARGET/PROGRESS.md"
fill "$TEMPLATES/DECISIONS.md"    "$TARGET/DECISIONS.md"
fill "$TEMPLATES/assets.yaml"     "$TARGET/assets.yaml"
fill "$TEMPLATES/budgets.yaml"    "$TARGET/config/budgets.yaml"
sc_ok "state files, CLAUDE.md, config/budgets.yaml"

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

  1. Fill in GAME_PLAN.md   - vision, scope, milestones, non-goals
  2. Fill in DECISIONS.md   - engine version, approved tools and asset sources
                              (D-001 is already recorded for you)
  3. Verify the scaffold:   $STUDIO_CORE/scripts/verify.sh "$TARGET"
  4. Plan the first milestone, then work one task at a time.

  studio-core resolves as $SC_PATH_NOTE from this repo.
EOF

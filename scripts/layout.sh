#!/usr/bin/env bash
# layout.sh - the project's shape, cheaply, for the planner.
#
#     layout.sh [project-path] [--depth N]     default: cwd, depth 2
#
# Prints directories under scenes/ scripts/ tests/ tuning/ assets/ to the given
# depth with a file count per directory, then the top-level files. No file
# contents, no full listing - the planner needs real path names to write an
# enumerable `scope`, not the code. Roughly 30-60 lines for a mid-sized game.
#
# Exit: 0 | 2 project path wrong.

set -uo pipefail

PROJECT_ARG=""
DEPTH=2
while [ $# -gt 0 ]; do
  case "$1" in
    --depth) DEPTH="${2:-2}"; shift ;;
    -h|--help) sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) printf 'error: unknown option %s\n' "$1" >&2; exit 2 ;;
    *) PROJECT_ARG="$1" ;;
  esac
  shift
done

PROJECT="${PROJECT_ARG:-$PWD}"
[ -d "$PROJECT" ] || { printf 'error: project path does not exist: %s\n' "$PROJECT" >&2; exit 2; }
cd "$PROJECT" || exit 2

printf 'layout  %s\n' "$PWD"

for top in scenes scripts tests tuning assets addons; do
  [ -d "$top" ] || continue
  # Directories to DEPTH, each with its own direct file count.
  find "$top" -mindepth 0 -maxdepth "$DEPTH" -type d -not -path '*/.git*' 2>/dev/null | sort \
    | while IFS= read -r d; do
        n=$(find "$d" -mindepth 1 -maxdepth 1 -type f -not -name '.gitkeep' 2>/dev/null | wc -l | tr -d ' ')
        deeper=$(find "$d" -mindepth "$((DEPTH + 1))" -type f 2>/dev/null | head -1)
        case "$d" in
          */*) indent="  ${d//[^\/]/}"; indent="${indent//\//  }"; name="${d##*/}" ;;
          *)   indent="  "; name="$d" ;;
        esac
        if [ -n "$deeper" ] && [ "$(printf '%s' "$d" | tr -cd '/' | wc -c)" -ge "$((DEPTH - 1))" ]; then
          printf '%s%s/  (%s files, more below)\n' "$indent" "$name" "$n"
        else
          printf '%s%s/  (%s files)\n' "$indent" "$name" "$n"
        fi
      done
done

printf '\nroot files:\n'
find . -maxdepth 1 -type f -not -name '.*' 2>/dev/null | sed 's|^\./||' | sort | sed 's/^/  /'

# The names a scope list most often needs: scripts and scenes, by name only.
if [ -d scripts ] || [ -d scenes ]; then
  printf '\nscripts and scenes:\n'
  find scripts scenes -type f \( -name '*.gd' -o -name '*.tscn' \) 2>/dev/null | sort | sed 's/^/  /'
fi

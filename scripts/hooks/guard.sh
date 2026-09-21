#!/usr/bin/env bash
# guard.sh - Claude Code hook entry point. Resolves studio-core and python,
# then runs guard.py <subcommand> with the hook JSON still on stdin.
#
# Wired by the game repo's .claude/settings.json (see templates/game-settings.json).
# Never blocks on a missing interpreter: a hook that cannot run allows, and
# says so on stderr, rather than wedging the session.
#
# Exit: 0 allow | 2 block (reason on stderr).

set -uo pipefail

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [ "${STUDIO_GUARD:-}" = "off" ]; then exit 0; fi

# Resolve python without sourcing _resolve.sh, which would exit the hook on a
# resolution failure. The guard lives beside _sclib.py, so studio-core is
# already found; only an interpreter is needed.
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1; then
    if [ "$c" = "py" ]; then PY="py -3"; else PY="$c"; fi
    if $PY -c 'import sys, yaml; sys.exit(0 if sys.version_info[0]==3 else 1)' >/dev/null 2>&1; then
      # shellcheck disable=SC2086
      exec $PY "$SELF_DIR/guard.py" "$@"
    fi
  fi
done

printf 'guard.sh: python 3 with PyYAML not found - hook allowed, rules unenforced\n' >&2
exit 0

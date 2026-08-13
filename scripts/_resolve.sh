#!/usr/bin/env bash
# _resolve.sh - locate studio-core and provide shared helpers.
#
# SOURCED, not executed, by every other script in this directory:
#
#     . "$(dirname "${BASH_SOURCE[0]}")/_resolve.sh"
#
# Running it directly prints the resolved path, which is the quickest way to
# debug a "cannot find studio-core" failure.
#
# RESOLUTION ORDER (see DECISIONS.md D-001 in any game repo):
#   1. $STUDIO_CORE            - escape hatch for non-standard layouts
#   2. ../studio-core          - sibling-directory convention, relative to the
#                                project directory (see SC_PROJECT_HINT below)
#   3. the directory containing this script - only reachable when a script is
#      invoked from inside studio-core itself, since sourcing this file means
#      studio-core was already located. Present so studio-core's own CI can run
#      verify.sh with no game repo and no environment set up.
#   4. fail, naming 1 and 2.
#
# A candidate only counts if it carries studio-core's markers, so a stray
# directory named studio-core cannot be silently selected.
#
# No script hardcodes a path or assumes cwd. Exports:
#   STUDIO_CORE      absolute path to studio-core
#   SC_SCRIPTS       $STUDIO_CORE/scripts
#   SC_PYTHON        a working python 3 interpreter
# and the sc_* helper functions below.

# Not `set -e` here: this file is sourced, and killing the caller's shell on a
# non-zero test is not the contract. Callers set their own options.

# --- output helpers --------------------------------------------------------

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  SC_RED=$'\033[31m'; SC_GRN=$'\033[32m'; SC_YEL=$'\033[33m'
  SC_DIM=$'\033[2m';  SC_BLD=$'\033[1m';  SC_OFF=$'\033[0m'
else
  SC_RED=''; SC_GRN=''; SC_YEL=''; SC_DIM=''; SC_BLD=''; SC_OFF=''
fi

sc_section() { printf '\n%s==>%s %s%s%s\n' "$SC_BLD" "$SC_OFF" "$SC_BLD" "$*" "$SC_OFF"; }
sc_ok()      { printf '  %sPASS%s  %s\n' "$SC_GRN" "$SC_OFF" "$*"; }
sc_skip()    { printf '  %sSKIP%s  %s\n' "$SC_DIM" "$SC_OFF" "$*"; }
sc_warn()    { printf '  %sWARN%s  %s\n' "$SC_YEL" "$SC_OFF" "$*" >&2; }
sc_fail()    { printf '  %sFAIL%s  %s\n' "$SC_RED" "$SC_OFF" "$*" >&2; }
sc_info()    { printf '        %s\n' "$*"; }
sc_die()     { printf '\n%serror:%s %s\n' "$SC_RED" "$SC_OFF" "$*" >&2; exit "${2:-2}"; }

sc_have() { command -v "$1" >/dev/null 2>&1; }

# Absolute path without requiring realpath (absent on some minimal images).
sc_abspath() {
  local p="$1"
  if [ -d "$p" ]; then
    (cd "$p" 2>/dev/null && pwd)
  else
    local d b
    d=$(dirname "$p"); b=$(basename "$p")
    d=$(cd "$d" 2>/dev/null && pwd) || return 1
    printf '%s/%s\n' "$d" "$b"
  fi
}

# --- studio-core resolution ------------------------------------------------

# Markers that identify a real studio-core checkout.
sc_is_studio_core() {
  [ -n "$1" ] && [ -d "$1" ] \
    && [ -f "$1/CLAUDE.md" ] \
    && [ -f "$1/config/budgets.yaml" ] \
    && [ -f "$1/scripts/_resolve.sh" ]
}

# SC_PROJECT_HINT lets a caller anchor the sibling lookup at the project it is
# operating on rather than at cwd. verify.sh sets it from its path argument.
sc_resolve_studio_core() {
  local anchor="${SC_PROJECT_HINT:-$PWD}" cand
  anchor=$(sc_abspath "$anchor" 2>/dev/null || printf '%s' "$PWD")

  # 1. environment override
  if [ -n "${STUDIO_CORE:-}" ]; then
    cand=$(sc_abspath "$STUDIO_CORE" 2>/dev/null || printf '%s' "$STUDIO_CORE")
    if sc_is_studio_core "$cand"; then
      STUDIO_CORE="$cand"; export STUDIO_CORE; return 0
    fi
    sc_die "\$STUDIO_CORE is set to '$STUDIO_CORE' but that is not a studio-core
       checkout (expected CLAUDE.md, config/budgets.yaml and scripts/_resolve.sh
       beneath it). Fix the variable or unset it to fall back to ../studio-core."
  fi

  # 2. sibling-directory convention
  cand=$(sc_abspath "$anchor/../studio-core" 2>/dev/null || true)
  if sc_is_studio_core "$cand"; then
    STUDIO_CORE="$cand"; export STUDIO_CORE; return 0
  fi

  # 3. this script's own repo (studio-core running against itself)
  cand=$(sc_abspath "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null || true)
  if sc_is_studio_core "$cand"; then
    STUDIO_CORE="$cand"; export STUDIO_CORE; return 0
  fi

  sc_die "cannot locate studio-core. Tried, in order:
         1. \$STUDIO_CORE            (not set)
         2. $anchor/../studio-core   (not a studio-core checkout)
       Set STUDIO_CORE to the checkout path, or place this repo as a sibling of
       studio-core. See .env.example, and DECISIONS.md D-001 for the rationale."
}

sc_resolve_studio_core
SC_SCRIPTS="$STUDIO_CORE/scripts"
export SC_SCRIPTS

# --- python ----------------------------------------------------------------

# Order matters: python3 first, then python (Windows/git-bash), then the py
# launcher. Verified to be Python 3 before being accepted.
sc_find_python() {
  local c
  for c in python3 python py; do
    sc_have "$c" || continue
    if [ "$c" = "py" ]; then
      if py -3 -c 'import sys; sys.exit(0 if sys.version_info[0]==3 else 1)' >/dev/null 2>&1; then
        printf 'py -3\n'; return 0
      fi
    elif "$c" -c 'import sys; sys.exit(0 if sys.version_info[0]==3 else 1)' >/dev/null 2>&1; then
      printf '%s\n' "$c"; return 0
    fi
  done
  return 1
}

SC_PYTHON=$(sc_find_python || true)
export SC_PYTHON

sc_require_python() {
  [ -n "$SC_PYTHON" ] || sc_die "python 3 not found on PATH (looked for python3, python, py -3).
       check-budgets.py, check-licences.py and gen-manifest.py all need it."
  # shellcheck disable=SC2086
  $SC_PYTHON -c 'import yaml' >/dev/null 2>&1 || sc_die "python 3 found ($SC_PYTHON) but PyYAML is not installed.
       Install it with:  $SC_PYTHON -m pip install pyyaml"
}

# --- project resolution ----------------------------------------------------

# A "project" is a game repo. Godot presence is checked separately: a repo with
# state files but no project.godot is a valid, if empty, scaffold.
sc_resolve_project() {
  local p="${1:-$PWD}"
  [ -d "$p" ] || sc_die "project path does not exist: $p"
  sc_abspath "$p"
}

sc_has_godot_project() { [ -f "$1/project.godot" ]; }

# --- direct invocation -----------------------------------------------------

# BASH_SOURCE[0] == $0 only when this file was executed rather than sourced.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  printf 'STUDIO_CORE = %s\n' "$STUDIO_CORE"
  printf 'SC_SCRIPTS  = %s\n' "$SC_SCRIPTS"
  printf 'SC_PYTHON   = %s\n' "${SC_PYTHON:-<not found>}"
fi

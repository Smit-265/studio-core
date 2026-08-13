#!/usr/bin/env bash
# verify.sh - the verification gate. Nothing is "done" until this exits 0.
#
#     verify.sh [project-path]        default: cwd
#       --strict      missing Godot or a missing test runner becomes a failure
#                     rather than a skip. CI uses this; a laptop usually does not.
#       --no-engine   skip every Godot step (fast asset-only pass)
#       --quiet       less chatter, same exit code
#
# Runs, in order: engine import, GDScript parse, unit tests, manifest freshness,
# licences, budgets. Roughly 90% of verification lives here rather than in an
# agent, because a script that costs nothing can run on every commit.
#
# Exit: 0 all checks passed | 1 one or more checks failed | 2 could not run.

set -uo pipefail

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

PROJECT_ARG=""
STRICT=0
NO_ENGINE=0
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --strict)    STRICT=1 ;;
    --no-engine) NO_ENGINE=1 ;;
    --quiet)     QUIET=1 ;;
    -h|--help)   sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)          printf 'error: unknown option %s (see --help)\n' "$1" >&2; exit 2 ;;
    *)           [ -n "$PROJECT_ARG" ] && { printf 'error: more than one project path given\n' >&2; exit 2; }
                 PROJECT_ARG="$1" ;;
  esac
  shift
done

# Anchor studio-core resolution at the project being verified, not at cwd.
SC_PROJECT_HINT="${PROJECT_ARG:-$PWD}"
export SC_PROJECT_HINT
# shellcheck source=/dev/null
. "$SELF_DIR/_resolve.sh"

PROJECT=$(sc_resolve_project "${PROJECT_ARG:-$PWD}") || exit 2

FAILURES=0
SKIPS=0
step_failed() { FAILURES=$((FAILURES + 1)); }
step_skipped() { SKIPS=$((SKIPS + 1)); }

# Under --strict a skip is a failure: CI must not quietly verify nothing.
soft_skip() {
  if [ "$STRICT" -eq 1 ]; then
    sc_fail "$1"
    sc_info "(--strict: skips are failures)"
    step_failed
  else
    sc_skip "$1"
    step_skipped
  fi
}

[ "$QUIET" -eq 1 ] || {
  printf '%sverify%s  project: %s\n' "$SC_BLD" "$SC_OFF" "$PROJECT"
  printf '        studio-core: %s\n' "$STUDIO_CORE"
}

# ---------------------------------------------------------------------------
# 0. state files
# ---------------------------------------------------------------------------
sc_section "state files"
missing_state=""
for f in GAME_PLAN.md PROGRESS.md DECISIONS.md assets.yaml; do
  [ -f "$PROJECT/$f" ] || missing_state="$missing_state $f"
done
if [ -n "$missing_state" ]; then
  sc_warn "missing:$missing_state"
  sc_info "scaffold them from studio-core/templates/, or run new-project.sh"
else
  sc_ok "all four present"
fi

# ---------------------------------------------------------------------------
# 1. engine - import and parse
# ---------------------------------------------------------------------------
sc_section "engine"

GODOT=""
if [ "$NO_ENGINE" -eq 1 ]; then
  sc_skip "engine checks disabled (--no-engine)"
elif ! sc_has_godot_project "$PROJECT"; then
  sc_skip "no project.godot in $PROJECT - nothing for the engine to import"
  sc_info "this is expected for a freshly scaffolded repo"
  NO_ENGINE=1
else
  for cand in "${GODOT_BIN:-}" godot godot4 Godot; do
    [ -n "$cand" ] || continue
    if sc_have "$cand"; then GODOT="$cand"; break; fi
  done
  if [ -z "$GODOT" ]; then
    soft_skip "Godot not found on PATH (looked for \$GODOT_BIN, godot, godot4, Godot)"
    sc_info "install Godot 4.x, or set GODOT_BIN to the executable"
    NO_ENGINE=1
  else
    sc_info "using $($GODOT --version 2>/dev/null | head -1 || echo "$GODOT")"
  fi
fi

if [ "$NO_ENGINE" -eq 0 ]; then
  import_log=$(mktemp)
  # --import exists on 4.2+; older builds do a full import on --quit instead.
  if ! "$GODOT" --headless --path "$PROJECT" --import >"$import_log" 2>&1; then
    "$GODOT" --headless --path "$PROJECT" --quit >"$import_log" 2>&1 || true
  fi
  if grep -Eq 'SCRIPT ERROR|Parse Error|Failed to load|ERROR: Condition' "$import_log"; then
    sc_fail "import reported errors"
    grep -E 'SCRIPT ERROR|Parse Error|Failed to load|ERROR: Condition' "$import_log" | head -20 | sed 's/^/        /'
    step_failed
  else
    sc_ok "project imports cleanly"
  fi
  rm -f "$import_log"

  # Per-file parse. The import pass catches most of this, but --check-only is
  # the unambiguous signal and it is what makes a deliberate syntax error fail.
  parse_failed=0
  gd_count=0
  while IFS= read -r gd; do
    gd_count=$((gd_count + 1))
    rel=${gd#"$PROJECT/"}
    out=$("$GODOT" --headless --path "$PROJECT" --check-only --script "res://$rel" 2>&1)
    status=$?
    if [ $status -ne 0 ] || printf '%s' "$out" | grep -Eq 'Parse Error|SCRIPT ERROR'; then
      sc_fail "$rel"
      printf '%s\n' "$out" | grep -E 'Parse Error|SCRIPT ERROR|error' | head -5 | sed 's/^/        /'
      parse_failed=$((parse_failed + 1))
    fi
  done < <(find "$PROJECT" -name '*.gd' -not -path '*/.git/*' -not -path '*/addons/*' 2>/dev/null)

  if [ "$gd_count" -eq 0 ]; then
    sc_skip "no .gd files outside addons/"
  elif [ "$parse_failed" -gt 0 ]; then
    sc_info "$parse_failed of $gd_count script(s) failed to parse"
    step_failed
  else
    sc_ok "$gd_count script(s) parse"
  fi
fi

# ---------------------------------------------------------------------------
# 2. tests
# ---------------------------------------------------------------------------
sc_section "tests"
if [ "$NO_ENGINE" -eq 1 ]; then
  sc_skip "engine unavailable - cannot run engine tests"
elif [ -f "$PROJECT/addons/gut/gut_cmdln.gd" ]; then
  if "$GODOT" --headless --path "$PROJECT" -s addons/gut/gut_cmdln.gd -gdir=res://tests -gexit; then
    sc_ok "GUT suite passed"
  else
    sc_fail "GUT suite failed"; step_failed
  fi
elif [ -f "$PROJECT/addons/gdUnit4/runtest.sh" ]; then
  if (cd "$PROJECT" && ./addons/gdUnit4/runtest.sh --add tests --continue); then
    sc_ok "gdUnit4 suite passed"
  else
    sc_fail "gdUnit4 suite failed"; step_failed
  fi
else
  soft_skip "no test framework installed (looked for addons/gut, addons/gdUnit4)"
fi

# ---------------------------------------------------------------------------
# 3. manifest freshness, licences, budgets
# ---------------------------------------------------------------------------
sc_require_python

sc_section "loaders"
$SC_PYTHON "$SC_SCRIPTS/check-loaders.py" "$PROJECT" || step_failed

sc_section "manifest"
if [ -f "$PROJECT/assets.yaml" ]; then
  if $SC_PYTHON "$SC_SCRIPTS/gen-manifest.py" "$PROJECT" --check; then
    :
  else
    step_failed
  fi
else
  sc_skip "no assets.yaml"
fi

sc_section "licences"
$SC_PYTHON "$SC_SCRIPTS/check-licences.py" "$PROJECT" || step_failed

sc_section "budgets"
$SC_PYTHON "$SC_SCRIPTS/check-budgets.py" "$PROJECT" || step_failed

# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------
printf '\n'
if [ "$FAILURES" -eq 0 ]; then
  printf '%sverify: PASS%s' "$SC_GRN" "$SC_OFF"
  [ "$SKIPS" -gt 0 ] && printf ' %s(%d step(s) skipped)%s' "$SC_DIM" "$SKIPS" "$SC_OFF"
  printf '\n'
  exit 0
fi
printf '%sverify: FAIL%s - %d check(s) failed\n' "$SC_RED" "$SC_OFF" "$FAILURES"
printf 'Two-strike rule: at most two fix attempts, then stop and report.\n'
exit 1

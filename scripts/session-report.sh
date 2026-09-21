#!/usr/bin/env bash
# session-report.sh - what changed since last session, cheaply.
#
#     session-report.sh [project-path] [--since REF] [--mark] [--full]
#
#       --since REF   git ref or date to report from. Default: the marker
#                     recorded by the last --mark, else the last 7 days.
#       --mark        record HEAD as the session boundary and exit. Run this at
#                     session end, BEFORE the final commit, so the line it
#                     writes into PROGRESS.md is committed with the rest.
#       --full        include per-file churn, not just the summary
#
# Exists so a new session can reconstruct state by reading, not by re-reading
# the codebase. Output is deliberately compact: it is going into a context
# window that costs money.
#
# The marker is the `**Session boundary:**` line in PROGRESS.md, so it is
# committed and both machines of a two-person studio see the same window.
# .studio/last-session is kept as a local fallback for a PROGRESS.md that
# predates the line.
#
# Exit: 0 always, unless the project path is wrong (2).

set -uo pipefail

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

PROJECT_ARG=""
SINCE=""
MARK=0
FULL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="${2:-}"; shift ;;
    --mark)  MARK=1 ;;
    --full)  FULL=1 ;;
    -h|--help) sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) printf 'error: unknown option %s (see --help)\n' "$1" >&2; exit 2 ;;
    *)  PROJECT_ARG="$1" ;;
  esac
  shift
done

SC_PROJECT_HINT="${PROJECT_ARG:-$PWD}"
export SC_PROJECT_HINT
# shellcheck source=/dev/null
. "$SELF_DIR/_resolve.sh"

PROJECT=$(sc_resolve_project "${PROJECT_ARG:-$PWD}") || exit 2
cd "$PROJECT" || exit 2

sc_have git || sc_die "git not found on PATH"
git rev-parse --git-dir >/dev/null 2>&1 || sc_die "$PROJECT is not a git repository.
       Run 'git init' - the reviewer agent reads diffs, so history is a hard dependency."

MARKER_DIR="$PROJECT/.studio"
MARKER="$MARKER_DIR/last-session"

# Write or replace the boundary line in PROGRESS.md. Placed after **Harness:**
# (or **Last updated:**) so the header block stays the one place a resuming
# session looks. Returns 1 when neither anchor exists.
sc_mark_progress() {
  local f="$1" sha="$2" line tmp
  line="**Session boundary:** \`$sha\` · marked $(date +%Y-%m-%d) by \`session-report.sh --mark\`"
  tmp=$(mktemp) || return 1
  if grep -q '^\*\*Session boundary:\*\*' "$f"; then
    MARKLINE="$line" awk '/^\*\*Session boundary:\*\*/ && !d { print ENVIRON["MARKLINE"]; d=1; next } { print }' "$f" > "$tmp"
  elif grep -q '^\*\*Harness:\*\*' "$f"; then
    MARKLINE="$line" awk '{ print } /^\*\*Harness:\*\*/ && !d { print ENVIRON["MARKLINE"]; d=1 }' "$f" > "$tmp"
  elif grep -q '^\*\*Last updated:\*\*' "$f"; then
    MARKLINE="$line" awk '{ print } /^\*\*Last updated:\*\*/ && !d { print ENVIRON["MARKLINE"]; d=1 }' "$f" > "$tmp"
  else
    rm -f "$tmp"; return 1
  fi
  cat "$tmp" > "$f" && rm -f "$tmp"
}

if [ "$MARK" -eq 1 ]; then
  HEAD_SHA=$(git rev-parse HEAD 2>/dev/null) || sc_die "no commits yet - nothing to mark"
  mkdir -p "$MARKER_DIR"
  printf '%s\n' "$HEAD_SHA" > "$MARKER"
  if [ -f "$PROJECT/PROGRESS.md" ] && sc_mark_progress "$PROJECT/PROGRESS.md" "$HEAD_SHA"; then
    printf 'session marked at %s - boundary line written to PROGRESS.md; commit it\n' \
      "$(git log -1 --format='%h %s')"
  else
    sc_warn "PROGRESS.md has no header line to anchor on - marker kept locally only"
    printf 'session marked at %s\n' "$(git log -1 --format='%h %s')"
  fi
  exit 0
fi

# Resolve the reporting window: PROGRESS.md line first, local file second.
candidate=""
if [ -z "$SINCE" ]; then
  candidate=$(sed -n 's/^\*\*Session boundary:\*\* *`\([0-9a-f]\{7,40\}\)`.*/\1/p' "$PROJECT/PROGRESS.md" 2>/dev/null | head -1)
  [ -n "$candidate" ] || { [ -f "$MARKER" ] && candidate=$(tr -d '[:space:]' < "$MARKER"); }
fi
if [ -z "$SINCE" ] && [ -n "$candidate" ]; then
  if git cat-file -e "$candidate^{commit}" 2>/dev/null; then
    SINCE="$candidate"
    WINDOW="since last marked session ($(git rev-parse --short "$SINCE"))"
  else
    sc_warn "marker $candidate is not a commit in this repo - falling back to 7 days"
  fi
fi
if [ -z "$SINCE" ]; then
  RANGE_ARGS=(--since=7.days)
  WINDOW="last 7 days (no session marker - run --mark at session end)"
else
  RANGE_ARGS=("$SINCE..HEAD")
  WINDOW="${WINDOW:-since $SINCE}"
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '(none)')
DIRTY=$(git status --porcelain | wc -l | tr -d ' ')

printf '%ssession report%s  %s\n' "$SC_BLD" "$SC_OFF" "$PROJECT"
printf '  branch %s | %s uncommitted change(s) | %s\n' "$BRANCH" "$DIRTY" "$WINDOW"

# Which harness this repo last verified against. Games track studio-core's head
# rather than pinning it (D-001), so the harness moves underneath a game between
# sessions and a resuming session cannot assume it is the one the last session
# used. verify.sh stamps PROGRESS.md; this reads that stamp back and says so
# when studio-core has moved since.
RECORDED=$(sed -n 's/^\*\*Harness:\*\* *//p' "$PROJECT/PROGRESS.md" 2>/dev/null | head -1)
SC_VERSION=$(tr -d '[:space:]' < "$STUDIO_CORE/VERSION" 2>/dev/null)
[ -n "$SC_VERSION" ] || SC_VERSION="unknown"
SC_SHA=$(git -C "$STUDIO_CORE" rev-parse --short HEAD 2>/dev/null)
[ -n "$SC_SHA" ] || SC_SHA="unknown"
NOW="studio-core $SC_VERSION ($SC_SHA)"

printf '  harness now: %s\n' "$NOW"
case "$RECORDED" in
  "")        printf '  %slast verified against: never recorded - run verify.sh%s\n' \
               "$SC_DIM" "$SC_OFF" ;;
  "$NOW"*)   printf '  %slast verified against: same%s\n' "$SC_DIM" "$SC_OFF" ;;
  *not\ yet\ recorded*)
             printf '  %slast verified against: never recorded - run verify.sh%s\n' \
               "$SC_DIM" "$SC_OFF" ;;
  *)         printf '  %s! last verified against: %s%s\n' "$SC_YEL" "$RECORDED" "$SC_OFF"
             printf '    %sharness moved since - re-run verify.sh before trusting a green past run%s\n' \
               "$SC_DIM" "$SC_OFF" ;;
esac

sc_section "commits"
if ! git log "${RANGE_ARGS[@]}" --format='  %h  %ad  %s' --date=short 2>/dev/null | grep -q .; then
  printf '  none\n'
else
  git log "${RANGE_ARGS[@]}" --format='  %h  %ad  %s' --date=short
fi

sc_section "files touched"
# git log, not git diff: --since is a revision-walk option and git diff ignores
# it, which silently reports the working tree instead of the window.
CHANGED=$(git log "${RANGE_ARGS[@]}" --name-only --format='' 2>/dev/null | grep -v '^$' | sort -u)
if [ -z "$CHANGED" ]; then
  printf '  none\n'
elif [ "$FULL" -eq 1 ]; then
  printf '%s\n' "$CHANGED" | sed 's/^/  /'
else
  # Directory-level rollup: enough to know where the work happened, without
  # paying for a full file list.
  printf '%s\n' "$CHANGED" \
    | awk -F/ '{ if (NF>1) { sub(/\/[^\/]*$/, ""); print } else { print "." } }' \
    | sort | uniq -c | sort -rn | head -12 \
    | awk '{printf "  %4d  %s\n", $1, $2}'
fi

if [ "$DIRTY" -gt 0 ]; then
  sc_section "uncommitted"
  git status --short | head -20 | sed 's/^/  /'
fi

# PROGRESS.md is the authority on what is in flight; surface it here so a
# resuming session does not have to open the file to find the live task.
if [ -f "$PROJECT/PROGRESS.md" ]; then
  sc_section "PROGRESS.md"
  # The template carries a commented-out example task; skipping HTML comment
  # blocks keeps placeholder text out of the report.
  awk '
    /<!--/                  { incomment=1 }
    /-->/                   { incomment=0; next }
    incomment               { next }
    /^## In progress/       { sec="inprog"; print "  in progress:"; next }
    /^## Blockers/          { sec="block";  print "  blockers:";    next }
    /^## /                  { sec="";                                next }
    sec=="inprog" && /^(id|goal|agent|attempts|base_sha):/ { print "    " $0 }
    sec=="inprog" && /^none$/ { print "    none" }
    sec=="block"  && /^\| [0-9]/ { print "    " $0 }
  ' "$PROJECT/PROGRESS.md"
fi

printf '\n%sReconstruct from this and PROGRESS.md - not by re-reading the codebase.%s\n' \
  "$SC_DIM" "$SC_OFF"
printf '%sRun with --mark at session end to set the next boundary.%s\n' "$SC_DIM" "$SC_OFF"

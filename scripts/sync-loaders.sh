#!/usr/bin/env bash
# sync-loaders.sh - regenerate a game repo's .claude/ loaders from studio-core.
#
#     sync-loaders.sh [project-path]     default: cwd
#
# Run this after studio-core gains, renames or removes an agent, command or
# skill. Idempotent: running it twice changes nothing the second time.
#
# A loader carries frontmatter and an instruction to read the real definition
# from studio-core - no behaviour of its own. See DECISIONS.md D-003.
#
# Generation is done by check-loaders.py --write, so the generator and the
# checker are the same code and cannot disagree about what a loader should be.
# Stale loaders (definition removed upstream) are reported by check-loaders.py
# rather than deleted here: removing a file the human may have been mid-way
# through renaming is not a thing a sync script should decide.
#
# Exit: 0 synced | 2 could not run.

set -uo pipefail

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

PROJECT_ARG="${1:-$PWD}"
SC_PROJECT_HINT="$PROJECT_ARG"
export SC_PROJECT_HINT
# shellcheck source=/dev/null
. "$SELF_DIR/_resolve.sh"

PROJECT=$(sc_resolve_project "$PROJECT_ARG") || exit 2
sc_require_python

if [ "$PROJECT" = "$STUDIO_CORE" ]; then
  sc_die "$PROJECT is studio-core itself. It holds the definitions; loaders would be circular."
fi

sc_section "syncing loaders"
sc_info "from $STUDIO_CORE/.claude"
sc_info "into $PROJECT/.claude"

$SC_PYTHON "$SC_SCRIPTS/check-loaders.py" "$PROJECT" --write || exit 2

# Verify what was just written, so a sync that silently produced something the
# checker rejects fails here rather than in CI.
$SC_PYTHON "$SC_SCRIPTS/check-loaders.py" "$PROJECT" --quiet || {
  sc_fail "loaders still do not validate after syncing - this is a bug in check-loaders.py"
  exit 2
}
sc_ok "loaders in sync"

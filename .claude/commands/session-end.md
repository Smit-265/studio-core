---
description: Write state, commit, and mark the session boundary so the next session resumes cheaply
argument-hint: "[project path — defaults to cwd]"
allowed-tools: Read, Edit, Write, Bash
---

Close out the session for: **$ARGUMENTS** (empty means cwd).

Do these in order. A session that ends without them has wasted its tokens, because the next one
cannot reconstruct state without re-reading the codebase.

1. **Update the in-progress packet** in `PROGRESS.md`: current `attempts`, and — if the task is
   unfinished — enough state for a cold session to continue without re-deriving it. Leave
   `base_sha` alone.

2. **Move finished work to Completed**: one row each, with the commit sha. Delete the packet.

3. **Record blockers.** Anything waiting on a human decision says so explicitly, so the next
   session opens with the question rather than rediscovering it. Delete resolved ones.

4. **Write Notes for next session** — only what the packets and tables do not already say. Clear
   notes that have been acted upon; stale notes cost tokens on every read.

5. **Update the `Last updated` line.**

6. **Commit**, then mark the boundary:
   ```sh
   "${STUDIO_CORE:-../studio-core}/scripts/session-report.sh" . --mark
   ```

Report: what was completed, what is in flight with its `attempts` count, open blockers, and the
marker sha. Keep it short — this summary is not state, `PROGRESS.md` is.

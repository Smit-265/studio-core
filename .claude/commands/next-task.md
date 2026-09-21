---
description: Execute the next task packet — builder or asset-pipeline runs it per its agent field, verify.sh gates it, reviewer checks the diff
argument-hint: "[task id, e.g. T-003 — defaults to the in-progress packet, else the top of the queue]"
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

Execute task: **$ARGUMENTS** (empty means the in-progress packet, otherwise the top of the queue).

1. Read `PROGRESS.md`. Resume the in-progress packet if there is one; do not pull a new packet
   while one is open. With an id given and nothing in progress, pull that packet from the
   queue even if it is not at the top — out-of-order is the human's call, so honour it.

2. **Check `attempts` before anything else.** If it is 2 or more, stop and report with the last
   error output. Do not attempt a fix — the count is in the file exactly so a fresh session
   cannot restart the loop.

3. Delegate to the agent the packet's `agent` field names — **builder** or
   **asset-pipeline**. Either one moves the packet to **In progress**, stamps `base_sha` with
   current HEAD before touching a file, works only inside the packet's `scope`, and runs
   `verify.sh` before declaring anything done.

4. If `verify.sh` fails: the agent increments `attempts`, saves `PROGRESS.md`, and gets one
   more attempt. On the second failure, stop and report.

5. On success, with the change committed, delegate to the **reviewer** agent. It diffs
   `base_sha..HEAD` and returns a verdict. If `base_sha` is missing it stops — that is a real
   finding, not an obstacle to work around.

6. Report: the packet id and goal, `verify.sh` result, the reviewer's verdict and findings, and
   the commit sha. If the reviewer returned FAIL, do not queue a fix automatically — report the
   three options from the `state-files` skill (fix packet, accept, revert) and stop. The human
   picks; `attempts` is untouched by a review verdict.

One packet. Do not continue into the next one.

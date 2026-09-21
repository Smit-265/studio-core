#!/usr/bin/env python3
"""guard.py - Claude Code hooks that make the harness rules mechanical.

CLAUDE.md states the rules; an agent can still ignore prose. These run as
Claude Code hooks in the GAME repo (wired by templates/game-settings.json)
and refuse the tool call instead. Deterministic-first applies to the harness
too.

    guard.py scope        PreToolUse  Edit|Write|MultiEdit|NotebookEdit
                          deny a write outside the in-progress packet's scope
    guard.py sequential   PreToolUse  Agent      - deny a second concurrent agent
    guard.py agent-done   PostToolUse Agent / SubagentStop - release the lock
    guard.py git-tree     PreToolUse  Bash       - deny git rooted outside the game repo
    guard.py session-start SessionStart          - snapshot PROGRESS.md
    guard.py stop-state   Stop                   - nudge once if PROGRESS.md untouched

Input: the hook JSON on stdin. Output: exit 0 to allow, exit 2 with a reason
on stderr to block (Claude sees the reason). Anything unexpected - no
PROGRESS.md, no packet, unparsable input - allows, because a guard that
blocks the design stage or a human's manual edit is worse than no guard.

Escape hatch: STUDIO_GUARD=off in the environment disables every guard. That
is a human's call, made outside the session.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _sclib import packet_scope_allows, parse_progress  # noqa: E402

LOCK_MAX_AGE_S = 2 * 60 * 60   # a lock older than this is a crashed session, not a live agent
STATE_DIR = ".studio"          # gitignored in every scaffolded repo

# Files any agent may write regardless of scope, because the harness itself
# asks them to: the state file every agent updates, and the provenance file
# the asset-pipeline appends to.
ALWAYS_ALLOWED = {"PROGRESS.md"}
AGENT_EXTRA = {"asset-pipeline": {"assets.yaml"}}

GIT_WRITES = re.compile(r"\bgit\b(?!\s+(?:--version|help))")


def block(reason: str) -> int:
    sys.stderr.write(reason.rstrip() + "\n")
    return 2


def read_input() -> dict:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def project_dir(payload: dict) -> Path:
    """The game repo: CLAUDE_PROJECT_DIR when Claude Code sets it, else cwd."""
    for cand in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd"), os.getcwd()):
        if cand:
            p = Path(cand).expanduser()
            if p.is_dir():
                return p.resolve()
    return Path.cwd().resolve()


def in_progress_packet(project: Path) -> dict | None:
    path = project / "PROGRESS.md"
    if not path.is_file():
        return None
    try:
        prog = parse_progress(path)
    except Exception:
        return None
    pkts = [p for p in prog["in_progress"] if isinstance(p, dict)]
    return pkts[0] if len(pkts) == 1 else None


def rel_to(project: Path, raw: str) -> str | None:
    """Repo-relative posix path, or None when the file is outside the repo."""
    try:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = project / p
        return p.resolve().relative_to(project).as_posix()
    except (ValueError, OSError):
        return None


# --- scope ------------------------------------------------------------------

def cmd_scope(payload: dict) -> int:
    project = project_dir(payload)
    pkt = in_progress_packet(project)
    if pkt is None:
        return 0  # no live packet: design stage, planning, or a human editing by hand

    raw = (payload.get("tool_input") or {}).get("file_path") \
        or (payload.get("tool_input") or {}).get("notebook_path")
    if not raw:
        return 0
    rel = rel_to(project, str(raw))
    if rel is None:
        return 0  # scratch files outside the repo are not scope creep

    allowed = set(ALWAYS_ALLOWED) | AGENT_EXTRA.get(str(pkt.get("agent", "")), set())
    if rel in allowed or packet_scope_allows(rel, pkt.get("scope") or []):
        return 0

    scope = "\n".join(f"  - {s}" for s in (pkt.get("scope") or [])) or "  (empty)"
    return block(
        f"scope guard: `{rel}` is outside packet {pkt.get('id', '?')}'s scope:\n{scope}\n"
        "Touching it is scope creep. Stop and report what the task needs and why; a human "
        "widens the scope in PROGRESS.md, not the agent. (STUDIO_GUARD=off disables this.)"
    )


# --- sequential -------------------------------------------------------------

def lock_path(project: Path) -> Path:
    return project / STATE_DIR / "agent.lock"


def cmd_sequential(payload: dict) -> int:
    project = project_dir(payload)
    lock = lock_path(project)
    if lock.is_file():
        try:
            age = time.time() - lock.stat().st_mtime
            held = lock.read_text(encoding="utf-8").strip()
        except OSError:
            age, held = 0.0, "?"
        if age < LOCK_MAX_AGE_S:
            return block(
                f"sequential guard: an agent is already running ({held}, started "
                f"{int(age)}s ago). One agent at a time - wait for it to return, then "
                "delegate the next step. If that agent crashed, delete "
                f"{lock.relative_to(project).as_posix()}."
            )
    name = (payload.get("tool_input") or {}).get("subagent_type") \
        or (payload.get("tool_input") or {}).get("description") or "agent"
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(f"{name} pid={os.getpid()} session={payload.get('session_id', '?')}\n",
                        encoding="utf-8")
    except OSError:
        pass
    return 0


def cmd_agent_done(payload: dict) -> int:
    try:
        lock_path(project_dir(payload)).unlink()
    except OSError:
        pass
    return 0


# --- git-tree ---------------------------------------------------------------

def cmd_git_tree(payload: dict) -> int:
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    if not GIT_WRITES.search(cmd):
        return 0
    project = project_dir(payload)
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()

    def inside(p: Path) -> bool:
        try:
            p.resolve().relative_to(project)
            return True
        except ValueError:
            return False

    if not inside(cwd):
        return block(
            f"git guard: cwd is {cwd}, not inside the game repo {project}. base_sha and the "
            "review diff must come from the game's history; a git call rooted elsewhere is "
            "the wrong tree. cd to the game repo (no -C, no path juggling) and retry."
        )
    m = re.search(r"\bgit\s+(?:-C|--git-dir[= ])\s*([^\s]+)", cmd)
    if m and not inside(Path(m.group(1).strip("'\""))):
        return block(
            f"git guard: `git -C {m.group(1)}` points outside the game repo. Run git with "
            "the working directory set to this repo instead."
        )
    return 0


# --- session-start / stop-state ---------------------------------------------

def progress_digest(project: Path) -> str:
    path = project / "PROGRESS.md"
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd_session_start(payload: dict) -> int:
    project = project_dir(payload)
    try:
        d = project / STATE_DIR
        d.mkdir(parents=True, exist_ok=True)
        (d / "progress.snapshot").write_text(progress_digest(project), encoding="utf-8")
        # A stale lock from a crashed session must not block the first delegation.
        lock = lock_path(project)
        if lock.is_file() and time.time() - lock.stat().st_mtime > LOCK_MAX_AGE_S:
            lock.unlink()
    except OSError:
        pass
    return 0


def cmd_stop_state(payload: dict) -> int:
    if payload.get("stop_hook_active"):
        return 0  # already nudged once this turn; never loop on a Stop hook
    project = project_dir(payload)
    snap = project / STATE_DIR / "progress.snapshot"
    if not snap.is_file() or not (project / "PROGRESS.md").is_file():
        return 0
    try:
        before = snap.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    if before != progress_digest(project):
        return 0

    # PROGRESS.md untouched. Only worth a nudge if work actually happened.
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=project,
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return 0
    changed = [ln for ln in out.splitlines() if ln.strip() and "PROGRESS.md" not in ln
               and STATE_DIR not in ln]
    if not changed:
        return 0
    return block(
        f"state guard: {len(changed)} file(s) changed this session but PROGRESS.md has not. "
        "Write state before ending - what got done, what is in flight, what is blocked - "
        "then stop. A session that ends without this has wasted its tokens."
    )


COMMANDS = {
    "scope": cmd_scope,
    "sequential": cmd_sequential,
    "agent-done": cmd_agent_done,
    "git-tree": cmd_git_tree,
    "session-start": cmd_session_start,
    "stop-state": cmd_stop_state,
}


def main(argv: list[str]) -> int:
    if os.environ.get("STUDIO_GUARD", "").lower() in ("off", "0", "false"):
        return 0
    if len(argv) != 2 or argv[1] not in COMMANDS:
        sys.stderr.write(f"usage: guard.py <{'|'.join(COMMANDS)}>\n")
        return 0  # misconfiguration must not block the session
    try:
        return COMMANDS[argv[1]](read_input())
    except Exception as exc:  # a broken guard allows; it never wedges a session
        sys.stderr.write(f"guard.py {argv[1]}: {exc} (allowing)\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

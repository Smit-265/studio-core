#!/usr/bin/env python3
"""check-progress.py - the task packets in PROGRESS.md honour their contract.

The packet is the unit of work the whole harness moves around, and until now
its shape was enforced by prose alone. This makes it a build failure: every
packet has exactly the declared fields, ids are unique for the life of the
repo, the queue is clean, the in-progress slot holds at most one packet, and
`tools` names only what DECISIONS.md approves.

    check-progress.py [project-path]     default: cwd
      --quiet     only print failures
      --strict    treat warnings as failures

Warnings cover things a human may have chosen deliberately - an in-progress
packet at attempts 2, an empty base_sha on a packet a builder has started -
and are surfaced rather than failed so a mid-task session is not blocked by
its own state.

Exit: 0 clean | 1 violation | 2 the check could not run.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sclib import (  # noqa: E402
    EXIT_CONFIG,
    EXIT_OK,
    PACKET_AGENTS,
    PACKET_FIELDS,
    Report,
    bold,
    parse_progress,
)

ID_RE = re.compile(r"^T-\d{3,}$")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|", re.MULTILINE)


def approved_tools(project: Path) -> set[str] | None:
    """First column of the tables in DECISIONS.md §1 and §2, lowercased.

    None when DECISIONS.md is absent, so the caller can warn instead of
    failing every packet with a non-empty tools list.
    """
    path = project / "DECISIONS.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    names: set[str] = set()
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if line.startswith("### "):
            # "Candidates - NOT approved" lives under §2 as a sub-heading.
            section = ""
            continue
        if not (section.startswith("1.") or section.startswith("2.")):
            continue
        m = TABLE_ROW.match(line)
        if not m:
            continue
        name = m.group(1).strip().lower()
        if name and not name.startswith("-") and "{{" not in name \
                and name not in ("tool / dependency", "source"):
            names.add(name)
    return names


def check_packet(where: str, pkt: object, in_progress: bool,
                 tools_ok: set[str] | None, rep: Report) -> str | None:
    if not isinstance(pkt, dict):
        rep.error(f"{where}: not a mapping (got {type(pkt).__name__}). A packet is a YAML "
                  "block with the fields id, goal, scope, acceptance, tools, agent, base_sha, "
                  "attempts.")
        return None

    pid = str(pkt.get("id", "")).strip()
    label = f"{where} ({pid})" if pid else where

    missing = [f for f in PACKET_FIELDS if f not in pkt]
    extra = [f for f in pkt if f not in PACKET_FIELDS]
    if missing:
        rep.error(f"{label}: missing field(s) {', '.join(missing)}. Every packet carries "
                  f"exactly: {', '.join(PACKET_FIELDS)}.")
    if extra:
        rep.error(f"{label}: unknown field(s) {', '.join(extra)}. The packet shape is fixed; "
                  "detail that does not fit belongs in goal or acceptance, not a new key.")

    if not ID_RE.match(pid):
        rep.error(f"{label}: id must look like T-001 (T- then three or more digits).")

    goal = pkt.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        rep.error(f"{label}: goal is empty. One sentence stating what is true when done.")
    elif len(goal.strip()) > 240:
        rep.warn(f"{label}: goal is {len(goal.strip())} characters - that is a paragraph, not "
                 "a sentence. Detail belongs in acceptance.")

    scope = pkt.get("scope")
    if not isinstance(scope, list) or not scope or not all(isinstance(s, str) and s.strip()
                                                             for s in scope):
        rep.error(f"{label}: scope must be a non-empty list of paths. If it cannot be "
                  "enumerated, the task is too broad - split it.")

    acc = pkt.get("acceptance")
    if not isinstance(acc, list) or not acc or not all(isinstance(a, str) and a.strip()
                                                         for a in acc):
        rep.error(f"{label}: acceptance must be a non-empty list of checkable outcomes.")
    elif not any("verify.sh" in a for a in acc):
        rep.error(f"{label}: acceptance never mentions verify.sh. Every packet ends with "
                  "`verify.sh exits 0`.")

    tools = pkt.get("tools")
    if tools is None:
        tools = []
    if not isinstance(tools, list):
        rep.error(f"{label}: tools must be a list ([] when none).")
    elif tools:
        if tools_ok is None:
            rep.warn(f"{label}: tools {tools} cannot be checked - no DECISIONS.md.")
        else:
            for t in tools:
                if str(t).strip().lower() not in tools_ok:
                    rep.error(f"{label}: tool {t!r} is not in DECISIONS.md §1 or §2. Approving "
                              "a tool or source is a human decision; record it there first.")

    agent = pkt.get("agent")
    if agent not in PACKET_AGENTS:
        rep.error(f"{label}: agent must be one of {', '.join(PACKET_AGENTS)} (got {agent!r}).")

    sha = pkt.get("base_sha")
    if sha is None:
        sha = ""
    sha = str(sha).strip()
    if sha and not SHA_RE.match(sha):
        rep.error(f"{label}: base_sha {sha!r} is not a git sha. The builder sets it from "
                  "`git rev-parse HEAD`; nothing else writes it.")
    if in_progress and not sha:
        rep.warn(f"{label}: in progress with an empty base_sha. The builder stamps it before "
                 "touching a file; the reviewer will refuse to run without it.")
    if not in_progress and sha:
        rep.error(f"{label}: queued packet has base_sha set. Only the builder sets it, at "
                  "task start. Clear it, or move the packet to In progress if it was started.")

    attempts = pkt.get("attempts")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
        rep.error(f"{label}: attempts must be an integer >= 0 (got {attempts!r}).")
    elif not in_progress and attempts != 0:
        rep.error(f"{label}: queued packet has attempts {attempts}. A packet enters the queue "
                  "at 0; a non-zero count on a queued packet means it was moved back "
                  "without a human resetting it.")
    elif in_progress and attempts >= 2:
        rep.warn(f"{label}: attempts is {attempts} - two-strike rule reached. Do not start a "
                 "fix; a human amends the packet or parks it.")

    return pid or None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        sys.stderr.write(f"error: project path does not exist: {project}\n")
        return EXIT_CONFIG

    path = project / "PROGRESS.md"
    if not path.is_file():
        print(f"progress: skipped - no PROGRESS.md in {project}")
        return EXIT_OK

    rep = Report("progress")
    prog = parse_progress(path)
    for err in prog["raw_errors"]:
        rep.error(f"{err}. A packet is fenced ```yaml; fix the block or remove it.")

    if not args.quiet:
        print(f"{bold('progress')}  {path.name}: {len(prog['in_progress'])} in progress, "
              f"{len(prog['queue'])} queued, {len(prog['completed'])} completed"
              + (f", {prog['placeholders']} scaffold placeholder(s)"
                 if prog["placeholders"] else ""))

    tools_ok = approved_tools(project)
    seen: dict[str, str] = {}

    def remember(pid: str | None, where: str) -> None:
        if not pid:
            return
        if pid in seen:
            rep.error(f"{where}: id {pid} already used in {seen[pid]}. Ids are unique for the "
                      "life of the repo, even for deleted tasks.")
        else:
            seen[pid] = where

    if len(prog["in_progress"]) > 1:
        rep.error(f"In progress holds {len(prog['in_progress'])} packets. Exactly one, or the "
                  "word `none`. Finish or park all but one.")
    elif not prog["in_progress"]:
        body = prog["sections"].get("in progress", "")
        if not re.search(r"^none\s*$", body, re.MULTILINE):
            rep.warn("In progress has no packet and no literal `none` line. Write `none` so a "
                     "resuming session does not have to infer it.")

    for n, pkt in enumerate(prog["in_progress"], 1):
        remember(check_packet(f"In progress #{n}", pkt, True, tools_ok, rep), "In progress")
    for n, pkt in enumerate(prog["queue"], 1):
        remember(check_packet(f"Task queue #{n}", pkt, False, tools_ok, rep), "Task queue")
    for pid in prog["completed"]:
        if pid == "T-000":
            continue  # template example row
        remember(pid, "Completed")

    if args.strict and rep.warnings:
        rep.errors.extend(f"(strict) {w}" for w in rep.warnings)
        rep.warnings = []

    return rep.finish(f"{len(seen)} packet id(s) accounted for")


if __name__ == "__main__":
    raise SystemExit(main())

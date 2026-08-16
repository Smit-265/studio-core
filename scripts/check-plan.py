#!/usr/bin/env python3
"""check-plan.py - GAME_PLAN.md prose against the enforced budget config.

GAME_PLAN.md is what agents read. config/budgets.yaml is what check-budgets.py
enforces. They can disagree silently, and when they do the prose wins, because
that is what an agent acts on. This finds the disagreement.

    check-plan.py [project-path]      default: cwd
      --quiet     only print findings

WARNINGS ONLY. This never fails a build and always exits 0. Section 3 is prose
written with a human during design; a hard gate on it would be brittle and would
fire on phrasing rather than on substance. The fix for every finding here is the
same and it is cheap: put the number in config/budgets.yaml and have the plan
point at it.

Exit: 0, always.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sclib import (  # noqa: E402
    EXIT_OK,
    bold,
    dim,
    find_studio_core,
    green,
    yellow,
)

# Keyword -> which family of config numbers a figure on this line should match.
# Deliberately broad: a false negative here is silence, which is the failure this
# script exists to prevent, while a false positive costs one line of output.
KINDS = {
    "tri": ("tri", "tris", "triangle", "triangles", "poly", "polys", "polycount",
            "polygon", "polygons", "vert", "verts", "vertex", "vertices"),
    "tex": ("texture", "textures", "texel", "texels", "px", "pixel", "pixels",
            "resolution", "atlas", "lightmap"),
    "size": ("mb", "gb", "kb", "mib", "gib", "megabyte", "megabytes", "gigabyte",
             "filesize", "footprint"),
}

# `500`, `1.5k`, `512px`, `2048x2048`, `≤500`, `500-tri`, `8 MB`. Suffix k/m
# multiplies out so a plan written as `15k tris` matches a config written as
# `15000`; the suffix is only taken when a letter does not follow it, so `15kb`
# reads as 15 rather than 15000. The trailing guard blocks digits and dots but
# not letters - a limit is almost always written welded to its unit.
NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?:\s*([kKmM])(?![a-zA-Z]))?(?![\d.])")

WORD = re.compile(r"[a-z]+")


def numbers_on(line: str) -> list[int]:
    out: list[int] = []
    for raw, suffix in NUM.findall(line):
        value = float(raw)
        if suffix in ("k", "K"):
            value *= 1_000
        elif suffix in ("m", "M"):
            value *= 1_000_000
        if value == int(value):
            out.append(int(value))
    return out


def kinds_on(line: str) -> set[str]:
    words = set(WORD.findall(line.lower()))
    return {kind for kind, keys in KINDS.items() if words & set(keys)}


def section_three(text: str) -> str | None:
    """The body of GAME_PLAN.md section 3, or None if there is no such section."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s*3[.)]?\s", line) or (
            line.startswith("##") and "art direction" in line.lower()
        ):
            start = i + 1
            break
    if start is None:
        return None
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def config_numbers(cfg: dict) -> dict[str, set[int]]:
    """Every number the merged budget config actually enforces, by family."""
    def ints(values) -> set[int]:
        return {int(v) for v in values if isinstance(v, (int, float)) and float(v).is_integer()}

    geometry = cfg.get("geometry", {}) or {}
    textures = cfg.get("textures", {}) or {}
    files = cfg.get("files", {}) or {}
    build = cfg.get("build", {}) or {}

    tri = ints((geometry.get("triangles", {}) or {}).values())
    tri |= ints([geometry.get("per_file_total")])
    tex = ints((textures.get("max_dimension", {}) or {}).values())
    size = ints((files.get("max_mb", {}) or {}).values())
    size |= ints([build.get("source_mb"), build.get("export_mb")])
    return {"tri": tri, "tex": tex, "size": size}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    plan = project / "GAME_PLAN.md"
    if not plan.is_file():
        if not args.quiet:
            print(f"{dim('plan')}  no GAME_PLAN.md - nothing to reconcile")
        return EXIT_OK

    body = section_three(plan.read_text(encoding="utf-8", errors="replace"))
    if body is None:
        if not args.quiet:
            print(f"{dim('plan')}  GAME_PLAN.md has no section 3 - nothing to reconcile")
        return EXIT_OK

    # Budget config, via check-budgets' own loader so the merge semantics cannot
    # drift between the two scripts. Anything wrong with the config itself is
    # check-budgets' finding to report, not this one's - stay quiet and exit 0.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_check_budgets", Path(__file__).resolve().parent / "check-budgets.py")
        mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
        spec.loader.exec_module(mod)                         # type: ignore[union-attr]
        from _sclib import Report as _Report
        cfg = mod.load_config(project, find_studio_core(project), _Report("plan"))
    except SystemExit:
        if not args.quiet:
            print(f"{dim('plan')}  budget config could not be loaded - "
                  "see the budgets step for why")
        return EXIT_OK
    except Exception as exc:                                  # noqa: BLE001
        if not args.quiet:
            print(f"{dim('plan')}  skipped: {exc}")
        return EXIT_OK

    known = config_numbers(cfg)
    all_known = known["tri"] | known["tex"] | known["size"]

    findings: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        # Template placeholders and commented-out guidance are not claims.
        if not line or line.startswith(("<!--", "-->", ">")) or "{{" in line:
            continue
        kinds = kinds_on(line)
        if not kinds:
            continue
        # A line that already points at the config is doing the right thing.
        if "budgets.yaml" in line:
            continue
        expected = all_known if len(kinds) > 1 else known[next(iter(kinds))]
        for value in numbers_on(line):
            if value not in expected:
                findings.append(f"{value} ({'/'.join(sorted(kinds))}) - {line}")

    if not args.quiet:
        print(f"{bold('plan')}  {plan}  {dim('(section 3 vs merged budget config)')}")

    if not findings:
        print(f"{green('plan: OK')} - no bare limits in section 3 that the config lacks")
        return EXIT_OK

    for f in findings:
        print(f"  {yellow('warn')}  {f}")
    print(f"\n{yellow('plan: ' + str(len(findings)) + ' warning(s)')} - section 3 states a "
          "limit the merged budget config does not enforce.")
    print("       Put the number in config/budgets.yaml and have the plan point at it, or "
          "drop it from the prose.")
    print(f"       {dim('Warning only - prose is prose. This never fails the build.')}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

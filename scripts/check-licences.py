#!/usr/bin/env python3
"""check-licences.py - every shipping asset has recorded provenance.

SHIP-BLOCKER. An asset with no entry, or an entry with no licence, fails the
build. Unlicensed art is a legal problem, not a tidiness problem, and the only
cheap moment to catch it is the commit that adds the file.

Validates assets.yaml - the machine-readable source of truth - against the
filesystem. ASSET_MANIFEST.md is a generated view and is never parsed here.

    check-licences.py [project-path]     default: cwd
      --quiet     only print failures
      --strict    treat warnings as failures

Exit: 0 clean | 1 violation | 2 the check could not run.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sclib import (  # noqa: E402
    EXIT_CONFIG,
    EXIT_OK,
    Report,
    bold,
    load_assets_file,
    matches_any,
    norm_asset_path,
    walk_asset_root,
)

REQUIRED_FIELDS = ("path", "type", "source_url", "author", "licence", "attribution_required", "date_added")

# Values that look like a licence but record nothing. Rejecting these is the
# point of the check: "free" is not a licence, it is a memory of one.
NON_LICENCES = {"", "free", "unknown", "n/a", "na", "none", "tbd", "todo", "?", "-"}

VALID_TYPES = {"model", "texture", "material", "audio", "font", "shader", "other"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_entry(idx: int, entry: object, project: Path, rep: Report) -> str | None:
    """Validate one assets.yaml entry. Returns its normalised path, or None."""
    where = f"assets.yaml entry #{idx + 1}"

    if not isinstance(entry, dict):
        rep.error(f"{where} is not a mapping (got {type(entry).__name__}). "
                  "Each entry is a `- path: ...` block.")
        return None

    raw_path = entry.get("path")
    label = f"{where} ({raw_path})" if raw_path else where

    missing = [f for f in REQUIRED_FIELDS if entry.get(f) in (None, "")]
    if missing:
        rep.error(f"{label}: missing required field(s): {', '.join(missing)}. "
                  f"Required: {', '.join(REQUIRED_FIELDS)}.")

    if not raw_path:
        return None
    rel = norm_asset_path(raw_path)

    licence = str(entry.get("licence", "")).strip()
    if licence.lower() in NON_LICENCES:
        rep.error(f"{label}: licence is {licence!r}, which records nothing. "
                  "Use the SPDX identifier (CC0-1.0, CC-BY-4.0, OFL-1.1, MIT) or the "
                  "licence name exactly as the source states it.")

    source = str(entry.get("source_url", "")).strip()
    if source and source != "original" and not source.startswith(("http://", "https://")):
        rep.error(f"{label}: source_url {source!r} is neither a URL nor `original`. "
                  "It must resolve to the asset's own page.")

    added = str(entry.get("date_added", "")).strip()
    if added and not DATE_RE.match(added):
        rep.error(f"{label}: date_added {added!r} is not YYYY-MM-DD.")
    elif added:
        try:
            if date.fromisoformat(added) > date.today():
                rep.warn(f"{label}: date_added {added} is in the future.")
        except ValueError:
            rep.error(f"{label}: date_added {added!r} is not a real date.")

    atype = entry.get("type")
    if atype and atype not in VALID_TYPES:
        rep.warn(f"{label}: type {atype!r} is not one of {', '.join(sorted(VALID_TYPES))}.")

    attribution = entry.get("attribution_required")
    if attribution is not None and not isinstance(attribution, bool):
        rep.error(f"{label}: attribution_required must be true or false, "
                  f"got {attribution!r}.")

    mods = entry.get("modifications") or []
    if mods and not isinstance(mods, list):
        rep.error(f"{label}: modifications must be a list of {{change, date}} entries.")
    elif isinstance(mods, list):
        for m in mods:
            if not isinstance(m, dict) or not m.get("change"):
                rep.error(f"{label}: each modification needs a `change:` line. "
                          "Some licences require stating that changes were made.")
                break

    return rel


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".", help="project path (default: cwd)")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        sys.stderr.write(f"error: project path does not exist: {project}\n")
        return EXIT_CONFIG

    rep = Report("licences")
    data, path = load_assets_file(project)

    if not data:
        # No assets.yaml. Fine only if there is nothing to license.
        stray = walk_asset_root(project, "assets/", [])
        if stray:
            rep.error(
                f"no assets.yaml in {project}, but {len(stray)} file(s) exist under assets/. "
                "Every shipping asset needs recorded provenance - copy "
                "studio-core/templates/assets.yaml here and add an entry per file. "
                f"First few: {', '.join(stray[:3])}"
            )
            return rep.finish()
        rep.note("no assets.yaml and no assets - nothing to check")
        return rep.finish("empty project")

    asset_root = str(data["asset_root"]).strip().rstrip("/") + "/"
    ignore = data["ignore"]

    if not args.quiet:
        print(f"{bold('licences')}  {path}  (root: {asset_root})")

    # --- entries ----------------------------------------------------------
    declared: dict[str, int] = {}
    for i, entry in enumerate(data["assets"]):
        rel = check_entry(i, entry, project, rep)
        if rel is None:
            continue
        if rel in declared:
            rep.error(f"{rel}: declared twice in assets.yaml "
                      f"(entries #{declared[rel] + 1} and #{i + 1}). Remove one.")
            continue
        declared[rel] = i

        if not rel.startswith(asset_root):
            rep.warn(f"{rel}: outside the declared asset_root ({asset_root}). "
                     "It will not be found by the filesystem sweep.")

    # --- filesystem sweep -------------------------------------------------
    on_disk = walk_asset_root(project, asset_root, ignore)
    on_disk_set = set(on_disk)

    for rel in on_disk:
        if rel not in declared:
            rep.error(f"{rel}: on disk with no entry in assets.yaml. "
                      "Add one recording source_url, author and licence - or delete the file.")

    for rel in declared:
        if not rel.startswith(asset_root):
            continue
        if rel not in on_disk_set:
            abs_path = project / rel
            if abs_path.exists():
                # Present but not matched: on a case-insensitive filesystem this
                # is exactly how a casing drift shows up, and it breaks on Linux.
                actual = next((d for d in on_disk if d.lower() == rel.lower()), None)
                if actual:
                    rep.error(f"{rel}: case mismatch - the file on disk is {actual}. "
                              "Paths are case-sensitive on Linux and in CI; fix assets.yaml.")
                elif matches_any(rel[len(asset_root):], ignore):
                    rep.warn(f"{rel}: has an entry but matches an `ignore` pattern.")
                else:
                    rep.error(f"{rel}: has an entry but was not found by the sweep.")
            else:
                rep.error(f"{rel}: entry in assets.yaml but no such file. "
                          "Deleting an asset means deleting its entry, in the same commit.")

    # --- rejected list ----------------------------------------------------
    for i, r in enumerate(data["rejected"]):
        if not isinstance(r, dict):
            rep.warn(f"rejected entry #{i + 1} is not a mapping.")
            continue
        for field in ("name", "source_url", "reason", "date"):
            if not r.get(field):
                rep.warn(f"rejected entry #{i + 1}: missing `{field}`. "
                         "Incomplete rejections get re-evaluated in a later session.")
                break

    if args.strict and rep.warnings:
        rep.errors.extend(f"(strict) {w}" for w in rep.warnings)
        rep.warnings = []

    code = rep.finish(f"{len(declared)} asset(s) recorded, {len(on_disk)} on disk")
    return code if code != EXIT_OK else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""gen-manifest.py - render ASSET_MANIFEST.md from assets.yaml.

assets.yaml is the source of truth; the markdown is a view of it for people.
Hand edits to the markdown are overwritten here and are invisible to
check-licences.py, which is why the generated file carries a DO-NOT-EDIT header.

    gen-manifest.py [project-path]      default: cwd
      --check     do not write; exit 1 if the manifest is out of date
      --stdout    write to stdout instead of the file
      --name X    game name for the heading (default: project directory name)

Output is deterministic — no wall-clock timestamp, just a fingerprint of the
data. That is what makes --check usable in CI: a regeneration with no data
change produces byte-identical output.

Exit: 0 clean | 1 out of date (--check) | 2 the generator could not run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sclib import (  # noqa: E402
    ASSETS_SCHEMA_VERSION,
    EXIT_CONFIG,
    EXIT_OK,
    EXIT_VIOLATION,
    green,
    load_assets_file,
    norm_asset_path,
    red,
)

HEADER = """<!-- GENERATED FILE — DO NOT EDIT BY HAND.
     Source of truth: assets.yaml
     Regenerate:      scripts/gen-manifest.py
     Hand edits are overwritten on the next regeneration and are invisible to
     check-licences.py, which validates assets.yaml against the filesystem.
     To add, change, or remove an asset: edit assets.yaml, then regenerate. -->
"""

NONE_ROW = "| _none recorded_ |"


def fingerprint(data: dict) -> str:
    payload = json.dumps(
        {"assets": data.get("assets", []), "rejected": data.get("rejected", [])},
        sort_keys=True, default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def esc(value: object) -> str:
    """Table-cell safe: pipes would break the row, newlines would break the table."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render(data: dict, name: str) -> str:
    assets = [a for a in data.get("assets", []) if isinstance(a, dict)]
    rejected = [r for r in data.get("rejected", []) if isinstance(r, dict)]
    assets.sort(key=lambda a: norm_asset_path(a.get("path", "")))
    rejected.sort(key=lambda r: str(r.get("name", "")))

    root = str(data.get("asset_root", "assets/"))
    out: list[str] = [HEADER, f"# ASSET_MANIFEST — {name}", ""]
    out += ["Human-readable view of `assets.yaml`. Provenance and licensing for every asset "
            "that ships.", ""]
    out += [f"**Source:** `assets.yaml` (schema v{ASSETS_SCHEMA_VERSION}) · "
            f"**Fingerprint:** `{fingerprint(data)}` · "
            f"**Assets:** {len(assets)} · **Rejected:** {len(rejected)}", ""]
    out += ["Licence coverage is a ship-blocker. `check-licences.py` reads `assets.yaml`, walks",
            f"`{root}`, and fails on any file without an entry or any entry without a licence.",
            "", "---", ""]

    # 1. assets
    out += ["## 1. Assets", "",
            "| Path | Type | Source | Author | Licence | Attribution | Added |",
            "|---|---|---|---|---|---|---|"]
    if not assets:
        out.append(NONE_ROW + " | | | | | |")
    for a in assets:
        path = norm_asset_path(a.get("path", ""))
        src = esc(a.get("source_url"))
        src_cell = "original" if src == "original" else (f"[link]({src})" if src else "")
        out.append("| `{}` | {} | {} | {} | `{}` | {} | {} |".format(
            path, esc(a.get("type")), src_cell, esc(a.get("author")),
            esc(a.get("licence")), "yes" if a.get("attribution_required") else "no",
            esc(a.get("date_added"))))
    out += ["", "---", ""]

    # 2. modifications
    out += ["## 2. Modifications", "",
            "Assets altered after acquisition. Some licences require stating that changes "
            "were made.", "",
            "| Path | Change | Date |", "|---|---|---|"]
    mod_rows = [
        (norm_asset_path(a.get("path", "")), m)
        for a in assets
        for m in (a.get("modifications") or [])
        if isinstance(m, dict)
    ]
    if not mod_rows:
        out.append(NONE_ROW + " | |")
    for path, m in mod_rows:
        out.append(f"| `{path}` | {esc(m.get('change'))} | {esc(m.get('date'))} |")
    out += ["", "---", ""]

    # 3. attribution
    out += ["## 3. Attribution text", "",
            "Copy verbatim into in-game credits and any store page. Generated from every "
            "entry with `attribution_required: true`.", "", "```"]
    credits = [a for a in assets if a.get("attribution_required")]
    if not credits:
        out.append("(no attribution-required assets)")
    for a in credits:
        out.append("{} by {} — {} — licensed under {}".format(
            Path(norm_asset_path(a.get("path", ""))).stem, a.get("author", "?"),
            a.get("source_url", "?"), a.get("licence", "?")))
    out += ["```", "", "---", ""]

    # 4. rejected
    out += ["## 4. Rejected", "",
            "Evaluated and turned down. Recorded so a later session does not re-source the "
            "same asset.", "",
            "| Asset | Source | Reason | Detail | Date |", "|---|---|---|---|---|"]
    if not rejected:
        out.append(NONE_ROW + " | | | |")
    for r in rejected:
        src = esc(r.get("source_url"))
        out.append("| {} | {} | {} | {} | {} |".format(
            esc(r.get("name")), f"[link]({src})" if src else "",
            esc(r.get("reason")), esc(r.get("detail")), esc(r.get("date"))))

    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--check", action="store_true", help="exit 1 if out of date, write nothing")
    ap.add_argument("--stdout", action="store_true", help="write to stdout")
    ap.add_argument("--name", help="game name for the heading")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        sys.stderr.write(f"error: project path does not exist: {project}\n")
        return EXIT_CONFIG

    data, source = load_assets_file(project)
    if not data:
        if args.check:
            return EXIT_OK  # nothing to generate from, nothing to be stale
        sys.stderr.write(f"error: no assets.yaml in {project} - nothing to generate from.\n")
        return EXIT_CONFIG

    name = args.name or project.name
    text = render(data, name)

    if args.stdout:
        sys.stdout.write(text)
        return EXIT_OK

    target = project / "ASSET_MANIFEST.md"

    if args.check:
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current == text:
            print(f"{green('manifest: OK')} - ASSET_MANIFEST.md matches assets.yaml")
            return EXIT_OK
        reason = "does not exist" if current is None else "is out of date"
        print(f"{red('manifest: FAILED')} - ASSET_MANIFEST.md {reason}.\n"
              f"  Regenerate with:  gen-manifest.py {project}")
        return EXIT_VIOLATION

    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"{green('wrote')} {target}  ({len(data.get('assets', []))} asset(s), "
          f"from {source.name})")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

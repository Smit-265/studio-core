#!/usr/bin/env python3
"""check-budgets.py - asset budgets, enforced from config, never from code.

Thresholds come from studio-core/config/budgets.yaml, deep-merged with the game
repo's config/budgets.yaml if present. No number in this file is a budget.

    check-budgets.py [project-path]     default: cwd
      --print-config   dump the merged config and exit (for debugging overrides)
      --quiet          only print failures
      --strict         treat warnings as failures

Merge rules, restated from the config header because they surprise people:
  * mappings merge key-by-key; a scalar leaf in the game file replaces the default
  * LISTS REPLACE WHOLESALE - rule order matters, and merged ordered rules
    produce surprises
  * an unknown key in a game override is a hard error, never a silent no-op

Exit: 0 clean | 1 violation | 2 the check could not run.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sclib import (  # noqa: E402
    EXIT_CONFIG,
    EXIT_OK,
    Report,
    bold,
    die,
    dim,
    find_studio_core,
    load_assets_file,
    load_yaml,
    matches_any,
    norm_asset_path,
    walk_asset_root,
)

MB = 1024 * 1024

# Mappings whose keys are names the studio invents - asset classes, texture
# roles, file types. A game may add new ones, so unknown keys here are allowed
# and cross-checked instead of rejected.
OPEN_PATHS = {
    "geometry.triangles",
    "textures.max_dimension",
    "textures.role_suffixes",
    "files.max_mb",
    "files.extensions",
}


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

def deep_merge(base: dict, over: dict, path: str = "") -> dict:
    out = dict(base)
    for key, value in over.items():
        here = f"{path}.{key}" if path else key
        if key not in base:
            if path in OPEN_PATHS:
                out[key] = value
                continue
            known = ", ".join(sorted(base)) or "(none)"
            die(f"unknown key `{here}` in the game's config/budgets.yaml.\n"
                f"       Known keys at this level: {known}\n"
                "       A typo'd threshold that silently does nothing is worse than no "
                "threshold, so this is fatal.")
        if isinstance(value, dict) and isinstance(base[key], dict):
            out[key] = deep_merge(base[key], value, here)
        else:
            # Scalars replace. Lists replace wholesale, deliberately.
            out[key] = value
    return out


def load_config(project: Path, studio_core: Path, rep: Report) -> dict:
    defaults = load_yaml(studio_core / "config" / "budgets.yaml", "studio-core budgets.yaml")
    if defaults.get("version") != 1:
        die(f"studio-core config/budgets.yaml declares version {defaults.get('version')!r}, "
            "this tooling expects 1.")

    override_path = project / "config" / "budgets.yaml"
    if override_path.resolve() == (studio_core / "config" / "budgets.yaml").resolve():
        # Running against studio-core itself: the defaults are not an override.
        return defaults
    if not override_path.is_file():
        rep.note(f"no per-game config/budgets.yaml - using studio-core defaults only")
        return defaults

    override = load_yaml(override_path, "game budgets.yaml")
    override.pop("version", None)
    merged = deep_merge(defaults, override)
    rep.note(f"merged overrides from {override_path}")
    return merged


def validate_config(cfg: dict, rep: Report) -> None:
    """Catch typos in the open mappings, where unknown keys are legal."""
    classes = set(cfg["geometry"]["triangles"])
    used = {cfg["classify"]["default"]} | {
        r.get("class") for r in cfg["classify"]["rules"] if isinstance(r, dict)
    }
    for cls in sorted(used - classes):
        rep.error(f"classify assigns class {cls!r} but geometry.triangles has no budget for it. "
                  "Add the budget or fix the class name.")
    for cls in sorted(classes - used):
        rep.warn(f"geometry.triangles defines {cls!r} but no classify rule produces it - "
                 "dead budget, or a typo in a rule.")

    roles = set(cfg["textures"]["max_dimension"]) - {"default"}
    suffixed = set(cfg["textures"]["role_suffixes"])
    for role in sorted(roles - suffixed):
        rep.warn(f"textures.max_dimension defines role {role!r} with no entry in "
                 "role_suffixes - nothing will ever be classified as that role.")


# --------------------------------------------------------------------------
# format readers - no third-party imaging or mesh libraries
# --------------------------------------------------------------------------

def image_size(path: Path) -> tuple[int, int] | None:
    """(width, height) for formats we can read from the header, else None."""
    try:
        with path.open("rb") as fh:
            head = fh.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", head[16:24])
                return w, h
            if head[:2] == b"\xff\xd8":  # JPEG: walk the marker chain to an SOF
                fh.seek(2)
                while True:
                    b = fh.read(1)
                    if not b:
                        return None
                    if b != b"\xff":
                        continue
                    marker = fh.read(1)
                    while marker == b"\xff":
                        marker = fh.read(1)
                    if not marker:
                        return None
                    m = marker[0]
                    if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                        fh.read(3)  # length (2) + precision (1)
                        h, w = struct.unpack(">HH", fh.read(4))
                        return w, h
                    size = struct.unpack(">H", fh.read(2))[0]
                    fh.seek(size - 2, 1)
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                fourcc = head[12:16]
                if fourcc == b"VP8X":
                    w = int.from_bytes(head[24:27], "little") + 1
                    h = int.from_bytes(head[27:30], "little") + 1
                    return w, h
                if fourcc == b"VP8 ":
                    fh.seek(26)
                    w, h = struct.unpack("<HH", fh.read(4))
                    return w & 0x3FFF, h & 0x3FFF
                if fourcc == b"VP8L":
                    fh.seek(21)
                    bits = int.from_bytes(fh.read(4), "little")
                    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    except (OSError, struct.error, IndexError):
        return None
    return None


def _gltf_tris(doc: dict) -> int | None:
    accessors = doc.get("accessors") or []
    total = 0
    for mesh in doc.get("meshes") or []:
        for prim in mesh.get("primitives") or []:
            mode = prim.get("mode", 4)
            idx = prim.get("indices")
            if idx is not None and idx < len(accessors):
                count = accessors[idx].get("count", 0)
            else:
                pos = (prim.get("attributes") or {}).get("POSITION")
                if pos is None or pos >= len(accessors):
                    continue
                count = accessors[pos].get("count", 0)
            if mode == 4:
                total += count // 3
            elif mode in (5, 6):
                total += max(0, count - 2)
            # points/lines contribute no triangles
    return total


def triangle_count(path: Path) -> int | None:
    """Triangles in a mesh file, or None when the format cannot be read.

    glTF/GLB and OBJ are parsed. FBX and .blend are binary formats whose
    parsers are a project in themselves; they are reported as unmeasurable
    rather than silently passed.
    """
    suffix = path.suffix.lower()
    try:
        if suffix == ".gltf":
            with path.open("r", encoding="utf-8") as fh:
                return _gltf_tris(json.load(fh))
        if suffix == ".glb":
            with path.open("rb") as fh:
                magic, _version, _length = struct.unpack("<4sII", fh.read(12))
                if magic != b"glTF":
                    return None
                chunk_len, chunk_type = struct.unpack("<I4s", fh.read(8))
                if chunk_type != b"JSON":
                    return None
                return _gltf_tris(json.loads(fh.read(chunk_len).decode("utf-8")))
        if suffix == ".obj":
            tris = 0
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("f "):
                        verts = len(line.split()) - 1
                        if verts >= 3:
                            tris += verts - 2
            return tris
    except (OSError, ValueError, struct.error, UnicodeDecodeError):
        return None
    return None


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------

def classify(rel: str, cfg: dict, overrides: dict) -> str:
    if rel in overrides:
        return overrides[rel]
    for rule in cfg["classify"]["rules"]:
        if isinstance(rule, dict) and matches_any(rel, [rule.get("glob", "")]):
            return rule.get("class", cfg["classify"]["default"])
    return cfg["classify"]["default"]


def file_type(rel: str, cfg: dict) -> str | None:
    ext = Path(rel).suffix.lower()
    for type_name, exts in cfg["files"]["extensions"].items():
        if ext in [str(e).lower() for e in exts or []]:
            return type_name
    return None


def texture_role(rel: str, cfg: dict) -> str:
    stem = Path(rel).stem.lower()
    for role, suffixes in cfg["textures"]["role_suffixes"].items():
        for suf in suffixes or []:
            if stem.endswith(str(suf).lower()):
                return role
    return "default"


def is_pot(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def check_one(rel: str, project: Path, cfg: dict, overrides: dict, rep: Report,
              warn_ratio: float) -> None:
    abs_path = project / rel
    ftype = file_type(rel, cfg)

    if ftype is None:
        rep.error(f"{rel}: extension {Path(rel).suffix or '(none)'} is not in "
                  "files.extensions. Either it does not belong under the asset root, or "
                  "budgets.yaml needs to learn about it.")
        return

    # size on disk
    limit_mb = cfg["files"]["max_mb"].get(ftype)
    if limit_mb is None:
        rep.error(f"{rel}: type {ftype!r} has no entry in files.max_mb.")
    else:
        size = abs_path.stat().st_size
        limit = float(limit_mb) * MB
        if size > limit:
            rep.error(f"{rel}: {size / MB:.1f} MB exceeds the {ftype} budget of {limit_mb} MB.")
        elif size > limit * warn_ratio:
            rep.warn(f"{rel}: {size / MB:.1f} MB is near the {ftype} budget of {limit_mb} MB.")

    # geometry
    if ftype == "model":
        cls = classify(rel, cfg, overrides)
        budget = cfg["geometry"]["triangles"].get(cls)
        tris = triangle_count(abs_path)
        if tris is None:
            rep.warn(f"{rel}: cannot count triangles in {abs_path.suffix} - budget "
                     f"({cls}: {budget}) not enforced. Export to .glb to have it checked.")
        elif budget is None:
            rep.error(f"{rel}: classified as {cls!r} which has no geometry.triangles budget.")
        else:
            if tris > int(budget):
                rep.error(f"{rel}: {tris} tris exceeds the {cls} budget of {budget}.")
            elif tris > int(budget) * warn_ratio:
                rep.warn(f"{rel}: {tris} tris is near the {cls} budget of {budget}.")
            per_file = cfg["geometry"].get("per_file_total")
            if per_file and tris > int(per_file):
                rep.error(f"{rel}: {tris} tris exceeds geometry.per_file_total of {per_file}.")

    # textures
    if ftype == "texture":
        dims = image_size(abs_path)
        if dims is None:
            rep.warn(f"{rel}: cannot read dimensions from {abs_path.suffix} - "
                     "texture budget not enforced.")
        else:
            w, h = dims
            role = texture_role(rel, cfg)
            cap = cfg["textures"]["max_dimension"].get(
                role, cfg["textures"]["max_dimension"]["default"])
            longest = max(w, h)
            if longest > int(cap):
                rep.error(f"{rel}: {w}x{h} exceeds the {role} cap of {cap}px "
                          "on the longest edge.")
            elif longest > int(cap) * warn_ratio:
                rep.warn(f"{rel}: {w}x{h} is near the {role} cap of {cap}px.")
            if cfg["textures"].get("require_power_of_two") and not (is_pot(w) and is_pot(h)):
                rep.error(f"{rel}: {w}x{h} is not power-of-two. Non-PoT textures cost "
                          "memory and break some compression paths.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".", help="project path (default: cwd)")
    ap.add_argument("--print-config", action="store_true", help="dump merged config and exit")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        sys.stderr.write(f"error: project path does not exist: {project}\n")
        return EXIT_CONFIG

    rep = Report("budgets")
    studio_core = find_studio_core(project)
    cfg = load_config(project, studio_core, rep)

    if args.print_config:
        json.dump(cfg, sys.stdout, indent=2, sort_keys=True)
        print()
        return EXIT_OK

    validate_config(cfg, rep)
    warn_ratio = float(cfg.get("warn_at_percent", 90)) / 100.0

    data, _ = load_assets_file(project)
    asset_root = str(data.get("asset_root", "assets/")).strip().rstrip("/") + "/"
    ignore = data.get("ignore", [])
    overrides = {
        norm_asset_path(e["path"]): e["budget_class"]
        for e in data.get("assets", [])
        if isinstance(e, dict) and e.get("path") and e.get("budget_class")
    }

    if not (project / asset_root).is_dir():
        rep.note(f"no {asset_root} directory - nothing to measure")
        return rep.finish("empty project")

    if not args.quiet:
        print(f"{bold('budgets')}  {project}  {dim('(root: ' + asset_root + ')')}")

    files = walk_asset_root(project, asset_root, ignore)
    total_bytes = 0
    for rel in files:
        try:
            total_bytes += (project / rel).stat().st_size
        except OSError:
            continue
        check_one(rel, project, cfg, overrides, rep, warn_ratio)

    # whole-project ceilings
    build_cfg = cfg.get("build", {})
    src_cap = build_cfg.get("source_mb")
    if src_cap and total_bytes > float(src_cap) * MB:
        rep.error(f"asset root is {total_bytes / MB:.0f} MB, over build.source_mb "
                  f"of {src_cap} MB.")
    count_cap = build_cfg.get("max_asset_count")
    if count_cap and len(files) > int(count_cap):
        rep.error(f"{len(files)} assets, over build.max_asset_count of {count_cap}.")

    export_cap = build_cfg.get("export_mb")
    export_dir = next((project / d for d in ("build", "export", "dist")
                       if (project / d).is_dir()), None)
    if export_cap and export_dir:
        exported = sum(p.stat().st_size for p in export_dir.rglob("*") if p.is_file())
        if exported > float(export_cap) * MB:
            rep.error(f"{export_dir.name}/ is {exported / MB:.0f} MB, over build.export_mb "
                      f"of {export_cap} MB.")

    if args.strict and rep.warnings:
        rep.errors.extend(f"(strict) {w}" for w in rep.warnings)
        rep.warnings = []

    return rep.finish(f"{len(files)} asset(s), {total_bytes / MB:.1f} MB")


if __name__ == "__main__":
    raise SystemExit(main())

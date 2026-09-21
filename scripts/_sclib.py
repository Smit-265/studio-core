"""_sclib.py - shared helpers for studio-core's python checks.

Imported, never run. check-licences.py, check-budgets.py and gen-manifest.py
all need to find studio-core, load YAML, walk the asset root and report
consistently; this is the one copy of that logic.
"""

from __future__ import annotations

import fnmatch
import os
import re
import sys
from pathlib import Path, PurePosixPath

try:
    import yaml
except ImportError:  # pragma: no cover - environment problem, not logic
    sys.stderr.write(
        "error: PyYAML is not installed.\n"
        "       Install it with:  %s -m pip install pyyaml\n" % sys.executable
    )
    raise SystemExit(2)

ASSETS_SCHEMA_VERSION = 1
BUDGETS_SCHEMA_VERSION = 1

# Exit codes, shared by every check so callers can tell them apart.
EXIT_OK = 0
EXIT_VIOLATION = 1   # the thing being checked is wrong
EXIT_CONFIG = 2      # the check itself could not run

_COLOUR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


def red(t: str) -> str:
    return _c("31", t)


def green(t: str) -> str:
    return _c("32", t)


def yellow(t: str) -> str:
    return _c("33", t)


class Report:
    """Collects errors and warnings, prints them grouped, decides the exit code.

    Messages are meant to be actionable: each one says what is wrong and what to
    do about it, because the reader is often an agent with no other context.
    """

    def __init__(self, title: str) -> None:
        self.title = title
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def finish(self, summary: str = "") -> int:
        for n in self.notes:
            print(f"  {dim('note')}  {n}")
        for w in self.warnings:
            print(f"  {yellow('warn')}  {w}")
        for e in self.errors:
            print(f"  {red('FAIL')}  {e}")

        if self.errors:
            print(
                f"\n{red(self.title + ': FAILED')} - "
                f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
            )
            return EXIT_VIOLATION

        tail = f" ({len(self.warnings)} warning(s))" if self.warnings else ""
        print(f"\n{green(self.title + ': OK')}{tail}{(' - ' + summary) if summary else ''}")
        return EXIT_OK


def die(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    sys.stderr.write(f"error: {msg}\n")
    raise SystemExit(EXIT_CONFIG)


def find_studio_core(project: Path) -> Path:
    """Mirror of scripts/_resolve.sh, for scripts invoked directly.

    Order: $STUDIO_CORE, then <project>/../studio-core, then this file's own
    repo. See DECISIONS.md D-001.
    """
    def looks_right(p: Path) -> bool:
        return (
            p.is_dir()
            and (p / "CLAUDE.md").is_file()
            and (p / "config" / "budgets.yaml").is_file()
            and (p / "scripts" / "_resolve.sh").is_file()
        )

    env = os.environ.get("STUDIO_CORE")
    if env:
        cand = Path(env).expanduser().resolve()
        if looks_right(cand):
            return cand
        die(
            f"$STUDIO_CORE is set to '{env}' but that is not a studio-core checkout.\n"
            "       Fix the variable or unset it to fall back to ../studio-core."
        )

    cand = (project.resolve().parent / "studio-core")
    if looks_right(cand):
        return cand

    cand = Path(__file__).resolve().parent.parent
    if looks_right(cand):
        return cand

    die(
        "cannot locate studio-core. Tried, in order:\n"
        "         1. $STUDIO_CORE            (not set)\n"
        f"         2. {project.resolve().parent / 'studio-core'}   (not a studio-core checkout)\n"
        "       Set STUDIO_CORE, or place the game repo as a sibling of studio-core."
    )


def load_yaml(path: Path, what: str) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        die(f"{what} not found: {path}")
    except yaml.YAMLError as exc:
        die(f"{what} is not valid YAML ({path}):\n       {exc}")
    if data is None:
        data = {}
    if not isinstance(data, dict):
        die(f"{what} must be a mapping at the top level ({path}), got {type(data).__name__}")
    return data


def norm_asset_path(raw: str) -> str:
    """Repo-relative, forward slashes, `res://` stripped.

    Godot users write `res://assets/x.png`; the filesystem check needs
    `assets/x.png`. Accept both, store one.
    """
    p = str(raw).strip().replace("\\", "/")
    if p.startswith("res://"):
        p = p[len("res://"):]
    return p.lstrip("./")


def matches_any(rel_path: str, patterns: list) -> bool:
    """fnmatch with `**` treated as 'any depth', which fnmatch does not do.

    `**/*.import` should match `a/b/c.import`, so try the pattern as written and
    with a leading `**/` collapsed away.
    """
    pp = PurePosixPath(rel_path)
    for pat in patterns or []:
        pat = str(pat)
        if fnmatch.fnmatch(rel_path, pat):
            return True
        if pat.startswith("**/") and fnmatch.fnmatch(pp.name, pat[3:]):
            return True
        if pp.match(pat):
            return True
    return False


def walk_asset_root(project: Path, asset_root: str, ignore: list) -> list[str]:
    """Every file under asset_root, repo-relative, ignore patterns applied.

    Returns paths with the on-disk casing so a case mismatch in assets.yaml is
    caught even on a case-insensitive filesystem, which is the whole point of
    doing the comparison here rather than with a plain exists() call.
    """
    root = project / asset_root
    if not root.is_dir():
        return []

    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in {".git", ".import", "__pycache__"})
        for name in sorted(filenames):
            abs_path = Path(dirpath) / name
            rel = abs_path.relative_to(project).as_posix()
            rel_to_root = abs_path.relative_to(root).as_posix()
            if matches_any(rel_to_root, ignore) or matches_any(rel, ignore):
                continue
            found.append(rel)
    return found


def load_assets_file(project: Path, report: Report | None = None) -> tuple[dict, Path]:
    """Load assets.yaml, validating only what every caller depends on."""
    path = project / "assets.yaml"
    if not path.is_file():
        return {}, path

    data = load_yaml(path, "assets.yaml")
    version = data.get("version")
    if version != ASSETS_SCHEMA_VERSION:
        die(
            f"assets.yaml declares version {version!r}, this tooling expects "
            f"{ASSETS_SCHEMA_VERSION}. ({path})"
        )
    data.setdefault("asset_root", "assets/")
    data.setdefault("ignore", [])
    data.setdefault("assets", [])
    data.setdefault("rejected", [])

    for key in ("assets", "rejected", "ignore"):
        if data[key] is None:
            data[key] = []
        if not isinstance(data[key], list):
            die(f"assets.yaml: `{key}` must be a list, got {type(data[key]).__name__}")

    return data, path


def rel_display(project: Path, path: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return str(path)


# --- PROGRESS.md ------------------------------------------------------------
#
# PROGRESS.md is markdown for people, but the packets in it are fenced YAML so
# a script can read them without regex over prose. This is the one parser;
# check-progress.py, the hook guards and session-report all go through it so
# they cannot disagree about what "the in-progress packet" is.

PACKET_FIELDS = ("id", "goal", "scope", "acceptance", "tools", "agent", "base_sha", "attempts")
PACKET_AGENTS = ("builder", "asset-pipeline")

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE = re.compile(r"^```ya?ml[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
_TABLE_ID = re.compile(r"^\|\s*(T-\d+)\s*\|", re.MULTILINE)


def _sections(text: str) -> dict[str, str]:
    """Split on `## ` headings. Keys are lowercased heading text."""
    out: dict[str, str] = {}
    key = ""
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if key:
                out[key] = "\n".join(buf)
            key = line[3:].strip().lower()
            buf = []
        else:
            buf.append(line)
    if key:
        out[key] = "\n".join(buf)
    return out


def parse_progress(path: Path) -> dict:
    """Return {"in_progress": [packet], "queue": [packet], "completed": [ids],
    "raw_errors": [str], "sections": {name: text}}.

    A packet is whatever safe_load gives back for one fenced block - normally a
    dict. Malformed YAML is reported in raw_errors, not raised, so a checker can
    say which block is broken rather than dying on the first one. HTML comments
    are stripped first: the template keeps a worked example inside one. Blocks
    still carrying `{{...}}` template prompts are counted, not parsed.
    """
    text = _HTML_COMMENT.sub("", path.read_text(encoding="utf-8"))
    secs = _sections(text)
    result: dict = {"in_progress": [], "queue": [], "completed": [],
                    "placeholders": 0, "raw_errors": [], "sections": secs}

    def blocks(section: str, dest: str) -> None:
        body = secs.get(section, "")
        for n, m in enumerate(_FENCE.finditer(body), 1):
            if "{{" in m.group(1):
                # Scaffold example still carrying template prompts. Not a packet.
                result["placeholders"] += 1
                continue
            try:
                data = yaml.safe_load(m.group(1))
            except yaml.YAMLError as exc:
                result["raw_errors"].append(f"{section}: block #{n} is not valid YAML: {exc}")
                continue
            result[dest].append(data)

    blocks("in progress", "in_progress")
    blocks("task queue", "queue")
    result["completed"] = _TABLE_ID.findall(secs.get("completed", ""))
    return result


def is_placeholder(packet: object) -> bool:
    """True for a scaffold example still carrying `{{...}}` prompts."""
    return "{{" in str(packet)


def packet_scope_allows(rel_path: str, scope: list) -> bool:
    """Does a repo-relative path fall inside a packet's scope list?

    An entry names a file exactly, or a directory (trailing slash or no
    extension) whose contents are all in scope. Globs are honoured via
    matches_any so a planner may write `scenes/ui/*.tscn` if it must.
    """
    rel = norm_asset_path(rel_path)
    for entry in scope or []:
        e = norm_asset_path(str(entry)).rstrip("/")
        if not e:
            continue
        if rel == e or rel.startswith(e + "/"):
            return True
        if any(ch in e for ch in "*?[") and matches_any(rel, [e]):
            return True
    return False

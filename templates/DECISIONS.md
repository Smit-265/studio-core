# DECISIONS — {{GAME_NAME}}

> **Append-only.** Entries are settled. Agents must not re-litigate anything recorded here —
> follow it, or escalate to the human. To reverse a decision, append a new entry that
> supersedes the old one and mark the old one `SUPERSEDED BY D-nnn`; never delete or rewrite.
>
> Read by: planner (always — task tools and sources come from here), builder and
> asset-pipeline (before introducing any tool, dependency, or asset).

**Last appended:** {{DATE}}

---

## 1. Approved tools and dependencies

Only what is listed here may be used. Anything else is an escalation to the human, not a
judgement call.

| Tool / dependency | Version | Used for | Approved |
|---|---|---|---|
| Godot | 4.7.1.stable | Engine | {{DATE}} |
| | | | |

---

## 2. Approved asset sources

An asset may only be sourced from this list. Every acquisition is appended to `assets.yaml`
with its SPDX licence — `check-licences.py` is a ship-blocker.

| Source | URL | Licence | Attribution required | Approved |
|---|---|---|---|---|
| | | | | |

### Candidates — NOT approved

Recommendations only. Moving a row into the table above is a human decision.

| Source | Licence | Note |
|---|---|---|
| {{candidate}} | {{licence}} | {{why it might suit}} |

---

## 3. MCP servers

**No agent installs an MCP server.** This section lists candidates only; installation and
configuration are human decisions, made outside any agent session.

| Candidate | Would provide | Status |
|---|---|---|
| {{name}} | {{capability}} | candidate — not installed |

---

## 4. Style constraints

Hard limits the asset-pipeline and builder enforce without asking. Keep these concrete enough
that a script could check most of them.

| Constraint | Value |
|---|---|
| Art direction | {{one line}} |
| Palette | {{restriction}} |
| Texture resolution cap | {{px}} |
| Poly budget per {{class of object}} | {{tris}} |
| Audio format / rate | {{format}} |
| Naming convention | see `asset-import` skill |

Numeric budgets enforced by `check-budgets.py` live in `config/budgets.yaml`, not here — this
table records the *decision*; the config records the *threshold*. Keep them in agreement.

This table and `config/budgets.yaml` are about **assets**. Gameplay numbers do not belong in
either; they live in `tuning/game_tuning.tres`. See D-004.

---

## 5. Architecture decisions

Newest last. One entry per decision. Keep each under ten lines — this file is read often.

### D-001 — studio-core is resolved by convention, not pinned

- **Date:** {{DATE}}
- **Decision:** This repo locates studio-core at `$STUDIO_CORE` if set, else the sibling
  directory `../studio-core`, else it fails with a message naming both. `scripts/_resolve.sh`
  in studio-core implements this; no script hardcodes a path or assumes cwd. This game tracks
  studio-core's head — no version pin.
- **Rationale:** A two-person studio running several games needs harness fixes to reach every
  game without a per-repo migration. Pinning gives reproducibility but guarantees drift: each
  game ends up on a different harness version and every improvement becomes N migrations.
  Tracking head inverts that — one harness, and breakage surfaces immediately rather than at
  the next upgrade.
- **Alternatives rejected:** *git submodule* because pinning is the wrong default before a
  game ships — it turns every harness fix into a submodule bump per repo. *Vendoring/copying
  scripts* because it forks the harness on day one. *Installing studio-core as a package*
  because it adds a build step and a registry to a two-person studio.
- **Consequences:** A studio-core change can break this repo without warning. `verify.sh` is
  what catches it, so it runs in CI on push and PR, and a red build after a harness change is
  the expected signal, not a surprise. **Migration path: once this game ships, pin it** —
  convert studio-core to a git submodule here and point `$STUDIO_CORE` at the submodule path.
  A shipped game must be rebuildable at its shipped state; an in-development one benefits more
  from tracking head. Record that switch as its own decision when it happens.
- **Status:** active

### D-002 — Godot is pinned to 4.7.1.stable

- **Date:** {{DATE}}
- **Decision:** This project targets **Godot 4.7.1.stable**, not "4.x". `project.godot` declares
  it in `config/features`, and the `godot-conventions` skill is written against this version.
  Changing minor version is a decision, recorded here as a superseding entry.
- **Rationale:** "4.x" is not a version — GDScript syntax, import defaults and node APIs move
  between minors, so conventions written against a range are written against nothing. A pin
  also means `verify.sh` failures are attributable to the change under test rather than to an
  engine that drifted underneath the project.
- **Alternatives rejected:** *Tracking latest stable* because an engine upgrade landing
  mid-milestone turns every failure into a bisect. *Pinning to a patch-exact build in CI only*
  because the two-person studio develops locally and would hit the drift first.
- **Consequences:** Upgrading is deliberate work: bump the pin, run `verify.sh`, fix what
  breaks, append a superseding decision. Contributors install this exact version; `GODOT_BIN`
  in `.env` points at it when several are installed side by side.
- **Status:** active

### D-003 — Agents reach this repo through thin loaders, not copies

- **Date:** {{DATE}}
- **Decision:** `.claude/` in this repo contains **loaders**, not definitions. Each loader file
  carries only its own frontmatter and an instruction to resolve studio-core (per D-001), read
  the real definition at `$STUDIO_CORE/.claude/<path>`, and follow it exactly. No behaviour
  lives in a loader. Loaders are generated by `sync-loaders.sh` and verified by
  `check-loaders.py`, which runs inside `verify.sh`.
- **Rationale:** Agents must run with the **working directory set to this repo**. The builder
  stamps `base_sha` from `git rev-parse HEAD` and the reviewer diffs `base_sha..HEAD`; both must
  target this repo's history. Running agents from studio-core with a path argument would make
  every git call depend on a correctly-passed `-C`, and a git invocation silently targeting the
  wrong tree is a whole bug class. It would also root file operations in the wrong repo, working
  against the narrow-scope rule that keeps token cost down.
- **Alternatives rejected:** *Running agents from studio-core against a path* for the git-rooting
  reason above. *Symlinks* because they are not platform-neutral and break on a plain Windows
  checkout. *Copying the definitions* because that forks the harness on day one, which is exactly
  what D-001 exists to prevent.
- **Consequences:** Loaders can drift from their sources, so drift is made a build failure rather
  than a discipline problem: `check-loaders.py` fails on a missing loader, an extra loader, or a
  frontmatter mismatch. When studio-core gains or renames a definition, run `sync-loaders.sh`.
  Editing a loader's body is always wrong — the content belongs upstream in studio-core.
- **Status:** active

### D-004 — Gameplay tuning lives in a Godot Resource, not in YAML

- **Date:** {{DATE}}
- **Decision:** Every gameplay number — drain rates, speeds, damage, timers, spawn counts,
  thresholds — lives in `tuning/game_tuning.tres`, an instance of the `GameTuning` Resource
  defined in `tuning/game_tuning.gd`. `config/budgets.yaml` is the **asset budget schema only**
  (triangle counts, texture dimensions, file sizes) and never holds gameplay values. Scripts
  read tuning through a preloaded const, never by re-deriving a number locally.
- **Rationale:** Two hard reasons and one soft one. `check-budgets.py` fails at exit 2 on any
  key it does not recognise, so a gameplay value in `budgets.yaml` does not merely sit in the
  wrong file — it breaks the budget check outright. Godot cannot read YAML at runtime without a
  third-party parser, so a value there is unreachable from the game even if the checker allowed
  it. And a `.tres` opens in the inspector, which means a value can be changed between playtests
  with no rebuild; a number that needs a code edit to adjust will not actually get tuned.
- **Alternatives rejected:** *`config/budgets.yaml`* for the two reasons above. *Constants in
  the scripts that use them* because tuning then requires a code change per iteration and the
  values scatter across files. *A JSON or CFG file in `user://`* because it is not version
  controlled with the game and diverges per machine. *An autoload with plain vars* because it is
  not editable in the inspector and not serialisable.
- **Consequences:** Adding a tuning value is two steps — an `@export` in `game_tuning.gd`, then
  a value set in the inspector — and both land in the diff, `.tres` being text. The resource is
  shared by reference, so anything mutating it at runtime calls `.duplicate()` first or every
  instance silently shares the change. `GAME_PLAN.md` and `DECISIONS.md` may quote a tuning
  value, but the `.tres` is the source of truth and prose that disagrees with it is wrong.
- **Status:** active

### D-005 — {{title}}

- **Date:**
- **Decision:**
- **Rationale:**
- **Alternatives rejected:**
- **Consequences:**
- **Status:** active

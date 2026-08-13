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

### D-003 — {{title}}

- **Date:**
- **Decision:**
- **Rationale:**
- **Alternatives rejected:**
- **Consequences:**
- **Status:** active

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
| {{engine}} | {{version}} | Engine | {{date}} |
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

### D-001 — {{title}}

- **Date:** {{date}}
- **Decision:** {{what was decided, one or two sentences}}
- **Rationale:** {{why — the reason that will not be obvious in six months}}
- **Alternatives rejected:** {{option}} because {{reason}}
- **Consequences:** {{what this now commits us to}}
- **Status:** active

### D-002 — {{title}}

- **Date:**
- **Decision:**
- **Rationale:**
- **Alternatives rejected:**
- **Consequences:**
- **Status:** active

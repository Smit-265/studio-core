---
name: asset-import
description: Import settings per asset type, naming and directory rules that the budget checker depends on, style-constraint enforcement, and the assets.yaml entry format. Load before sourcing or importing any asset.
---

# asset-import

**This file is capped at 150 lines.** A loaded skill sits on-context for the rest of the
session. Overflow goes in a reference file beside this one, loaded only when its case comes up.

Godot **4.7.1.stable** (`DECISIONS.md` D-002). Budgets come from `config/budgets.yaml`; this
skill explains the naming and layout that make those budgets apply correctly.

---

## Before acquiring anything

1. The source must already be in `DECISIONS.md` §2. Not listed → escalate. Do not acquire from
   a source and record the decision afterwards.
2. Check the style constraints in `DECISIONS.md` §4 before downloading, not after.
3. Check `assets.yaml` `rejected:` — it may already have been evaluated and turned down.

**Never generate art.** Sourcing, checking and recording is the job; making the asset is not.

---

## Directory layout — it drives the budget class

`config/budgets.yaml` assigns a triangle budget by matching the path, first rule wins. Put a
model in the wrong directory and it gets the wrong budget silently.

| Path | Class | Default budget |
|---|---|---|
| `assets/characters/player/**` | `character_player` | 40 000 tris |
| `assets/characters/**` | `character_npc` | 25 000 tris |
| `assets/environment/**` | `environment_module` | 8 000 tris |
| `assets/vegetation/**` | `vegetation` | 3 000 tris |
| `assets/props/large/**` | `prop_large` | 15 000 tris |
| `assets/props/medium/**` | `prop_medium` | 5 000 tris |
| `assets/props/**` | `prop_small` | 1 500 tris |
| anything else | `prop_small` | 1 500 tris |

The fallback is deliberately tight: an unclassified asset should be noisy, not exempt. For a
genuine exception, set `budget_class:` on that asset's `assets.yaml` entry — not a new rule.

Check the numbers rather than trusting this table: `check-budgets.py --print-config`.

## Naming — it drives the texture role

Texture caps are chosen by **filename suffix**. A texture with no recognised suffix gets the
`default` cap of 1024px, which is usually not what was intended.

| Suffix | Role | Cap |
|---|---|---|
| `_albedo`, `_basecolor`, `_col`, `_diff` | albedo | 2048 |
| `_normal`, `_nrm`, `_n` | normal | 2048 |
| `_rough`, `_rgh` | roughness | 1024 |
| `_metal`, `_mtl` | metallic | 1024 |
| `_ao`, `_occlusion` | ao | 1024 |
| `_emit`, `_emission` | emission | 1024 |
| `_ui`, `_icon`, `_hud` | ui | 2048 |
| `_sky`, `_skybox`, `_hdri`, `_panorama` | skybox | 4096 |

All lowercase, `snake_case`, no spaces, no version suffixes (`_final`, `_v2`, `_new`). Name a
file for what it is: `crate_wooden_albedo.png`, not `crate2_FINAL_albedo.png`.

**Textures must be power-of-two** on both edges — `require_power_of_two` is on by default.
Non-PoT costs memory and breaks compression paths.

---

## Import settings

Set these in the Godot import dock, then commit the generated `.import` file alongside the
asset. `.import` files are ignored by the licence check but are what make the setting stick.

**Textures**
- Compress mode `VRAM Compressed` for anything in the 3D world; `Lossless` for UI and icons.
- Mipmaps **on** for world textures, **off** for UI.
- `Fix Alpha Border` on for anything with transparency; it kills the dark halo.
- sRGB: on for albedo and emission, **off** for normal, roughness, metallic and AO. Getting
  this wrong makes lighting subtly wrong everywhere and is hard to trace back.

**Models** (`.glb` preferred — it is the one format the budget checker can count triangles in)
- One mesh per file for props; a character may carry its skeleton and animations.
- Apply transforms and freeze scale before export. Import scale stays 1.0.
- Generate LODs on for anything over the `prop_medium` budget.
- Physics/collision is authored in the scene, not baked into the imported mesh.

**Audio**
- SFX: `.wav`, 44.1kHz, mono unless the effect is genuinely positional-stereo. Loop off unless
  the sound loops; set loop points in the import dock, not in the file.
- Music/ambience: `.ogg`, stereo. Loop on.
- Normalise before import. Do not rely on runtime volume to fix a hot file.

**Fonts**
- `.ttf`/`.otf`. Enable only the sizes actually used; every extra size is atlas space.
- Antialiasing on, MSDF for UI text that scales.

---

## Recording it — assets.yaml

Append one entry per file, **at acquisition time**, not before release.

```yaml
  - path: assets/props/crate_wooden.glb
    type: model                # model|texture|material|audio|font|shader|other
    source_url: https://example.org/assets/crate-wooden
    author: A. Example
    licence: CC0-1.0           # SPDX id, or the licence name verbatim
    attribution_required: false
    date_added: 2026-08-13
    modifications:             # optional; some licences require stating changes
      - change: retopologised from 4.2k to 900 tris
        date: 2026-08-13
```

Rules the checker enforces:

- `path` is repo-relative with **exact casing**. A `res://` prefix is accepted and stripped.
  Casing drift passes on Windows and fails in CI.
- `licence` is never blank, `free`, `unknown`, `n/a` or `tbd`. Those record nothing.
- `source_url` resolves to the asset's own page — not a search result, not a homepage. Studio-made
  work uses `original`.
- Deleting an asset means deleting its entry, **in the same commit**.

Rejections go in `rejected:` with `name`, `source_url`, `reason`
(`licence|style|budget|quality|other`) and `date`, so a later session does not re-source it.

## Finishing

```sh
gen-manifest.py .      # regenerate ASSET_MANIFEST.md - never hand-edit it
verify.sh .            # licences and budgets both run here
```

Both must pass before the task is done. `check-licences.py` is a ship-blocker: an unlicensed
asset is a legal problem, not a tidiness problem.

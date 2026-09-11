# Map V1 — Hub crowding glass guide (Design)

**Status:** FAIL → Builder enhance peel · cite Local shot `:8802` Cellar `_10` · `{binder}`  
**Shot:** `(Local FAIL shot — dense root hub)`  
**Lock:** Dig REPLACE / md-viewer / focus ring stay PASS — do **not** regress dig.

## FAIL (what the shot shows)

Dense dense binder root: outer blue **lot plates** collide (`pos-lot`/`local`, `lot-a`/`lot-b`, bottom cluster). Labels pile and cover plates (`lot-d`, `suite-lot…`, `lot-c`, `dense binderPOS-export`, `engine-backups` on-plate). Dig/md/focus OK — this is **lots→hub layout density only**.

## Goal

Readable hub at dense roots: **no plate∩plate**, **no label∩plate**, **no label∩label** at rest. Hover/focus may reveal more.

## Prefer (in order)

### 1. Density-aware orbit radius (do this first)

When lot (folder) count on the current hub ≥ **12**, grow the lot orbit radius (~**+25–35%**). Recheck collisions. Cheap; preserves one-ring mental model.

### 2. Multi-orbit when still crowded

Keep **files (md)** on a **tight inner ring**; put **lots** on **outer** ring(s).

If lots still collide after (1):

- Split lots across **two outer orbits** (R1 / R2), alternating or by name-hash so siblings don’t stack.
- Never put lots on the file ring.

### 3. Labels — hide-until-hover at density

When neighbor angular gap is tight (or lot count ≥ 12):

- **At rest:** plates only (or plates + truncated label if gap allows).
- **Hover / focus / dig-select:** full label.
- Hub name (`dense binder`) always visible.
- Prefer labels **outside** the plate (radial outward), never painted across the plate face.

### 4. Longer stagger (with hide-until-hover)

Alternate label radial offset (near / far) for adjacent lots so survivors don’t share a baseline. Increase min angular step with plate width at that radius (`Δθ ≥ approx plateChord / R`).

### 5. Plate radius (last)

If plates still kiss after radius + multi-orbit: shrink lot plate size ~10–15% at dense hubs only (not dig fan nodes). Don’t shrink so far that hit targets break.

## Do not

- Break dig REPLACE / dig fan / md-viewer / focus ring.
- Invent cream / LLC chrome.
- Show Dig on Overview.
- Fake empty — honest empty stays.

## Glass DoD (this peel)

1. Dense `{binder}` hub: **no plate overlaps** at rest.  
2. At rest: **no label covering a plate**; crowded labels hide until hover.  
3. Dig into a lot → dig fan still REPLACE (prior PASS).  
4. Focus ring still visible on keyboard/hover target.  
5. Dark PC tokens unchanged.

## Soft (non-blocking)

- Calendar lead mid-header flex (parked).  
- Settings HTML cold tip `_9` until JS (parked).

## Soft nits (Local — non-blocking; same peel or follow-up)

- **Dig-fan overlap on fat folders** — dense dig REPLACE still PASS, but fan labels/plates can overlap on wide children. Prefer same density tools: grow dig radius, hide-until-hover labels, stagger. Don’t break dig REPLACE.
- **md-viewer right clip** — viewer can clip on the right edge at dig depth. Keep panel inside stage; slight max-width / inset from chrome. Matches #36 enhance note (md-viewer width).

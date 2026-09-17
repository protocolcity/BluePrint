# Work v2 visual finish — paint only

**Dogfood:** .89 behavior OK (caps / +N / seat-load / flow counts); chrome still reads v1.
**Gap:** mock = factory hero; live = plain text under a filter wall.
**Scope:** CSS/layout paint in Work-view hosts only. **No** caps, facets, membership, or WorkLane reopen.

---

## Look-fors (pass/fail)

### 1. Flow strip — colored stages (+ mini bars if cheap)
- Each stage: **dot color · label · count** — not one grey `Open → Ready → Live → Done` string.
- Colors (suite tokens): Open = info/blue · Ready = accent/violet · Live = alive/green · Done = dim/grey.
- Optional cheap: 8–12 mini vertical bars per stage scaled to count (cap bar count visually).
- FAIL: single muted arrow line as the only flow chrome.

### 2. Seat chips — ready/stalled color weight
- Chip = card (border + slight fill), not flat text.
- **ready** count uses alive/info weight; **stalled** count uses danger/red weight (word + number).
- You / named seats / others same chip grammar.
- FAIL: stalled same grey as ready; chips quieter than filter inputs.

### 3. Hero above filter-mast
- Order top→bottom: **Title → Hero (seat chips + flow) → Facets/search mast → bands**.
- Hero visual weight ≥ filter mast (size, contrast, padding). Filters stay tools; hero is the factory read.
- FAIL: search/filter row above or louder than seat-load + flow (live .89 pattern).

### 4. Band scarcity color
- **Act now:** warm left rule + count in attention/gold-danger family; band reads scarcest.
- **My todos:** quieter count (info/dim); no alarm weight.
- **Seat backlog:** neutral; seat group headers muted uppercase/small.
- FAIL: three bands same grey weight as a ticket wall.

### 5. Freeze (do not reopen)
- Caps 8/8/≤9 +N logic · membership · Overview Option D · Map A 10 pages · no n8n canvas · no POS.

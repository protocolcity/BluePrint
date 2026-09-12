# suite/ — BluePrint citizen glass (`:8801`)

**Law (founder, 2026-07-28 · pc-581):** this folder **is** the ship face —
Map glass over WorkLane + WorkForce. Port-era peers (`desk_v1`, `roster_v1`,
`ported`, `horizon`) and tools theater are **archived** under
`_archive/port-era-2026-07/` — do not re-port or polish them. Engines stay
API-only (:8799 WorkLane, :8797 WorkForce; census in-process). **Citizen
entry is only `:8801` (pc-277 ONE DOOR).** Capture (create agent / work
order) lives in preferred AI chat + MCP/`wl`, not suite forms.

**Demo vs launch (founder, 2026-07-17):** this folder on :8801 against a
founded city with host engines already up is **demo**. **Launch** is when a
stranger can install BluePrint + WorkLane + WorkForce **or** found/adopt a
first folder and run without pre-existing 879x launchd. See
[`docs/SHIP_COORDINATION.md`](../docs/SHIP_COORDINATION.md). Prefer work that
moves the boot/install/adopt path, not only host-coupled polish.

**Install + live shell (founder, 2026-07-19):** north-star install is
**Homebrew** over real PyPI (ladder: pc-258/259, tp-215, wf-73 → pc-260).
In parallel, build toward a **live suite shell** — fast views over disk
truth, not full-page stills (**pc-261**; note
[`docs/research/suite-live-shell-2026-07.md`](../docs/research/suite-live-shell-2026-07.md)).
Truth stays files + engine stores; suite is a thin client (shell nav, composed
paint, SWR, then pulse, then selective SSE).

**Ship IA (founder 2026-07-24):** `/` = **Overview**; dig-in = **`/workspace-map`**
only. Work orders + agents are **on the Map** (tape, folder panels, people).
Retired peer URLs **302 → Map**: `/skin` · `/map` · `/explorer` · `/desk` ·
`/roster` · `/agents` · `/ported` · `/home` (Files list absorbed — pc-1278).
Detail deep links: `/ticket` · `/person` · `/read` · `/settings`.
Canon: [`docs/specs/SUITE_IA.md`](../docs/specs/SUITE_IA.md) ·
[`SHIP_BOUNDARY.md`](../docs/specs/SHIP_BOUNDARY.md).

## Ship shape (map-first)

- **Overview** (`/` · `/overview`) — system brief (KPIs, projects, activity).
- **Map** (`/workspace-map`) — hierarchy folder dig-in: folders, open counts, hands
  motion (park → approach → **peek folder** → live / return), work-order tape,
  paper drawer. Live shell: pulse + soft patches (not full-page stills).
- _(Project Files list `/home?project=` retired — 302 → Map; pc-1278.
  `.md` opens via paper drawer / `/read`.)_
- **Detail** — `/ticket?id=` · `/person?name=` · `/read?path=` · `/settings`.
- **Workspace calendar** (`/calendar.ics` · pc-1125) — VCALENDAR of open
  work-order **timer gates** (`gate_type=timer` + `gate_until`) and
  **`deadline:YYYY-MM-DD` labels** across all WorkLane product stores.
  Subscribe from Apple Calendar (File → New Calendar Subscription) at
  `http://127.0.0.1:8803/calendar.ics`. Optional HTML list:
  `/calendar`. **Convention:** founders/hands put real-world dates on
  tickets as those labels/gates — no second date store. Regenerated on
  request (≈30s suite cache); set Apple’s refresh interval on the
  subscription. Jobs stay off the feed by default.
- **Lumber** (archived under `_archive/port-era-2026-07/`): port-era peers
  (`desk_v1`, `roster_v1`); peer triad docs below this line are historical.

**Place law:** Map is the lay of the workspace. Project depth is Map dig-in;
the separate Files/Home list (`/home?project=`) is retired — 302 → Map (pc-1278).

**Home (place) doctrine — Finder layers** (host `/home` retired pc-1278;
kept as record — paper drawer / gold-border law lives on in Map dig-in):

| Layer | What | Behavior |
|---|---|---|
| **Trust** | Finder-parity of the *current* folder | Every entry surfaces (incl. Hidden). Path bar is navigation. |
| **Work** | All `.md` + managed folders (`AGENTS.md` inside) | Papers open **in-place** via the side drawer (`suite-paper.js`); full `/read` page remains for Cmd/Ctrl-click and deep links. Never leave BluePrint. **Gold border** = one signal: required BP law files (`AGENTS` / vendor pointers / `PERIMETER` / `CONTRACT` / `prompt`), managed folders, presence strip, and for-You. Ordinary papers stay plain. |
| **Scenery** | Non-md files | Visible, dimmed, not opened in-suite (cheap to maintain). |

`/law/<path>` redirects to `/read?path=`. Depth is unlimited via `&path=`.

**Hat doctrine (presence strip):** the same **You**, different digital hat by
depth — city Map = **Mayor**; project Home = **Owner of &lt;project&gt;**
with full work / who / access. **Path drill** (`&path=`) collapses to a thin
hat bar only (Finder folder · same project law · no extra required files) —
work/who/access are not per-folder government.

Vocabulary freeze (see [`docs/specs/SUITE_VOCABULARY.md`](../docs/specs/SUITE_VOCABULARY.md)):
**Workspace · Project · Map · Overview · Work orders · Agents · You**.
No Explorer·Desk·Agents peer triad on ship chrome. Class noun is **view**.
Horizon chips hidden until a product ships.

**Map vs lumber:** dig-in is **`/workspace-map`** only (`workspace_map.html`; was `skin_demo.html`).
`/home?project=` is absorbed into Map (pc-1278); `map_v1.html` is deleted lumber.
Old peer routes 302 to Map. Street annex `tools/map.html` / `:8796` remains lumber
— never the citizen door. Radial nodes = **folders**. Never label the diagram UI
as the census engine (API only).

Honest adoption: suite Map pillar owns dual paint + city APIs; condemned Office
render / street-map annex stay life-support only.

**Leftover port queue (pc-290):** full inventory of Office / cityhall /
`map.html` behaviors still missing from suite Map/Home (plus N/A lumber) lives
in [`docs/specs/SUITE_PORT_LEFTOVERS.md`](../docs/specs/SUITE_PORT_LEFTOVERS.md).
Children carry implementation; do not polish `:8796` renders.

**Mast law:** city place wears **`[CityFolder] — Map`**; project place wears
**`[Project] — Home`** (or folder segment under path drill). Desk/Roster:
**`[Folder] — Desk|Roster`**. City view (`/skin`) keeps the Map room brand
with subline “City view”.

**Peer door law (`suite-nav.js`):** place · Desk · Roster change **room** and
**preserve `?project=`**. Place door label is **Map** (city) or **Home**
(project). `&path=` is place-only (never on Desk/Roster doors). On the place
sheet, the place door is the **current** place URL (incl. path). Climb to
city via breadcrumb.

**Home · Overview:** each door has an operate surface (Home) and **Overview**
(verbose live brief). Overview is **not** a peer product door — it sits in the
**suite meta band** under the header bar (right), opposite optional path
context (left on Map/Home). Peer doors stay Map|Home · Desk · Roster only;
planned horizon chips share the right cluster on **every** operate room
(Map/Home · Desk · Roster · Overview — not Map-only). Meta band is suite
chrome — pages fill path left; they do not own Overview.
`/overview?room=map|home|desk|roster&project=` — place pillar shows as Map or
Home by depth.

**Roads, rings, and PERIMETER — how visual layers map to law (`docs/research/dual-skin-roads-perimeter-2026-07.md`):**

Both suite surfaces (text Map and `/skin`) render over the same city truth. The `/skin` demo exposes an **authority ring layout** and **road layers** that correspond directly to protocol law — do not collapse them.

| Ring (visual) | What | Law level |
|---|---|---|
| **Core** | You — human gates, all authority | L0 citizen / seat |
| **Mid** | Office staff (WorkForce L0 ops) | L0 contracts + roster staff sector |
| **Outer** | Project houses (managed folders) | L1 law (folder `AGENTS.md`) |

Three road layers — never merge them:

- **Layer A — attention (You ↔ house):** gold spoke when for-You count > 0 for a project. An **attention signal**, not a grant. Source: `/api/attention`.
- **Layer B — ops / episodic (Office staff ↔ house):** draw only when a staff worker has an **active shift targeting that house** or a declared PERIMETER row. Staff reach many houses, but the connection is **time-bounded** — a permanent road to every house is spaghetti.
- **Layer C — PERIMETER grants (declared cross-folder only):** parse city-root `PERIMETER.md` → `/api/city` `edges[]`. Kinds (`docs/specs/CITY_EDGES.md`): `consumes-http` (service line) · `export-lane` (export rail) · `press-pass` (badge, no road) · `reference-only` (faint one-way). **WIDTH LAW: empty PERIMETER = no Layer C roads.** Never infer edges from git remotes or folder adjacency.

L0 / L1 reading: a Layer C road is a **cross-L1 grant** — it requires a ratified row in the L0 city PERIMETER. Without a row, houses are sovereign and unconnected; they still appear in the outer ring, just road-free. Layer A gold spokes are **not grants** — they flow from the You's authority seat, not from PERIMETER.

**Shipped (2026-07-21 · historical file names — `skin_demo.html` is now `workspace_map.html`; `map_v1.html` since deleted):** Layer C paint on City view (`skin_demo.html` grant paths + export rail terminals + press-pass badges) and Blueprint Map (`map_v1.html` PERIMETER band + topology sketch). Empty `edges[]` shows an honest empty-registry note — never invents roads. Layer A attention spokes + Layer B staff-shift arcs + five-event motion + F13 hire/farewell/patrol live on `/skin` (pc-249 · pc-251 · pc-244). Research: `docs/research/dual-skin-roads-perimeter-2026-07.md` §7 / §9.

**Law at this level (pc-250) — per-depth paper drawer:**

On every operate room (Map · Home · Desk · Roster) and on the Person page, a
**"Law at this level"** control opens the suite paper reader (`suite-paper.js`
in-place drawer) for the authoritative law papers governing the current depth —
without leaving BluePrint. No engine URLs are exposed.

| Depth | "This level" | Papers (opened via `/law/<path>`) |
|---|---|---|
| City (Map · city Desk · city Roster) | City root folder | `AGENTS.md` (L0 charter, primary) · `PERIMETER.md` (edge grants, linked from reader) |
| Project (Home · project Desk · project Roster) | Managed folder `<slug>/` | `<slug>/AGENTS.md` (L1 house law) |
| Worker seat (Person page) | Named worker | `workers/<name>/CONTRACT.md` (L2 lane) · `workers/<name>/prompt.md` (L3 identity) — stacked law view (reuse person law stack) |

Law: the control is a **reader affordance only** — it never modifies law files,
never exposes raw engine paths, and never reads law from outside the founded
folder. Vendor pointers (`CLAUDE.md`, `GROK.md`) carry gold borders on Home as
required-paper signals; they are thin pointers to the L2 contract, not law
themselves, and are not surfaced by "Law at this level."

**For code worker (pc-250 implementation):** `/law/<rel-path>` already redirects
to `/read?path=`. Wire "Law at this level" as a button in the context strip (hat
zone or meta band) that fires `suite-paper.js` with the depth-appropriate path.
City Map → `AGENTS.md` with a "PERIMETER →" link inside the reader.
Project Home → `<slug>/AGENTS.md`. Desk/Roster: inherit the current depth's law
(city or project per `?project=` scope). Person page → stacked CONTRACT + prompt
(reuse existing person law stack pattern).

## Files

- `serve.py` — suite server (port 8801). Static pages + `/api/ground` +
  `/api/file` + `/api/tasks` + proxies citylens/workforce. `/` → Overview;
  retired page routes (`/map` · `/home` · `/skin` …) 302 → `/workspace-map`.
  `/law/*` → `/read`.
- `workspace_map.html` — **Map** dig-in at `/workspace-map` (was
  `skin_demo.html` at `/skin`; `map_v1.html` was the old Files page —
  deleted lumber): folders, rings, people over the founded folder; data
  from suite `/api/city` + `/api/people` + `/api/attention`. Productized
  as the Map (**pc-273**); ships in package-data. Theater (roads/motion):
  **pc-249** / **pc-251**.
- `suite-nav.js` — peer doors + place label/href helpers + **ticket jump**
  box in the meta band (`tp-207` / `tp207` → drawer; `/` or ⌘K focuses).
- `suite-paper.js` — Summary for papers (`/read?path=`) and Desk slips
  (`/ticket?id=`): **Scan** (edge rail) and **Read stage** (viewport-aware
  center sheet, soft-dim scene) per attention law (pc-272 /
  `docs/specs/SUITE_PERIMETER.md`). Long bodies / gate weight auto-promote;
  Stage ↔ Rail toggle; Full stays Cmd/Ctrl-click or "full page". Prev/next
  (←/→ · j/k · [/]); Esc / backdrop / ×.
- `read_v1.html` — paper reader (markdown rendered, stay in BluePrint).
- _(desk_v1.html, roster_v1.html, overview_v1.html retired — routes 302 to Map; pc-1215. map_v1.html deleted 2026-08-31 — `/home` 302 to Map; pc-1278.)_

## Local city config — `.protocolcity/`

Machine-local display preferences that are never exported or treated as city
law live in a dotdir at the city root (`{city-root}/.protocolcity/`):

| File | What | Law |
|---|---|---|
| `hidden.json` | Folder slugs hidden from Map/Home plots | Display-only (pc-239). **Never an operational scope** — engines, exports, backups, and patrols must never read this as an exclusion. |

Schema: `{ "note": "Display-only …", "hidden": ["slug", …] }`. Served by
`suite/serve.py` at `/api/hidden` (GET list · POST toggle).

**Owner-of-truth decision (pc-239):** `hidden.json` stays in `.protocolcity/`,
not in `PERIMETER.md` or `AGENTS.md`.

- `PERIMETER.md` owns edge grants (WIDTH LAW) — folder visibility is a viewer
  preference, not a permission boundary. Mixing them corrupts its single purpose.
- `AGENTS.md` owns agent instructions — machine-local display state is not
  instruction law, and placing it there risks workers reading it as an
  operational scope (exactly what the pc-239 "never operational" law bars).
- The dotdir at city root is the right home: hidden by design, outside any
  neighborhood repo, machine-local like `local/` inside a neighborhood.

Portability: this file does not travel with city exports. A fresh machine's
Map is unfiltered until its owner re-declares display preferences. If
multi-machine city sync ever ships, `.protocolcity/` is runtime evidence, not
versioned charter — the same distinction as `local/` vs `AGENTS.md`.

CLI integration (`protocolcity hide/unhide <folder>`) and citylens native
support are code work tracked in pc-239.

## Project local config — `local/` inside each project folder

Per-project runtime state that is display-only or ephemeral lives in a `local/`
directory **inside each project folder** (`<city-root>/<project>/local/`). Like
`.protocolcity/` at the city root, these files are machine-local and must be
gitignored inside each project's own repo. They never travel with city exports
or BluePrint archives.

### App doors and links (`local/doors.json`)

Declares the doors and related links shown on project Home. Served by
`suite/serve.py` at `/api/project/<slug>/doors` (GET returns list; POST full
replace for in-UI pin/edit/remove — pc-1172). Absent file → empty list, no
error. Host-action execute: `POST /api/project/<slug>/doors/run` with
`{ "index": N }` (loopback clients only).

Schema:

```json
{
  "doors": [
    { "label": "tradeOS", "url": "http://127.0.0.1:8788", "kind": "app" },
    { "label": "Grafana", "url": "http://127.0.0.1:3000", "kind": "link" },
    { "label": "Project Map", "kind": "suite", "path": "/workspace-map?project=tradeos" },
    {
      "label": "Station1 VNC",
      "kind": "host-action",
      "action": "run_script",
      "script": "kiosk/open-station.sh",
      "args": ["Station1", "--control"]
    },
    {
      "label": "Open folder",
      "kind": "host-action",
      "action": "open_path",
      "path": "."
    }
  ]
}
```

| Field | Required | Values | Meaning |
|---|---|---|---|
| `label` | yes | string ≤ 40 chars | Button / chip text displayed on Home |
| `kind` | no | `"app"` (default) · `"link"` · `"url"` · `"suite"` · `"host-action"` | Door type (see below) |
| `url` | for app/link/url | absolute `http(s)` URL | Opens in a new tab |
| `path` | for suite · open_path | suite path starting with `/`, or project-relative path | Suite navigation or Finder open |
| `action` | for host-action | `"open_path"` · `"run_script"` | Allowlisted host operation |
| `script` | for run_script | relative path under `scripts/` | e.g. `kiosk/open-station.sh` |
| `args` | optional | string list (safe charset) | Passed to the script (max 12) |

**Kinds**

| Kind | Renders as | Behavior |
|---|---|---|
| `app` / `url` | Primary gold chip | New-tab http(s) |
| `link` | Secondary strip chip | New-tab http(s) |
| `suite` | Primary chip | In-suite navigation (`path` only; no scheme) |
| `host-action` | Dashed primary chip | Confirm → `doors/run` on loopback |

Entries render in declaration order. Reorder / pin / edit from project Home
(**+ Pin** and chip tools). The `tradeOS` defaults (`http://127.0.0.1:8788`,
`kind: "app"`) are conventional, not hardcoded — any project sets its own doors
or none.

**Law:** `local/doors.json` is machine-local display config. It is **not** a
permission grant and must never be read by engines, export scripts, or patrols
as an operational scope. Host-actions are intentional pins of **already
allowlisted** project scripts / Finder paths — not free-form shell from the
browser. Suite binds loopback by default; `/doors/run` also rejects non-loopback
peers. An absent or empty `doors` array renders nothing (graceful empty state);
Home remains valid without it. No secrets in doors.json.

### Citizen notes (`local/notes.md`)

A plain markdown file for ephemeral notes, reminders, and runtime context about
the project. Served by `suite/serve.py` at `/api/project/<slug>/notes`
(GET returns raw markdown · POST body saves in-place). Rendered on project Home
as a read/write panel; editing in-suite saves back via POST. An absent
`notes.md` renders an empty editable panel (creates the file on first save).

**Law:** `local/notes.md` is runtime evidence — gitignored, machine-local, not
exported. Content must never be interpreted as city law, agent instruction, or
AGENTS.md substitute. Notes belong to You on this machine; they are not a
shared document.

### Gitignore expectation

Each project repo should gitignore its own `local/` directory (the city-wide
convention for ephemeral runtime evidence — see AGENTS.md). BluePrint does not
enforce this, but the close-out law for any feature that writes to `local/`
must verify the repo's `.gitignore` includes `local/`. Code worker: add
`local/` to `tradeOS/.gitignore` (and any other project repos that adopt
doors/notes) as part of the pc-242 implementation slice.

### API contract (for code worker)

Two new endpoints in `suite/serve.py`:

| Endpoint | Method | Body | Response |
|---|---|---|---|
| `/api/project/<slug>/doors` | GET | — | `{ "doors": [...] }` (empty list if absent) |
| `/api/project/<slug>/doors` | POST | `{ "doors": [...] }` full replace | `{ "ok": true, "doors": [...] }` (validated) |
| `/api/project/<slug>/doors/run` | POST | `{ "index": N }` | `{ "ok": true, ... }` host-action only; loopback |
| `/api/project/<slug>/notes` | GET | — | raw markdown string (empty string if absent) |
| `/api/project/<slug>/notes` | POST | raw markdown body | `{ "ok": true }` |

Path resolution: `<city-root>/<slug>/local/doors.json` and
`<city-root>/<slug>/local/notes.md`. `<city-root>` is the folder the suite
serves from (same root used by `/api/ground`). A project slug that does not map
to a real subfolder → 404.

**UI:** the Map project dig-in (`/workspace-map?project=<slug>`) paints doors
in the Open / Pin strip (`suite.placeOpen.*`; host-actions via `/doors/run`).
The old `/home` Home surface is retired (pc-1278); its notes panel is not ship
face (see [`docs/specs/SUITE_VIEWER.md`](../docs/specs/SUITE_VIEWER.md)),
though the notes API remains. City Map stays clean.

## Component kit (`suite/components/`, pc-294)

Vanilla ES modules — no React. Each component is
`mount(el, props) → { update, destroy }`. Pages own data; components own DOM.
Design authority:
[`docs/research/bp-suite-production-architecture-2026-07.md`](../docs/research/bp-suite-production-architecture-2026-07.md)
§5.

| Export | Module | Props (main) | A11y |
|---|---|---|---|
| `SuiteUI.ErrorBanner` | `error-banner.js` | `message`, `upstream?`, `onRetry?` | `role=alert` |
| `SuiteUI.EmptyState` | `empty-state.js` | `title`, `hint?`, `action?` | `role=region` + `aria-label` |
| `SuiteUI.LoadingBlock` | `loading-block.js` | `label?`, `variant: skeleton\|pulse`, `rows?` | `aria-busy=true` |
| `SuiteUI.Pathbar` | `pathbar.js` | `crumbs: [{ label, href? }]` | last crumb `aria-current=page` |
| `SuiteUI.Slip` | `slip.js` | `id`, `title`, `status?`, `age?`, `forYou?`, `loading?`, `href?` | composite `aria-label` |
| `SuiteUI.LiveTail` | `live-tail.js` | `url?`, `worker?`, `active?` | `role=log`; idle if no stream |

**Load on a room host** (after `suite.css` / before room script):

```html
<script type="module" src="/components/index.js"></script>
```

`index.js` assigns `window.SuiteUI` and auto-links `/components/suite-ui.css`
on first mount (tokens still come from `suite.css`).

**Adopted hosts (pc-299):** `desk_v1.html` (Slip + EmptyState + ErrorBanner +
Pathbar; route retired pc-1215), `workspace_map.html` (live Map — Finder/managed
tags remain Map-local siblings; `map_v1.html` deleted; was `skin_demo.html`,
module load only on City paint), `roster_v1.html` (Pathbar; route retired
pc-1215). Each host loads
`<script type="module" src="/components/index.js">` and awaits
`import("/components/index.js")` before first paint so `window.SuiteUI` is
ready (module scripts are deferred).

**Usage sketch (Desk tray — port-era `desk_v1`, since archived):**

```js
// after ensureSuiteUI():
const tray = document.getElementById("tray");
const errHost = document.getElementById("err");
const error = SuiteUI.ErrorBanner.mount(errHost, { message: "" });
// empty tray:
SuiteUI.EmptyState.mount(host, {
  title: "nothing waiting on You",
  hint: "Human gates and for-You work land here when filed.",
});
// on bootstrap 502:
error.update({
  message: "Desk unavailable (…)",
  upstream: "citylens / worklane",
  onRetry: () => redraw("retry"),
});
// row paint — <a class="slip"> hosts:
const a = document.createElement("a");
a.className = "slip";
tray.appendChild(a);
SuiteUI.Slip.mount(a, {
  id: "pc-299",
  title: "adopt component kit on Desk tray + Pathbar",
  status: "in_progress",
  forYou: true,
  href: "/ticket?id=pc-299",
});
// shared pathbar (Map/Desk/Roster #pathbar):
SuiteUI.Pathbar.mount(document.getElementById("pathbar"), {
  crumbs: [
    { label: "City", href: "/desk" },
    { label: "Desk" },
  ],
});
```

Served from `suite/` root via SimpleHTTP (`/components/*.js`,
`/components/suite-ui.css`) — no `serve.py` route map required.

### Component kit checklist (manual / adopter QA)

- [x] `/components/index.js` returns 200 on :8801; `window.SuiteUI` has all six mounts
- [x] ErrorBanner: empty message → hidden; non-empty → `role=alert` + visible Retry when `onRetry` set (Desk `#err`)
- [x] EmptyState: title in `aria-label`; tray/outbox empty placards on Desk
- [x] LoadingBlock: host `aria-busy=true`; skeleton rows; `prefers-reduced-motion` kills animation (Desk boot tray)
- [x] Pathbar: last crumb has `aria-current="page"`; middle crumbs are links (Map/Desk/Roster `#pathbar`)
- [x] Slip: `forYou` gold ring + label includes "for You"; tray rows via `SuiteUI.Slip.mount`
- [ ] LiveTail: no `url` / `active:false` → idle placard (no EventSource); stream error → status line *(not adopted this pass)*
- [x] `:focus-visible` gold ring on Retry / empty action / path links (suite-ui.css)
- [x] **pc-299:** Desk tray + Map/Desk/Roster pathbar adopters landed

## Suite smoke crawl (stranger-lens QA)

Before ship or after suite surface changes, run the thin HTTP crawler against a
live suite on :8801. It is suite-specific (not a tradeOS visual-sweep port) —
status codes + body sentinels for Map / Desk / Roster / Home / ported / read +
project doors/notes APIs. Report lands under gitignored `local/`:

```bash
# suite already up (launchd com.protocolcity.suite or python3 suite/serve.py)
python3 scripts/suite_smoke_crawl.py
# optional: SUITE_BASE=http://127.0.0.1:8801 PROJECT=tradeos python3 scripts/suite_smoke_crawl.py
```

Output: `local/visual-sweep-suite-YYYY-MM-DD.txt` (PASS/FAIL per path). Exit 1
on any failure or if suite is down.

## Development — editing suite HTML/JS (pc-769)

**The DX gap:** the live suite LaunchAgent (`com.protocolcity.suite`) runs from
the Homebrew Cellar site-packages, **not** from this repo. Edits to
`suite/*.html`, `suite/*.js`, or `suite/map/*.js` in the repo are invisible
to the running service until you copy them to both Cellar paths:

```
/opt/homebrew/Cellar/blueprint/<version>/libexec/lib/python3.11/site-packages/suite/
/opt/homebrew/Cellar/blueprint/<version>/libexec/lib64/python3.11/site-packages/suite/
```

**After any suite HTML/JS edit, sync to both paths:**

```bash
bash scripts/suite_sync_ui.sh
# then restart only if serve.py changed (launchd-owned when service installed):
blueprint serve
# never: blueprint stop && blueprint serve  — that bootouts launchd and leaves
# a shell orphan that dies with the terminal (pc-1072)
```

**Check for drift without copying (zero-change probe):**

```bash
bash scripts/suite_sync_ui.sh --check
# exits 0 = in sync, 1 = drift (lists mismatched / missing files)
```

The script targets the **live LaunchAgent** Cellar version (parses
`ProgramArguments` in `~/Library/LaunchAgents/com.protocolcity.suite.plist`),
not merely the highest `sort -V` directory under Cellar — so a sync cannot go
dark across version skew (pc-1030). If the plist is absent it falls back to
newest Cellar with a loud warning; if live ≠ newest it still syncs/checks the
live unit and exits non-zero with a banner. HTML/JS/CSS/py files are compared;
`__pycache__` and other generated dirs are excluded.

**When serve.py changes:** restart the suite service after sync (`blueprint stop
&& blueprint serve`) — Python modules are loaded at startup.

**For HTML/JS-only changes:** the suite serves static files on each request, so
a sync is enough without a restart.

**Dogfood mode (no copy needed — pc-788 / permanent founder host):** set
`BLUEPRINT_SUITE_DIR` so the LaunchAgent reads Map glass from the git tree —
no Cellar sync, no “I thought that was fixed” drift:

```bash
# Permanent (founder-present; persists in service.json + heal reinstalls):
blueprint service install --root ~/YourCity --force --dogfood
# or: --suite-dir /path/to/ProtocolCity

# One-shot shell only:
BLUEPRINT_SUITE_DIR=/path/to/ProtocolCity blueprint serve --root ~/YourCity
```

`BLUEPRINT_SUITE_DIR` is checked before importlib.resources, so it wins over the
Cellar copy. Chrome shows `+dogfood`. `scripts/suite_sync_ui.sh` no-ops when
the live plist has dogfood set.

On **release** hosts (default brew users) the sync script remains the close-out
path. See `docs/specs/DOGFOOD_AND_LOCAL_OPS.md`.

## Tickets

Anchor: pc-189 (ship cut) · Map port: see pc ticket filed 2026-07-16 ·
Desk port: tp ticket · Roster port: wf ticket · Reuse audit: pc ticket.

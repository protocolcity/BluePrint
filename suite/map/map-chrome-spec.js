/*! map-chrome-spec.js — folder-as-node seats + map legend SoT (pc-604/pc-631/pc-632/pc-635)
 *
 * Pure data for Workspace Map. Host (workspace_map.html) paints via
 * folderChromeLayout / renderMapLegend. Edit grammar here + host CSS together.
 */
(function (global) {
  "use strict";

  /**
   * Declarative interior seats — unit 50×40 (tab ~y0–12, body y12–40).
   * NOTHING stationary outside the silhouette.
   *
   * Tab is the *left* lip only (x≈2–18, y≈5–12). Body top is y≥12 full width.
   *
   *   · openBadge UV retired from paint (pc-892) — slot kept for layout compat only
   *   · name upper body — full width
   *   · stacks row L→R: you · hands · jobs · work · papers · instr
   *     (matches Settings Faces hierarchy; SoT shared via FOLDER_INTERIOR_SEATS pc-1075)
   *     you (👤 default · suite.youGlyph) = this project’s For You count · hide when 0
   *     hands = hired Agents · hide when 0
   *     jobs (⏰) = scheduled jobs · hide when 0
   *     work (🎫) = live open work orders · click → full WO overview
   *     papers (📄) = handbook only · hide when 0
   *     instr (📜) = planted Instructions · hide when 0 (own seat — not corner myth)
   *   · manila fill still carries work-signal ladder; no lip digit
   */
  var FOLDER_SEAT_SPEC = {
    /* Upper body — title alone (count is on tab, not beside name) */
    name: { ux: 25, uy: 16, ox: 0, oy: 0, face: false },
    /* Tab lip — right end of left tab (on manila, not body-title band) */
    openBadge: { ux: 15.5, uy: 7.5, ox: 0, oy: 0, face: false },
    /*
     * Inventory row — L→R you · hands · jobs · work · papers · instr.
     * Mirrors Settings Faces hierarchy (pc-1075): You · Agents · Staff · Jobs ·
     * Work orders · Papers · Instructions. Staff folds into the hands seat on Map.
     * UV defaults are full-row anchors; host packFolderInteriorRow (pc-899)
     * recenters only *present* seats so empty slots leave no middle hole.
     */
    you: { ux: 4.5, uy: 29, ox: 0, oy: 0, face: true },
    hands: { ux: 12.5, uy: 29, ox: 0, oy: 0, face: true },
    jobs: { ux: 20.5, uy: 29, ox: 0, oy: 0, face: true },
    work: { ux: 28.5, uy: 29, ox: 0, oy: 0, face: true },
    papers: { ux: 36.5, uy: 29, ox: 0, oy: 0, face: true },
    instr: { ux: 44.5, uy: 29, ox: 0, oy: 0, face: true },
  };

  /* pc-1075: canonical order — mirrors Settings Faces (You · Agents · Staff · Jobs ·
   * Work orders · Papers · Instructions). STACK_GLYPH_REGISTRY in settings_v1.html
   * must agree with this list (after the static You + Agents rows). */
  var FOLDER_INTERIOR_SEATS = [
    "you",
    "hands",
    "jobs",
    "work",
    "papers",
    "instr",
  ];
  /* Compatibility name for soft-reseat callers during the host extraction. */
  var FOLDER_LIP_SEATS = FOLDER_INTERIOR_SEATS;
  var FOLDER_SHAPE_SPEC = {
    minAspect: 1.2,
    preferredAspect: 1.28,
    maxAspect: 1.4,
    /* pc-720: bigger manila at every load tier so seat pitch + label fit */
    minWidth: 64,
    maxWidth: 148,
    widthPerLoad: 1 / 0.52,
    fullSeatsMinPx: 64,
    stackOnlyMinPx: 42,
  };

  /**
   * ONE scale system for seats + attention bubble + count dots (pc-867/pc-880).
   * Do not ratchet these down in drive-by polish — host reads chipPx/badgeR
   * from here. Folders grow with load; chip size stays constant.
   *
   *   chipPx     base MAP_CHIP (world units at scale 1)
   *   chipScale  paint multiplier (clamped chipScaleMin…Max)
   *   badgeR     stack inventory digits (hands/jobs/work — not papers)
   *   openBadgeR For You / Stuck lip bubble (= same visual weight as seats)
   *
   * Seat face grammar (Option A · pc-880 · pc-924 D · 6th seat):
   *   papers  — handbook presence only (no digit); never law
   *   instr   — 📜 Instructions presence only (no digit); hide when empty
   *   hands / jobs / work — legible count when n ≥ 1; hide when empty
   *   activity — folder edge + rail LIVE (never corner bubble)
   *   urgency — tab lip open# + manila ladder (not stack dots)
   */
  var FOLDER_INDICATOR_SPEC = {
    /* chipPx — hit-box base: governs hit-pad radius, badge offset, HIER_SEAT_HALF.
     * Not the rendered emoji face size — that is glyphFontPx below (pc-1117). */
    chipPx: 18,
    /* pc-880: was 5.5 — digits read as dots; 7 keeps face legible at chip scale */
    badgeR: 7,
    /* Attention bubble r ≈ chip half so ⭐ sits with inventory faces */
    openBadgeR: 8,
    chipScale: 0.9,
    chipScaleMin: 0.78,
    chipScaleMax: 1.0,
    /* pc-1117: CSS --type-display (suite.css:11) is the emoji face size.
     * glyphFontPx × chipScale = rendered glyph diameter in SVG px (26 × 0.9 = 23.4).
     * packFolderInteriorRow uses this to derive pitch so the interior row fits
     * within the card silhouette at every (card scale × seat count) combination. */
    glyphFontPx: 26,
  };

  function folderDetailTier(renderedWidthPx) {
    /* pc-843: prefer full seats; only shed when clearly tiny on screen */
    var px = Number(renderedWidthPx);
    if (!(px > 0) || px >= 56) return "full";
    if (px >= 36) return "stack";
    return "echo";
  }
  /*
   * Color / channel law (Map + Outline — one register, same meanings):
   *   soft gold dig focus     = current dig leaf only (Map glow · Outline row)
   *   solid gold chip/badge   = For You work (act-now gates — urgency)
   *   finder blue             = UI selection, links, FABs (not presence)
   *   managed membership      = View options + grey unmanaged (no green dots)
   * Presence ≠ For You: soft ambient edge vs solid count pill.
   * Never blue for “You are here.”
   */
  var CHANNEL_CHARTER =
    "soft gold = dig focus · solid gold = For You · blue = UI only · managed = view options";

  /**
   * Map text speaks the suite type ramp. Numeric pixels stay in suite.css;
   * these roles say which fitted-view size each world-space label targets.
   */
  /*
   * pc-719: folder face names use **label** (11px), not heading (16px).
   * Heading is masthead-scale; manila cards are chip-scale like the left rail.
   * pc-833: dig-focus leaf may promote to secondary (readable at dig center);
   * orbit children stay label/caption — never mast heading.
   */
  var MAP_TYPE_ROLE_SPEC = {
    /* Face names = label scale inside manila (pc-865); dig leaf may promote */
    folderName: "label",
    digFocusName: "secondary",
    secondary: "label",
    caption: "caption",
  };

  function fittedWorldFontSize(targetPx, pxPerWorld) {
    var target = Number(targetPx);
    var scale = Number(pxPerWorld);
    if (!(target > 0) || !(scale > 0)) return 0;
    return target / scale;
  }

  /**
   * Work-order signal ladder — one ranked state per folder, worst state wins.
   * Badge + fill share this state; border remains agent presence.
   */
  var WORK_SIGNAL_LADDER = [
    {
      /* id stays needs-you (CSS); citizen label = For You — one act-now product */
      id: "needs-you",
      label: "For You",
      cls: "needs-you",
      mark: "Y",
      filter: "for_you",
    },
    {
      id: "stuck",
      label: "Stuck",
      cls: "stuck",
      mark: "!",
      filter: "stalled",
    },
    {
      id: "flowing",
      label: "Flowing",
      cls: "flowing",
      mark: "▶",
      filter: "in_progress",
    },
    {
      id: "queued",
      label: "Queued",
      cls: "queued",
      mark: "",
      filter: "ready",
    },
    {
      id: "starved",
      label: "Starved",
      cls: "starved",
      mark: "○",
      filter: "ready",
    },
  ];

  /**
   * Shared Map + Outline legend — one register, both projections.
   * Every row must mean the same thing in Map and Outline.
   * Map-only paint (folder edge stroke idle/walk/live/fault) stays out;
   * those are stage chrome, not a shared channel.
   *
   * Rows:
   *   Folder fill — manila face colors (same ladder as Work; color swatches)
   *   Work        — open urgency emoji faces (Outline lockstep) — **status**, not seats
   *   Stacks      — you · work · papers · instr · jobs · hands (📜 under Stacks)
   *
   * Two channels (pc-1018 — do not conflate):
   *   Work badges (kind=badge)  = fixed ladder faces ⭐❗▶️◻○ — NOT suite.youGlyph
   *   Stacks you (map-symbol)   = live getYouGlyph() ← Settings → Faces · You
   * Hint on Work/Stacks rows paints as "· status" / "· your faces" in legend chrome.
   *
   * Inventory (pc-915/pc-942 — shown · intentional exclusion):
   *   SHOWN  Folder fill mini-manila swatches (needs-you…starved colors)
   *   SHOWN  Work faces ⭐ ❗ ▶️ ◻ ○  (same ladder; emoji for Outline; status only)
   *   SHOWN  Stack faces: you · work · paper · instr · job · hand (Settings live)
   *   OUT    Edge stroke idle/walk/live/fault — stage motion (README + fab title)
   *   OUT    Dig soft-gold focus · managed grey — dig leaf + View options, not key
   *   OUT    Count badge digits (badgeR) — quantity on a seat face, not a kind
   *   OUT    Transient FX / actors — theater, not shared channel
   *
   * face: on map-symbol items = fallback only when get*Glyph helpers unavailable.
   * Live paint prefers helpers so Settings suite.*Glyph stays lockstep (pc-915).
   * Work kind=badge faces are static status DNA — softRefresh never rebinds them.
   *
   * Keep lockstep with WORK_SIGNAL_LADDER, folder seats, Outline chips.
   */
  /* pc-900/pc-915: legend titles match ship paint (no retired lip open# myth). */
  var MAP_LEGEND_SPEC = [
    {
      /*
       * Folder face fills (manila ladder) — colors citizens actually see on
       * project folders. Work row below keeps emoji faces for Outline lockstep.
       * Founder dogfood 2026-08-02: legend was untruthful without these swatches.
       */
      label: "Folder fill",
      items: [
        {
          kind: "folder-swatch",
          cls: "needs-you",
          text: "For You",
          fill: "#e9c46a",
          title:
            "Gold manila tab/body — project has act-now work on You (gate_type=human).",
        },
        {
          kind: "folder-swatch",
          cls: "stuck",
          text: "Stuck",
          fill: "#c45a4a",
          title:
            "Red-tinted manila — blocked, stalled, or open with no routed hand.",
        },
        {
          kind: "folder-swatch",
          cls: "flowing",
          text: "In progress",
          fill: "#4a9b6a",
          title:
            "Green-tinted manila — a hand is live on this project (work-flowing fill).",
        },
        {
          kind: "folder-swatch",
          cls: "queued",
          text: "Ready",
          fill: "#fffdf8",
          title: "Neutral cream manila — open backlog waiting for a hand.",
        },
        {
          kind: "folder-swatch",
          cls: "starved",
          text: "Empty queue",
          fill: "#ebe6dc",
          title:
            "Pale manila — scheduled hands, nothing ready (empty feed).",
        },
      ],
    },
    {
      /* Status ladder only — not Settings Faces (pc-1018). */
      label: "Work",
      hint: "status",
      items: [
        {
          kind: "badge",
          cls: "needs-you",
          text: "For You",
          face: "⭐",
          title:
            "Act-now status (not Settings → Faces · You). Gold tab/body when this project needs You now. ⭐ is the fixed Work ladder mark — it does not follow suite.youGlyph. Your seat face is Stacks · You. Outline ⭐+n.",
        },
        {
          kind: "badge",
          cls: "stuck",
          text: "Stuck",
          face: "❗",
          title:
            "Status ladder — red tab/body wash when blocked, stalled, or open with no hand. Map fill only (no lip !#). Outline ❗. Fixed mark, not a Settings face.",
        },
        {
          kind: "badge",
          cls: "flowing",
          text: "In progress",
          face: "▶️",
          title:
            "Status ladder — green tab/body + green edge when a hand is live. Live open pile = Stacks work seat (🎫 default). Fixed ▶️ mark.",
        },
        {
          kind: "badge",
          cls: "queued",
          text: "Ready",
          /* Neutral manila — not a digit sample (🔢 misread as seat count). */
          face: "◻",
          title:
            "Status ladder — neutral manila for open backlog waiting for a hand. Ready depth in WO chips · work seat = live open count.",
        },
        {
          kind: "badge",
          cls: "starved",
          text: "Empty queue",
          face: "○",
          title:
            "Status ladder — pale manila when scheduled hands have nothing ready. Edge may still show approaching (blue dash).",
        },
      ],
    },
    {
      /* L→R seats: you · work · papers · instr · jobs · hands — Settings faces */
      label: "Stacks",
      hint: "your faces",
      items: [
        {
          kind: "map-symbol",
          symbol: "you",
          text: "You",
          /* Fallback only — live paint uses getYouGlyph() (default 👤). */
          face: "👤",
          title:
            "Your face from Settings → Faces · You (suite.youGlyph) + gold For You count. Not the Work ⭐ status mark. First seat (L) · hide when 0. Workspace total = left-rail You card.",
        },
        {
          kind: "map-symbol",
          symbol: "work",
          text: "Work orders",
          face: "🎫",
          title:
            "Live open WO pile — work glyph + count when n≥1. Click → full overview for this place.",
        },
        {
          kind: "map-symbol",
          symbol: "md",
          text: "Papers",
          face: "📄",
          title:
            "Root handbook .md only (README · docs · not law). Click → Handbook dig. Instructions are the next seat (📜) — never mixed into Papers.",
        },
        {
          kind: "map-symbol",
          symbol: "md",
          instruction: true,
          face: "📜",
          title:
            "Instructions — AGENTS/CLAUDE/GROK/PERIMETER. Own stack seat when law exists. Click → law dig + door “All instructions on board”. Not handbook.",
          text: "Instructions",
        },
        {
          kind: "map-symbol",
          symbol: "agent",
          text: "Agent",
          face: "✋",
          title:
            "Hired Agent (kind=lane) — claims work orders from a ready feed; persona sprite. Count when n≥1. Activity = edge stroke (approaching/live), not this bubble.",
        },
        {
          kind: "map-symbol",
          symbol: "staff",
          text: "Staff",
          face: "👔",
          title:
            "Staff ops seat (kind=job + staff=true): chief-of-staff · health-patrol · workspace-efficiency. Function-named sprite, distinct from Agents.",
        },
        {
          kind: "map-symbol",
          symbol: "job",
          text: "Job",
          face: "⏰",
          title:
            "Scheduled job (kind=job, plumbing) — ⏰ pile with count. Do not claim backlog.",
        },
      ],
    },
  ];

  /**
   * Canonical object→click matrix for Map + Outline (pc-1086).
   * Single source of truth — PLACE_OVERVIEW_REPORT.md and map/README.md
   * reference this instead of maintaining partial duplicates.
   *
   * Fields:
   *   id          machine-readable slug (checked by check_place_overview_report.py)
   *   label       human label
   *   surface     "map" | "outline" | "both"
   *   seat_id     matches FOLDER_INTERIOR_SEATS where applicable; null otherwise
   *   glyph       representative emoji; null for non-glyph objects
   *   opens       what clicking delivers (function names are authoritative)
   *   layer       "L1" | "L2" | "L3" | "board" | "scroll" per PLACE_OVERVIEW_REPORT
   *   scan        true = in-map Scan (right rail / dig panel); false = Full page / ext
   *   cmd_click   what ⌘/Ctrl-click delivers; null = no escape hatch
   *   hide_when   condition under which the element is absent; null = always rendered
   */
  var CLICK_MATRIX = [
    /* ── Map: workspace ──────────────────────────────────────────────── */
    {
      id: "workspace_badge",
      label: "Workspace badge (hub center)",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Workspace L1 overview — showWorkspaceDetail",
      layer: "L1",
      scan: true,
      cmd_click: "Finder (openFolderInFinder at workspace root)",
      hide_when: null,
    },
    /* ── Map: project folder ──────────────────────────────────────────── */
    {
      id: "folder_face_name",
      label: "Folder face / name",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Project L1 overview — openFolderInSuite → enterProjectDigIn (stays on Map)",
      layer: "L1",
      scan: true,
      cmd_click: "Finder",
      hide_when: null,
    },
    /* ── Map: interior seat badges (FOLDER_INTERIOR_SEATS order) ─────── */
    {
      id: "seat_you",
      label: "you seat · For You count",
      surface: "map",
      seat_id: "you",
      glyph: "👤",
      opens: "For You WO pile for this project — openProjectWorkOrders(filter:'for_you')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "For You count = 0",
    },
    {
      id: "seat_hands",
      label: "hands seat · agents count",
      surface: "map",
      seat_id: "hands",
      glyph: "✋",
      opens: "Agents-only list — openProjectSeatPanel('hands') → openMapPresenceSeatList",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "hired agent count = 0",
    },
    {
      id: "seat_jobs",
      label: "jobs seat · scheduled jobs count",
      surface: "map",
      seat_id: "jobs",
      glyph: "⏰",
      opens: "Jobs-only list — openProjectSeatPanel('jobs') → openMapPresenceSeatList(isJob)",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "job count = 0",
    },
    {
      id: "seat_work",
      label: "work seat · live open WO count",
      surface: "map",
      seat_id: "work",
      glyph: "🎫",
      opens: "Live open WO pile — openProjectSeatPanel('work') → openProjectWorkOrders(filter:'open')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "live open count = 0",
    },
    {
      id: "seat_papers",
      label: "papers seat · handbook count",
      surface: "map",
      seat_id: "papers",
      glyph: "📄",
      opens: "Handbook-only list Layer D (README/docs; law excluded) — openProjectSeatPanel('papers')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "handbook count = 0",
    },
    {
      id: "seat_instr",
      label: "instructions seat · law presence",
      surface: "map",
      seat_id: "instr",
      glyph: "📜",
      opens: "Instructions Layer C (planted law: AGENTS/CLAUDE/GROK/PERIMETER) — openProjectSeatPanel('instr'); door 'All instructions on board' (openBoardInstructionsOverview) is primary",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "no planted law at project root",
    },
    /* ── Map: actors under folder (live names) ───────────────────────── */
    {
      id: "live_name_under_folder",
      label: "Live name under folder body",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Person / job dig-in — inspectPerson → SuitePersonSheet (in-map)",
      layer: "L3",
      scan: true,
      cmd_click: "Full /person page",
      hide_when: "no live or on-approach actor at this folder",
    },
    /* ── Map: WO tape row ────────────────────────────────────────────── */
    {
      id: "wo_tape_row",
      label: "WO tape row (left rail + dig)",
      surface: "both",
      seat_id: null,
      glyph: null,
      opens: "Ticket drawer — SuitePaper.openTicket (in-map drawer)",
      layer: "L3",
      scan: true,
      cmd_click: "Full /ticket page",
      hide_when: null,
    },
    /* ── Map: pulse cells (project dig-in) ──────────────────────────── */
    {
      id: "pulse_for_you",
      label: "Pulse cell · For You",
      surface: "map",
      seat_id: null,
      glyph: "⭐",
      opens: "For You WO pile (digPulseActions.for_you); falls to Stuck filter if For You=0 and Stuck>0",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "pulse_map_work",
      label: "Pulse cell · Map work",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "WO pile by signal — stuck→stalled filter, starved→ready filter, else→open filter (digPulseActions.map_work)",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "pulse_presence",
      label: "Pulse cell · Presence",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Scroll 'Working on now' section in current panel (digPulseActions.presence)",
      layer: "scroll",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    /* ── Map: KPI chips (project dig-in strip) ───────────────────────── */
    {
      id: "kpi_status",
      label: "KPI chip · status / live",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Scroll 'Working on now' / agents section (buildProjectStats)",
      layer: "scroll",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "kpi_hands_jobs",
      label: "KPI chip · hands · jobs",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Scroll agents section (buildProjectStats)",
      layer: "scroll",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "kpi_live_open",
      label: "KPI chip · live open",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Filter open WOs + scroll Work orders — digInWoFilter='open' (buildProjectStats)",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "kpi_for_you",
      label: "KPI chip · For You",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Filter For You WOs + scroll For You — digInWoFilter='for_you' (buildProjectStats)",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "kpi_stuck",
      label: "KPI chip · stuck",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Filter stalled WOs + scroll Stuck — digInWoFilter='stalled' (buildProjectStats)",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "signal.id !== 'stuck'",
    },
    /* ── Map/Outline: pile chips (WO left-rail filter tabs) ──────────── */
    {
      id: "pile_chip_live",
      label: "Pile chip · live",
      surface: "both",
      seat_id: null,
      glyph: null,
      opens: "Filter WO pile to live open (in_progress / in_review) — MAP_WO_CHIP_FILTERS[0]",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "pile_chip_ready",
      label: "Pile chip · ready",
      surface: "both",
      seat_id: null,
      glyph: null,
      opens: "Filter WO pile to backlog/ready — MAP_WO_CHIP_FILTERS[1]",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "pile_chip_deferred",
      label: "Pile chip · deferred",
      surface: "both",
      seat_id: null,
      glyph: null,
      opens: "Filter WO pile to deferred / parked — MAP_WO_CHIP_FILTERS[2]",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    {
      id: "pile_chip_for_you",
      label: "Pile chip · For You",
      surface: "both",
      seat_id: null,
      glyph: "⭐",
      opens: "Filter WO pile to human-gated (for_you) — MAP_WO_CHIP_FILTERS[3]",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    /* ── Map: inspect-panel action doors ────────────────────────────── */
    {
      id: "door_all_work_orders",
      label: "Door · All work orders (N)",
      surface: "both",
      seat_id: null,
      glyph: null,
      opens: "Full live open WO pile — openProjectWorkOrders(filter:'open'); L1 WO rule: pile is never listed on overview, only behind this door",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "no joined WorkLane store",
    },
    {
      id: "door_all_instr",
      label: "Door · All instructions on board",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "Board-wide instructions overview — openBoardInstructionsOverview (full instructions panel; not a new page)",
      layer: "board",
      scan: false,
      cmd_click: null,
      hide_when: null,
    },
    /* ── Open entries (place-open chip row) ──────────────────────────── */
    {
      id: "place_open_chip",
      label: "Open entry chip (product port / personal pin)",
      surface: "map",
      seat_id: null,
      glyph: null,
      opens: "External URL — window.open in new tab (place-open-chip[data-entry-href])",
      layer: "L1",
      scan: false,
      cmd_click: null,
      hide_when: "no joined store and no personal pins",
    },
    /* ── Outline: row ────────────────────────────────────────────────── */
    {
      id: "outline_row",
      label: "Outline row (project name)",
      surface: "outline",
      seat_id: null,
      glyph: null,
      opens: "Project L1 overview + map dig-in — _outlineEnterPlot → showProjectDetail (same as folder face click)",
      layer: "L1",
      scan: true,
      cmd_click: null,
      hide_when: null,
    },
    /* ── Outline: project chips ──────────────────────────────────────── */
    {
      id: "ol_for_you",
      label: "Outline chip ⭐ For You",
      surface: "outline",
      seat_id: null,
      glyph: "⭐",
      opens: "For You WO pile — _outlineChipAction('for_you') → openProjectWorkOrders(filter:'for_you')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "For You count = 0",
    },
    {
      id: "ol_stuck",
      label: "Outline chip ❗ Stuck",
      surface: "outline",
      seat_id: null,
      glyph: "❗",
      opens: "Stalled filter + map dig-in — _outlineChipAction('stuck') → stalled rail + scroll Stuck section",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "signal.id !== 'stuck'",
    },
    {
      id: "ol_flowing",
      label: "Outline chip ▶️ In progress",
      surface: "outline",
      seat_id: null,
      glyph: "▶️",
      opens: "Live open WO pile — _outlineChipAction('open')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "signal.id !== 'flowing' or For You / Stuck chip already shown",
    },
    {
      id: "ol_open",
      label: "Outline chip 🎫 N live open WOs",
      surface: "outline",
      seat_id: null,
      glyph: "🎫",
      opens: "Live open WO pile — _outlineChipAction('open') → openProjectSeatPanel('work')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "live open count = 0",
    },
    {
      id: "ol_starved",
      label: "Outline chip ○ Empty queue",
      surface: "outline",
      seat_id: null,
      glyph: "○",
      opens: "Work seat panel / open pile — _outlineChipAction('open')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "signal.id !== 'starved'",
    },
    {
      id: "ol_hands",
      label: "Outline chip ✋ N agents",
      surface: "outline",
      seat_id: null,
      glyph: "✋",
      opens: "Agents-only list — _outlineChipAction('hands') → openProjectSeatPanel('hands')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "agent count = 0",
    },
    {
      id: "ol_jobs",
      label: "Outline chip ⏰ N jobs",
      surface: "outline",
      seat_id: null,
      glyph: "⏰",
      opens: "Jobs-only list — _outlineChipAction('jobs') → openProjectSeatPanel('jobs')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "job count = 0",
    },
    {
      id: "ol_papers",
      label: "Outline chip 📄 N handbook papers",
      surface: "outline",
      seat_id: null,
      glyph: "📄",
      opens: "Handbook-only list — _outlineChipAction('papers') → openProjectSeatPanel('papers')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "non-law paper count = 0",
    },
    {
      id: "ol_instr",
      label: "Outline chip 📜 instructions",
      surface: "outline",
      seat_id: null,
      glyph: "📜",
      opens: "Instructions Layer C — _outlineChipAction('instr') → openProjectSeatPanel('instr')",
      layer: "L2",
      scan: true,
      cmd_click: null,
      hide_when: "no planted law at project root (boolean presence; no count digit)",
    },
  ];

  global.MapChromeSpec = {
    FOLDER_SEAT_SPEC: FOLDER_SEAT_SPEC,
    FOLDER_INTERIOR_SEATS: FOLDER_INTERIOR_SEATS,
    FOLDER_LIP_SEATS: FOLDER_LIP_SEATS,
    FOLDER_SHAPE_SPEC: FOLDER_SHAPE_SPEC,
    FOLDER_INDICATOR_SPEC: FOLDER_INDICATOR_SPEC,
    folderDetailTier: folderDetailTier,
    CHANNEL_CHARTER: CHANNEL_CHARTER,
    MAP_TYPE_ROLE_SPEC: MAP_TYPE_ROLE_SPEC,
    fittedWorldFontSize: fittedWorldFontSize,
    WORK_SIGNAL_LADDER: WORK_SIGNAL_LADDER,
    MAP_LEGEND_SPEC: MAP_LEGEND_SPEC,
    CLICK_MATRIX: CLICK_MATRIX,
  };
})(typeof window !== "undefined" ? window : globalThis);

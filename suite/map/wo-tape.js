/*! wo-tape.js — Work-order tape store + render (pc-1248 Phase 3-B)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4 Phase 3).
 * Module-scope tape state lives here only — host calls the public API.
 *
 * Browser: window.WoTape
 * Public: { init, paint } plus bridge accessors used by Map host
 * during the strangler (filter/scope, desk cache, slip meta, beats).
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    getModel: null,
    getLastCity: null,
    getLastPeople: null,
    getLastAtt: null,
    getLastTpScene: null,
    getPrevTransitionIds: null,
    flashHudNote: null,
    storeSlugEquivalents: null,
    prodFromTid: null,
    resolveSlipProduct: null,
    displaySlipProduct: null,
    mapFolderSlugSet: null,
    isOrphanDemoSlip: null,
    forYouAttItems: null,
    forYouCountsByProduct: null,
    forYouUrgencyBoost: null,
    forYouCategoryFromSlip: null,
    forYouProductLabel: null,
    applyWorkspaceWoKpiFilter: null,
    openCount: null,
    normKey: null,
    listFilterQueryMatch: null,
    wireMapEntityPreview: null,
    selectMapEntity: null,
    clearMapEntityPreviewKind: null,
    syncMapEntitySelection: null,
    focusProjectOnMap: null,
    findPlotBySlug: null,
    softPatchHierarchyBubbles: null,
    softPatchLotOpenCounts: null,
    softPatchCityFolderOpenBadge: null,
    softRefreshOpenDigSurfaces: null,
    paintHygieneSurfaces: null,
    transitionVerb: null,
    fetchJsonTimeout: null,
    getAttentionByProduct: null,
    seatHandFromTask: null,
    deskProductForPlot: null,
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  function hostModel() {
    var g = H("getModel");
    return g ? g() : null;
  }

  var _lastAtt = null;
  var _lastTpScene = null;
  var _lastCityData = null;
  var _lastPeople = null;

  function syncHost() {
    var g;
    g = H("getLastAtt");
    _lastAtt = g ? g() : _lastAtt;
    g = H("getLastPeople");
    _lastPeople = g ? g() : _lastPeople;
    g = H("getLastCity");
    _lastCityData = g ? g() : _lastCityData;
    g = H("getLastTpScene");
    _lastTpScene = g ? g() : _lastTpScene;
  }

  function hostRepaint(city, people, att, tpScene) {
    /* Prefer full host orchestrator (agents + tape + hygiene). */
    var fn = H("repaintInsights");
    if (fn) {
      fn();
      return;
    }
    paint({
      city: city,
      people: people,
      att: att,
      tpScene: tpScene,
    });
  }

  function flashHudNote(msg) {
    var fn = H("flashHudNote");
    if (fn) return fn(msg);
  }
  function storeSlugEquivalents(s) {
    var fn = H("storeSlugEquivalents");
    return fn ? fn(s) : [];
  }
  function normalizeStoreSlug(s) {
    if (typeof WoBuckets !== "undefined" && WoBuckets.normalizeStoreSlug) {
      return WoBuckets.normalizeStoreSlug(s);
    }
    return String(s || "")
      .toLowerCase()
      .trim();
  }
  function prodFromTid(tid) {
    var fn = H("prodFromTid");
    return fn ? fn(tid) : "";
  }
  function resolveSlipProduct(prod, tid) {
    var fn = H("resolveSlipProduct");
    return fn ? fn(prod, tid) : normalizeStoreSlug(prod) || "unknown";
  }
  function displaySlipProduct(prod) {
    var fn = H("displaySlipProduct");
    return fn ? fn(prod) : String(prod || "");
  }
  function mapFolderSlugSet() {
    var fn = H("mapFolderSlugSet");
    return fn ? fn() : {};
  }
  function isOrphanDemoSlip(row, folderSlugs) {
    var fn = H("isOrphanDemoSlip");
    return fn ? fn(row, folderSlugs) : false;
  }
  function forYouAttItems(items) {
    var fn = H("forYouAttItems");
    return fn ? fn(items) : items || [];
  }
  function forYouCountsByProduct(items) {
    var fn = H("forYouCountsByProduct");
    return fn ? fn(items) : {};
  }
  function forYouUrgencyBoost(it) {
    var fn = H("forYouUrgencyBoost");
    return fn ? fn(it) : 0;
  }
  function forYouCategoryFromSlip(r) {
    var fn = H("forYouCategoryFromSlip");
    return fn ? fn(r) : { face: "decide", label: "Decide" };
  }
  function forYouProductLabel(prod) {
    var fn = H("forYouProductLabel");
    return fn ? fn(prod) : String(prod || "");
  }
  function applyWorkspaceWoKpiFilter(f) {
    var fn = H("applyWorkspaceWoKpiFilter");
    if (fn) return fn(f);
  }
  function openCount(n) {
    var fn = H("openCount");
    return fn ? fn(n) : 0;
  }
  function normKey(k) {
    var fn = H("normKey");
    return fn ? fn(k) : String(k || "").toLowerCase();
  }
  function listFilterQueryMatch(parts, q) {
    var fn = H("listFilterQueryMatch");
    return fn ? fn(parts, q) : true;
  }
  function wireMapEntityPreview(el, maker) {
    var fn = H("wireMapEntityPreview");
    if (fn) return fn(el, maker);
  }
  function selectMapEntity(ent) {
    var fn = H("selectMapEntity");
    if (fn) return fn(ent);
  }
  function clearMapEntityPreviewKind(k) {
    var fn = H("clearMapEntityPreviewKind");
    if (fn) return fn(k);
  }
  function syncMapEntitySelection() {
    var fn = H("syncMapEntitySelection");
    if (fn) return fn();
  }
  function focusProjectOnMap(slug, plot, extra) {
    var fn = H("focusProjectOnMap");
    if (fn) return fn(slug, plot, extra);
  }
  function findPlotBySlug(slug) {
    var fn = H("findPlotBySlug");
    return fn ? fn(slug) : null;
  }
  function softPatchHierarchyBubbles() {
    var fn = H("softPatchHierarchyBubbles");
    if (fn) return fn();
  }
  function softPatchLotOpenCounts() {
    var fn = H("softPatchLotOpenCounts");
    if (fn) return fn();
  }
  function softPatchCityFolderOpenBadge() {
    var fn = H("softPatchCityFolderOpenBadge");
    if (fn) return fn();
  }
  function softRefreshOpenDigSurfaces() {
    var fn = H("softRefreshOpenDigSurfaces");
    if (fn) return fn();
  }
  function transitionVerb(t) {
    var fn = H("transitionVerb");
    if (fn) return fn(t);
    return "update";
  }
  function isYouishSeat(name) {
    return global.AgentsPanel && AgentsPanel.isYouishSeat
      ? AgentsPanel.isYouishSeat(name)
      : /^(you|founder|founder-terminal)$/i.test(String(name || "").trim());
  }
  function seatHandFromLabels(labels) {
    return global.AgentsPanel && AgentsPanel.seatHandFromLabels
      ? AgentsPanel.seatHandFromLabels(labels)
      : "";
  }
  function seatHandFromTask(t) {
    var fn = H("seatHandFromTask");
    if (fn) return fn(t);
    return global.AgentsPanel && AgentsPanel.seatHandFromTask
      ? AgentsPanel.seatHandFromTask(t)
      : "";
  }
  function deskProductForPlot(p) {
    var fn = H("deskProductForPlot");
    return fn ? fn(p) : "";
  }
  function isDeferredGate(gateType, gateNote) {
    if (
      typeof WoBuckets !== "undefined" &&
      WoBuckets &&
      typeof WoBuckets.isDeferredGate === "function"
    ) {
      return WoBuckets.isDeferredGate(gateType, gateNote);
    }
    var gt = String(gateType == null ? "" : gateType)
      .toLowerCase()
      .trim();
    return gt === "deferred";
  }

  var prevTransitionIds = null;
  function readPrevTransitionIds() {
    var g = H("getPrevTransitionIds");
    if (g) {
      var v = g();
      if (v) prevTransitionIds = v;
    }
    return prevTransitionIds;
  }

  let _tapeSig = "";
  let _tapeOrderSig = "";
  let _tapeEverBuilt = false;
  let _chipSig = "";
  let _chipBuilt = false;
  let _lastSlipRows = null;
  const LIST_FILTER_MIN = 12;

  function woFilterFromQuery() {
    /* pc-1345: Overview parked hop — /workspace-map?wo=deferred|ice|parked */
    try {
      if (typeof global.location === "undefined" || !global.location) return "";
      var raw = String(
        new URLSearchParams(global.location.search || "").get("wo") || ""
      )
        .toLowerCase()
        .trim();
      if (raw === "deferred" || raw === "ice" || raw === "parked") return "deferred";
    } catch (eQ) {}
    return "";
  }

  let mapWoFilter = woFilterFromQuery() || "all"; /* pc-485: total overview is the product default */
  let _woQueryScrolled = false;
  /* pc-605: when set, WO tape scopes to this product/slug (open# click) */
  let mapWoProjectKey = "";
  /*
   * pc-1044: list cap is per filter source.
   * - Workspace scope: up to MAP_WO_LIST_CAP rows across ALL projects (not
   *   MAP_WO_LIST_CAP per store). Cap badge must say "workspace-wide".
   * - Project dig-in: up to MAP_WO_LIST_CAP rows for that one store.
   * Chip tallies stay uncapped via /api/wo-gate-counts (count ≠ list length).
   * pc-1314: workspace filter=all is a short what-moved digest (not this cap).
   */
  const MAP_WO_LIST_CAP = 100;
  const MAP_WO_DIGEST_CAP = 24; /* pc-1314: workspace what-moved strip */
  const MAP_WO_DESK_TTL_MS = 20000;
  /* Last product key used to fill _woDeskCache / _woGateCounts ("" = workspace) */
  let _woDeskCacheScope = "";
  /*
   * pc-921 / pc-918: short ## Glance + last-known status for live strip
   * enrichment. Light /api/tasks should ship glance; when it does not
   * (stale serve) or SSE lands title-only, single-task hydrate fills this map.
   */
  const _slipMetaByTid = Object.create(null);
  /*
   * pc-546: per-product live/deferred heat from the open-family dual-read.
   * Folder fill / bubble size / open badge prefer live; ice is secondary.
   * Keys = lowercase product/slug aliases. Cold index → fall back to store raw open.
   */
  let _folderHeatByKey = Object.create(null);
  let _folderHeatAt = 0;
  /* pc-490: show text filter when a scoped rail has this many+ rows */
  /** Left-rail tape text filter (sticky across soft repaints; cleared on Esc). */
  let mapWoTextFilter = "";
  let _mapTapeFilterWired = false;

  const MAP_WO_FILTERS = [
    "live",
    "deferred",
    "for_you",
    "yours", /* pc-601: worker:you list — not gold */
    "ready",
    "open", /* alias → live (pc-547) */
    "in_progress",
    "in_review",
    "stalled",
    "done",
    "all",
  ];
  /* Compact pile doors only; total pill owns the live all-status feed. */
  const MAP_WO_CHIP_FILTERS = [
    "live",
    "ready",
    "deferred",
    "for_you",
  ];
  /* filter → { rows, at, loading } — desk-backed list per chip */
  let _woDeskCache = {};
  /*
   * pc-547 / pc-688: chip tallies are authoritative (uncapped /api/wo-gate-counts
   * + folder.store.ready). Lists stay capped at MAP_WO_LIST_CAP — count ≠ length.
   * pc-1044: when mapWoProjectKey is set, counts/lists are product-scoped.
   * pc-1065: scope stamp + gen guard — never paint workspace live/ready/deferred
   * beside a project-scoped for-you (stale in-flight fetch must not win).
   */
  let _woGateCounts = {
    live: null,
    deferred: null,
    ready: null,
    /* deskScopeKey() that produced these tallies ("" = workspace) */
    scope: "",
    at: 0,
    loading: false,
  };
  /* Bumped on every open-family fetch start; stale resolves discard. */
  let _woOpenFamilyGen = 0;
  let _glanceHydrateInflight = Object.create(null);
  /* pc-918: tids already hydrated this session (even if Glance empty) */
  let _glanceHydrateDone = Object.create(null);
  const _deskListInflight = Object.create(null);
  let _deskListChain = Promise.resolve();
  let _woDeskLastError = "";
  /*
   * Client live activity ring — SSE + local events promote to top of WO strip
   * before the next tp-scene poll (true "what's happening" feed).
   */
  let _liveActivityFeed = [];
  const LIVE_ACTIVITY_MAX = 80;
  const _pendingTapeBeats = Object.create(null);
  /* tid:kind → last play ms — stops soft-patch replaying CSS beats (pc-898) */
  let _playedTapeBeats = Object.create(null);
  const TAPE_BEAT_CLASSES = [
    "is-feed-filed-beat",
    "is-feed-claimed-beat",
    "is-feed-done-beat",
    "is-feed-comment-beat",
    "is-label-flash",
  ];


  /** pc-452: set the left Work orders view + repaint the feed. */
  function setMapWoFilterFromInspect(filter) {
    const f = normalizeWoFilter(filter);
    mapWoFilter = f;
    _tapeSig = "";
    _chipSig = "";
    _chipBuilt = false;
    function repaint() {
      if (true && hostModel()) {
        hostRepaint(
          hostModel().city,
          hostModel().workers,
          _lastAtt,
          typeof _lastTpScene !== "undefined" ? _lastTpScene : null
        );
      }
    }
    try {
      if (typeof ensureWoDeskFilter === "function" && f !== "all") {
        ensureWoDeskFilter(f, repaint);
      }
    } catch (eEns) {}
    try {
      repaint();
    } catch (ePaint) {}
    const rail =
      document.getElementById("map-rail-wo") ||
      document.getElementById("map-mod-wo");
    if (rail) {
      try {
        rail.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } catch (eR) {}
    }
  }


  function ensureMapTapeFilterWired() {
    if (_mapTapeFilterWired) return;
    const input = document.getElementById("map-tape-filter");
    if (!input) return;
    _mapTapeFilterWired = true;
    input.addEventListener("input", function () {
      mapWoTextFilter = input.value || "";
      if (true && hostModel()) {
        try {
          hostRepaint(
            hostModel().city,
            {
              in_flight: (hostModel().workers || [])
                .filter(function (w) {
                  return w && w.working;
                })
                .map(function (w) {
                  return w.name;
                }),
              sectors: [],
            },
            _lastAtt,
            _lastTpScene
          );
        } catch (eR) {}
      }
    });
    input.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      e.preventDefault();
      e.stopPropagation();
      if (input.value) {
        input.value = "";
        mapWoTextFilter = "";
        input.dispatchEvent(new Event("input"));
      }
    });
  }


  function syncMapTapeFilterChrome(preTextCount, shownCount) {
    ensureMapTapeFilterWired();
    const wrap = document.getElementById("map-tape-filter-wrap");
    const input = document.getElementById("map-tape-filter");
    const meta = document.getElementById("map-tape-filter-meta");
    if (!wrap || !input) return;
    const show = preTextCount >= LIST_FILTER_MIN || !!String(mapWoTextFilter || "").trim();
    wrap.hidden = !show;
    if (!show) return;
    if (input.value !== (mapWoTextFilter || "")) {
      /* Soft repaint — don't clobber caret while typing */
      if (document.activeElement !== input) {
        input.value = mapWoTextFilter || "";
      }
    }
    if (meta) {
      const q = String(mapWoTextFilter || "").trim();
      if (q) {
        meta.hidden = false;
        meta.textContent = shownCount + " of " + preTextCount + " match";
      } else {
        meta.hidden = true;
        meta.textContent = "";
      }
    }
  }


  /** Canonical store slug for desk scope (pc-1044). */
  function deskScopeKey() {
    return mapWoProjectKey ? normalizeStoreSlug(mapWoProjectKey) : "";
  }


  /**
   * pc-1065: only trust chip tallies whose scope matches the current dig-in.
   * Returns null when counts are missing, loading, or from another scope.
   */
  function trustedWoGateCounts() {
    const want = deskScopeKey();
    if (
      !_woGateCounts ||
      _woGateCounts.live == null ||
      String(_woGateCounts.scope || "") !== want
    ) {
      return null;
    }
    return _woGateCounts;
  }


  /**
   * Invalidate desk list/count caches when dig-in scope changes so a fresh
   * project dig never reuses the workspace pile under a project header.
   */
  function ensureWoDeskScopeFresh() {
    const scope = deskScopeKey();
    if (_woDeskCacheScope === scope) return;
    _woDeskCacheScope = scope;
    _woDeskCache = {};
    /* Invalidate any in-flight open-family resolve for the previous scope. */
    _woOpenFamilyGen += 1;
    _woGateCounts = {
      live: null,
      deferred: null,
      ready: null,
      scope: scope,
      at: 0,
      loading: false,
    };
  }

  function normalizeWoFilter(f) {
    f = String(f || "all");
    if (f === "tape" || f === "everything") return "all";
    /* pc-547: open reading = live (non-ice); ice/park aliases → deferred */
    if (f === "open" || f === "open_live") return "live";
    if (f === "ice" || f === "open_deferred" || f === "deferred_open")
      return "deferred";
    if (f === "need_you") return "for_you";
    if (f === "your_list" || f === "you_list" || f === "worker_you") return "yours";
    if (MAP_WO_FILTERS.indexOf(f) < 0) return "all";
    return f;
  }


  /**
   * pc-605: open# on a folder → left WO rail focused on that project’s open work.
   * Face/name dig-in stays full project overview; badge is the WO shortcut.
   */
  function focusProjectWorkOrders(plotOrSlug, filter) {
    const key = String(
      (plotOrSlug && (plotOrSlug.slug || plotOrSlug.name || plotOrSlug.product)) ||
        plotOrSlug ||
        ""
    )
      .toLowerCase()
      .trim();
    mapWoProjectKey = key;
    const f = normalizeWoFilter(filter || "live");
    setMapWoFilterFromInspect(f);
    try {
      flashHudNote(
        (key || "project") +
          " · work orders" +
          (f === "live" ? " (live open)" : " · " + f.replace(/_/g, " "))
      );
    } catch (eN) {}
  }


  function clearMapWoProjectScope() {
    mapWoProjectKey = "";
  }


  /**
   * pc-692: dig-in WO controls share one grammar with the left rail.
   * Dig-in glance "open" → left-rail live; for You maps 1:1.
   * Sets mapWoProjectKey + filter so the city list matches the dig-in pile.
   */
  function syncDigInWoToLeftRail(plotOrSlug, digFilter) {
    const raw = String(digFilter || "open").toLowerCase();
    /* Dig glance filters map 1:1 onto left-rail WO doors */
    let leftFilter = "live";
    if (raw === "for_you" || raw === "need_you") leftFilter = "for_you";
    else if (raw === "stalled" || raw === "stuck") leftFilter = "stalled";
    else if (raw === "deferred" || raw === "ice") leftFilter = "deferred";
    else if (raw === "ready" || raw === "queued") leftFilter = "ready";
    else if (raw === "open" || raw === "live") leftFilter = "live";
    focusProjectWorkOrders(plotOrSlug, leftFilter);
  }


  /** pc-692/pc-767: WorkLane engine + scope line (always painted). */
  function mapWoScopeChromeText() {
    const f = normalizeWoFilter(mapWoFilter);
    const filterBit =
      f === "all"
        ? ""
        : f === "live"
          ? "live open"
          : f === "deferred"
            ? "deferred"
            : f === "ready"
              ? "ready"
              : f === "for_you"
                ? "for You"
                : f === "yours"
                  ? "your list"
                  : f.replace(/_/g, " ");
    const base = mapWoProjectKey
      ? "WorkLane (WOs) · " + mapWoProjectKey
      : "WorkLane (WOs) · workspace";
    return base + (filterBit ? " · " + filterBit : "");
  }


  /**
   * pc-1044: exact store-slug match (alias-normalized), never bidirectional
   * substring — worklane vs workforce must not cross-match.
   */
  function rowMatchesProjectScope(r) {
    if (!mapWoProjectKey) return true;
    const want = storeSlugEquivalents(mapWoProjectKey);
    if (!want.length) return true;
    const prod = normalizeStoreSlug(r.prod || r.product || r.focus || "");
    if (prod && want.indexOf(prod) >= 0) return true;
    const fromTid = normalizeStoreSlug(prodFromTid(r.tid || r.id || ""));
    if (fromTid && want.indexOf(fromTid) >= 0) return true;
    return false;
  }

  /* pc-1396: HTML escape lives in /esc.js */
  var escAttr = function (s) { return global.__bp.escAttr(s); };
  var escHtml = function (s) { return global.__bp.esc(s); };

  function slipIsWorkerYou(r) {
    const labs = r.labels || r.labelList || [];
    if (Array.isArray(labs)) {
      for (let i = 0; i < labs.length; i++) {
        if (String(labs[i] || "").toLowerCase() === "worker:you") return true;
      }
    }
    const s = String(r.labelStr || r.labStr || "").toLowerCase();
    return s.indexOf("worker:you") >= 0;
  }

  function slipStatusKey(r) {
    return String((r && (r.status || r.stamp)) || "")
      .toLowerCase()
      .replace(/ /g, "_");
  }

  /* Host pile + tape chips share this filter. Must stay module-scope —
   * a paint() nest left host call sites as ReferenceError (blank Map). */
  function rowMatchesWoFilter(r, filt) {
    if (!rowMatchesProjectScope(r)) return false;
    const f = normalizeWoFilter(filt || mapWoFilter);
    const st = slipStatusKey(r);
    const stamp = String((r && r.stamp) || "").toLowerCase();
    const deferred =
      !!(r && r.isDeferred) ||
      isDeferredGate(
        (r && (r.gateType || r.gate_type)) || "",
        (r && (r.gateNote || r.gate_note)) || ""
      ) ||
      stamp === "deferred" ||
      stamp.indexOf("deferred") >= 0;
    if (f === "all") return true;
    if (f === "yours") {
      /* pc-601: worker:you personal list — quiet, never gold */
      if (deferred && !slipIsWorkerYou(r) && !(r && r.isWorkerYou)) return false;
      return !!(r && r.isWorkerYou) || slipIsWorkerYou(r);
    }
    if (f === "for_you") {
      /* Attention-driven only — never gold deferred parks (wl-257) */
      if (deferred) return false;
      /* worker:you personal list is not gold For You */
      if ((r && r.isWorkerYou) || slipIsWorkerYou(r)) return false;
      return (
        !!(r && r.isYou) ||
        stamp.indexOf("for you") >= 0 ||
        stamp.indexOf("need") >= 0 ||
        st.indexOf("for_you") >= 0 ||
        st.indexOf("need") >= 0
      );
    }
    if (f === "deferred") {
      /* pc-1345: tracking umbrellas ride the parked tape when easy */
      const tracking =
        String((r && (r.gateType || r.gate_type)) || "")
          .toLowerCase()
          .trim() === "tracking" || stamp === "tracking";
      return (
        (deferred || tracking) &&
        !(r && r.isDone) &&
        st !== "done" &&
        st !== "canceled"
      );
    }
    if (f === "ready") {
      return (
        !!(r && r.isReady) ||
        (st === "backlog" &&
          !deferred &&
          !(r && r.gateType) &&
          !(r && r.gate_type) &&
          stamp !== "deferred")
      );
    }
    if (f === "live") {
      /* Open without ice — backlog/ip/review excluding deferred parks */
      if ((r && r.isDone) || st === "done" || st === "canceled") return false;
      if (deferred) return false;
      return true;
    }
    if (f === "stalled") {
      return (
        st === "stalled" ||
        stamp.indexOf("stalled") >= 0 ||
        st === "embargo" ||
        stamp.indexOf("embargo") >= 0
      );
    }
    if (f === "in_progress") {
      /* Claimed / actively worked — not review, not for-you alone */
      return (
        st === "in_progress" ||
        st === "claimed" ||
        stamp === "claimed" ||
        stamp === "in progress"
      );
    }
    if (f === "in_review") {
      /* Human review / gates — status in_review or stamp review */
      return (
        st === "in_review" ||
        stamp === "review" ||
        stamp.indexOf("in review") >= 0 ||
        (stamp.indexOf("review") >= 0 && stamp.indexOf("for you") < 0)
      );
    }
    if (f === "done") {
      return !!(r && r.isDone) || st === "done" || st === "canceled";
    }
    /* fallback open = live (non-ice open) */
    if ((r && r.isDone) || st === "done" || st === "canceled") return false;
    return !deferred;
  }

  function getFolderHeatAt() {
    return _folderHeatAt;
  }

  function repaintWoInsights() {
    syncHost();
    var m = hostModel();
    if (!m) return;
    hostRepaint(
      m.city,
      {
        in_flight: (m.workers || [])
          .filter(function (w) {
            return w && w.working;
          })
          .map(function (w) {
            return w.name;
          }),
        sectors: [],
      },
      { items: (_lastAtt && _lastAtt.items) || [] },
      _lastTpScene
    );
  }


  function slipMatchesListFilter(r, q) {
    if (!r) return false;
    if (!String(q || "").trim()) return true;
    return listFilterQueryMatch(
      [
        r.tid,
        r.id,
        r.title,
        r.stamp,
        r.status,
        r.prod,
        r.focus,
        r.kind,
        r.isYou ? "you need for_you" : "",
      ],
      q
    );
  }


  function slipUpdatedMsShared(raw) {
    if (raw == null || raw === "") return 0;
    if (typeof raw === "number" && isFinite(raw)) {
      return raw < 1e12 ? raw * 1000 : raw;
    }
    const t = Date.parse(String(raw));
    return isFinite(t) ? t : 0;
  }


  /**
   * pc-1187: compact relative age for WO open/touch lines (no "ago").
   * Returns "" | "just now" | "12m" | "3h" | "9d".
   */
  function formatAgeCompact(ms) {
    if (!ms || !isFinite(ms) || ms <= 0) return "";
    const ago = Date.now() - ms;
    if (ago < 45 * 1000) return "just now";
    if (ago < 60 * 60 * 1000)
      return Math.max(1, Math.round(ago / 60000)) + "m";
    if (ago < 24 * 60 * 60 * 1000)
      return Math.max(1, Math.round(ago / 3600000)) + "h";
    return Math.max(1, Math.round(ago / 86400000)) + "d";
  }


  /**
   * pc-1314: KEEP-pin standing chew leftover (felix pins). Motion
   * (claimed / closed) still belongs on the what-moved digest.
   */
  function isKeepPinTitle(title) {
    return /^\s*KEEP\s+pin:/i.test(String(title || ""));
  }
  function isStandingChewLeftover(r) {
    if (!r) return false;
    const title = String(r.title || "");
    const glance = String(r.glance || "");
    if (!isKeepPinTitle(title) && !isKeepPinTitle(glance)) return false;
    if (r.isDone || r.isMotion) return false;
    const st = String(r.status || "")
      .toLowerCase()
      .replace(/ /g, "_");
    if (
      st === "done" ||
      st === "canceled" ||
      st === "cancelled" ||
      st === "in_progress" ||
      st === "in_review"
    )
      return false;
    const stamp = String(r.stamp || "").toLowerCase();
    if (
      stamp === "claimed" ||
      stamp === "done" ||
      stamp === "closed" ||
      stamp === "canceled" ||
      stamp === "review"
    )
      return false;
    return true;
  }

  /**
   * pc-1314: workspace digest when-line is last move (filed/claimed/closed),
   * not open-age. Example: "12m ago · Aug 30, 11:04".
   */
  function formatSlipMovedWhen(updatedMs) {
    if (!updatedMs || !isFinite(updatedMs) || updatedMs <= 0) return "";
    const ago = Date.now() - updatedMs;
    let rel = "";
    if (ago < 45 * 1000) rel = "just now";
    else if (ago < 60 * 60 * 1000)
      rel = Math.max(1, Math.round(ago / 60000)) + "m ago";
    else if (ago < 24 * 60 * 60 * 1000)
      rel = Math.max(1, Math.round(ago / 3600000)) + "h ago";
    else if (ago < 7 * 24 * 60 * 60 * 1000)
      rel = Math.max(1, Math.round(ago / 86400000)) + "d ago";
    else {
      const d = new Date(updatedMs);
      return (
        d.toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        }) +
        " · " +
        d.toLocaleTimeString(undefined, {
          hour: "numeric",
          minute: "2-digit",
        })
      );
    }
    const d = new Date(updatedMs);
    const abs = d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
    return rel + " · " + abs;
  }

  /**
   * pc-1187: citizen open-age line from created_at (primary) + last touch.
   * Example: "open 9d · touched 1d". Falls back to open-from-touch when
   * created is unknown (attention payloads without created_at).
   */
  function formatSlipOpenWhen(createdMs, updatedMs) {
    const open = formatAgeCompact(createdMs);
    const touch = formatAgeCompact(updatedMs);
    if (open) {
      if (
        touch &&
        touch !== open &&
        updatedMs &&
        createdMs &&
        Math.abs(updatedMs - createdMs) > 90 * 1000
      ) {
        return "open " + open + " · touched " + touch;
      }
      return "open " + open;
    }
    if (touch) return "open " + touch;
    return "";
  }


  /** Prefer created_at open age for slip-when; last-touch secondary. */
  function slipWhenLine(r) {
    if (!r) return "";
    const created = r.created || 0;
    const updated = r.updated || 0;
    return formatSlipOpenWhen(created, updated);
  }


  /**
   * pc-921: PROCESS ## Glance → one rail line (mirrors suite.api.task_glance).
   */
  function extractGlanceText(desc, maxLen) {
    const lim = maxLen > 0 ? maxLen : 160;
    let text = String(desc || "")
      .replace(/\r\n/g, "\n")
      .trim();
    if (!text) return "";
    let body = "";
    const m = text.match(/##\s*Glance\s*\n([\s\S]*?)(?=\n##\s|\n#\s[^#]|$)/i);
    if (m) body = m[1] || "";
    else {
      const lines = text.split("\n");
      for (let i = 0; i < lines.length; i++) {
        let s = String(lines[i] || "").trim();
        if (!s) {
          if (body) break;
          continue;
        }
        if (s.charAt(0) === "#") {
          if (body) break;
          continue;
        }
        const low = s.toLowerCase();
        if (
          low === "glance" ||
          low === "where" ||
          low === "done when" ||
          low === "detail"
        )
          continue;
        body = s;
        break;
      }
    }
    body = String(body || "")
      .replace(/\s+/g, " ")
      .replace(/^[-*•]\s+/, "")
      .trim();
    if (!body) return "";
    if (body.length > lim) {
      let cut = body.slice(0, lim - 1).replace(/\s+\S*$/, "");
      if (cut.length < lim * 0.55) cut = body.slice(0, lim - 1);
      body = cut.replace(/[.,;:]+$/, "") + "…";
    }
    return body;
  }


  function rememberSlipMeta(row) {
    if (!row) return;
    const tid = String(row.tid || row.id || "").trim();
    if (!tid) return;
    const prev = _slipMetaByTid[tid] || {};
    const glance = String(
      row.glance != null ? row.glance : prev.glance || ""
    ).trim();
    const title = String(
      row.title != null ? row.title : prev.title || ""
    ).trim();
    const status = String(
      row.status != null ? row.status : prev.status || ""
    )
      .toLowerCase()
      .replace(/ /g, "_");
    const stamp = String(row.stamp != null ? row.stamp : prev.stamp || "").trim();
    const gateType =
      row.gateType != null
        ? row.gateType
        : row.gate_type != null
          ? row.gate_type
          : prev.gateType || "";
    const gateNote =
      row.gateNote != null
        ? row.gateNote
        : row.gate_note != null
          ? row.gate_note
          : prev.gateNote || "";
    const holder = String(
      row.holder != null ? row.holder : prev.holder || ""
    )
      .trim()
      .toLowerCase();
    _slipMetaByTid[tid] = {
      glance: glance || prev.glance || "",
      title: title || prev.title || "",
      status: status || prev.status || "",
      stamp: stamp || prev.stamp || "",
      holder: holder || prev.holder || "",
      labels:
        Array.isArray(row.labels) && row.labels.length
          ? row.labels
          : prev.labels || [],
      gateType: gateType == null ? "" : String(gateType),
      gateNote: String(gateNote || ""),
      isDeferred:
        row.isDeferred != null
          ? !!row.isDeferred
          : prev.isDeferred != null
            ? !!prev.isDeferred
            : isDeferredGate(gateType, gateNote),
      updated: Math.max(row.updated || 0, prev.updated || 0),
      /* pc-1187: keep earliest created_at (open age); never promote to last-touch */
      created: (function () {
        const c = row.created || 0;
        const p = prev.created || 0;
        if (c && p) return Math.min(c, p);
        return c || p || 0;
      })(),
      at: Date.now(),
    };
  }


  function enrichSlipFromMeta(row) {
    if (!row || !row.tid) return row;
    const tid = String(row.tid);
    const meta = _slipMetaByTid[tid];
    let next = row;
    function patch(key, val) {
      if (val == null || val === "") return;
      if (next[key] && String(next[key]).trim()) return;
      if (next === row) next = Object.assign({}, row);
      next[key] = val;
    }
    if (meta) {
      patch("glance", meta.glance);
      patch("title", meta.title);
      patch("holder", meta.holder);
      /* pc-1187: open age from desk/hydrate created_at */
      if (meta.created && !(next.created > 0)) {
        if (next === row) next = Object.assign({}, row);
        next.created = meta.created;
      }
      if (
        (!next.labels || !next.labels.length) &&
        meta.labels &&
        meta.labels.length
      ) {
        if (next === row) next = Object.assign({}, row);
        next.labels = meta.labels;
      }
      /* Prefer fresher store status when live ring is stale (cancel/gate) */
      if (
        meta.status &&
        meta.updated &&
        (row.updated || 0) < meta.updated &&
        String(row.status || "") !== meta.status
      ) {
        if (next === row) next = Object.assign({}, row);
        next.status = meta.status;
        if (meta.stamp) next.stamp = meta.stamp;
        next.isDone =
          meta.status === "done" ||
          meta.status === "canceled" ||
          meta.status === "cancelled";
        next.isMotion =
          meta.status === "in_progress" || meta.status === "in_review";
        if (meta.isDeferred != null) {
          next.isDeferred = !!meta.isDeferred;
          if (next.isDeferred) next.stamp = "deferred";
        }
        if (meta.gateType != null) next.gateType = meta.gateType;
        if (meta.gateNote != null) next.gateNote = meta.gateNote;
      }
    }
    /* pc-1067: fill holder from desk seat index when labels/owner missing */
    if (!next.holder || !String(next.holder).trim()) {
      const hit = AgentsPanel.getDeskHolderByTid()[tid];
      if (hit && hit.hand) {
        if (next === row) next = Object.assign({}, row);
        next.holder = hit.hand;
      }
    }
    return next;
  }


  /** Invalidate desk list TTL so next paint refetches (status/gate truth). */
  function bustWoDeskCache() {
    Object.keys(_woDeskCache || {}).forEach(function (k) {
      const c = _woDeskCache[k];
      if (c) {
        c.at = 0;
        c.loading = false;
      }
    });
    if (_woGateCounts) {
      _woGateCounts.at = 0;
      _woGateCounts.loading = false;
    }
  }

  function hydrateSlipGlance(tid) {
    tid = String(tid || "").trim();
    if (!tid) return;
    if (_glanceHydrateInflight[tid]) return;
    if (_glanceHydrateDone[tid]) return;
    const meta = _slipMetaByTid[tid];
    if (meta && meta.glance) return;
    _glanceHydrateInflight[tid] = true;
    const url = "/api/task/" + encodeURIComponent(tid);
    fetch(url, { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("task " + r.status);
        return r.json();
      })
      .then(function (d) {
        const t = (d && (d.task || d)) || {};
        const glance =
          extractGlanceText(t.description || t.desc || "") ||
          String(t.glance || "").trim();
        const title = String(t.title || t.summary || "").trim();
        const st = String(t.status || "")
          .toLowerCase()
          .replace(/ /g, "_");
        const gateType = t.gate_type != null ? t.gate_type : t.gateType;
        const gateNote =
          t.gate_note != null
            ? t.gate_note
            : t.gateNote != null
              ? t.gateNote
              : "";
        _glanceHydrateDone[tid] = true;
        /* pc-1028: use the store's true updated_at, never wall-clock — a
         * cache refill must not promote the slip to the top of the live ring. */
        const storeUpdatedMs = slipUpdatedMsShared(
          t.updated_at || t.updated || t.created_at
        );
        const storeCreatedMs = slipUpdatedMsShared(t.created_at || t.created);
        rememberSlipMeta({
          tid: tid,
          glance: glance,
          title: title,
          status: st,
          stamp: st.replace(/_/g, " "),
          gateType: gateType,
          gateNote: gateNote,
          isDeferred: isDeferredGate(gateType, gateNote),
          updated: storeUpdatedMs,
          created: storeCreatedMs,
        });
        /* Patch live ring + desk cache rows */
        try {
          if (glance || title || st) {
            injectLiveActivity({
              tid: tid,
              title: title || tid,
              glance: glance,
              status: st || "backlog",
              stamp: st
                ? isDeferredGate(gateType, gateNote)
                  ? "deferred"
                  : st.replace(/_/g, " ")
                : "filed",
              updated: storeUpdatedMs,
              created: storeCreatedMs,
              isNew: false,
              fromLive: true,
              needGlance: false,
              gateType: gateType,
              gateNote: gateNote,
              isDeferred: isDeferredGate(gateType, gateNote),
            });
          }
        } catch (eInj) {}
        Object.keys(_woDeskCache || {}).forEach(function (filter) {
          const c = _woDeskCache[filter];
          if (!c || !Array.isArray(c.rows)) return;
          c.rows.forEach(function (row, i) {
            if (!row || String(row.tid) !== tid) return;
            c.rows[i] = enrichSlipFromMeta(
              Object.assign({}, row, {
                glance: glance || row.glance,
                title: title || row.title,
                status: st || row.status,
                needGlance: glance ? false : row.needGlance,
                created: storeCreatedMs || row.created || 0,
              })
            );
          });
        });
        forceTapeRepaint();
      })
      .catch(function () {
        /* degrade: allow one later retry on next list cycle */
        delete _glanceHydrateDone[tid];
      })
      .then(function () {
        delete _glanceHydrateInflight[tid];
      });
  }


  function slipFromApiTask(t) {
    if (!t) return null;
    const tid = String(t.id || t.task_id || "").trim();
    if (!tid) return null;
    const st = String(t.status || "backlog")
      .toLowerCase()
      .replace(/ /g, "_");
    const rawProd = String(
      t.product || t.store || t.project || ""
    ).trim();
    const prod = resolveSlipProduct(rawProd, tid);
    const labels = t.labels || t.tags || [];
    const labStr = Array.isArray(labels)
      ? labels.map(String).join(" ").toLowerCase()
      : String(labels || "").toLowerCase();
    const isDemo =
      labStr.indexOf("demo") >= 0 || labStr.indexOf("founding") >= 0;
    const gateType = t.gate_type != null ? t.gate_type : t.gateType;
    const gateNote =
      t.gate_note != null
        ? t.gate_note
        : t.gateNote != null
          ? t.gateNote
          : "";
    const isDeferred = isDeferredGate(gateType, gateNote);
    /* Ready = backlog claimable (no gate). Deferred has a gate; not ready. */
    const isReady =
      st === "backlog" &&
      !isDeferred &&
      (gateType == null || String(gateType).trim() === "");
    let stamp = st.replace(/_/g, " ");
    if (isDeferred) stamp = "deferred";
    else if (isReady) stamp = "ready";
    /* pc-1067: normalize IP stamp so pill reads CLAIMED (not IN PROGRESS) */
    else if (st === "in_progress") stamp = "claimed";
    const labList = Array.isArray(labels)
      ? labels.map(function (x) {
          return String(x);
        })
      : [];
    /* pc-1067: seat hand for CLAIMED · <hand> chip */
    const holder = seatHandFromTask(t);
    const glance = String(
      t.glance != null
        ? t.glance
        : extractGlanceText(t.description || t.desc || "")
    ).trim();
    const isDone =
      st === "done" || st === "canceled" || st === "cancelled";
    /* pc-918: light list may omit glance (stale serve / title-only create) */
    const needGlance = !glance && !isDone;
    const row = {
      key: "desk:" + tid,
      prod: prod,
      tid: tid,
      title: String(t.title || t.summary || "").trim().slice(0, 96),
      glance: glance.slice(0, 160),
      stamp: stamp,
      status: st,
      focus: prod,
      isYou: false,
      isWorkerYou: labStr.indexOf("worker:you") >= 0,
      labels: labList,
      labelStr: labStr,
      holder: holder,
      isMotion: st === "in_progress" || st === "in_review",
      isDone: isDone,
      isNew: false,
      isDemo: isDemo,
      isDeferred: isDeferred,
      isReady: isReady,
      needGlance: needGlance,
      gateType: gateType == null ? "" : String(gateType),
      gateNote: String(gateNote || ""),
      updated: slipUpdatedMsShared(
        t.updated_at || t.updated || t.created_at
      ),
      /* pc-1187: open age anchor — display only, never reorder by this alone */
      created: slipUpdatedMsShared(t.created_at || t.created),
      fromDesk: true,
    };
    rememberSlipMeta(row);
    return row;
  }


  function fetchTasksByStatus(status, limit) {
    const lim = Math.max(1, Math.min(limit || MAP_WO_LIST_CAP, MAP_WO_LIST_CAP));
    const st = status ? String(status) : "";
    const product = deskScopeKey();
    const key = "st:" + st + ":" + lim + ":" + (product || "_all");
    if (_deskListInflight[key]) return _deskListInflight[key];
    const q = new URLSearchParams();
    q.set("limit", String(lim));
    if (st) q.set("status", st);
    /* pc-1044: dig-in rail must not pull the whole city desk */
    if (product) q.set("product", product);
    const run = function () {
      return fetch("/api/tasks?" + q.toString(), { cache: "no-store" })
        .then(function (r) {
          if (!r.ok) {
            const err = new Error("desk HTTP " + r.status);
            err.status = r.status;
            throw err;
          }
          return r.json();
        })
        .then(function (d) {
          if (!d || d.ok === false) {
            throw new Error(
              (d && (d.error || d.message)) || "desk list failed"
            );
          }
          _woDeskLastError = "";
          return d.tasks || [];
        });
    };
    /* Serialize WorkLane list hops; same key shares one in-flight promise. */
    const p = _deskListChain.then(run, run);
    _deskListChain = p.then(
      function () {},
      function () {}
    );
    const wrapped = p.then(
      function (tasks) {
        delete _deskListInflight[key];
        return tasks;
      },
      function (err) {
        delete _deskListInflight[key];
        _woDeskLastError = String((err && err.message) || err || "desk error");
        throw err;
      }
    );
    _deskListInflight[key] = wrapped;
    return wrapped;
  }


  /**
   * pc-1337: product-scoped worker:you backlog (host/remind/note).
   * Workspace-wide fetch is refused — Overview holds the quiet pile.
   */
  function fetchWorkerYouNotes(limit) {
    const lim = Math.max(1, Math.min(limit || MAP_WO_LIST_CAP, MAP_WO_LIST_CAP));
    const product = deskScopeKey();
    if (!product) return Promise.resolve([]);
    const key = "you:" + lim + ":" + product;
    if (_deskListInflight[key]) return _deskListInflight[key];
    const q = new URLSearchParams();
    q.set("limit", String(lim));
    q.set("status", "backlog");
    q.set("label", "worker:you");
    q.set("product", product);
    q.set("preview", "0");
    const run = function () {
      return fetch("/api/tasks?" + q.toString(), { cache: "no-store" })
        .then(function (r) {
          if (!r.ok) {
            const err = new Error("desk HTTP " + r.status);
            err.status = r.status;
            throw err;
          }
          return r.json();
        })
        .then(function (d) {
          if (!d || d.ok === false) {
            throw new Error(
              (d && (d.error || d.message)) || "desk list failed"
            );
          }
          _woDeskLastError = "";
          return d.tasks || [];
        });
    };
    const p = _deskListChain.then(run, run);
    _deskListChain = p.then(
      function () {},
      function () {}
    );
    const wrapped = p.then(
      function (tasks) {
        delete _deskListInflight[key];
        return tasks;
      },
      function (err) {
        delete _deskListInflight[key];
        _woDeskLastError = String((err && err.message) || err || "desk error");
        throw err;
      }
    );
    _deskListInflight[key] = wrapped;
    return wrapped;
  }

  /* pc-1337: quiet You notes for the dug-in store — not claimed live work. */
  function isProjectYouNote(r) {
    if (!r) return false;
    if (!(r.isWorkerYou || slipIsWorkerYou(r))) return false;
    const st = slipStatusKey(r);
    if (
      st === "done" ||
      st === "canceled" ||
      st === "cancelled" ||
      st === "in_progress" ||
      st === "claimed" ||
      st === "in_review"
    )
      return false;
    if (st && st !== "backlog") return false;
    if (r.isDeferred) return false;
    const gt = String(r.gateType || r.gate_type || "").trim();
    if (gt) return false;
    return true;
  }

  function unionAndPinProjectNotes(rows) {
    const seen = Object.create(null);
    const notes = [];
    const rest = [];
    function take(r) {
      if (!r || !r.tid) return;
      const tid = String(r.tid);
      if (seen[tid]) return;
      seen[tid] = 1;
      if (isProjectYouNote(r)) notes.push(r);
      else rest.push(r);
    }
    const cached = (_woDeskCache.yours && _woDeskCache.yours.rows) || [];
    cached.forEach(take);
    (rows || []).forEach(take);
    return notes.concat(rest);
  }

  function ensureWoProjectNotes(repaint) {
    ensureWoDeskScopeFresh();
    const fetchScope = deskScopeKey();
    if (!fetchScope) {
      /* pc-1337: workspace-wide yours hop is retired */
      _woDeskCache.yours = {
        rows: [],
        at: Date.now(),
        loading: false,
        error: false,
      };
      return;
    }
    const now = Date.now();
    const c = _woDeskCache.yours;
    if (
      c &&
      !c.loading &&
      Array.isArray(c.rows) &&
      typeof c.at === "number" &&
      now - c.at < MAP_WO_DESK_TTL_MS
    ) {
      return;
    }
    if (c && c.loading) return;
    _woDeskCache.yours = {
      rows: (c && c.rows) || [],
      at: (c && c.at) || 0,
      loading: true,
    };
    fetchWorkerYouNotes(MAP_WO_LIST_CAP)
      .then(function (tasks) {
        if (deskScopeKey() !== fetchScope) return;
        const rows = [];
        const seen = Object.create(null);
        (tasks || []).forEach(function (t) {
          const s = slipFromApiTask(t);
          if (!s || !isProjectYouNote(s) || seen[s.tid]) return;
          seen[s.tid] = 1;
          rows.push(s);
        });
        sortSlipsRecent(rows);
        try {
          queueMissingGlanceHydrate(rows);
        } catch (eHydYou) {}
        _woDeskCache.yours = {
          rows: rows.slice(0, MAP_WO_LIST_CAP),
          at: Date.now(),
          loading: false,
          error: false,
        };
        _tapeSig = "";
        if (typeof repaint === "function") {
          try {
            if (hostModel()) repaint();
          } catch (eR) {}
        }
      })
      .catch(function () {
        if (deskScopeKey() !== fetchScope) return;
        if (_woDeskCache.yours) {
          _woDeskCache.yours.loading = false;
          _woDeskCache.yours.error = true;
          _woDeskCache.yours.at = 0;
        }
        if (typeof repaint === "function") {
          try {
            if (hostModel()) repaint();
          } catch (eR2) {}
        }
      });
  }


  /**
   * pc-918: when light list/SSE land title-only, pull Glance for open slips.
   * Caps concurrent hydrates so a full tape cannot stampede /api/task.
   */
  function queueMissingGlanceHydrate(rows) {
    const list = rows || [];
    let n = 0;
    const max = 24;
    for (let i = 0; i < list.length && n < max; i++) {
      const r = list[i];
      if (!r || !r.tid) continue;
      if (r.isDone) continue;
      const g = String(r.glance || "").trim();
      if (g) continue;
      try {
        hydrateSlipGlance(r.tid);
        n++;
      } catch (eQ) {}
    }
  }


  /**
   * pc-918 / pc-973: degraded desk path when live-strip is missing (stale suite)
   * or 5xx. Parallel status pulls (was serial ≈3.9s stall) — desk already
   * coalesces; 3–4 concurrent status lists beat a waterfall on cold rails.
   */
  function fetchLiveStripSerialFallback(family, limit) {
    const lim = Math.max(1, Math.min(limit || MAP_WO_LIST_CAP, MAP_WO_LIST_CAP));
    const fam =
      family === "all" || family === "recency" || family === "tape"
        ? "all"
        : "open";
    const statuses =
      fam === "all"
        ? ["backlog", "in_progress", "in_review", "done"]
        : ["backlog", "in_progress", "in_review"];
    return Promise.all(
      statuses.map(function (st) {
        return fetchTasksByStatus(st, lim)
          .then(function (tasks) {
            return { st: st, tasks: tasks || [] };
          })
          .catch(function () {
            return { st: st, tasks: [] };
          });
      })
    ).then(function (rows) {
      const by = {};
      const tasks = [];
      const seen = {};
      rows.forEach(function (row) {
        by[row.st] = row.tasks;
        (row.tasks || []).forEach(function (t) {
          if (!t) return;
          const tid = String(t.id || t.task_id || "").trim();
          if (!tid || seen[tid]) return;
          seen[tid] = 1;
          tasks.push(t);
        });
      });
      _woDeskLastError = "";
      return {
        ok: true,
        tasks: tasks,
        by_status: by,
        family: fam,
        error: null,
        source: "parallel_fallback",
      };
    });
  }


  /**
   * pc-934: one suite hop for multi-status desk tape (serial WL pulls server-side).
   * family "open" = backlog+ip+review; "all" adds done (recency strip).
   * Resolves { ok, tasks, by_status, error } — never silent empty on hard fail.
   * pc-918: non-JSON/404/5xx → serial status fallback (stale serve without route).
   */
  function fetchLiveStrip(family, limit) {
    const lim = Math.max(1, Math.min(limit || MAP_WO_LIST_CAP, MAP_WO_LIST_CAP));
    const fam =
      family === "all" || family === "recency" || family === "tape"
        ? "all"
        : "open";
    const product = deskScopeKey();
    const key = "strip:" + fam + ":" + lim + ":" + (product || "_all");
    if (_deskListInflight[key]) return _deskListInflight[key];
    const q = new URLSearchParams();
    q.set("family", fam);
    q.set("limit", String(lim));
    /* pc-1044: server-side product scope when dug into a project */
    if (product) q.set("product", product);
    const run = function () {
      return fetch("/api/tasks/live-strip?" + q.toString(), {
        cache: "no-store",
      })
        .then(function (r) {
          const ct = String(r.headers.get("content-type") || "").toLowerCase();
          if (!r.ok || ct.indexOf("json") < 0) {
            return r.text().then(function () {
              return {
                http: r.status,
                body: {
                  ok: false,
                  error: "live-strip HTTP " + r.status,
                },
              };
            });
          }
          return r.json().then(function (d) {
            return { http: r.status, body: d };
          });
        })
        .then(function (pack) {
          const d = pack.body || {};
          if (
            pack.http === 404 ||
            pack.http >= 500 ||
            d.ok === false
          ) {
            const msg =
              (d && (d.error || d.message)) ||
              "live-strip HTTP " + pack.http;
            _woDeskLastError = String(msg);
            /* Fall back — do not leave open-family / all tape empty */
            return fetchLiveStripSerialFallback(fam, lim);
          }
          _woDeskLastError = "";
          return {
            ok: true,
            tasks: (d && d.tasks) || [],
            by_status: (d && d.by_status) || {},
            family: (d && d.family) || fam,
            error: null,
          };
        })
        .catch(function (err) {
          _woDeskLastError = String(
            (err && err.message) || err || "live-strip error"
          );
          return fetchLiveStripSerialFallback(fam, lim);
        });
    };
    const p = _deskListChain.then(run, run);
    _deskListChain = p.then(
      function () {},
      function () {}
    );
    const wrapped = p.then(
      function (result) {
        delete _deskListInflight[key];
        return result;
      },
      function (err) {
        delete _deskListInflight[key];
        if (!_woDeskLastError) {
          _woDeskLastError = String((err && err.message) || err || "desk error");
        }
        throw err;
      }
    );
    _deskListInflight[key] = wrapped;
    return wrapped;
  }


  function sortSlipsRecent(rows) {
    rows.sort(function (a, b) {
      const pa = String(a.prod || a.focus || "").toLowerCase();
      const pb = String(b.prod || b.focus || "").toLowerCase();
      if (pa !== pb) return pa.localeCompare(pb);
      if (a.isYou !== b.isYou) return a.isYou ? -1 : 1;
      const bu = b.updated || 0;
      const au = a.updated || 0;
      if (bu !== au) return bu - au;
      return String(a.tid || "").localeCompare(String(b.tid || ""));
    });
    return rows;
  }

  /** Live activity strip: newest event first; fresh isNew rows pin above. */
  function sortSlipsByUpdated(rows) {
    const freshMs = 12000;
    const now = Date.now();
    rows.sort(function (a, b) {
      const aFresh = a && a.isNew && now - (a.updated || 0) < freshMs ? 1 : 0;
      const bFresh = b && b.isNew && now - (b.updated || 0) < freshMs ? 1 : 0;
      if (bFresh !== aFresh) return bFresh - aFresh;
      const bu = (b && b.updated) || 0;
      const au = (a && a.updated) || 0;
      if (bu !== au) return bu - au;
      return String((a && a.tid) || "").localeCompare(String((b && b.tid) || ""));
    });
    return rows;
  }

  function injectLiveActivity(row) {
    if (!row || !row.tid) return;
    const tid = String(row.tid).trim();
    if (!tid) return;
    const prevLive = (_liveActivityFeed || []).find(function (r) {
      return r && String(r.tid) === tid;
    });
    const meta = _slipMetaByTid[tid] || {};
    const st = String(row.status || row.stamp || (prevLive && prevLive.status) || "")
      .toLowerCase()
      .replace(/ /g, "_");
    const glance = String(
      row.glance != null && String(row.glance).trim()
        ? row.glance
        : (prevLive && prevLive.glance) || meta.glance || ""
    ).trim();
    const title = String(
      row.title || (prevLive && prevLive.title) || meta.title || ""
    )
      .trim()
      .slice(0, 96);
    let stamp = row.stamp || st || "update";
    if (st === "canceled" || st === "cancelled") stamp = "canceled";
    else if (st === "done") stamp = "done";
    const next = Object.assign({}, prevLive || {}, row, {
      tid: tid,
      key: row.key || "live:" + tid,
      updated: row.updated || Date.now(),
      /* pc-1187: never invent created from last-touch; keep earliest known */
      created:
        row.created ||
        (prevLive && prevLive.created) ||
        meta.created ||
        0,
      isNew: row.isNew !== false,
      fromLive: true,
      stamp: stamp,
      status: st,
      title: title,
      glance: glance.slice(0, 160),
      prod: row.prod || row.focus || (prevLive && prevLive.prod) || "",
      focus: row.focus || row.prod || (prevLive && prevLive.focus) || "",
      isDone:
        st === "done" || st === "canceled" || st === "cancelled" || !!row.isDone,
      isMotion: st === "in_progress" || st === "in_review",
    });
    if (row.gateType != null || row.gate_type != null) {
      next.gateType =
        row.gateType != null ? row.gateType : row.gate_type;
    }
    if (row.gateNote != null || row.gate_note != null) {
      next.gateNote =
        row.gateNote != null ? row.gateNote : row.gate_note;
    }
    if (next.gateType != null || next.gateNote != null) {
      next.isDeferred = isDeferredGate(next.gateType, next.gateNote);
      if (next.isDeferred && st === "backlog") next.stamp = "deferred";
    }
    rememberSlipMeta(next);
    _liveActivityFeed = _liveActivityFeed.filter(function (r) {
      return r && String(r.tid) !== tid;
    });
    _liveActivityFeed.unshift(next);
    if (_liveActivityFeed.length > LIVE_ACTIVITY_MAX) {
      _liveActivityFeed.length = LIVE_ACTIVITY_MAX;
    }
    if (next.isNew) {
      try {
        queueTapeBeat(tid, next.status || next.stamp, "");
      } catch (eB) {}
    }
    /* Title-only create → hydrate Glance immediately */
    if (!next.glance && (next.isNew || row.needGlance)) {
      try {
        hydrateSlipGlance(tid);
      } catch (eH) {}
    }
  }

  function mergeLiveActivityFeed(baseRows) {
    const byTid = {};
    (baseRows || []).forEach(function (r) {
      if (!r || !r.tid) return;
      const tid = String(r.tid);
      const enriched = enrichSlipFromMeta(r);
      const prev = byTid[tid];
      if (!prev || (enriched.updated || 0) >= (prev.updated || 0))
        byTid[tid] = enriched;
    });
    const now = Date.now();
    _liveActivityFeed = _liveActivityFeed.filter(function (r) {
      return r && r.tid && now - (r.updated || 0) < 6 * 60 * 60 * 1000;
    });
    _liveActivityFeed.forEach(function (r) {
      if (!r || !r.tid) return;
      const tid = String(r.tid);
      const prev = byTid[tid];
      if (!prev || (r.updated || 0) >= (prev.updated || 0)) {
        byTid[tid] = enrichSlipFromMeta(
          Object.assign({}, prev || {}, r, {
            isNew: !!(r.isNew || (prev && prev.isNew)),
            glance:
              (r.glance && String(r.glance).trim()) ||
              (prev && prev.glance) ||
              "",
            title:
              (r.title && String(r.title).trim()) ||
              (prev && prev.title) ||
              "",
          })
        );
      } else if (prev && r.glance && !prev.glance) {
        byTid[tid] = Object.assign({}, prev, { glance: r.glance });
      }
    });
    const out = Object.keys(byTid).map(function (k) {
      return byTid[k];
    });
    return sortSlipsByUpdated(out);
  }


  /**
   * pc-547 / pc-688: open-family desk scan → capped live/deferred/ready *lists*
   * plus authoritative chip *counts* from /api/wo-gate-counts (uncapped).
   * Dual-read ice drops out of Live so OPEN≠ice pile. Count ≠ list length.
   */
  function ensureWoOpenFamily(repaint) {
    ensureWoDeskScopeFresh();
    const now = Date.now();
    const keys = ["live", "deferred", "ready"];
    const fetchScope = deskScopeKey();
    let allFresh = true;
    for (let i = 0; i < keys.length; i++) {
      const c = _woDeskCache[keys[i]];
      if (
        !(
          c &&
          !c.loading &&
          Array.isArray(c.rows) &&
          typeof c.at === "number" &&
          now - c.at < MAP_WO_DESK_TTL_MS
        )
      ) {
        allFresh = false;
        break;
      }
    }
    if (
      allFresh &&
      _woGateCounts.at &&
      now - _woGateCounts.at < MAP_WO_DESK_TTL_MS &&
      !_woGateCounts.loading &&
      String(_woGateCounts.scope || "") === fetchScope
    ) {
      return;
    }
    if (_woGateCounts.loading && String(_woGateCounts.scope || "") === fetchScope)
      return;
    const gen = ++_woOpenFamilyGen;
    _woGateCounts.loading = true;
    _woGateCounts.scope = fetchScope;
    keys.forEach(function (k) {
      const prev = _woDeskCache[k];
      _woDeskCache[k] = {
        rows: (prev && prev.rows) || [],
        at: (prev && prev.at) || 0,
        loading: true,
      };
    });
    const lim = MAP_WO_LIST_CAP;
    function fetchWoGateCounts() {
      /* pc-1044: product= so dig-in chips show project numbers */
      const gq = new URLSearchParams();
      if (fetchScope) gq.set("product", fetchScope);
      const gurl =
        "/api/wo-gate-counts" + (gq.toString() ? "?" + gq.toString() : "");
      return fetch(gurl, { cache: "no-store" })
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          if (d && d.ok !== false && typeof d.live === "number") {
            return d;
          }
          return null;
        })
        .catch(function () {
          return null;
        });
    }
    /*
     * pc-934: one live-strip hop for open-family rows (suite serializes WL).
     * Gate counts stay a separate tallies seam (uncapped) — not 3× /api/tasks.
     */
    Promise.all([fetchLiveStrip("open", lim), fetchWoGateCounts()])
      .then(function (parts) {
        /* pc-1065: dig-in flipped while in flight — discard workspace/other resolve */
        if (gen !== _woOpenFamilyGen || deskScopeKey() !== fetchScope) {
          return;
        }
        const strip = parts[0] || {};
        const gatePayload = parts[1];
        const seen = {};
        const openRows = [];
        const by = strip.by_status || {};
        const rawTasks = (by.backlog || [])
          .concat(by.in_progress || [])
          .concat(by.in_review || []);
        const fallback = strip.tasks || [];
        (rawTasks.length ? rawTasks : fallback).forEach(function (t) {
          const s = slipFromApiTask(t);
          if (!s || s.isDone || seen[s.tid]) return;
          seen[s.tid] = 1;
          openRows.push(s);
        });
        const liveRows = [];
        const deferredRows = [];
        const readyRows = [];
        openRows.forEach(function (s) {
          if (s.isDeferred) deferredRows.push(s);
          else liveRows.push(s);
          if (s.isReady) readyRows.push(s);
        });
        sortSlipsRecent(liveRows);
        sortSlipsRecent(deferredRows);
        sortSlipsRecent(readyRows);
        /* pc-918: desk light rows without Glance → single-task hydrate ≤1s */
        try {
          queueMissingGlanceHydrate(openRows);
        } catch (eHyd) {}
        const at = Date.now();
        _woDeskCache.live = {
          rows: liveRows.slice(0, lim),
          at: at,
          loading: false,
          error: false,
        };
        _woDeskCache.deferred = {
          rows: deferredRows.slice(0, lim),
          at: at,
          loading: false,
          error: false,
        };
        _woDeskCache.ready = {
          rows: readyRows.slice(0, lim),
          at: at,
          loading: false,
          error: false,
        };
        /* pc-688: chip numbers from uncapped tally — never capped list length */
        if (gatePayload) {
          _woGateCounts = {
            live: gatePayload.live,
            deferred: gatePayload.deferred,
            ready: gatePayload.ready,
            scope: fetchScope,
            at: at,
            loading: false,
          };
        } else {
          /* Soft fallback only when count seam fails — mark stale for retry */
          _woGateCounts = {
            live: liveRows.length,
            deferred: deferredRows.length,
            ready: readyRows.length,
            scope: fetchScope,
            at: 0,
            loading: false,
          };
        }
        /* pc-546 / pc-875: folder heat — sampled live preferred; by_product fills cap miss */
        rebuildFolderHeatFromOpenRows(openRows, at, gatePayload);
        /*
         * pc-898: chip counts always soft-update; only force tape rebuild when
         * the active filter is a desk pile (live/deferred/ready). Clearing
         * _tapeSig on every gate fetch remounted the activity feed and made
         * the work-order rail flicker under poll load.
         */
        _chipSig = "";
        try {
          const f =
            typeof mapWoFilter !== "undefined"
              ? String(mapWoFilter || "all")
              : "all";
          if (
            f === "live" ||
            f === "deferred" ||
            f === "ready" ||
            f === "in_progress" ||
            f === "in_review" ||
            f === "backlog"
          ) {
            _tapeSig = "";
          }
        } catch (eF) {}
        if (typeof repaint === "function") {
          try {
            /*
             * pc-995: repaintWoInsights early-returns when hostModel() is still null
             * at fetch-resolve (cold race). Queue one retry so warm desk rows
             * still land after buildScene without waiting for cinema/heartbeat
             * (both park while document.hidden).
             */
            if (!hostModel()) {
              ensureWoOpenFamily._pendingRepaint = repaint;
            } else {
              ensureWoOpenFamily._pendingRepaint = null;
              repaint();
            }
          } catch (eR) {}
        }
        /* Soft-patch folder badges/bubbles now that live heat is warm */
        try {
          if (typeof softPatchHierarchyBubbles === "function") {
            softPatchHierarchyBubbles();
          }
          if (typeof softPatchLotOpenCounts === "function") {
            softPatchLotOpenCounts();
          }
          if (typeof softPatchCityFolderOpenBadge === "function") {
            softPatchCityFolderOpenBadge();
          }
        } catch (eHeat) {}
        try {
          softRefreshOpenDigSurfaces();
        } catch (eDigH) {}
      })
      .catch(function () {
        /* pc-1065: stale reject after dig-in flip — do not touch current scope */
        if (gen !== _woOpenFamilyGen || deskScopeKey() !== fetchScope) {
          return;
        }
        _woGateCounts.loading = false;
        keys.forEach(function (k) {
          if (_woDeskCache[k]) {
            _woDeskCache[k].loading = false;
            _woDeskCache[k].error = true;
            /* Do not invent a fresh at — allow retry after TTL */
            if (!_woDeskCache[k].at) _woDeskCache[k].at = 0;
          }
        });
        if (typeof repaint === "function") {
          try {
            repaint();
          } catch (eR2) {}
        }
      });
  }


  /**
   * pc-546 / pc-552 / pc-875: aggregate dual-read open slips → per-product
   * live/deferred heat. Seeds every map plot at live=0 **sampled=false** so
   * unsampled products fall back to store raw (register 🎫 under list cap).
   * Bumped rows and uncapped by_product mark sampled=true (trusted live).
   */
  function rebuildFolderHeatFromOpenRows(openRows, at, gatePayload) {
    const heat = Object.create(null);
    function heatKeysFor(prod) {
      const raw = String(prod || "")
        .toLowerCase()
        .trim();
      if (!raw) return [];
      const keys = [raw];
      try {
        if (typeof normKey === "function") {
          const nk = normKey(raw);
          if (nk && nk !== raw) keys.push(nk);
        }
      } catch (eNk) {}
      return keys;
    }
    function seed(prod) {
      const keys = heatKeysFor(prod);
      for (let i = 0; i < keys.length; i++) {
        const k = keys[i];
        if (!heat[k]) heat[k] = { live: 0, deferred: 0, sampled: false };
      }
    }
    function bump(prod, field) {
      const keys = heatKeysFor(prod);
      for (let i = 0; i < keys.length; i++) {
        const k = keys[i];
        if (!heat[k]) heat[k] = { live: 0, deferred: 0, sampled: false };
        heat[k][field]++;
        heat[k].sampled = true;
      }
    }
    /* Seed known folders first — warm index must cover the whole map */
    try {
      const plots =
        typeof hostModel() !== "undefined" && hostModel() && hostModel().plots
          ? hostModel().plots
          : [];
      for (let pi = 0; pi < plots.length; pi++) {
        const p = plots[pi];
        if (!p) continue;
        seed(p.slug);
        seed(p.name);
        seed(p.product);
        try {
          if (typeof deskProductForPlot === "function") {
            seed(deskProductForPlot(p));
          }
        } catch (eDp) {}
      }
    } catch (eSeed) {}
    (openRows || []).forEach(function (s) {
      if (!s) return;
      const field = s.isDeferred ? "deferred" : "live";
      bump(s.prod, field);
      if (s.focus && s.focus !== s.prod) bump(s.focus, field);
    });
    /* pc-875: uncapped by_product overrides seed zeros for products missed by list cap */
    try {
      const by =
        gatePayload && gatePayload.by_product && typeof gatePayload.by_product === "object"
          ? gatePayload.by_product
          : null;
      if (by) {
        Object.keys(by).forEach(function (prod) {
          const row = by[prod];
          if (!row || typeof row !== "object") return;
          const keys = heatKeysFor(prod);
          for (let i = 0; i < keys.length; i++) {
            const k = keys[i];
            if (!heat[k]) heat[k] = { live: 0, deferred: 0, sampled: false };
            heat[k].live = Math.max(0, row.live | 0);
            heat[k].deferred = Math.max(0, row.deferred | 0);
            heat[k].sampled = true;
          }
        });
      }
    } catch (eBy) {}
    _folderHeatByKey = heat;
    _folderHeatAt = typeof at === "number" ? at : Date.now();
    try {
      if (typeof hostModel() !== "undefined" && hostModel()) {
        hostModel().folderHeat = heat;
        hostModel().folderHeatAt = _folderHeatAt;
      }
    } catch (eM) {}
  }


  /** Look up live/deferred heat for a plot (slug · name · product aliases). */
  function folderHeatFor(p) {
    if (!p || !_folderHeatAt) return null;
    const heat = _folderHeatByKey;
    if (!heat) return null;
    const cands = [
      p.slug,
      p.name,
      p.product,
      typeof deskProductForPlot === "function" ? deskProductForPlot(p) : "",
    ];
    for (let i = 0; i < cands.length; i++) {
      const raw = String(cands[i] || "")
        .toLowerCase()
        .trim();
      if (!raw) continue;
      if (heat[raw]) return heat[raw];
      try {
        var nkFn = H("normKey");
        if (nkFn) {
          const nk = nkFn(raw);
          if (nk && heat[nk]) return heat[nk];
        }
      } catch (eH) {}
    }
    return null;
  }


  function deferredCount(n) {
    if (
      typeof window !== "undefined" &&
      window.WoBuckets &&
      typeof window.WoBuckets.folderDeferred === "function"
    ) {
      return window.WoBuckets.folderDeferred(n, {
        heat: folderHeatFor(n),
        heatWarm: !!_folderHeatAt,
      });
    }
    const h = folderHeatFor(n);
    if (h && h.sampled) return Math.max(0, h.deferred | 0);
    return 0;
  }


  /**
   * Load up to MAP_WO_LIST_CAP rows for one filter from the desk (or attention).
   * Each filter is independent — not a slice of a shared recent feed.
   */
  function ensureWoDeskFilter(filter, repaint) {
    filter = normalizeWoFilter(filter);
    ensureWoDeskScopeFresh();
    /* for_you / stalled resolved sync from attention inside paintMapInsights */
    if (filter === "for_you" || filter === "stalled") return;
    /* pc-1337: yours is a labeled notes fetch, not family=all recency */
    if (filter === "yours") {
      ensureWoProjectNotes(repaint);
      return;
    }
    /* pc-547: live / deferred / ready share one open-family scan */
    if (filter === "live" || filter === "deferred" || filter === "ready") {
      ensureWoOpenFamily(repaint);
      return;
    }
    const now = Date.now();
    const c = _woDeskCache[filter];
    /* Fresh cache (including empty result) — do not re-fetch */
    if (
      c &&
      !c.loading &&
      Array.isArray(c.rows) &&
      typeof c.at === "number" &&
      now - c.at < MAP_WO_DESK_TTL_MS
    ) {
      return;
    }
    if (c && c.loading) return;
    _woDeskCache[filter] = {
      rows: (c && c.rows) || [],
      at: (c && c.at) || 0,
      loading: true,
    };
    const lim = MAP_WO_LIST_CAP;
    let p;
    if (filter === "all") {
      /*
       * pc-482 / pc-934: multi-status live strip via one live-strip hop
       * (suite serializes backlog+ip+review+done — no client Promise.all stampede).
       */
      p = fetchLiveStrip("all", lim).then(function (strip) {
        const seen = {};
        const rows = [];
        const by = (strip && strip.by_status) || {};
        const parts = [
          by.backlog || [],
          by.in_progress || [],
          by.in_review || [],
          by.done || [],
        ];
        const flat = parts[0]
          .concat(parts[1])
          .concat(parts[2])
          .concat(parts[3]);
        const source =
          flat.length > 0 ? flat : (strip && strip.tasks) || [];
        source.forEach(function (t) {
          const s = slipFromApiTask(t);
          if (!s || seen[s.tid]) return;
          seen[s.tid] = 1;
          rows.push(s);
        });
        sortSlipsByUpdated(rows);
        try {
          queueMissingGlanceHydrate(rows);
        } catch (eHydAll) {}
        return rows.slice(0, lim);
      });
    } else if (filter === "in_progress") {
      p = fetchTasksByStatus("in_progress", lim).then(function (tasks) {
        const rows = sortSlipsRecent(
          (tasks || []).map(slipFromApiTask).filter(Boolean)
        ).slice(0, lim);
        try {
          queueMissingGlanceHydrate(rows);
        } catch (eHydIp) {}
        return rows;
      });
    } else if (filter === "in_review") {
      p = fetchTasksByStatus("in_review", lim).then(function (tasks) {
        const rows = sortSlipsRecent(
          (tasks || []).map(slipFromApiTask).filter(Boolean)
        ).slice(0, lim);
        try {
          queueMissingGlanceHydrate(rows);
        } catch (eHydRv) {}
        return rows;
      });
    } else if (filter === "done") {
      p = fetchTasksByStatus("done", lim).then(function (tasks) {
        return sortSlipsRecent(
          (tasks || []).map(slipFromApiTask).filter(Boolean)
        ).slice(0, lim);
      });
    } else {
      p = Promise.resolve([]);
    }
    p.then(function (rows) {
      _woDeskCache[filter] = {
        rows: rows || [],
        at: Date.now(),
        loading: false,
        error: false,
      };
      if (normalizeWoFilter(mapWoFilter) !== filter) return;
      _tapeSig = "";
      if (typeof repaint === "function") {
        try {
          repaint();
        } catch (eR) {}
      }
    }).catch(function () {
      if (_woDeskCache[filter]) {
        _woDeskCache[filter].loading = false;
        _woDeskCache[filter].error = true;
        _woDeskCache[filter].at = 0;
      }
      if (normalizeWoFilter(mapWoFilter) === filter && typeof repaint === "function") {
        try {
          repaint();
        } catch (eR2) {}
      }
    });
  }


  /**
   * WO live-strip status pill class (pc-707).
   * DONE (sage) ≠ FILED (blue) ≠ CANCELED (rose) — never share flat grey.
   */
  function slipPillClass(r) {
    const st = String((r && (r.status || r.stamp)) || "")
      .toLowerCase()
      .replace(/ /g, "_");
    if (typeof mapWoFilter !== "undefined" && mapWoFilter === "for_you") {
      /* pc-1180 / pc-1177: distinct Decide (terracotta) vs Read (steel-blue) */
      const cat = forYouCategoryFromSlip(r);
      return cat && cat.face === "read" ? "st-read" : "st-decide";
    }
    if (st === "canceled" || st === "cancelled") return "st-canceled";
    if (st === "done" || st === "closed" || (r && r.isDone)) return "st-done";
    if (st === "in_progress" || st === "claimed" || (r && r.isMotion)) {
      return "st-progress";
    }
    if (st === "in_review" || st.indexOf("review") >= 0) return "st-review";
    if (st === "stalled" || st === "embargo") return "st-stalled";
    if (st === "deferred" || st === "ice" || st === "parked") {
      return "st-deferred";
    }
    if (st === "ready" || st === "queued") {
      if (r && (r.isWorkerYou || slipIsWorkerYou(r))) return "st-filed";
      return "st-ready";
    }
    if (st === "backlog" || st === "filed" || st === "open") return "st-filed";
    if (st.indexOf("for_you") >= 0 || st.indexOf("need") >= 0) return "st-you";
    return "st-open";
  }


  /**
   * pc-1067: WO status pill. Claimed shows holder — "CLAIMED · figaro".
   * Data already on the slip (labels / holder / desk seat index).
   */
  function slipPillLabel(r) {
    if (!r) return "OPEN";
    const st = String(r.status || "")
      .toLowerCase()
      .replace(/ /g, "_");
    const stamp = String(r.stamp || "")
      .toLowerCase()
      .replace(/_/g, " ")
      .trim();
    const isClaimed =
      st === "in_progress" ||
      st === "claimed" ||
      stamp === "claimed" ||
      stamp === "in progress";
    if (isClaimed) {
      let holder = String(r.holder || "").trim();
      if (!holder) holder = seatHandFromLabels(r.labels || r.labelStr || "");
      if ((!holder || isYouishSeat(holder)) && r.tid && AgentsPanel.getDeskHolderByTid()) {
        const hit = AgentsPanel.getDeskHolderByTid()[String(r.tid)];
        if (hit && hit.hand) holder = hit.hand;
      }
      if (holder && !isYouishSeat(holder)) {
        return ("CLAIMED · " + holder).slice(0, 28);
      }
      return "CLAIMED";
    }
    /* pc-1337: quiet You notes read as NOTE, not READY */
    if (r.isWorkerYou || slipIsWorkerYou(r)) return "NOTE";
    const raw = String(r.stamp || r.status || "open")
      .replace(/_/g, " ")
      .trim();
    return raw.toUpperCase().slice(0, 12);
  }


  /** Soft-patch pill class/label; optional tick animation on class change. */
  function applySlipPill(pillEl, r, opts) {
    if (!pillEl || !r) return;
    opts = opts || {};
    const pcls = slipPillClass(r);
    const lab = slipPillLabel(r);
    const nextCls = "slip-pill " + pcls;
    const classChanged = pillEl.className !== nextCls;
    if (classChanged) pillEl.className = nextCls;
    if (pillEl.textContent !== lab) pillEl.textContent = lab;
    if (classChanged && opts.tick !== false) {
      pillEl.classList.remove("is-pill-tick");
      void pillEl.offsetWidth;
      pillEl.classList.add("is-pill-tick");
      setTimeout(function () {
        try {
          pillEl.classList.remove("is-pill-tick");
        } catch (eT) {}
      }, 750);
    }
  }


  /** Soft-patch ## Glance line (pc-921 / pc-918) — text or skeleton, no full remount. */
  function applySlipGlance(btn, r) {
    if (!btn || !r) return;
    let gEl = btn.querySelector(".slip-glance");
    const text = String(r.glance || "").trim();
    const done =
      !!r.isDone ||
      String(r.status || "").toLowerCase() === "done" ||
      String(r.status || "").toLowerCase() === "canceled" ||
      String(r.status || "").toLowerCase() === "cancelled";
    /* pc-918: desk/title-only → skeleton until hydrate; then hide if none */
    const tidG = String(r.tid || "").trim();
    const pending =
      !text &&
      !done &&
      !!(r.isNew || r.fromLive || r.needGlance || r.fromDesk) &&
      !(tidG && _glanceHydrateDone[tidG]);
    if (!gEl) {
      gEl = document.createElement("span");
      gEl.className = "slip-glance";
      const titleEl = btn.querySelector(".slip-title");
      if (titleEl && titleEl.nextSibling) {
        btn.insertBefore(gEl, titleEl.nextSibling);
      } else if (titleEl) {
        titleEl.insertAdjacentElement("afterend", gEl);
      } else {
        btn.appendChild(gEl);
      }
    }
    if (text) {
      gEl.hidden = false;
      gEl.classList.remove("is-skel");
      if (gEl.textContent !== text) gEl.textContent = text;
    } else if (pending) {
      gEl.hidden = false;
      gEl.textContent = "";
      gEl.classList.add("is-skel");
      try {
        hydrateSlipGlance(r.tid);
      } catch (eH) {}
    } else {
      gEl.hidden = true;
      gEl.textContent = "";
      gEl.classList.remove("is-skel");
    }
  }


  function tapeBeatKind(status, eventType) {
    const st = String(status || "").toLowerCase().replace(/ /g, "_");
    const et = String(eventType || "").toLowerCase();
    /* pc-786: comment / label are first-class rail beats */
    if (
      et === "comment" ||
      et === "tp_comment" ||
      et === "task_comment" ||
      et === "wl_comment" ||
      st === "comment"
    )
      return "comment";
    if (et === "labels_changed" || et === "label" || st === "label")
      return "label";
    if (et === "created" || st === "backlog" || st === "filed") return "filed";
    if (
      st === "in_progress" ||
      st === "in_review" ||
      st === "claimed" ||
      st === "review"
    )
      return "claimed";
    if (st === "done" || st === "canceled" || st === "closed") return "done";
    return "";
  }


  function tapeBeatClass(kind) {
    if (kind === "filed") return "is-feed-filed-beat";
    if (kind === "claimed") return "is-feed-claimed-beat";
    if (kind === "done") return "is-feed-done-beat";
    if (kind === "comment") return "is-feed-comment-beat";
    if (kind === "label") return "is-label-flash";
    return "";
  }


  function tapeBeatForRow(row) {
    if (!row) return "";
    const tid = String(row.tid || row.id || "");
    const pending = tid ? _pendingTapeBeats[tid] : null;
    if (pending && Date.now() - pending.at <= 6000) return pending.kind;
    if (pending) delete _pendingTapeBeats[tid];
    if (!row.isNew) return "";
    return tapeBeatKind(row.status || row.stamp, "");
  }


  function playTapeBeat(rowEl, kind) {
    if (!rowEl || !kind) return;
    const cls = tapeBeatClass(kind);
    if (!cls) return;
    const tid = rowEl.getAttribute("data-tid") || "";
    /*
     * pc-898: never restart a beat already playing / just played for this
     * tid+kind — soft-patch was re-firing animations every poll (WO flicker).
     */
    if (!_playedTapeBeats) _playedTapeBeats = Object.create(null);
    const playKey = tid + ":" + kind;
    const lastAt = _playedTapeBeats[playKey] || 0;
    if (Date.now() - lastAt < 4000) {
      if (tid) delete _pendingTapeBeats[tid];
      return;
    }
    if (rowEl.classList.contains(cls)) {
      if (tid) delete _pendingTapeBeats[tid];
      return;
    }
    TAPE_BEAT_CLASSES.forEach(function (c) {
      rowEl.classList.remove(c);
    });
    void rowEl.offsetWidth;
    rowEl.classList.add(cls);
    _playedTapeBeats[playKey] = Date.now();
    if (tid) delete _pendingTapeBeats[tid];
    /* Clear sticky isNew so soft-patch does not re-qualify this row */
    try {
      if (tid && _liveActivityFeed) {
        _liveActivityFeed.forEach(function (r) {
          if (r && String(r.tid) === tid) r.isNew = false;
        });
      }
    } catch (eNew) {}
    setTimeout(function () {
      try {
        rowEl.classList.remove(cls);
      } catch (e) {}
    }, 1400);
  }


  function queueTapeBeat(tid, status, eventType) {
    tid = String(tid || "").trim();
    const kind = tapeBeatKind(status, eventType);
    if (!tid || !kind) return;
    _pendingTapeBeats[tid] = { kind: kind, at: Date.now() };
    const list = document.getElementById("map-tape-list");
    if (!list) return;
    let row = null;
    list.querySelectorAll("button.slip-row[data-tid]").forEach(function (btn) {
      if (!row && btn.getAttribute("data-tid") === tid) row = btn;
    });
    if (row) {
      playTapeBeat(row, kind);
      try {
        row.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } catch (eSc) {}
    }
  }


  function armRenderedTapeBeats(list) {
    if (!list) return;
    list
      .querySelectorAll(
        "button.slip-row.is-feed-filed-beat, " +
          "button.slip-row.is-feed-claimed-beat, " +
          "button.slip-row.is-feed-done-beat"
      )
      .forEach(function (row) {
        const kind = row.classList.contains("is-feed-filed-beat")
          ? "filed"
          : row.classList.contains("is-feed-claimed-beat")
            ? "claimed"
            : "done";
        const tid = row.getAttribute("data-tid") || "";
        if (tid) delete _pendingTapeBeats[tid];
        const cls = tapeBeatClass(kind);
        setTimeout(function () {
          try {
            row.classList.remove(cls);
          } catch (e) {}
        }, 1400);
      });
  }


  /** Soft-repaint WO tape so a just-filed row can appear (pc-468). */
  function forceTapeRepaint() {
    if (!hostModel()) return;
    try {
      _tapeSig = "";
      hostRepaint(
        _lastCityData || hostModel().city,
        _lastPeople || { sectors: [], in_flight: [] },
        _lastAtt || { items: [] },
        _lastTpScene
      );
    } catch (eT) {}
  }

  function paint(ctx) {
    syncHost();
    prevTransitionIds = readPrevTransitionIds();
    ctx = ctx || {};
    /* pc-1345: honor Overview parked hop even if tape booted before query parse. */
    try {
      var hop = woFilterFromQuery();
      if (hop && normalizeWoFilter(mapWoFilter) !== hop) {
        mapWoFilter = hop;
      }
    } catch (eHop) {}
    var city = ctx.city;
    var people = ctx.people;
    var att = ctx.att;
    var tpScene = ctx.tpScene;
    const stage = document.getElementById("stage");
    const woFiltersEl = document.getElementById("map-wo-filters");
    const tapeList = document.getElementById("map-tape-list");
    const tapeEmpty = document.getElementById("map-tape-empty");
    const woCapEl = document.getElementById("map-wo-cap");
    const woTotalEl = document.getElementById("map-wo-total");
    if (!tapeList && !woFiltersEl) return;
    mapWoFilter = normalizeWoFilter(mapWoFilter);
    try {
      if (!_woQueryScrolled && woFilterFromQuery()) {
        _woQueryScrolled = true;
        var tapeHop =
          woFiltersEl ||
          document.getElementById("map-wo-cap") ||
          document.querySelector(".map-wo-tape");
        if (tapeHop && tapeHop.scrollIntoView) {
          tapeHop.scrollIntoView({ block: "nearest" });
        }
      }
    } catch (eScroll) {}
    const folders = (city && (city.folders || city.neighborhoods)) || [];
    const attItems = (att && att.items) || [];

    /*
     * Desk-column work orders — latest update first.
     * Prefer For You attention slips; fill with open transitions.
     * Click → SuitePaper drawer (stay on Map); ⌘-click would be full page later.
     */
    const slipRows = [];
    const seenSlip = {};
    function slipUpdatedMs(raw) {
      if (raw == null || raw === "") return 0;
      if (typeof raw === "number" && isFinite(raw)) {
        return raw < 1e12 ? raw * 1000 : raw;
      }
      const t = Date.parse(String(raw));
      return isFinite(t) ? t : 0;
    }
    /** Relative + absolute stamp for work-order cards */
    function formatSlipWhen(ms) {
      if (!ms || !isFinite(ms) || ms <= 0) return "";
      const ago = Date.now() - ms;
      let rel = "";
      if (ago < 45 * 1000) rel = "just now";
      else if (ago < 60 * 60 * 1000)
        rel = Math.max(1, Math.round(ago / 60000)) + "m ago";
      else if (ago < 24 * 60 * 60 * 1000)
        rel = Math.max(1, Math.round(ago / 3600000)) + "h ago";
      else if (ago < 7 * 24 * 60 * 60 * 1000)
        rel = Math.max(1, Math.round(ago / 86400000)) + "d ago";
      else {
        const d = new Date(ms);
        rel =
          d.toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          }) +
          " · " +
          d.toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit",
          });
        return rel;
      }
      const d = new Date(ms);
      const abs = d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
      return rel + " · " + abs;
    }
    /* pc-1314: workspace digest uses moved time; piles keep open-age. */
    function tapeWhenLine(r) {
      if (mapWoFilter === "all" && !mapWoProjectKey) {
        return (
          formatSlipMovedWhen((r && r.updated) || 0) ||
          formatSlipWhen((r && r.updated) || 0)
        );
      }
      return slipWhenLine(r) || formatSlipWhen((r && r.updated) || 0);
    }
    function pushSlip(row) {
      if (!row || !row.tid) return;
      const key = String(row.tid) + ":" + (row.prod || "");
      if (seenSlip[key]) {
        /* Prefer richer / newer row when attention + transition both exist */
        const prev = seenSlip[key];
        if ((row.updated || 0) >= (prev.updated || 0)) {
          const idx = slipRows.indexOf(prev);
          if (idx >= 0) slipRows[idx] = row;
          seenSlip[key] = row;
        }
        return;
      }
      seenSlip[key] = row;
      slipRows.push(row);
    }
    attItems.forEach(function (it) {
      if (!it) return;
      const tid = String(it.id || "").trim();
      if (!tid) return;
      const kind = String(it.kind || "need you").replace(/_/g, " ");
      /* pc-198 / pc-949: one citizen stamp — For You (never Needs You on glass) */
      let stamp = "for you";
      if (
        kind === "human gate" ||
        kind === "in review" ||
        kind === "need you" ||
        kind === "needs you" ||
        (kind.indexOf("founder") >= 0 && kind.indexOf("decision") >= 0)
      ) {
        stamp = "for you";
      } else if (kind === "stalled") {
        stamp = "stalled";
      } else if (kind === "embargo") {
        stamp = "embargo";
      } else if (kind) {
        stamp = kind;
      }
      let updated = slipUpdatedMs(
        it.waiting_since ||
          it.updated_at ||
          it.updated ||
          it.since ||
          it.ts ||
          it.created_at
      );
      if (!updated && typeof it.age_minutes === "number" && isFinite(it.age_minutes)) {
        updated = Date.now() - Math.max(0, it.age_minutes) * 60000;
      }
      /* pc-1187: open age from created_at when present; else meta from desk */
      let created = slipUpdatedMs(it.created_at || it.created);
      if (!created && _slipMetaByTid[tid] && _slipMetaByTid[tid].created) {
        created = _slipMetaByTid[tid].created;
      }
      const attProd = resolveSlipProduct(
        it.product || it.project || it.store,
        tid
      );
      pushSlip({
        key: "att:" + tid,
        prod: attProd,
        tid: tid,
        title: String(it.title || it.summary || "").trim().slice(0, 96),
        stamp: stamp,
        status: String(it.status || kind || "").toLowerCase().replace(/ /g, "_"),
        focus: attProd,
        isYou: true,
        isMotion: false,
        isNew: false,
        updated: updated,
        created: created,
      });
    });
    const transitions = ((tpScene && tpScene.recent_transitions) || []).slice();
    const transitionFeedRows = [];
    const transitionFeedSeen = {};
    const titleById = {};
    ((tpScene && tpScene.filed) || []).forEach(function (f) {
      if (f && f.id) titleById[String(f.id)] = f.title || "";
    });
    Object.keys(_woDeskCache || {}).forEach(function (filter) {
      const cached = _woDeskCache[filter];
      ((cached && cached.rows) || []).forEach(function (row) {
        if (row && row.tid && row.title) {
          titleById[String(row.tid)] = row.title;
        }
      });
    });
    transitions.forEach(function (t) {
      if (!t) return;
      const tid = String(t.task_id || t.id || "").trim();
      if (!tid) return;
      const to = String(t.to_status || "").toLowerCase();
      const store = resolveSlipProduct(t.store || t.product || t.project, tid);
      let title = String(t.title || t.summary || titleById[tid] || "").trim();
      if (title === tid) title = "";
      const trKey = String(t.id || tid + ":" + (t.ts || "") + ":" + to);
      const isNewTr = !!(prevTransitionIds && !prevTransitionIds.has(trKey));
      const metaG = (_slipMetaByTid[tid] && _slipMetaByTid[tid].glance) || "";
      const metaC =
        (_slipMetaByTid[tid] && _slipMetaByTid[tid].created) || 0;
      const transitionRow = enrichSlipFromMeta({
        key: "tr:" + tid,
        prod: store,
        tid: tid,
        title: title.slice(0, 96),
        glance: String((t && t.glance) || metaG || "").trim(),
        stamp: transitionVerb(t),
        status: to,
        focus: store,
        isYou: false,
        isMotion: to === "in_progress" || to === "in_review",
        isDone: to === "done" || to === "canceled" || to === "cancelled",
        isNew: isNewTr,
        updated: slipUpdatedMs(t.ts || t.updated_at || t.at),
        created: slipUpdatedMs(t.created_at || t.created) || metaC,
        fromTransition: true,
      });
      pushSlip(transitionRow);
      const feedKey = tid + ":" + store;
      const priorFeedRow = transitionFeedSeen[feedKey];
      if (!priorFeedRow) {
        transitionFeedSeen[feedKey] = transitionRow;
        transitionFeedRows.push(transitionRow);
      } else if ((transitionRow.updated || 0) > (priorFeedRow.updated || 0)) {
        const feedIdx = transitionFeedRows.indexOf(priorFeedRow);
        if (feedIdx >= 0) transitionFeedRows[feedIdx] = transitionRow;
        transitionFeedSeen[feedKey] = transitionRow;
      }
      if (isNewTr) {
        try {
          injectLiveActivity(
            Object.assign({}, transitionRow, {
              isNew: true,
              updated: transitionRow.updated || Date.now(),
            })
          );
        } catch (eInj) {}
      }
    });
    /*
     * Sticky feed: never blank the list if this poll built zero slips
     * (empty attention + empty transitions). Hold last good rows.
     */
    if (
      !slipRows.length &&
      _lastSlipRows &&
      _lastSlipRows.length &&
      mapWoFilter
    ) {
      slipRows.push.apply(slipRows, _lastSlipRows);
    } else if (slipRows.length) {
      _lastSlipRows = slipRows.slice();
    }

    /* Pulse feed is one workspace heartbeat: pure recency, never project buckets. */
    sortSlipsByUpdated(slipRows);
    sortSlipsByUpdated(transitionFeedRows);

    /*
     * Desk store rollups = true city totals (2K+ tickets).
     * Slip rows = recent feed for the list (cannot render full desk here).
     * Count doors use store totals; For You uses the attention membership.
     */
    let nOpenDesk = 0;
    let nIpDesk = 0;
    let nRevDesk = 0;
    let nDoneDesk = 0;
    let nBacklogDesk = 0;
    let nReadyDesk = 0;
    let sawStoreReady = false;
    /* pc-1044: dig-in rollups use only the scoped project's store */
    const digWant = mapWoProjectKey
      ? storeSlugEquivalents(mapWoProjectKey)
      : null;
    function folderInWoScope(f) {
      if (!digWant) return true;
      const fkey = normalizeStoreSlug(
        (f && (f.product || f.slug || f.name || f.store_slug)) || ""
      );
      return !!fkey && digWant.indexOf(fkey) >= 0;
    }
    folders.forEach(function (f) {
      if (!folderInWoScope(f)) return;
      const st = (f && f.store) || {};
      nBacklogDesk += st.backlog || 0;
      nIpDesk += st.in_progress || 0;
      nRevDesk += st.in_review || 0;
      nDoneDesk += st.done || 0;
      nOpenDesk +=
        (st.backlog || 0) + (st.in_progress || 0) + (st.in_review || 0);
      /* pc-688: ready chip prefers scene/store rollup (same family as nOpenDesk) */
      if (st && Object.prototype.hasOwnProperty.call(st, "ready")) {
        sawStoreReady = true;
        nReadyDesk += st.ready || 0;
      }
    });
    /* Grand total — workspace = all stores; dig-in = scoped store only */
    const nDeskTotal = nOpenDesk + nDoneDesk;
    /*
     * Citizen "open" on the subline = live open (deferred excluded) when dual-read
     * is warm — same number as the live count door. Raw nOpenDesk still used for
     * diagnostics / total math; it includes deferred-still-in-backlog rows.
     * pc-1065: only use gate tallies whose scope matches dig-in (else folder rollup).
     */
    let nLiveOpenCitizen = 0;
    const gateTrustedEarly = trustedWoGateCounts();
    if (gateTrustedEarly && gateTrustedEarly.live != null) {
      nLiveOpenCitizen = gateTrustedEarly.live | 0;
    } else {
      folders.forEach(function (f) {
        if (!folderInWoScope(f)) return;
        try {
          nLiveOpenCitizen += openCount(f) | 0;
        } catch (eOc) {
          const st0 = (f && f.store) || {};
          nLiveOpenCitizen +=
            (st0.backlog || 0) +
            (st0.in_progress || 0) +
            (st0.in_review || 0);
        }
      });
    }

    /* List counts from feed; compact count doors use store totals when available */
    const folderSlugsCount = mapFolderSlugSet();
    function keepSlipCount(r) {
      return r && !isOrphanDemoSlip(r, folderSlugsCount);
    }
    const nLiveFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "live");
    }).length;
    const nDeferredFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "deferred");
    }).length;
    const nReadyFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "ready");
    }).length;
    const nForYouFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "for_you");
    }).length;
    const nIpFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "in_progress");
    }).length;
    const nRevFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "in_review");
    }).length;
    const nStalledFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "stalled");
    }).length;
    const nDoneFeed = slipRows.filter(function (r) {
      return keepSlipCount(r) && rowMatchesWoFilter(r, "done");
    }).length;
    /* pc-558: For You door = same membership as list (never max with feed) */
    /* pc-767: when project-scoped, chip count matches scoped list (not workspace total) */
    const nForYouAttClean = forYouAttItems(attItems).length;
    /* pc-1044 / pc-1090: dig-in For You via canonical slug key (no alias fan-out) */
    const nForYou = mapWoProjectKey
      ? (forYouCountsByProduct(attItems)[normalizeStoreSlug(mapWoProjectKey)] | 0)
      : nForYouAttClean;
    const nStalledAtt = attItems.filter(function (it) {
      const k = String((it && it.kind) || "")
        .toLowerCase()
        .replace(/ /g, "_");
      if (k !== "stalled" && k !== "embargo") return false;
      const tid = String((it && it.id) || "").trim();
      return !isOrphanDemoSlip(
        { tid: tid, prod: (it && (it.product || it.project)) || "" },
        folderSlugsCount
      );
    }).length;
    const nStalled = Math.max(nStalledFeed, nStalledAtt);

    /*
     * Per-filter list source (each cap = MAP_WO_LIST_CAP independently):
     *   for_you / stalled → attention tray (full set, not transition leftovers)
     *   live / deferred / ready → open-family desk scan (gate dual-read)
     *   yours → /api/tasks?status=backlog&label=worker:you&product= (pc-1337)
     *   ip / review / done → /api/tasks?status=…&limit=100
     * Feed is only an interim fallback while desk fetch is in flight.
     */
    function slipsFromAttention(forStalled) {
      const rows = [];
      attItems.forEach(function (it) {
        if (!it) return;
        const tid = String(it.id || "").trim();
        if (!tid) return;
        const kind = String(it.kind || "need you").replace(/_/g, " ");
        const k = kind.toLowerCase().replace(/ /g, "_");
        if (forStalled) {
          if (k !== "stalled" && k !== "embargo") return;
        } else {
          /* for_you: human gates + founder decisions; not pure stalled-only */
          if (k === "stalled" || k === "embargo") return;
        }
        /* pc-949: one citizen stamp family — for you (CSS uppercase → FOR YOU) */
        let stamp = forStalled ? "stalled" : "for you";
        if (!forStalled) {
          if (
            kind === "human gate" ||
            kind === "in review" ||
            kind === "need you" ||
            kind === "needs you" ||
            kind.indexOf("founder") >= 0
          )
            stamp = "for you";
          else if (kind) stamp = kind;
        }
        let updated = slipUpdatedMs(
          it.waiting_since ||
            it.updated_at ||
            it.updated ||
            it.since ||
            it.ts ||
            it.created_at
        );
        if (
          !updated &&
          typeof it.age_minutes === "number" &&
          isFinite(it.age_minutes)
        ) {
          updated = Date.now() - Math.max(0, it.age_minutes) * 60000;
        }
        /* pc-1187: open age from created_at when present; else desk meta */
        let created = slipUpdatedMs(it.created_at || it.created);
        if (!created && _slipMetaByTid[tid] && _slipMetaByTid[tid].created) {
          created = _slipMetaByTid[tid].created;
        }
        const attProd = resolveSlipProduct(
          it.product || it.project || it.store,
          tid
        );
        rows.push({
          key: "att:" + tid,
          prod: attProd,
          tid: tid,
          title: String(it.title || it.summary || "").trim().slice(0, 96),
          stamp: stamp,
          status: String(it.status || kind || "")
            .toLowerCase()
            .replace(/ /g, "_"),
          focus: attProd,
          isYou: !forStalled,
          isMotion: false,
          isNew: false,
          updated: updated,
          created: created,
          fromAtt: true,
        });
      });
      /* Same orphan/demo hide as the open tape */
      const fs = mapFolderSlugSet();
      const kept = rows.filter(function (r) {
        return !isOrphanDemoSlip(r, fs);
      });
      /* pc-558: For You urgency order; stalled keeps product-alpha recency */
      if (forStalled) sortSlipsRecent(kept);
      else {
        kept.sort(function (a, b) {
          const sa = forYouUrgencyBoost({
            title: a.title,
            kind: a.stamp,
            note: "",
            age_minutes:
              a.updated > 0
                ? Math.max(0, (Date.now() - a.updated) / 60000)
                : 0,
            product: a.prod,
            id: a.tid,
          });
          const sb = forYouUrgencyBoost({
            title: b.title,
            kind: b.stamp,
            note: "",
            age_minutes:
              b.updated > 0
                ? Math.max(0, (Date.now() - b.updated) / 60000)
                : 0,
            product: b.prod,
            id: b.tid,
          });
          if (sb !== sa) return sb - sa;
          const bu = b.updated || 0;
          const au = a.updated || 0;
          if (bu !== au) return au - bu; /* older waiting first ≈ lower updated */
          const pa = String(a.prod || "").toLowerCase();
          const pb = String(b.prod || "").toLowerCase();
          if (pa !== pb) return pa.localeCompare(pb);
          return String(a.tid || "").localeCompare(String(b.tid || ""));
        });
      }
      return kept.slice(0, MAP_WO_LIST_CAP);
    }

    function repaintWoInsights() {
      if (!hostModel()) return;
      hostRepaint(
        hostModel().city || city,
        {
          in_flight: (hostModel().workers || [])
            .filter(function (w) {
              return w && w.working;
            })
            .map(function (w) {
              return w.name;
            }),
          sectors: [],
        },
        { items: attItems },
        tpScene || _lastTpScene
      );
    }

    /* pc-547: keep live/deferred/ready counts warm even when chip is not selected */
    ensureWoOpenFamily(repaintWoInsights);
    /* pc-995: flush desk-warm repaint that resolved before hostModel() existed (async) */
    try {
      if (hostModel() && ensureWoOpenFamily._pendingRepaint) {
        const pending = ensureWoOpenFamily._pendingRepaint;
        ensureWoOpenFamily._pendingRepaint = null;
        setTimeout(function () {
          try {
            if (typeof pending === "function" && hostModel()) pending();
          } catch (eP) {}
        }, 0);
      }
    } catch (ePend) {}

    let listRows;
    let listFromDesk = false;
    let listLoading = false;
    /* pc-1044: bust desk cache when dig scope flips before any filter read */
    ensureWoDeskScopeFresh();
    if (mapWoFilter === "all") {
      /*
       * pc-1314: no project selected → what-moved digest (filed / claimed /
       * closed) from transitions + SSE ring. Do not union the open live +
       * deferred piles — that plated KEEP-pin ready leftovers as "the city
       * moved." Project dig-in still shows that place's queue.
       * pc-921: warm open-family so _slipMetaByTid gets Glance/status.
       * pc-1044: always apply project scope when dug in (was missing here).
       */
      if (!mapWoProjectKey) {
        listRows = mergeLiveActivityFeed(transitionFeedRows.slice()).filter(
          function (r) {
            return rowMatchesProjectScope(r) && !isStandingChewLeftover(r);
          }
        );
      } else {
        /* pc-1337: that cabinet's queue = live/deferred slips + quiet notes */
        const woOpenInventory = []
          .concat((_woDeskCache.live && _woDeskCache.live.rows) || [])
          .concat((_woDeskCache.deferred && _woDeskCache.deferred.rows) || []);
        listRows = unionAndPinProjectNotes(
          mergeLiveActivityFeed(
            transitionFeedRows.slice().concat(woOpenInventory)
          )
        ).filter(rowMatchesProjectScope);
      }
      listFromDesk = false;
      listLoading = false;
      ensureWoOpenFamily(repaintWoInsights);
      if (mapWoProjectKey) ensureWoProjectNotes(repaintWoInsights);
    } else if (mapWoFilter === "for_you") {
      listRows = slipsFromAttention(false).filter(rowMatchesProjectScope);
      listFromDesk = true;
    } else if (mapWoFilter === "yours") {
      /* pc-1337: project-scoped worker:you notes; workspace dump is retired */
      if (!mapWoProjectKey) {
        listRows = [];
        listFromDesk = true;
        listLoading = false;
        ensureWoProjectNotes(repaintWoInsights);
      } else {
        const ysrc = (_woDeskCache.yours && _woDeskCache.yours.rows) || [];
        listRows = ysrc
          .filter(function (r) {
            return rowMatchesWoFilter(r, "yours");
          })
          .slice(0, MAP_WO_LIST_CAP);
        listFromDesk = true;
        listLoading = !!(
          _woDeskCache.yours &&
          _woDeskCache.yours.loading &&
          !ysrc.length
        );
        ensureWoProjectNotes(repaintWoInsights);
      }
    } else if (mapWoFilter === "stalled") {
      listRows = slipsFromAttention(true).filter(rowMatchesProjectScope);
      listFromDesk = true;
    } else {
      const cached = _woDeskCache[mapWoFilter];
      const cacheFresh =
        cached &&
        !cached.loading &&
        typeof cached.at === "number" &&
        Date.now() - cached.at < MAP_WO_DESK_TTL_MS &&
        Array.isArray(cached.rows);
      if (cacheFresh) {
        /* pc-1044: fresh-cache path must still honor dig-in scope */
        listRows = cached.rows
          .filter(rowMatchesProjectScope)
          .slice(0, MAP_WO_LIST_CAP);
        listFromDesk = true;
        listLoading = false;
      } else if (cached && cached.loading) {
        listRows = (cached.rows && cached.rows.length
          ? cached.rows.filter(rowMatchesProjectScope)
          : slipRows.filter(function (r) {
              return rowMatchesWoFilter(r, mapWoFilter);
            })
        ).slice(0, MAP_WO_LIST_CAP);
        listFromDesk = !!(cached.rows && cached.rows.length);
        listLoading = true;
      } else {
        listRows = slipRows.filter(function (r) {
          return rowMatchesWoFilter(r, mapWoFilter);
        });
        listLoading = true;
      }
      ensureWoDeskFilter(mapWoFilter, repaintWoInsights);
    }
    /*
     * Drop demo/orphan stores (recipes sample, etc.) with no map hub.
     * Non–for-you filters: strip isYou so cards don't gold-wash from
     * sticky attention rows mixed into the open feed.
     * pc-1044 belt: re-apply project scope so no path can leak city feed.
     */
    const folderSlugs = mapFolderSlugSet();
    const filtered = (listRows || [])
      .filter(function (r) {
        if (!rowMatchesProjectScope(r)) return false;
        if (isOrphanDemoSlip(r, folderSlugs)) return false;
        if (r && r.isDemo && isOrphanDemoSlip(r, folderSlugs)) return false;
        return true;
      })
      .map(function (r) {
        if (!r) return r;
        if (mapWoFilter !== "for_you" && r.isYou) {
          return Object.assign({}, r, { isYou: false });
        }
        return r;
      });
    /* pc-490: scoped text filter after feed selection, before cap */
    const preTextCount = filtered.length;
    const textQ = mapWoTextFilter || "";
    const textFiltered = String(textQ).trim()
      ? filtered.filter(function (r) {
          return slipMatchesListFilter(r, textQ);
        })
      : filtered;
    const totalMatched = textFiltered.length;
    /* pc-983: cross-bucket fallback — when text filter finds 0 in scope,
     * search live+ready+deferred+for-you so a gated or deferred slip id
     * is never presented as non-existent. */
    let tapeSlice;
    let isCrossBucket = false;
    let crossBucketSearched = false;
    if (String(textQ).trim() && totalMatched === 0) {
      crossBucketSearched = true;
      const _cbSeen = Object.create(null);
      const _cbAllOpen = [];
      const _cbBuckets = [
        { rows: (_woDeskCache.live && _woDeskCache.live.rows) || [], label: "live" },
        { rows: (_woDeskCache.ready && _woDeskCache.ready.rows) || [], label: "ready" },
        { rows: (_woDeskCache.deferred && _woDeskCache.deferred.rows) || [], label: "deferred" },
        { rows: slipsFromAttention(false), label: "for you" },
      ];
      _cbBuckets.forEach(function (b) {
        b.rows.forEach(function (r) {
          if (!r || !r.tid || _cbSeen[r.tid]) return;
          _cbSeen[r.tid] = true;
          _cbAllOpen.push(Object.assign({}, r, { _crossBucket: b.label }));
        });
      });
      const _cbMatches = _cbAllOpen.filter(function (r) {
        return slipMatchesListFilter(r, textQ);
      });
      if (_cbMatches.length) {
        tapeSlice = _cbMatches.slice(0, MAP_WO_LIST_CAP);
        isCrossBucket = true;
      }
    }
    const listCap =
      mapWoFilter === "all" && !mapWoProjectKey
        ? MAP_WO_DIGEST_CAP
        : MAP_WO_LIST_CAP;
    if (!isCrossBucket) tapeSlice = textFiltered.slice(0, listCap);
    try {
      syncMapTapeFilterChrome(preTextCount, totalMatched);
    } catch (eTf) {}

    function wireWoChipClicks() {
      if (!woFiltersEl || woFiltersEl._wired) return;
      woFiltersEl._wired = true;
      woFiltersEl.addEventListener("click", function (ev) {
        const btn = ev.target && ev.target.closest
          ? ev.target.closest("[data-wo-filter]")
          : null;
        if (!btn || !woFiltersEl.contains(btn)) return;
        ev.preventDefault();
        ev.stopPropagation();
        const f = normalizeWoFilter(btn.getAttribute("data-wo-filter"));
        /* Primary: filter left-rail list (was dig-only → looked broken) */
        applyWorkspaceWoKpiFilter(f);
      });
    }

    function paintWoKpiSelected() {
      if (!woFiltersEl) return;
      const cur = normalizeWoFilter(mapWoFilter);
      const scoped = !!mapWoProjectKey;
      woFiltersEl.querySelectorAll("[data-wo-filter]").forEach(function (btn) {
        const id = normalizeWoFilter(btn.getAttribute("data-wo-filter"));
        const on = cur === id;
        btn.setAttribute("aria-pressed", on ? "true" : "false");
        btn.classList.toggle("is-selected", on);
      });
      try {
        const youCard = document.getElementById("map-you-card");
        if (youCard) {
          youCard.classList.toggle(
            "is-wo-filter",
            !scoped && cur === "for_you"
          );
        }
      } catch (eYou) {}
    }

    /*
     * Header total = all work orders on desk stores (open + done) — the 2K+ figure.
     * pc-482: pill is a filter control → multi-status live strip (capped).
     * pc-687: subline "X open · Y done" so the pill cannot read as open-only.
     */
    if (woTotalEl) {
      const t = String(nDeskTotal);
      if (woTotalEl.textContent !== t) woTotalEl.textContent = t;
      const allOn = mapWoFilter === "all";
      const pressed = allOn ? "true" : "false";
      if (woTotalEl.getAttribute("aria-pressed") !== pressed) {
        woTotalEl.setAttribute("aria-pressed", pressed);
      }
      woTotalEl.classList.toggle("is-selected", allOn);
      /* open = live open (not deferred); feed below = activity incl done */
      const openDoneLine =
        nLiveOpenCitizen + " open · " + nDoneDesk + " done";
      /* pc-1065: header scope cue matches dig-in pile (not "across projects" under project) */
      const totalScopeCue = mapWoProjectKey
        ? " in " + mapWoProjectKey
        : " across projects";
      woTotalEl.title =
        nDeskTotal +
        " work orders" +
        totalScopeCue +
        " (" +
        openDoneLine +
        "; open = live, deferred excluded)" +
        (allOn
          ? " · list is recent activity (file · claim · close), not full open inventory"
          : "");
      const ariaTotal =
        nDeskTotal +
        " work orders" +
        totalScopeCue +
        ", " +
        openDoneLine +
        (allOn ? ", showing recent activity" : "");
      if (woTotalEl.getAttribute("aria-label") !== ariaTotal) {
        woTotalEl.setAttribute("aria-label", ariaTotal);
      }
      const woTotalSubEl = document.getElementById("map-wo-total-sub");
      if (woTotalSubEl && woTotalSubEl.textContent !== openDoneLine) {
        woTotalSubEl.textContent = openDoneLine;
      }
      if (woTotalSubEl) {
        woTotalSubEl.title =
          "Open = live open (deferred/ice excluded — same as live door). Done = closed. Click total for recent activity feed.";
      }
      if (!woTotalEl._wiredAll) {
        woTotalEl._wiredAll = true;
        woTotalEl.addEventListener("click", function () {
          if (normalizeWoFilter(mapWoFilter) === "all" && !mapWoProjectKey)
            return;
          mapWoProjectKey = "";
          mapWoFilter = "all";
          _tapeSig = "";
          _chipSig = "";
          _chipBuilt = false;
          repaintWoInsights();
        });
      }
    }
    /* Soft-update compact counts from uncapped tallies; For You from attention */
    if (woFiltersEl) {
      /*
       * pc-1065: one scope for all four doors.
       * Trusted gate tallies only when scope stamp matches dig-in; otherwise
       * dig-in falls back to project folder rollups / feed (never workspace
       * live next to project-scoped for-you).
       */
      const gateOk = trustedWoGateCounts();
      const nLive =
        gateOk && gateOk.live != null
          ? gateOk.live
          : mapWoProjectKey
            ? Math.max(nLiveOpenCitizen, nLiveFeed)
            : Math.max(nLiveFeed, 0);
      let nDeferredScoped = 0;
      if (mapWoProjectKey && !(gateOk && gateOk.deferred != null)) {
        folders.forEach(function (f) {
          if (!folderInWoScope(f)) return;
          try {
            nDeferredScoped += deferredCount(f) | 0;
          } catch (eDef) {}
        });
      }
      const nDeferred =
        gateOk && gateOk.deferred != null
          ? gateOk.deferred
          : mapWoProjectKey
            ? Math.max(nDeferredScoped, nDeferredFeed)
            : Math.max(nDeferredFeed, 0);
      /* pc-688: store.ready rollup first; else /api/wo-gate-counts; else feed */
      const nReady = sawStoreReady
        ? nReadyDesk
        : gateOk && gateOk.ready != null
          ? gateOk.ready
          : Math.max(nReadyFeed, 0);
      const chipVals = {
        live: nLive,
        ready: nReady,
        deferred: nDeferred,
        for_you: nForYou,
      };
      const scopeHint = mapWoProjectKey
        ? " Scoped to " + mapWoProjectKey + "."
        : " Workspace-wide.";
      const chipMeta = {
        live:
          "Live open — non-deferred open work (" +
          nLive +
          ")." +
          scopeHint +
          " Same meaning as the “open” subline above. Click filters the list; again for recent activity.",
        deferred:
          "Deferred / ice (" +
          nDeferred +
          ") — not in live open." +
          scopeHint +
          " Click filters the list; again for recent activity.",
        ready:
          "Ready — open backlog with no gate (" +
          nReady +
          "). Subset of live open." +
          scopeHint +
          " Click filters the list.",
        for_you:
          "For You act-now (" +
          nForYou +
          "). Human gates only." +
          (mapWoProjectKey
            ? " Scoped to " + mapWoProjectKey + " (matches dig-in, not full You card)."
            : " Same set as the You card.") +
          " Click filters the list.",
      };
      /* pc-651 / pc-701: chip legend retired — strip any ghost node on paint */
      try {
        const ghostLeg = woFiltersEl.querySelector(
          "#map-wo-chip-legend, .map-wo-chip-legend"
        );
        if (ghostLeg) ghostLeg.remove();
      } catch (eLeg) {}
      const chipSig =
        [nLive, nReady, nDeferred, nForYou, nDeskTotal].join(",");
      const existing = woFiltersEl.querySelectorAll("[data-wo-filter]");
      const hasLegacy =
        !!woFiltersEl.querySelector('[data-wo-filter="all"]') ||
        !!woFiltersEl.querySelector('[data-wo-filter="need_you"]') ||
        !!woFiltersEl.querySelector('[data-wo-filter="tape"]') ||
        !!woFiltersEl.querySelector('[data-wo-filter="open"]') ||
        !!woFiltersEl.querySelector(".wo-chip") ||
        !!woFiltersEl.querySelector(".map-wo-chip-legend") ||
        !!woFiltersEl.querySelector("#map-wo-chip-legend");
      /* pc-701: count sentence only (live · ready · deferred · for you); no FOR YOU pill.
       * pc-995: map-fast chips share structure but carry data-fast-rail and are unwired. */
      const structureOk =
        existing.length === MAP_WO_CHIP_FILTERS.length &&
        !!woFiltersEl.querySelector('[data-wo-filter="live"]') &&
        !!woFiltersEl.querySelector('[data-wo-filter="deferred"]') &&
        !!woFiltersEl.querySelector('[data-wo-filter="ready"]') &&
        !!woFiltersEl.querySelector('[data-wo-filter="for_you"]') &&
        !!woFiltersEl.querySelector(".wo-count-line") &&
        !woFiltersEl.querySelector(".wo-chip") &&
        !woFiltersEl.querySelector(".map-wo-chip-legend") &&
        !woFiltersEl.querySelector("[data-fast-rail]") &&
        !hasLegacy &&
        _chipBuilt;

      /* pc-1133: aria-label map mirrors woCountDoor label strings */
      const _chipAriaLabels = {live:"live",ready:"ready",deferred:"deferred",for_you:"for you"};
      if (structureOk) {
        existing.forEach(function (btn) {
          const id = btn.getAttribute("data-wo-filter");
          const vEl = btn.querySelector(".v");
          if (vEl && chipVals[id] != null) {
            const next = String(chipVals[id]);
            if (vEl.textContent !== next) vEl.textContent = next;
            /* pc-1133: sync aria-label in same write as textContent */
            const ariaLabel = _chipAriaLabels[id];
            if (ariaLabel) {
              const ariaNext = "Filter work orders to " + ariaLabel + ", " + next;
              if (btn.getAttribute("aria-label") !== ariaNext) btn.setAttribute("aria-label", ariaNext);
            }
          }
          if (chipMeta[id] && btn.title !== chipMeta[id]) {
            btn.title = chipMeta[id];
          }
        });
        _chipSig = chipSig;
        /* pc-995: soft count update still needs click wiring if never bound */
        wireWoChipClicks();
        paintWoKpiSelected();
      } else if (_chipSig !== chipSig || hasLegacy || !structureOk) {
        _chipSig = chipSig;
        _chipBuilt = true;
        function woCountDoor(id, label, value, title) {
          return (
            '<button type="button" class="wo-count-link" ' +
            'data-wo-filter="' +
            id +
            '" aria-pressed="false" title="' +
            String(title || label).replace(/"/g, "&quot;") +
            '" aria-label="Filter work orders to ' +
            String(label).replace(/"/g, "&quot;") +
            ", " +
            value +
            '">' +
            '<span class="v">' +
            value +
            "</span>" +
            '<span class="l">' +
            label +
            "</span></button>"
          );
        }
        woFiltersEl.innerHTML =
          '<span class="wo-count-line" role="group" aria-label="Work-order counts">' +
          woCountDoor("live", "live", nLive, chipMeta.live) +
          '<span class="wo-count-sep" aria-hidden="true">·</span>' +
          woCountDoor("ready", "ready", nReady, chipMeta.ready) +
          '<span class="wo-count-sep" aria-hidden="true">·</span>' +
          woCountDoor("deferred", "deferred", nDeferred, chipMeta.deferred) +
          '<span class="wo-count-sep" aria-hidden="true">·</span>' +
          woCountDoor("for_you", "for you", nForYou, chipMeta.for_you) +
          "</span>";
        woFiltersEl._wired = false;
        wireWoChipClicks();
        paintWoKpiSelected();
      } else {
        wireWoChipClicks();
        paintWoKpiSelected();
      }
    }

    /* pc-559: hoist filterLabel above woCapEl — empty-state path below used it
     * outside the block → ReferenceError (blank Map skin on paintMapInsights).
     * pc-687: filter=all list is "recent activity" (capped pulse), not full inventory.
     * pc-692: scope chrome (Workspace vs project) is always painted separately. */
    const filterLabel =
      (mapWoProjectKey ? mapWoProjectKey + " · " : "Workspace · ") +
      (mapWoFilter === "all"
        ? "live activity"
        : mapWoFilter === "live"
          ? "live open"
          : mapWoFilter === "deferred"
            ? "deferred / ice"
            : mapWoFilter === "yours"
              ? "your list (worker:you)"
              : mapWoFilter === "for_you"
                ? "For You (act-now)"
                : mapWoFilter.replace(/_/g, " "));
    try {
      /* Scope attribution chrome retired — aria-label still names dig/filter context */
      const tapeAside = document.getElementById("map-tape");
      if (tapeAside) {
        const scopeText = mapWoScopeChromeText();
        tapeAside.setAttribute(
          "aria-label",
          mapWoProjectKey
            ? "Work orders · " + scopeText
            : "Work orders across projects"
        );
      }
    } catch (eScopePaint) {}
    if (woCapEl) {
      let capText = "";
      let capHide = true;
      /* pc-1065: cap badge uses same scope-trusted tallies as count doors */
      const gateCap = trustedWoGateCounts();
      const nLiveCap =
        gateCap && gateCap.live != null
          ? gateCap.live
          : mapWoProjectKey
            ? Math.max(nLiveOpenCitizen, nLiveFeed)
            : nLiveFeed;
      const nDeferredCap =
        gateCap && gateCap.deferred != null
          ? gateCap.deferred
          : nDeferredFeed;
      const nReadyCap = sawStoreReady
        ? nReadyDesk
        : gateCap && gateCap.ready != null
          ? gateCap.ready
          : nReadyFeed;
      const deskHint =
        mapWoFilter === "all"
          ? nDeskTotal
          : mapWoFilter === "live"
            ? nLiveCap
            : mapWoFilter === "deferred"
              ? nDeferredCap
              : mapWoFilter === "ready"
                ? nReadyCap
                : mapWoFilter === "in_progress"
                  ? nIpDesk
                  : mapWoFilter === "in_review"
                    ? nRevDesk
                    : mapWoFilter === "done"
                      ? nDoneDesk
                      : mapWoFilter === "for_you"
                        ? nForYou
                        : mapWoFilter === "stalled"
                          ? nStalled
                          : nDeskTotal;
      if (listLoading && !tapeSlice.length) {
        capHide = false;
        capText = "Loading " + filterLabel + "…";
      } else if (totalMatched >= MAP_WO_LIST_CAP && deskHint > MAP_WO_LIST_CAP) {
        /* pc-1044: badge workspace-wide vs per-project cap so truncation is visible */
        capHide = false;
        capText =
          "Showing " +
          MAP_WO_LIST_CAP +
          " of " +
          deskHint +
          " · " +
          filterLabel +
          (mapWoProjectKey
            ? " · per project"
            : " · workspace-wide cap") +
          (mapWoFilter === "all" ? " · newest first" : "") +
          (String(mapWoTextFilter || "").trim() ? " · text filter on" : "");
      } else if (totalMatched > 0 || isCrossBucket) {
        capHide = false;
        const textOn = String(mapWoTextFilter || "").trim();
        if (isCrossBucket) {
          /* pc-983: results came from outside the current scope */
          capText =
            tapeSlice.length +
            " found across all open · not in " +
            filterLabel;
        } else if (mapWoFilter === "all" && !textOn) {
          /* pc-687: all-filter caption = feed vs lifetime total, not "inventory" */
          /* pc-1314: workspace strip names the digest; project dig stays in-feed */
          capText = mapWoProjectKey
            ? totalMatched +
              " in feed · " +
              nDeskTotal +
              " total · " +
              filterLabel
            : tapeSlice.length +
              " what moved · " +
              nDeskTotal +
              " total · " +
              filterLabel;
        } else {
          capText = textOn
            ? totalMatched +
              " match · " +
              preTextCount +
              " " +
              filterLabel +
              " · filter on"
            : totalMatched +
              (listFromDesk ? " shown" : " in feed") +
              " · " +
              deskHint +
              " " +
              filterLabel +
              " · " +
              nDeskTotal +
              " total across the workspace";
        }
      } else if (deskHint > 0 || nDeskTotal > 0) {
        capHide = false;
        capText = listLoading
          ? "Loading…"
          : String(mapWoTextFilter || "").trim()
            ? (crossBucketSearched
                ? "No open match · use Map Search (top) for done/closed"
                : "0 match · " + preTextCount + " " + filterLabel + " · clear filter")
            : mapWoFilter === "all"
              ? "0 in feed · " + nDeskTotal + " total · " + filterLabel
              : "0 shown · " + deskHint + " " + filterLabel;
      }
      if (woCapEl.hidden !== capHide) woCapEl.hidden = capHide;
      if (!capHide && woCapEl.textContent !== capText) {
        woCapEl.textContent = capText;
      }
    }

    try {
      var _hy = H("paintHygieneSurfaces");
      if (_hy) _hy();
    } catch (eH) {}

    if (tapeList && tapeEmpty) {
      if (!tapeSlice.length) {
        if (!tapeList.hidden) tapeList.hidden = true;
        /* Keep empty message soft — don't thrash innerHTML of list every poll */
        tapeEmpty.hidden = false;
        /* pc-934: honest desk-down message — never fake empty tape after 502 stampede */
        const deskErr =
          !listLoading &&
          ((_woDeskCache[mapWoFilter] && _woDeskCache[mapWoFilter].error) ||
            (_woDeskCache.live && _woDeskCache.live.error) ||
            !!_woDeskLastError);
        const emptyMsg = listLoading
          ? "Loading " + filterLabel + "…"
          : deskErr
            ? "Work orders desk unreachable — retry shortly"
            : String(mapWoTextFilter || "").trim() && preTextCount > 0
              ? (crossBucketSearched
                  ? "No open match · try Map Search for done/closed · Esc clears"
                  : "No slips match filter · Esc clears")
              : mapWoFilter === "all" && nDeskTotal === 0
                ? mapWoProjectKey
                  ? "No work orders in " + mapWoProjectKey
                  : "No work orders across projects"
                : mapWoFilter === "yours" && !mapWoProjectKey
                  ? "Quiet notes live on Overview — open a project for that project's list"
                  : mapWoFilter === "yours"
                    ? "No quiet notes in " + mapWoProjectKey
                    : mapWoFilter === "for_you" && nForYou === 0
                  ? "No act-now work orders in this pile"
                  : mapWoFilter === "stalled" && nStalled === 0
                    ? "No stalled work orders"
                    : mapWoFilter === "done" && nDoneDesk === 0
                      ? "No done work orders"
                      : mapWoFilter === "live" &&
                          (function () {
                            const g = trustedWoGateCounts();
                            return (
                              (g && g.live != null
                                ? g.live
                                : mapWoProjectKey
                                  ? Math.max(nLiveOpenCitizen, nLiveFeed)
                                  : nLiveFeed) === 0
                            );
                          })()
                        ? "No live open work orders (ice is under Deferred)"
                        : mapWoFilter === "deferred" &&
                            (function () {
                              const g = trustedWoGateCounts();
                              return (
                                (g && g.deferred != null
                                  ? g.deferred
                                  : nDeferredFeed) === 0
                              );
                            })()
                          ? "No deferred / ice work orders"
                          : mapWoFilter === "ready" &&
                              (function () {
                                const g = trustedWoGateCounts();
                                return (
                                  (sawStoreReady
                                    ? nReadyDesk
                                    : g && g.ready != null
                                      ? g.ready
                                      : nReadyFeed) === 0
                                );
                              })()
                            ? "No ready (ungated backlog) work orders"
                            : mapWoFilter === "in_progress" && nIpDesk === 0
                              ? "No in-progress work orders"
                              : mapWoFilter === "in_review" && nRevDesk === 0
                                ? "No in-review work orders"
                                : "Quiet — no slips for this filter";
        if (tapeEmpty.textContent !== emptyMsg) {
          tapeEmpty.textContent = emptyMsg;
        }
        if (stage) stage.classList.remove("has-map-tape");
        _tapeSig = "";
      } else {
        tapeEmpty.hidden = true;
        tapeList.hidden = false;
        if (stage) stage.classList.add("has-map-tape");
        /*
         * Live feed sig = ordered activity (tid + stamp + updated).
         * Order or status change → full rebuild so newest event rises to top.
         */
        const tapeSig =
          mapWoFilter +
          "|" +
          tapeSlice
            .map(function (r) {
              return (
                String(r.tid || "") +
                ":" +
                String(r.stamp || r.status || "") +
                ":" +
                String(r.updated || 0)
              );
            })
            .join("|");
        const hasRows = !!tapeList.querySelector("button.slip-row");
        const orderOnlySig =
          mapWoFilter +
          "|" +
          tapeSlice
            .map(function (r) {
              return String(r.tid || "");
            })
            .join("|");
        const sameOrder =
          _tapeOrderSig === orderOnlySig && hasRows;
        const tapeHasFastRail = !!(
          tapeList.querySelector && tapeList.querySelector("[data-fast-rail]")
        );
        if (
          _tapeSig === tapeSig &&
          hasRows &&
          !tapeHasFastRail
        ) {
          /* Identical activity state — refresh when text + keep pills in sync */
          const byTid = {};
          tapeSlice.forEach(function (r) {
            byTid[String(r.tid || "")] = r;
          });
          tapeList.querySelectorAll("button.slip-row").forEach(function (btn) {
            const tid = btn.getAttribute("data-tid") || "";
            const r = byTid[tid];
            if (!r) return;
            const whenEl = btn.querySelector(".slip-when");
            if (whenEl) {
              const when = tapeWhenLine(r);
              if (when) {
                whenEl.hidden = false;
                if (whenEl.textContent !== when) whenEl.textContent = when;
              }
            }
            const pillEl0 = btn.querySelector(".slip-pill");
            if (pillEl0) applySlipPill(pillEl0, r, { tick: false });
            applySlipGlance(btn, r);
            /* Beats only from queueTapeBeat / true pending — not every soft poll */
            const tidKey = String(r.tid || "");
            if (tidKey && _pendingTapeBeats[tidKey]) {
              const beat = tapeBeatForRow(r);
              if (beat) playTapeBeat(btn, beat);
            }
          });
        } else if (sameOrder && !tapeHasFastRail) {
          /*
           * Same tid order (live feed or pile): soft-patch stamp/title/pill
           * without wiping the list (pc-700 / pc-707). Full rebuild only when
           * membership/order changes so newest-event re-rank still animates in.
           * pc-995: skip soft-patch while residual map-fast tape remains.
           */
          _tapeSig = tapeSig;
          const byTid2 = {};
          tapeSlice.forEach(function (r) {
            byTid2[String(r.tid || "")] = r;
          });
          tapeList.querySelectorAll("button.slip-row").forEach(function (btn) {
            const tid = btn.getAttribute("data-tid") || "";
            const r = byTid2[tid];
            if (!r) return;
            const titleEl = btn.querySelector(".slip-title");
            const whenEl = btn.querySelector(".slip-when");
            const pillEl = btn.querySelector(".slip-pill");
            const title = String(r.title || "").trim() || "—";
            if (titleEl && titleEl.textContent !== title) {
              titleEl.textContent = title;
            }
            if (whenEl) {
              const when = tapeWhenLine(r);
              if (when) {
                whenEl.hidden = false;
                if (whenEl.textContent !== when) whenEl.textContent = when;
                whenEl.title = [
                  r.created ? "opened " + new Date(r.created).toISOString() : "",
                  r.updated ? "touched " + new Date(r.updated).toISOString() : "",
                ]
                  .filter(Boolean)
                  .join(" · ");
              } else {
                whenEl.hidden = true;
                whenEl.textContent = "";
              }
            }
            /* tick:false — continuous pill re-tick was animating every poll */
            if (pillEl) applySlipPill(pillEl, r, { tick: false });
            applySlipGlance(btn, r);
            if (mapWoFilter === "for_you" && r.isYou) btn.classList.add("is-you");
            else btn.classList.remove("is-you");
            const rowDone =
              !!r.isDone ||
              String(r.status || "").toLowerCase() === "done" ||
              String(r.status || "").toLowerCase() === "canceled" ||
              String(r.status || "").toLowerCase() === "cancelled";
            btn.classList.toggle("is-feed-done", rowDone);
            const tidKey2 = String(r.tid || "");
            if (tidKey2 && _pendingTapeBeats[tidKey2]) {
              const beat = tapeBeatForRow(r);
              if (beat) playTapeBeat(btn, beat);
            } else if (r.isNew) {
              /* Consume isNew without replaying after first render */
              r.isNew = false;
            }
          });
        } else {
          _tapeOrderSig = orderOnlySig;
          /* Live activity: pin to top when feed reorders; piles keep scroll */
          const scrollY =
            mapWoFilter === "all" &&
            tapeSlice[0] &&
            tapeSlice[0].isNew
              ? 0
              : tapeList.scrollTop;
          _tapeSig = tapeSig;
          clearMapEntityPreviewKind("work");
          let html = "";
          /* First list mount: no beat storm — only real-time events animate */
          const tapeBeatsOk = !!_tapeEverBuilt;
          _tapeEverBuilt = true;
          tapeSlice.forEach(function (r) {
            const focus = resolveSlipProduct(r.focus || r.prod, r.tid);
            /* Card gold only meaningful on For You; pill still shows stamp */
            const showYou = mapWoFilter === "for_you" && !!r.isYou;
            const stLow = String(r.status || "").toLowerCase();
            const done =
              !!r.isDone ||
              stLow === "done" ||
              stLow === "canceled" ||
              stLow === "cancelled";
            let beatClass = "";
            if (tapeBeatsOk) {
              const tidB = String(r.tid || "");
              if (tidB && _pendingTapeBeats[tidB]) {
                beatClass = tapeBeatClass(tapeBeatForRow(r));
              }
            }
            /* Snapshot before consume — isNew must still drive glancePending */
            const wasNew = !!r.isNew;
            const glanceText = String(r.glance || "").trim();
            const tidForG = String(r.tid || "").trim();
            /* New/SSE/desk title-only → skeleton until hydrate (pc-921/918) */
            const glancePending =
              !glanceText &&
              !done &&
              !!(wasNew || r.fromLive || r.needGlance || r.fromDesk) &&
              !(tidForG && _glanceHydrateDone[tidForG]);
            if (r.isNew) r.isNew = false;
            const cls =
              "slip-row" +
              (showYou ? " is-you" : "") +
              (r.isMotion ? " is-motion" : "") +
              (done ? " is-feed-done" : "") +
              (beatClass ? " " + beatClass : "");
            const rawTitle = String(r.title || "").trim() || "—";
            /* For You filter: project · category first; id quiet in when line */
            let idLine = r.tid || "—";
            let pillText = slipPillLabel(r);
            let title = rawTitle;
            /* pc-1187: open age from created_at; last-touch secondary.
             * pc-1314: workspace digest uses moved time instead. */
            let when = tapeWhenLine(r);
            /* pc-983: cross-bucket — show bucket so user knows where it was found */
            if (r._crossBucket) idLine = r._crossBucket + " · " + (r.tid || "—");
            if (showYou || mapWoFilter === "for_you") {
              const cat = forYouCategoryFromSlip(r);
              const prod = forYouProductLabel(
                r.prod || r.focus || r.product || focus || ""
              );
              idLine = prod + " · " + cat.label;
              pillText = cat.label;
              title = rawTitle
                .replace(/^Inbox\s*[·•\-–]\s*/i, "")
                .replace(/^FOUNDER\s*[·•\-–]\s*/i, "");
              const idAge = [r.tid, when].filter(Boolean).join(" · ");
              when = idAge || when;
            }
            const whenTitle = [
              r.tid || "",
              r.created ? "opened " + new Date(r.created).toISOString() : "",
              r.updated ? "touched " + new Date(r.updated).toISOString() : "",
            ]
              .filter(Boolean)
              .join(" · ");
            html +=
              '<li class="slip-li"><button type="button" class="' +
              cls +
              '" data-focus="' +
              escAttr(focus) +
              '" data-entity-slug="' +
              escAttr(focus) +
              '" data-tid="' +
              escAttr(r.tid) +
              '">' +
              '<span class="slip-top">' +
              '<span class="slip-id">' +
              escHtml(idLine) +
              "</span>" +
              '<span class="slip-pill ' +
              slipPillClass(r) +
              '">' +
              escHtml(pillText) +
              "</span></span>" +
              '<span class="slip-title">' +
              escHtml(title) +
              "</span>" +
              (glanceText
                ? '<span class="slip-glance">' +
                  escHtml(glanceText) +
                  "</span>"
                : glancePending
                  ? '<span class="slip-glance is-skel" aria-hidden="true"></span>'
                  : '<span class="slip-glance" hidden></span>') +
              (when
                ? '<span class="slip-when" title="' +
                  escAttr(whenTitle) +
                  '">' +
                  escHtml(when) +
                  "</span>"
                : '<span class="slip-when" hidden></span>') +
              "</button></li>";
            if (glancePending && r.tid) {
              try {
                hydrateSlipGlance(r.tid);
              } catch (eHg) {}
            }
          });
          tapeList.innerHTML = html;
          armRenderedTapeBeats(tapeList);
          try {
            tapeList.scrollTop = scrollY;
          } catch (eSc) {}
          tapeList.querySelectorAll("button.slip-row").forEach(function (btn) {
            wireMapEntityPreview(btn, function () {
              return {
                kind: "work",
                tid: btn.getAttribute("data-tid") || "",
                slug:
                  btn.getAttribute("data-entity-slug") ||
                  btn.getAttribute("data-focus") ||
                  "",
              };
            });
            btn.addEventListener("click", function (e) {
              const tid = btn.getAttribute("data-tid");
              const f = btn.getAttribute("data-focus");
              if (!tid) {
                if (f) focusProjectOnMap(f, findPlotBySlug(f), null);
                return;
              }
              try {
                selectMapEntity({
                  kind: "work",
                  tid: tid,
                  slug: f || "",
                });
              } catch (eSel) {}
              /* Stay on Map — SuitePaper ticket drawer (same shell as AGENTS.md) */
              if (
                window.SuitePaper &&
                typeof SuitePaper.openTicket === "function"
              ) {
                if (e.metaKey || e.ctrlKey) {
                  location.href =
                    "/ticket?id=" +
                    encodeURIComponent(tid) +
                    (f ? "&project=" + encodeURIComponent(f) : "");
                  return;
                }
                try {
                  SuitePaper.openTicket(tid);
                  return;
                } catch (err) {
                  console.warn("SuitePaper.openTicket", err);
                }
              }
              location.href =
                "/ticket?id=" +
                encodeURIComponent(tid) +
                (f ? "&project=" + encodeURIComponent(f) : "");
            });
          });
        }
      }
    }
  }

  function bustTape() {
    _tapeSig = "";
    _tapeOrderSig = "";
  }
  function bustChips() {
    _chipSig = "";
    _chipBuilt = false;
  }
  function bustAll() {
    bustTape();
    bustChips();
  }

  function getFilter() {
    return mapWoFilter;
  }
  function setFilter(f) {
    mapWoFilter = normalizeWoFilter(f);
    return mapWoFilter;
  }
  function getProjectKey() {
    return mapWoProjectKey;
  }
  function setProjectKey(k) {
    mapWoProjectKey = String(k || "")
      .toLowerCase()
      .trim();
    return mapWoProjectKey;
  }
  function getTextFilter() {
    return mapWoTextFilter;
  }
  function setTextFilter(q) {
    mapWoTextFilter = String(q || "");
    return mapWoTextFilter;
  }
  function getDeskCache() {
    return _woDeskCache;
  }
  function getGateCounts() {
    return _woGateCounts;
  }
  function getSlipMeta() {
    return _slipMetaByTid;
  }
  function getLiveActivityFeed() {
    return _liveActivityFeed;
  }
  function getFolderHeat() {
    return _folderHeatByKey;
  }

  var WoTape = {
    setMapWoFilterFromInspect: setMapWoFilterFromInspect,
    ensureMapTapeFilterWired: ensureMapTapeFilterWired,
    syncMapTapeFilterChrome: syncMapTapeFilterChrome,
    deskScopeKey: deskScopeKey,
    trustedWoGateCounts: trustedWoGateCounts,
    ensureWoDeskScopeFresh: ensureWoDeskScopeFresh,
    normalizeWoFilter: normalizeWoFilter,
    focusProjectWorkOrders: focusProjectWorkOrders,
    clearMapWoProjectScope: clearMapWoProjectScope,
    syncDigInWoToLeftRail: syncDigInWoToLeftRail,
    mapWoScopeChromeText: mapWoScopeChromeText,
    rowMatchesProjectScope: rowMatchesProjectScope,
    rowMatchesWoFilter: rowMatchesWoFilter,
    getFolderHeatAt: getFolderHeatAt,
    repaintWoInsights: repaintWoInsights,
    slipIsWorkerYou: slipIsWorkerYou,
    slipMatchesListFilter: slipMatchesListFilter,
    slipUpdatedMsShared: slipUpdatedMsShared,
    formatAgeCompact: formatAgeCompact,
    formatSlipOpenWhen: formatSlipOpenWhen,
    formatSlipMovedWhen: formatSlipMovedWhen,
    isStandingChewLeftover: isStandingChewLeftover,
    slipWhenLine: slipWhenLine,
    extractGlanceText: extractGlanceText,
    rememberSlipMeta: rememberSlipMeta,
    enrichSlipFromMeta: enrichSlipFromMeta,
    bustWoDeskCache: bustWoDeskCache,
    hydrateSlipGlance: hydrateSlipGlance,
    slipFromApiTask: slipFromApiTask,
    fetchTasksByStatus: fetchTasksByStatus,
    fetchWorkerYouNotes: fetchWorkerYouNotes,
    isProjectYouNote: isProjectYouNote,
    unionAndPinProjectNotes: unionAndPinProjectNotes,
    ensureWoProjectNotes: ensureWoProjectNotes,
    queueMissingGlanceHydrate: queueMissingGlanceHydrate,
    fetchLiveStripSerialFallback: fetchLiveStripSerialFallback,
    fetchLiveStrip: fetchLiveStrip,
    sortSlipsRecent: sortSlipsRecent,
    sortSlipsByUpdated: sortSlipsByUpdated,
    injectLiveActivity: injectLiveActivity,
    mergeLiveActivityFeed: mergeLiveActivityFeed,
    ensureWoOpenFamily: ensureWoOpenFamily,
    rebuildFolderHeatFromOpenRows: rebuildFolderHeatFromOpenRows,
    folderHeatFor: folderHeatFor,
    deferredCount: deferredCount,
    ensureWoDeskFilter: ensureWoDeskFilter,
    slipPillClass: slipPillClass,
    slipPillLabel: slipPillLabel,
    applySlipPill: applySlipPill,
    applySlipGlance: applySlipGlance,
    tapeBeatKind: tapeBeatKind,
    tapeBeatClass: tapeBeatClass,
    tapeBeatForRow: tapeBeatForRow,
    playTapeBeat: playTapeBeat,
    queueTapeBeat: queueTapeBeat,
    armRenderedTapeBeats: armRenderedTapeBeats,
    forceTapeRepaint: forceTapeRepaint,
    init: init,
    paint: paint,
    bustTape: bustTape,
    bustChips: bustChips,
    bustAll: bustAll,
    getFilter: getFilter,
    setFilter: setFilter,
    getProjectKey: getProjectKey,
    setProjectKey: setProjectKey,
    getTextFilter: getTextFilter,
    setTextFilter: setTextFilter,
    getDeskCache: getDeskCache,
    getGateCounts: getGateCounts,
    getSlipMeta: getSlipMeta,
    getLiveActivityFeed: getLiveActivityFeed,
    getFolderHeat: getFolderHeat,
    get LIST_CAP() { return MAP_WO_LIST_CAP; },
  };

  function init(host) {
    if (!host || typeof host !== "object") return WoTape;
    Object.keys(_host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    if (typeof host.repaintInsights === "function") {
      _host.repaintInsights = host.repaintInsights;
    }
    return WoTape;
  }

  global.WoTape = WoTape;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = WoTape;
  }
})(typeof window !== "undefined" ? window : globalThis);

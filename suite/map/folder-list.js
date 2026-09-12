/*! folder-list.js — Outline folder-list store + render (pc-1260 Phase 3-C)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4 Phase 3).
 * Module-scope outline expand/sort/sig lives here only — host calls the public API.
 *
 * Browser: window.FolderList
 * Public: { init, paint } plus bridge accessors used by Map host
 * during the strangler (expand membership, outline render, reveal).
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    getModel: null,
    getMapDigIn: null,
    setMapDigIn: null,
    getMapProjection: null,
    getMapExpandLevel: null,
    getSvg: null,
    getLastCity: null,
    getLastPeople: null,
    getLastAtt: null,
    getLastTpScene: null,
    getPreDigCam: null,
    setPreDigCam: null,
    getDigEnterFitPending: null,
    setDigEnterFitPending: null,
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  /* Live mirrors of host vars — sync on every public/host-shim entry. */
  var model = null;
  var mapDigIn = null;
  var mapProjection = "map";
  var mapExpandLevel = 0;
  var svg = null;
  var _lastCityData = null;
  var _lastPeople = null;
  var _lastAtt = null;
  var _lastTpScene = null;
  var _preDigCam = null;
  var _digEnterFitPending = false;

  function syncFromHost() {
    var g;
    g = H("getModel");
    model = g ? g() : model;
    g = H("getMapDigIn");
    mapDigIn = g ? g() : mapDigIn;
    g = H("getMapProjection");
    mapProjection = g ? g() : mapProjection;
    g = H("getMapExpandLevel");
    mapExpandLevel = g ? g() : mapExpandLevel;
    g = H("getSvg");
    svg = g ? g() : svg;
    g = H("getLastCity");
    _lastCityData = g ? g() : _lastCityData;
    g = H("getLastPeople");
    _lastPeople = g ? g() : _lastPeople;
    g = H("getLastAtt");
    _lastAtt = g ? g() : _lastAtt;
    g = H("getLastTpScene");
    _lastTpScene = g ? g() : _lastTpScene;
    g = H("getPreDigCam");
    _preDigCam = g ? g() : _preDigCam;
    g = H("getDigEnterFitPending");
    _digEnterFitPending = g ? !!g() : _digEnterFitPending;
  }

  function syncToHost() {
    var s;
    s = H("setMapDigIn");
    if (s) s(mapDigIn);
    s = H("setPreDigCam");
    if (s) s(_preDigCam);
    s = H("setDigEnterFitPending");
    if (s) s(_digEnterFitPending);
  }

  function flashHudNote() {
    syncToHost();
    var fn = H('flashHudNote');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function paintMapExpandFab() {
    syncToHost();
    var fn = H('paintMapExpandFab');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function paintMapResetFab() {
    syncToHost();
    var fn = H('paintMapResetFab');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function paintStatic() {
    syncToHost();
    var fn = H('paintStatic');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function placeActors() {
    syncToHost();
    var fn = H('placeActors');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function clearExpandOverlay() {
    syncToHost();
    var fn = H('clearExpandOverlay');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function fitCameraToBounds() {
    syncToHost();
    var fn = H('fitCameraToBounds');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function fitWorkspaceCamera() {
    syncToHost();
    var fn = H('fitWorkspaceCamera');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function markCameraUserOwned() {
    syncToHost();
    var fn = H('markCameraUserOwned');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function mountMapViewFilters() {
    syncToHost();
    var fn = H('mountMapViewFilters');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function mountMapDigTrailChrome() {
    syncToHost();
    var fn = H('mountMapDigTrailChrome');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function showWorkspaceDetail() {
    syncToHost();
    var fn = H('showWorkspaceDetail');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function showProjectDetail() {
    syncToHost();
    var fn = H('showProjectDetail');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function exitMapDigIn() {
    syncToHost();
    var fn = H('exitMapDigIn');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function openBoardInstructionsOverview() {
    syncToHost();
    var fn = H('openBoardInstructionsOverview');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function scrollInspectSection() {
    syncToHost();
    var fn = H('scrollInspectSection');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function openProjectSeatPanel() {
    syncToHost();
    var fn = H('openProjectSeatPanel');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function openProjectWorkOrders() {
    syncToHost();
    var fn = H('openProjectWorkOrders');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function openPaperInSuite() {
    syncToHost();
    var fn = H('openPaperInSuite');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function goHref() {
    syncToHost();
    var fn = H('goHref');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function syncDigInWoToLeftRail() {
    syncToHost();
    var fn = H('syncDigInWoToLeftRail');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function goldFor() {
    syncToHost();
    var fn = H('goldFor');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function openCount() {
    syncToHost();
    var fn = H('openCount');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function placeState() {
    syncToHost();
    var fn = H('placeState');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function youPendingCount() {
    syncToHost();
    var fn = H('youPendingCount');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function workspacePlaceRollup() {
    syncToHost();
    var fn = H('workspacePlaceRollup');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function isNonStoreZone() {
    syncToHost();
    var fn = H('isNonStoreZone');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function actorIsJob() {
    syncToHost();
    var fn = H('actorIsJob');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function jobIsOnClock() {
    syncToHost();
    var fn = H('jobIsOnClock');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function projectHandsHired() {
    syncToHost();
    var fn = H('projectHandsHired');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function folderCityRel() {
    syncToHost();
    var fn = H('folderCityRel');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function folderPaperLevelScan() {
    syncToHost();
    var fn = H('folderPaperLevelScan');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function classifyPaperRole() {
    syncToHost();
    var fn = H('classifyPaperRole');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function isPcLawMd() {
    syncToHost();
    var fn = H('isPcLawMd');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function isProjectRootLayerLaw() {
    syncToHost();
    var fn = H('isProjectRootLayerLaw');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function joinRel() {
    syncToHost();
    var fn = H('joinRel');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function cityRelFromAbs() {
    syncToHost();
    var fn = H('cityRelFromAbs');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function snapshotCamera() {
    syncToHost();
    var fn = H('snapshotCamera');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function setDigNestedStageFlag() {
    syncToHost();
    var fn = H('setDigNestedStageFlag');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function getWorkGlyph() {
    syncToHost();
    var fn = H('getWorkGlyph');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function getHandGlyph() {
    syncToHost();
    var fn = H('getHandGlyph');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function getJobGlyph() {
    syncToHost();
    var fn = H('getJobGlyph');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function getInstrGlyph() {
    syncToHost();
    var fn = H('getInstrGlyph');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function paintFolderOnMap() {
    syncToHost();
    var fn = H('paintFolderOnMap');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function mapShowManaged() {
    syncToHost();
    var fn = H('mapShowManaged');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function mapShowUnmanaged() {
    syncToHost();
    var fn = H('mapShowUnmanaged');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function mapShowHidden() {
    syncToHost();
    var fn = H('mapShowHidden');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function isExpandOpsDirName() {
    syncToHost();
    var fn = H('isExpandOpsDirName');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function syncMapViewExpand() {
    syncToHost();
    var fn = H('syncMapViewExpand');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function syncMapViewDigFromLocal() {
    syncToHost();
    var fn = H('syncMapViewDigFromLocal');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function normalizeWoFilter() {
    syncToHost();
    var fn = H('normalizeWoFilter');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function isWorkspaceOpsWorker() {
    syncToHost();
    var fn = H('isWorkspaceOpsWorker');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function groupMdsOneLevel() {
    syncToHost();
    var fn = H('groupMdsOneLevel');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function repaintWoInsights() {
    syncToHost();
    var fn = H('repaintWoInsights');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function paintMapInsights() {
    syncToHost();
    var fn = H('paintMapInsights');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function clearMapEntitySelection() {
    syncToHost();
    var fn = H('clearMapEntitySelection');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function mapContentBounds() {
    syncToHost();
    var fn = H('mapContentBounds');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }
  function calibrateMapTypeRamp() {
    syncToHost();
    var fn = H('calibrateMapTypeRamp');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  const _outlineExpandState = {}; /* key "slug:relPath" → { entries } | { loading:true, token } */
  /*
   * Generation + per-request token: Collapse all / chevron-close must win over
   * in-flight /api/ground fetches (otherwise folders re-open after "Collapse all").
   */
  let _outlineExpandGen = 0;
  /* Workspace hub (Map center folder) always shown; projects nest under it */
  let _outlineHubExpanded = true;
  /* urgency (default) · alpha · custom — citizen sort for project list under hub */
  let _outlineSortMode = (function () {
    try {
      var v = localStorage.getItem("suite.outlineSort");
      return v === "alpha" ? "alpha" : v === "custom" ? "custom" : "urgency";
    } catch (e) {
      return "urgency";
    }
  })();
  let _outlineSig = "";
  /* pc-1119: drag-to-reorder state (custom sort mode only) */
  let _olDragSrc = null;
  let _olDragTarget = null;

  /**
   * pc-844: clear Outline ops-layer expand rows without recursion into
   * setMapExpandLevel (Collapse all must not re-enter Map expand).
   */
  function outlineClearExpandMembership() {
    _outlineExpandGen = (_outlineExpandGen | 0) + 1;
    Object.keys(_outlineExpandState).forEach(function (k) {
      delete _outlineExpandState[k];
    });
    _outlineHubExpanded = true;
    _outlineSig = "";
  }

  function splitEntriesOpsLayer(entries) {
    const dirs = (entries || []).filter(function (e) {
      return e && e.dir && !e.hidden;
    });
    const ops = [];
    const rest = [];
    dirs.forEach(function (e) {
      const nm = (e && (e.name || e.basename)) || "";
      if (isExpandOpsDirName(nm)) ops.push(e);
      else rest.push(e);
    });
    return { ops: ops, rest: rest, all: dirs };
  }

  /**
   * Outline: Expand folders = open every project row to **ops layers**
   * (same set as Map expand). Collapse = close all outline expand state.
   */
  /** True when any Outline row is expanded (chevrons or Expand FAB). */
  function outlineTreeHasOpen() {
    try {
      const keys = Object.keys(_outlineExpandState || {});
      for (let i = 0; i < keys.length; i++) {
        const st = _outlineExpandState[keys[i]];
        if (!st) continue;
        if (st.loading) return true;
        if (st.entries) return true;
      }
    } catch (e) {}
    return false;
  }

  function outlineCollapseAll() {
    /* Invalidate every in-flight ground fetch first */
    outlineClearExpandMembership();
    /* Keep hub open so projects remain visible as the top layer */
    _outlineHubExpanded = true;
    /* pc-844: collapse is shared — clear Map expand level too */
    syncMapViewExpand(0);
    try {
      const root = svg && (svg.querySelector("#root") || svg);
      const links = svg && svg.querySelector("#hierarchy-links");
      if (root) clearExpandOverlay(root, links);
      if (model) model._expandBounds = null;
      if (svg) svg.classList.remove("map-expand-on");
    } catch (eMapCol) {}
    try {
      renderMapOutline();
    } catch (e) {}
    try {
      paintMapExpandFab();
    } catch (eFab) {}
    try {
      flashHudNote("Outline · collapsed all folders");
    } catch (eN) {}
  }

  function outlineExpandAllTopProjects() {
    var plots = typeof outlinePlotsFromModel === "function"
      ? outlinePlotsFromModel()
      : (model && model.plots) || [];
    if (!plots.length) {
      try {
        flashHudNote("Outline · no projects to expand");
      } catch (eN) {}
      return;
    }
    var started = 0;
    var expandGen = _outlineExpandGen | 0;
    plots.forEach(function (p) {
      var slug = String(p.slug || p.name || "").toLowerCase();
      if (!slug) return;
      var key = _outlineKey(slug, "");
      var st = _outlineExpandState[key];
      /* Refresh open rows so opsOnly flag stays in sync with Map expand */
      if (st && st.entries && st.opsOnly) return;
      if (st && st.loading) return;
      started++;
      /* Force-open — ops layer only (parity with Map expand) */
      var token = {};
      _outlineExpandState[key] = {
        loading: true,
        opsOnly: true,
        token: token,
      };
      var scope;
      try {
        scope =
          typeof folderCityRel === "function"
            ? folderCityRel(p, null)
            : String(p.name || p.slug || "");
      } catch (eSc) {
        scope = String(p.name || p.slug || "");
      }
      (function (capturedKey, capturedScope, capturedToken, capturedGen) {
        fetch("/api/ground?scope=" + encodeURIComponent(capturedScope || ""), {
          cache: "no-store",
        })
          .then(function (r) {
            return r.ok ? r.json() : { entries: [] };
          })
          .then(function (data) {
            if (capturedGen !== (_outlineExpandGen | 0)) return;
            var cur = _outlineExpandState[capturedKey];
            if (!cur || cur.token !== capturedToken) return;
            var raw = data.entries || data.listing || [];
            var split = splitEntriesOpsLayer(raw);
            _outlineExpandState[capturedKey] = {
              entries: split.ops,
              more: split.rest.length,
              opsOnly: true,
              fullEntries: raw,
              token: capturedToken,
            };
            _outlineSig = "";
            if (mapProjection === "outline") renderMapOutline();
          })
          .catch(function () {
            if (capturedGen !== (_outlineExpandGen | 0)) return;
            var cur = _outlineExpandState[capturedKey];
            if (!cur || cur.token !== capturedToken) return;
            _outlineExpandState[capturedKey] = {
              entries: [],
              more: 0,
              opsOnly: true,
              token: capturedToken,
            };
            _outlineSig = "";
            if (mapProjection === "outline") renderMapOutline();
          });
      })(key, scope, token, expandGen);
    });
    _outlineSig = "";
    try {
      renderMapOutline();
    } catch (eR) {}
    try {
      flashHudNote(
        started
          ? "Outline · ops layers on " + started + " projects…"
          : "Outline · folders already open"
      );
    } catch (eH) {}
    try {
      paintMapExpandFab();
    } catch (eFabEx) {}
  }

  function _outlineKey(slug, relPath) {
    return String(slug || "") + ":" + String(relPath || "");
  }

  /**
   * Same plot universe as the Map ring (pc-758). Never read city.city —
   * census shape is neighborhoods/folders. Prefer full city + View-option
   * filter (pc-896) so Outline stays in lockstep when filters flip —
   * model.plots alone can lag after a soft poll dropped kinds.
   */
  function outlinePlotsFromModel() {
    var city = (model && model.city) || _lastCityData;
    if (city) {
      var raw = city.folders || city.neighborhoods || city.plots || [];
      if (raw && raw.length) {
        return raw.filter(function (p) {
          try {
            return typeof paintFolderOnMap === "function"
              ? paintFolderOnMap(p)
              : true;
          } catch (e) {
            return true;
          }
        });
      }
    }
    if (model && model.plots && model.plots.length) {
      return model.plots.filter(function (p) {
        try {
          return typeof paintFolderOnMap === "function"
            ? paintFolderOnMap(p)
            : true;
        } catch (e2) {
          return true;
        }
      });
    }
    return [];
  }

  function _buildOutlineSig() {
    if (!model || !model.city) return "nomodel";
    var plots = outlinePlotsFromModel();
    var openSum = 0, goldSum = 0;
    var slugBits = [];
    for (var i = 0; i < plots.length; i++) {
      try {
        var _ps = placeState(plots[i]);
        openSum += _ps.wo.liveOpen | 0;
        goldSum += _ps.wo.forYou | 0;
      } catch (e) {
        openSum += openCount(plots[i]);
        goldSum += goldFor(plots[i].slug, plots[i].name);
      }
      slugBits.push(
        String((plots[i] && (plots[i].slug || plots[i].name)) || "")
          .toLowerCase()
          .trim()
      );
    }
    var digSig = mapDigIn
      ? String((mapDigIn.plot && (mapDigIn.plot.slug || mapDigIn.plot.name)) || "") + ":" + (mapDigIn.trail || []).length
      : "";
    var hubBit = _outlineHubExpanded ? "h1" : "h0";
    var sortBit = _outlineSortMode === "alpha" ? "a" :
      _outlineSortMode === "custom" ? "c:" + (window.MapViewState ? MapViewState.customOrderSig() : "") : "u";
    /* pc-896: membership identity, not only length/open totals */
    var filtBit =
      (typeof mapShowManaged === "function" && mapShowManaged() ? "m1" : "m0") +
      (typeof mapShowUnmanaged === "function" && mapShowUnmanaged()
        ? "u1"
        : "u0") +
      (typeof mapShowHidden === "function" && mapShowHidden() ? "h1" : "h0");
    return (
      plots.length +
      ":" +
      openSum +
      ":" +
      goldSum +
      ":" +
      digSig +
      ":" +
      hubBit +
      ":" +
      sortBit +
      ":" +
      filtBit +
      ":" +
      slugBits.sort().join(",") +
      ":" +
      Object.keys(_outlineExpandState).sort().join(",")
    );
  }

  function renderMapOutlineIfOn() {
    syncFromHost();
    if (mapProjection !== "outline") return;
    var sig = _buildOutlineSig();
    if (sig === _outlineSig) return;
    _outlineSig = sig;
    renderMapOutline();
  }

  /** City-root basename — same source as mast “[FOLDER] workspace”. */
  function outlineWorkspaceHubName() {
    try {
      var city = model && model.city;
      var root = String((city && (city.city_root || city.root)) || "");
      var leaf = root.split(/[/\\]/).filter(Boolean).pop();
      if (leaf) return leaf;
    } catch (e) {}
    return "Workspace";
  }


  /** Ops / jobs staff on the workspace hub (Map center ring). */
  function outlineWorkspaceStaffCounts() {
    var hands = 0;
    var jobs = 0;
    var pool = (model && model.workers) || [];
    for (var i = 0; i < pool.length; i++) {
      var w = pool[i];
      if (!w || w.kind === "citizen") continue;
      var staff =
        !!w.workspaceOps ||
        w.homeKey === "__staff__" ||
        String(w.homeKey || "").indexOf("__") === 0;
      if (!staff) continue;
      if (typeof actorIsJob === "function" ? actorIsJob(w) : w.kind === "job") {
        /* pc-1023: off-clock jobs (no next_fire, not working) ≠ hub coverage */
        if (typeof jobIsOnClock === "function" ? !jobIsOnClock(w) : !String(w.next_fire || "").trim() && !w.working) {
          continue;
        }
        jobs++;
      } else {
        hands++;
      }
    }
    return { hands: hands, jobs: jobs };
  }

  /* Light city ships empty root_mds (truthy []) + shallow root_entries.
   * `root_mds || root_files` would never fall through. */
  function outlineWorkspaceRootPapers() {
    var city = model && model.city;
    if (!city) return [];
    var lists = [city.root_mds, city.root_files, city.root_entries];
    var out = [];
    var seen = {};
    for (var i = 0; i < lists.length; i++) {
      var arr = lists[i];
      if (!arr || !arr.length) continue;
      for (var j = 0; j < arr.length; j++) {
        var f = arr[j];
        if (!f) continue;
        var nm = String(f.name || f || "")
          .toLowerCase()
          .trim();
        if (!nm || seen[nm]) continue;
        seen[nm] = true;
        out.push(f);
      }
    }
    return out;
  }

  function outlineWorkspaceHasL0Instructions() {
    try {
      var city = model && model.city;
      var root = String((city && city.city_root) || "");
      var mds = outlineWorkspaceRootPapers();
      if (!Array.isArray(mds)) return false;
      return mds.some(function (f) {
        if (!f) return false;
        var nm = String(f.name || f || "").toLowerCase();
        if (
          typeof isProjectRootLayerLaw === "function" &&
          isProjectRootLayerLaw(f, root)
        )
          return true;
        return (
          (typeof isPcLawMd === "function" && isPcLawMd(nm)) ||
          nm === "agents.md" ||
          nm === "claude.md" ||
          nm === "boundaries.md" ||
          nm === "perimeter.md" ||
          nm === "grok.md"
        );
      });
    } catch (e) {
      return false;
    }
  }

  /** Dig workspace hub from Outline (Map center folder). */
  function _outlineEnterWorkspace() {
    try {
      if (mapDigIn && typeof exitMapDigIn === "function") exitMapDigIn();
    } catch (eEx) {}
    try {
      WoTape.setProjectKey("");
    } catch (eK) {}
    try {
      showWorkspaceDetail();
    } catch (eWs) {}
    try {
      flashHudNote(outlineWorkspaceHubName() + " · workspace overview");
    } catch (eN) {}
    _outlineSig = "";
    try {
      renderMapOutline();
    } catch (eR) {}
  }

  function _outlineHubChipAction(door) {
    var d = String(door || "").toLowerCase();
    if (d === "open" || d === "live") {
      try {
        WoTape.setProjectKey("");
        WoTape.setFilter(normalizeWoFilter("live"));
        if (global.WoTape) WoTape.bustTape();
        if (global.WoTape) WoTape.bustChips();
        if (typeof repaintWoInsights === "function") repaintWoInsights();
        else if (typeof paintMapInsights === "function" && model) {
          paintMapInsights(
            model.city || _lastCityData,
            _lastPeople,
            _lastAtt,
            _lastTpScene
          );
        }
        flashHudNote("Workspace · live open");
      } catch (eO) {}
      return;
    }
    if (d === "for_you" || d === "gold") {
      try {
        WoTape.setProjectKey("");
        WoTape.setFilter(normalizeWoFilter("for_you"));
        if (global.WoTape) WoTape.bustTape();
        if (typeof repaintWoInsights === "function") repaintWoInsights();
        flashHudNote("Workspace · For You");
      } catch (eY) {}
      return;
    }
    if (d === "stuck" || d === "stalled") {
      try {
        WoTape.setProjectKey("");
        WoTape.setFilter(normalizeWoFilter("stalled"));
        if (global.WoTape) WoTape.bustTape();
        if (typeof repaintWoInsights === "function") repaintWoInsights();
        flashHudNote("Workspace · stuck");
      } catch (eSt) {}
      return;
    }
    if (d === "hands" || d === "jobs") {
      _outlineEnterWorkspace();
      setTimeout(function () {
        try {
          scrollInspectSection("working on now") ||
            scrollInspectSection("agents");
        } catch (eSc) {}
      }, 120);
      return;
    }
    if (d === "instr" || d === "instructions" || d === "law") {
      /* pc-924: board-wide Instructions overview (primary discovery) */
      try {
        openBoardInstructionsOverview({ from: "outline-hub" });
      } catch (eBoard) {
        _outlineEnterWorkspace();
        setTimeout(function () {
          try {
            scrollInspectSection("instructions · workspace") ||
              scrollInspectSection("instructions");
          } catch (eSc2) {}
        }, 120);
      }
      return;
    }
    _outlineEnterWorkspace();
  }

  function _buildOutlineHubChips() {
    var wrap = document.createElement("span");
    wrap.className = "ol-chips";
    var plots = outlinePlotsFromModel().filter(function (p) {
      return p && !isNonStoreZone(p);
    });
    var roll = { open: 0, forYou: 0, flowing: 0, starved: 0, stuck: 0 };
    try {
      roll = workspacePlaceRollup(plots);
    } catch (eR) {
      plots.forEach(function (p) {
        try {
          roll.open += openCount(p) | 0;
        } catch (e) {}
      });
      try {
        roll.forYou = youPendingCount() | 0;
      } catch (eY) {}
    }
    var staff = outlineWorkspaceStaffCounts();
    var open = roll.open | 0;
    var gold = roll.forYou | 0;
    /* Work ladder lockstep MAP_LEGEND_SPEC (pc-864) */
    if (gold > 0) {
      var cg = _mkOutlineChipDoor(
        "is-gold",
        gold + " For You citywide · click → filter",
        gold + " For You work orders",
        function () {
          _outlineHubChipAction("for_you");
        }
      );
      _olFillChip(cg, "⭐", "ol-chip-work-face", gold);
      wrap.appendChild(cg);
    }
    if ((roll.stuck | 0) > 0 && gold <= 0) {
      var csk = _mkOutlineChipDoor(
        "is-stuck",
        (roll.stuck | 0) + " stuck projects · click → filter",
        (roll.stuck | 0) + " stuck",
        function () {
          _outlineHubChipAction("stuck");
        }
      );
      _olFillChip(csk, "❗", "ol-chip-work-face", roll.stuck | 0);
      wrap.appendChild(csk);
    }
    if ((roll.flowing | 0) > 0) {
      var cf = _mkOutlineChipDoor(
        "is-flowing",
        (roll.flowing | 0) + " projects in progress · Map ▶️",
        (roll.flowing | 0) + " in progress",
        function () {
          _outlineHubChipAction("open");
        }
      );
      _olFillChip(cf, "▶️", "ol-chip-work-face", roll.flowing | 0);
      wrap.appendChild(cf);
    }
    if (open > 0) {
      var c = _mkOutlineChipDoor(
        "is-open is-work",
        open +
          " live open work orders across projects · Map 🎫 seat · click → filter",
        open + " live open work orders workspace-wide",
        function () {
          _outlineHubChipAction("open");
        }
      );
      _olFillChip(
        c,
        typeof getWorkGlyph === "function" ? getWorkGlyph() : "🎫",
        "ol-chip-work-face",
        open
      );
      wrap.appendChild(c);
    }
    if ((roll.starved | 0) > 0) {
      var ce = _mkOutlineChipDoor(
        "is-starved",
        (roll.starved | 0) +
          " empty queue (scheduled hand, nothing ready) · Map ○",
        (roll.starved | 0) + " empty queue",
        function () {
          _outlineHubChipAction("open");
        }
      );
      _olFillChip(ce, "○", "ol-chip-work-face", roll.starved | 0);
      wrap.appendChild(ce);
    }
    if (staff.hands > 0) {
      var ca = _mkOutlineChipDoor(
        "is-hands",
        staff.hands +
          " workspace hand" +
          (staff.hands !== 1 ? "s" : "") +
          " (ops / jobs ring) · click → overview",
        staff.hands + " workspace hands",
        function () {
          _outlineHubChipAction("hands");
        }
      );
      _olFillChip(
        ca,
        typeof getHandGlyph === "function" ? getHandGlyph() : "✋",
        "ol-chip-face",
        staff.hands
      );
      wrap.appendChild(ca);
    }
    if (staff.jobs > 0) {
      var cj = _mkOutlineChipDoor(
        "is-jobs",
        staff.jobs +
          " workspace job" +
          (staff.jobs !== 1 ? "s" : "") +
          " (chief-of-staff · health-patrol · …) · click → overview",
        staff.jobs + " workspace jobs",
        function () {
          _outlineHubChipAction("jobs");
        }
      );
      _olFillChip(
        cj,
        typeof getJobGlyph === "function" ? getJobGlyph() : "⏰",
        "ol-chip-job-mark",
        staff.jobs
      );
      wrap.appendChild(cj);
    }
    if (outlineWorkspaceHasL0Instructions()) {
      var ci = _mkOutlineChipDoor(
        "is-instr",
        "Workspace instructions — AGENTS.md and Boundaries at workspace root. Click opens overview.",
        "Workspace instructions",
        function () {
          _outlineHubChipAction("instr");
        }
      );
      _olFillChip(
        ci,
        typeof getInstrGlyph === "function" ? getInstrGlyph() : "📜",
        "ol-chip-instr-face",
        null
      );
      wrap.appendChild(ci);
    }
    return wrap.children.length ? wrap : null;
  }

  function renderMapOutline() {
    syncFromHost();
    var host = document.getElementById("map-outline");
    if (!host || host.hidden) return;
    if (!model || !model.city) {
      host.innerHTML = '<div class="ol-loading">Loading workspace…</div>';
      return;
    }
    var city = model.city;
    var plots = outlinePlotsFromModel();
    var frag = document.createDocumentFragment();
    /*
     * Workspace hub first (Map center folder) — ops hands · clerk
     * jobs · Instructions. Projects nest under it (depth 1+).
     */
    var hubName = outlineWorkspaceHubName();
    var hubOpen = _outlineHubExpanded !== false;
    var hubFocused = !mapDigIn;
    var hubRow = document.createElement("div");
    hubRow.className =
      "ol-row ol-depth-0 is-hub" + (hubFocused ? " is-focused" : "");
    hubRow.setAttribute("tabindex", "0");
    hubRow.setAttribute("role", "row");
    hubRow.dataset.slug = "__workspace__";
    hubRow.title =
      hubName +
      " · workspace hub · workspace ops · Instructions · click for overview";

    var hubExp = document.createElement("button");
    hubExp.type = "button";
    hubExp.className = "ol-expand" + (hubOpen ? " is-open" : "");
    hubExp.setAttribute("aria-expanded", hubOpen ? "true" : "false");
    hubExp.setAttribute(
      "aria-label",
      hubOpen ? "Collapse projects" : "Expand projects"
    );
    hubExp.textContent = hubOpen ? "▾" : "▸";
    hubExp.addEventListener("click", function (ev) {
      ev.stopPropagation();
      _outlineHubExpanded = !_outlineHubExpanded;
      _outlineSig = "";
      renderMapOutline();
    });
    hubRow.appendChild(hubExp);

    var hubMark = document.createElement("span");
    hubMark.className = "ol-hub-mark";
    hubMark.textContent = "workspace";
    hubMark.setAttribute("aria-hidden", "true");
    hubRow.appendChild(hubMark);

    var hubNameEl = document.createElement("span");
    hubNameEl.className = "ol-name";
    hubNameEl.textContent = hubName;
    hubRow.appendChild(hubNameEl);

    /* pc-858: sort is chrome control — before inventory chips, not in the strip */
    var sortBtn = document.createElement("button");
    sortBtn.type = "button";
    sortBtn.className = "ol-hub-sort";
    sortBtn.textContent =
      _outlineSortMode === "alpha" ? "Sort · A–Z" :
      _outlineSortMode === "custom" ? "Sort · custom" : "Sort · work";
    sortBtn.title =
      _outlineSortMode === "alpha"
        ? "Projects sorted A–Z · click for custom ring order"
        : _outlineSortMode === "custom"
        ? "Projects in saved ring order · drag rows to reorder · click for by-work"
        : "Projects sorted by For You then live open · click for A–Z";
    sortBtn.setAttribute(
      "aria-label",
      "Sort projects: " +
        (_outlineSortMode === "alpha" ? "alphabetical" :
         _outlineSortMode === "custom" ? "custom ring order" : "by work urgency")
    );
    sortBtn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      _outlineSortMode = _outlineSortMode === "urgency" ? "alpha" :
                         _outlineSortMode === "alpha" ? "custom" : "urgency";
      try {
        localStorage.setItem("suite.outlineSort", _outlineSortMode);
      } catch (eLs) {}
      _outlineSig = "";
      renderMapOutline();
      try {
        flashHudNote(
          "Outline · sort " +
            (_outlineSortMode === "alpha" ? "A–Z" :
             _outlineSortMode === "custom" ? "custom" : "work")
        );
      } catch (eN) {}
    });
    hubRow.appendChild(sortBtn);

    var hubChips = _buildOutlineHubChips();
    if (hubChips) hubRow.appendChild(hubChips);

    hubRow.addEventListener("click", function (ev) {
      if (ev.target === hubExp || (hubExp && hubExp.contains(ev.target))) return;
      if (ev.target === sortBtn || (sortBtn && sortBtn.contains(ev.target))) return;
      if (ev.target.closest && ev.target.closest("button.ol-chip")) return;
      if (ev.metaKey || ev.ctrlKey) {
        var root = String((city && city.city_root) || "");
        if (root) {
          try {
            window.open("file://" + root);
          } catch (eO) {}
        }
        return;
      }
      _outlineEnterWorkspace();
    });
    hubRow.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        _outlineEnterWorkspace();
      }
      if (ev.key === "ArrowRight") {
        ev.preventDefault();
        if (!_outlineHubExpanded) {
          _outlineHubExpanded = true;
          _outlineSig = "";
          renderMapOutline();
        }
      }
      if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        if (_outlineHubExpanded) {
          _outlineHubExpanded = false;
          _outlineSig = "";
          renderMapOutline();
        }
      }
    });
    frag.appendChild(hubRow);

    /* L0 workspace root .md under hub (AGENTS.md, etc.) when expanded */
    if (hubOpen) {
      try {
        var cityRoot = String((city && city.city_root) || "");
        var wsMds = [];
        var seenWs = {};
        outlineWorkspaceRootPapers().forEach(function (f) {
          if (!f) return;
          var nm = String(f.name || "").trim();
          if (!nm || !/\.md$/i.test(nm)) return;
          var rel = String(f.rel || f.path || nm)
            .replace(/\\/g, "/")
            .replace(/^\/+/, "");
          /* root layer only — no nested path under city root listing */
          if (rel.indexOf("/") >= 0 && rel.split("/").length > 1) {
            var leaf = rel.split("/").pop();
            if (leaf !== nm) return;
          }
          var key = nm.toLowerCase();
          if (seenWs[key]) return;
          seenWs[key] = true;
          var isInstr =
            (typeof isPcLawMd === "function" && isPcLawMd(nm)) ||
            !!(f.rule || f.pointer) ||
            (typeof isProjectRootLayerLaw === "function" &&
              isProjectRootLayerLaw(f, cityRoot));
          wsMds.push({ name: nm, rel: nm, f: f, isInstr: isInstr });
        });
        wsMds.sort(function (a, b) {
          if (a.isInstr !== b.isInstr) return a.isInstr ? -1 : 1;
          return String(a.name).localeCompare(String(b.name));
        });
        if (wsMds.length) {
          var fakePlot = {
            path: cityRoot,
            name: hubName,
            slug: "__workspace__",
          };
          _renderOutlineMdRows(frag, fakePlot, wsMds, 1, "");
        }
      } catch (eWsMd) {}
    }

    if (!plots.length) {
      if (hubOpen) {
        var empty = document.createElement("div");
        empty.className = "ol-empty ol-depth-1";
        empty.textContent = "No managed projects found.";
        frag.appendChild(empty);
      }
      host.innerHTML = "";
      host.appendChild(frag);
      return;
    }

    if (!hubOpen) {
      host.innerHTML = "";
      host.appendChild(frag);
      return;
    }

    /* Sort: urgency (default) · A–Z · custom ring order — suite.outlineSort */
    var _olPs = new Map();
    plots.forEach(function (p) { try { _olPs.set(p, placeState(p)); } catch (e) {} });
    if (_outlineSortMode === "alpha") {
      plots.sort(function (a, b) {
        return String(a.name || a.slug || "").localeCompare(
          String(b.name || b.slug || ""),
          undefined,
          { sensitivity: "base" }
        );
      });
    } else if (_outlineSortMode === "custom") {
      /* pc-1119: saved custom order — ring and outline stay glued via MapViewState */
      var _olCo = window.MapViewState ? MapViewState.getCustomOrder() : [];
      plots.sort(function (a, b) {
        var ia = _olCo.indexOf(String(a.slug || a.name || "").toLowerCase());
        var ib = _olCo.indexOf(String(b.slug || b.name || "").toLowerCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        if (ia >= 0) return -1;
        if (ib >= 0) return 1;
        return String(a.name || a.slug || "").localeCompare(
          String(b.name || b.slug || ""),
          undefined,
          { sensitivity: "base" }
        );
      });
    } else {
      /* needs-you first, then live-open desc — placeState (Q6) */
      plots.sort(function (a, b) {
        var psa = _olPs.get(a), psb = _olPs.get(b);
        var ga = (psa ? psa.wo.forYou : goldFor(a.slug, a.name)) > 0 ? 1 : 0;
        var gb = (psb ? psb.wo.forYou : goldFor(b.slug, b.name)) > 0 ? 1 : 0;
        if (gb !== ga) return gb - ga;
        var oa = psa ? psa.wo.liveOpen : openCount(a);
        var ob = psb ? psb.wo.liveOpen : openCount(b);
        if (ob !== oa) return ob - oa;
        return String(a.name || a.slug || "").localeCompare(
          String(b.name || b.slug || ""),
          undefined,
          { sensitivity: "base" }
        );
      });
    }

    var digSlug = mapDigIn && mapDigIn.plot
      ? String(mapDigIn.plot.slug || mapDigIn.plot.name || "").toLowerCase()
      : "";
    var digTrail = mapDigIn ? (mapDigIn.trail || []) : [];
    /* Dig leaf only — Map is-you-here is one host; Outline must not gold the whole path */
    var digRel = mapDigIn ? String(mapDigIn.relPath || "") : "";

    plots.forEach(function (p) {
      var slug = String(p.slug || p.name || "").toLowerCase();
      var onPath = !!(digSlug && slug === digSlug);
      /* You presence = dig leaf only (project root when digRel empty) */
      var isFocused = onPath && !digRel;
      var expKey = _outlineKey(slug, "");
      var expState = _outlineExpandState[expKey];
      var isOpen = !!(expState && expState.entries);

      var managed = !!p.managed;
      var foreign = String(p.zone || "").toLowerCase() === "foreign";
      var row = document.createElement("div");
      /* Projects nest under workspace hub (Map center → ring) */
      row.className =
        "ol-row ol-depth-1" +
        (isFocused ? " is-focused" : "") +
        (foreign
          ? managed
            ? " is-managed-foreign"
            : " is-foreign-consumer"
          : managed
            ? ""
            : " is-unmanaged");
      row.setAttribute("tabindex", "0");
      row.setAttribute("role", "row");
      row.dataset.slug = slug;
      if (foreign) {
        row.title = managed
          ? "Upstream-owned · desk-joined · origin stays foreign"
          : "Upstream-owned · consumer mode · automations without adopt · code work → upstream issues";
      } else if (!managed) {
        row.title =
          "Unmanaged · explore only · no BluePrint join marker / desk law";
      }

      var expBtn = document.createElement("button");
      expBtn.type = "button";
      expBtn.className = "ol-expand" + (isOpen ? " is-open" : "");
      expBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
      expBtn.setAttribute("aria-label", isOpen ? "Collapse" : "Expand folders");
      /* Text chevrons — large hit target styled in CSS (not tiny ▶ glyphs) */
      expBtn.textContent = isOpen ? "▾" : "▸";
      (function (capturedP, capturedSlug) {
        expBtn.addEventListener("click", function (ev) {
          ev.stopPropagation();
          _toggleOutlineExpand(capturedP, capturedSlug, "");
        });
      })(p, slug);
      row.appendChild(expBtn);

      /* Managed membership = View options + grey unmanaged — no green status dots */
      if (foreign) {
        var uDot = document.createElement("span");
        uDot.className = managed
          ? "ol-unmanaged-badge ol-upstream-badge is-desk-joined"
          : "ol-unmanaged-badge ol-upstream-badge";
        uDot.textContent = "upstream-owned";
        uDot.title = managed
          ? "Desk-joined foreign · coordination only · origin stays upstream"
          : "Consumer mode · automations on without adopt · code work → upstream issues";
        row.appendChild(uDot);
      } else if (!managed) {
        var uDot = document.createElement("span");
        uDot.className = "ol-unmanaged-badge";
        uDot.textContent = "unmanaged";
        uDot.title =
          "Not BluePrint-managed (no join marker) · explore only · adopt to manage";
        row.appendChild(uDot);
      }

      var nameEl = document.createElement("span");
      nameEl.className = "ol-name";
      nameEl.textContent = String(p.name || p.slug || "");
      row.appendChild(nameEl);

      var chips = managed ? _buildOutlineProjectChips(p, _olPs.get(p)) : null;
      if (chips) row.appendChild(chips);

      (function (capturedP, capturedSlug) {
        row.addEventListener("click", function (ev) {
          if (ev.target === expBtn || (expBtn && expBtn.contains(ev.target))) return;
          if (ev.target.closest && ev.target.closest("button.ol-chip")) return;
          if (ev.metaKey || ev.ctrlKey) {
            if (capturedP.path) {
              try { var url = "file://" + capturedP.path; window.open(url); } catch (e) {}
            }
            return;
          }
          _outlineEnterPlot(capturedP, row);
        });
        row.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); _outlineEnterPlot(capturedP, row); }
          if (ev.key === "ArrowRight") { ev.preventDefault(); if (!isOpen) _toggleOutlineExpand(capturedP, capturedSlug, ""); }
          if (ev.key === "ArrowLeft") { ev.preventDefault(); if (isOpen) _toggleOutlineExpand(capturedP, capturedSlug, ""); }
        });
      })(p, slug);

      /* pc-1119: drag-to-reorder in custom sort mode */
      if (_outlineSortMode === "custom") {
        row.draggable = true;
        var handle = document.createElement("span");
        handle.textContent = "⠿";
        handle.style.cssText = "cursor:grab;padding:0 4px 0 2px;opacity:0.35;font-size:var(--type-label);user-select:none;flex-shrink:0;";
        handle.setAttribute("aria-hidden", "true");
        row.insertBefore(handle, row.firstChild);
        (function (rowEl, rowSlug) {
          rowEl.addEventListener("dragstart", function (ev) {
            _olDragSrc = rowSlug;
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", rowSlug);
            setTimeout(function () { rowEl.style.opacity = "0.4"; }, 0);
          });
          rowEl.addEventListener("dragend", function () {
            rowEl.style.opacity = "";
            _olDragTarget = null;
            var h2 = document.getElementById("map-outline");
            if (h2) {
              var r2 = h2.querySelectorAll(".ol-row.ol-depth-1[data-slug]");
              for (var ri = 0; ri < r2.length; ri++) r2[ri].style.borderTop = "";
            }
          });
          rowEl.addEventListener("dragover", function (ev) {
            ev.preventDefault();
            ev.dataTransfer.dropEffect = "move";
            if (_olDragTarget !== rowEl) {
              var h2 = document.getElementById("map-outline");
              if (h2) {
                var r2 = h2.querySelectorAll(".ol-row.ol-depth-1[data-slug]");
                for (var ri = 0; ri < r2.length; ri++) r2[ri].style.borderTop = "";
              }
              _olDragTarget = rowEl;
              rowEl.style.borderTop = "2px solid var(--accent,#4a9eff)";
            }
          });
          rowEl.addEventListener("drop", function (ev) {
            ev.preventDefault();
            if (!_olDragSrc || _olDragSrc === rowSlug) return;
            var h2 = document.getElementById("map-outline");
            if (!h2) return;
            var r2 = h2.querySelectorAll(".ol-row.ol-depth-1[data-slug]");
            var order = [];
            for (var ri = 0; ri < r2.length; ri++) {
              var ds = r2[ri].getAttribute("data-slug");
              if (ds) order.push(ds);
            }
            var fromIdx = order.indexOf(_olDragSrc);
            var toIdx = order.indexOf(rowSlug);
            if (fromIdx >= 0 && toIdx >= 0) {
              order.splice(fromIdx, 1);
              order.splice(toIdx, 0, _olDragSrc);
            }
            _olDragSrc = null;
            _olDragTarget = null;
            if (window.MapViewState) MapViewState.setCustomOrder(order);
            _outlineSig = "";
            renderMapOutline();
          });
        })(row, slug);
      }

      frag.appendChild(row);

      /*
       * Closed project = only the project row (chips are the doors: md / Instr.).
       * Root .md used to always paint under a closed chevron — that looked like
       * "Collapse all failed" and stacked Instr. chips under the project line.
       * Papers list only when the row is open via _renderOutlineChildren
       * (md chip still opens the seat without expanding).
       */
      if (expState && expState.loading) {
        var loadRow = document.createElement("div");
        loadRow.className = "ol-loading ol-depth-2";
        loadRow.textContent = "Loading folders…";
        frag.appendChild(loadRow);
      } else if (isOpen && expState.entries) {
        /* FAB expand / Map expand → opsOnly; manual dig chevron may be full */
        var useOps =
          !!expState.opsOnly || (typeof mapExpandLevel === "number" && mapExpandLevel > 0);
        /* depth 2: under workspace hub (0) + project (1) · includes root .md */
        _renderOutlineChildren(frag, p, expState.entries, "", 2, digTrail, onPath, {
          opsOnly: useOps,
          more: expState.more,
          digRel: digRel,
          fullEntries: expState.fullEntries || expState.entries,
        });
      }
    });

    host.innerHTML = "";
    host.appendChild(frag);
  }

  /**
   * Outline chips = Map seat doors (same placeState counts).
   * Click opens the same full stack panel as Map seats — not inert decoration.
   * pc-876: work/for_you must call openProjectSeatPanel like hands/papers/jobs
   * (was only syncing left-rail filter → no right-rail pile).
   */
  function _outlineChipAction(p, door) {
    if (!p) return;
    var d = String(door || "").toLowerCase();
    if (d === "open" || d === "live" || d === "work" || d === "wo") {
      try {
        openProjectSeatPanel(p, "work");
      } catch (eO) {
        try {
          syncDigInWoToLeftRail(p, "open");
        } catch (eO2) {}
      }
      return;
    }
    if (d === "for_you" || d === "gold") {
      try {
        /* Full For You pile in inspect + left-rail for_you — same as Map gold lip */
        if (typeof openProjectWorkOrders === "function") {
          openProjectWorkOrders(p.slug || p.name || p.product, p, {
            filter: "for_you",
            title: (p.name || p.slug || "project") + " · For You",
            expectedGold: goldFor(p.slug, p.name),
            expectedOpen: openCount(p),
          });
        }
        syncDigInWoToLeftRail(p, "for_you");
      } catch (eY) {
        try {
          syncDigInWoToLeftRail(p, "for_you");
        } catch (eY2) {}
      }
      try {
        flashHudNote((p.name || p.slug || "project") + " · For You");
      } catch (eN2) {}
      return;
    }
    if (d === "stuck" || d === "stalled") {
      try {
        syncDigInWoToLeftRail(p, "stalled");
      } catch (eS) {}
      try {
        _outlineEnterPlot(p, null);
      } catch (eDig) {}
      setTimeout(function () {
        try {
          scrollInspectSection("stuck") || scrollInspectSection("work orders");
        } catch (eSc) {}
      }, 120);
      return;
    }
    if (d === "hands" || d === "agents") {
      openProjectSeatPanel(p, "hands");
      return;
    }
    if (d === "jobs" || d === "job") {
      openProjectSeatPanel(p, "jobs");
      return;
    }
    if (d === "instr" || d === "instructions" || d === "law") {
      openProjectSeatPanel(p, "instr");
      return;
    }
    if (d === "papers" || d === "md") {
      openProjectSeatPanel(p, "papers");
      return;
    }
    try {
      _outlineEnterPlot(p, null);
    } catch (eDef) {}
  }

  function _mkOutlineChipDoor(cls, title, ariaLabel, onClick) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "ol-chip " + (cls || "");
    b.title = title || "";
    if (ariaLabel) b.setAttribute("aria-label", ariaLabel);
    b.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      if (typeof onClick === "function") onClick(ev);
    });
    return b;
  }

  /**
   * pc-858: one chip body — face mark + optional count (Map seat / legend DNA).
   * faceKind: work-face (# Y !) | emoji class | null for text-only (Instr).
   */
  function _olFillChip(chip, faceText, faceClass, countText) {
    if (!chip) return chip;
    chip.textContent = "";
    if (faceText != null && faceText !== "") {
      var m = document.createElement("span");
      m.className = faceClass || "ol-chip-face";
      m.setAttribute("aria-hidden", "true");
      m.textContent = faceText;
      chip.appendChild(m);
    }
    if (countText != null && countText !== "") {
      var n = document.createElement("span");
      n.className = "ol-chip-n";
      n.textContent = String(countText);
      chip.appendChild(n);
    }
    return chip;
  }

  function _buildOutlineProjectChips(p, prePs) {
    var wrap = document.createElement("span");
    wrap.className = "ol-chips";
    var ps = prePs || null;
    if (!ps) {
      try { ps = placeState(p); } catch (ePs) {}
    }
    var open = ps ? ps.wo.liveOpen | 0 : openCount(p);
    var gold = ps ? ps.wo.forYou | 0 : goldFor(p.slug, p.name);
    var sigId = ps && ps.signal ? String(ps.signal.id || "") : "";
    var faceN = ps ? ps.face | 0 : 0;
    var stuckFace = sigId === "stuck" ? Math.max(faceN, 1) : 0;
    var flowingFace = sigId === "flowing" ? Math.max(faceN, 1) : 0;
    var isStarved = sigId === "starved";
    var agents = ps ? ps.hands | 0 : projectHandsHired(p);
    var jobs = 0;
    if (model && model.workers) {
      var keys = [p.slug, p.name, p.product].filter(Boolean).map(function (k) {
        return String(k).toLowerCase();
      });
      jobs = model.workers.filter(function (w) {
        return w && actorIsJob(w) && keys.indexOf(String(w.homeKey || "").toLowerCase()) >= 0;
      }).length;
    }
    /* Instruction presence (boolean) — not a second paper count */
    var instr = false;
    try {
      var mds = p.root_mds || [];
      if (Array.isArray(mds)) {
        instr = mds.some(function (f) {
          var nm = String((f && (f.name || f)) || "").toLowerCase();
          return (
            (typeof isPcLawMd === "function" && isPcLawMd(nm)) ||
            nm === "agents.md" ||
            nm === "claude.md" ||
            nm === "perimeter.md" ||
            nm === "boundaries.md" ||
            nm === "grok.md"
          );
        });
      }
    } catch (e) {}

    /*
     * Work faces — MAP_LEGEND_SPEC Work row lockstep (pc-864/pc-915):
     *   ⭐ For You · ❗ Stuck · ▶️ In progress · ◻ Ready · ○ Empty queue
     * Open pile face = work glyph (🎫 default). Stacks: you · work · papers ·
     * jobs · hands · 📜 instructions
     */
    if (gold > 0) {
      var cg = _mkOutlineChipDoor(
        "is-gold",
        gold + " For You · same as map gold lip · click → filter",
        gold + " For You work orders",
        function () {
          _outlineChipAction(p, "for_you");
        }
      );
      _olFillChip(cg, "⭐", "ol-chip-work-face", gold);
      wrap.appendChild(cg);
    }
    if (stuckFace > 0) {
      var cs = _mkOutlineChipDoor(
        "is-stuck",
        stuckFace +
          " stuck · " +
          ((ps && ps.signal && ps.signal.reason) || "red map lip") +
          " · click → dig Stuck",
        stuckFace + " stuck work orders",
        function () {
          _outlineChipAction(p, "stuck");
        }
      );
      _olFillChip(cs, "❗", "ol-chip-work-face", stuckFace);
      wrap.appendChild(cs);
    }
    if (flowingFace > 0 && gold <= 0 && stuckFace <= 0) {
      var cf = _mkOutlineChipDoor(
        "is-flowing",
        "In progress · hand working here now · Map ▶️ · click → dig",
        "In progress",
        function () {
          _outlineChipAction(p, "open");
        }
      );
      _olFillChip(cf, "▶️", "ol-chip-work-face", flowingFace > 1 ? flowingFace : null);
      wrap.appendChild(cf);
    }
    if (open > 0) {
      var c = _mkOutlineChipDoor(
        "is-open is-work",
        open +
          " live open work orders (deferred excluded)" +
          (ps && ps.signal ? " · map " + (ps.signal.label || "") : "") +
          " · Map 🎫 seat · click → Work orders live",
        open + " live open work orders",
        function () {
          _outlineChipAction(p, "open");
        }
      );
      _olFillChip(
        c,
        typeof getWorkGlyph === "function" ? getWorkGlyph() : "🎫",
        "ol-chip-work-face",
        open
      );
      wrap.appendChild(c);
    }
    if (isStarved) {
      var ce = _mkOutlineChipDoor(
        "is-starved",
        "Empty queue · scheduled hand has nothing ready · Map ○ · click → dig",
        "Empty queue",
        function () {
          _outlineChipAction(p, "open");
        }
      );
      _olFillChip(ce, "○", "ol-chip-work-face", null);
      wrap.appendChild(ce);
    }
    if (agents > 0) {
      var ca = _mkOutlineChipDoor(
        "is-hands",
        agents +
          " hand" +
          (agents !== 1 ? "s" : "") +
          " · click → dig Agents",
        agents + " hands on this project",
        function () {
          _outlineChipAction(p, "hands");
        }
      );
      _olFillChip(
        ca,
        typeof getHandGlyph === "function" ? getHandGlyph() : "✋",
        "ol-chip-face",
        agents
      );
      wrap.appendChild(ca);
    }
    if (jobs > 0) {
      var cj = _mkOutlineChipDoor(
        "is-jobs",
        jobs +
          " job" +
          (jobs !== 1 ? "s" : "") +
          " · click → dig Jobs",
        jobs + " jobs on this project",
        function () {
          _outlineChipAction(p, "jobs");
        }
      );
      _olFillChip(
        cj,
        typeof getJobGlyph === "function" ? getJobGlyph() : "⏰",
        "ol-chip-job-mark",
        jobs
      );
      wrap.appendChild(cj);
    }
    /*
     * Papers = non-law root md count (Map 📄 seat). Law mds are 📜 only
     * so AGENTS.md is not double-counted as both paper + instruction.
     */
    var paperN = 0;
    var paperRows = [];
    try {
      paperRows = outlinePapersAtLevel(p, "") || [];
      paperN = paperRows.filter(function (r) {
        return r && !r.isInstr;
      }).length;
    } catch (ePn) {}
    if (paperN > 0) {
      var cp = _mkOutlineChipDoor(
        "is-papers",
        paperN +
          " handbook papers (instructions counted under 📜) · Map 📄 seat · click → list",
        paperN + " papers",
        function () {
          _outlineChipAction(p, "papers");
        }
      );
      _olFillChip(
        cp,
        typeof getPaperGlyph === "function" ? getPaperGlyph() : "📄",
        "ol-chip-paper-mark",
        paperN
      );
      wrap.appendChild(cp);
    }
    if (instr) {
      var ci = _mkOutlineChipDoor(
        "is-instr",
        "Instructions — AGENTS.md / pointers. Map gold 📜 · click → dig.",
        "Instructions on this project",
        function () {
          _outlineChipAction(p, "instr");
        }
      );
      _olFillChip(
        ci,
        typeof getInstrGlyph === "function" ? getInstrGlyph() : "📜",
        "ol-chip-instr-face",
        null
      );
      wrap.appendChild(ci);
    }
    return wrap.children.length ? wrap : null;
  }

  /**
   * Markdown at one folder level for Outline (census or ground listing).
   * Instructions (law) first, then A–Z — BluePrint as MD viewer.
   */
  function outlinePapersAtLevel(plot, underRel) {
    var under = String(underRel || "")
      .replace(/\\/g, "/")
      .replace(/^\/+|\/+$/g, "");
    var rows = [];
    var seen = {};
    function pushRow(name, rel, meta) {
      var nm = String(name || "").trim();
      if (!nm || !/\.md$/i.test(nm)) return;
      var key = String(rel || nm)
        .replace(/\\/g, "/")
        .toLowerCase();
      if (seen[key]) return;
      seen[key] = true;
      var f = meta || { name: nm, rel: rel || nm };
      var role =
        typeof classifyPaperRole === "function" ? classifyPaperRole(f) : "";
      var isInstr =
        role === "law" ||
        role === "architecture" ||
        (typeof isPcLawMd === "function" && isPcLawMd(nm)) ||
        !!(f.rule || f.pointer || f.instruction);
      rows.push({
        name: nm,
        rel: rel || nm,
        f: f,
        isInstr: isInstr,
      });
    }
    /* 1) Census scan — same source as Map papers stack */
    try {
      if (typeof folderPaperLevelScan === "function") {
        var scan = folderPaperLevelScan(plot, under);
        (scan.filesHere || []).forEach(function (row) {
          if (!row) return;
          pushRow(
            row.fileName || (row.f && row.f.name),
            row.rel || row.fileName,
            row.f
          );
        });
      }
    } catch (eSc) {}
    /* 2) root_entries / root_mds fallback when scan cold */
    if (!rows.length && !under) {
      try {
        ((plot && plot.root_entries) || []).forEach(function (e) {
          if (!e || e.dir || e.hidden) return;
          var nm = String(e.name || "");
          if (!/\.md$/i.test(nm)) return;
          pushRow(nm, nm, e);
        });
      } catch (eRe) {}
    }
    if (!rows.length && !under) {
      try {
        ((plot && plot.root_mds) || []).forEach(function (f) {
          if (!f) return;
          var rel = String(f.rel || f.name || "").replace(/\\/g, "/");
          if (rel.indexOf("/") >= 0) return; /* root only */
          pushRow(f.name || rel, rel, f);
        });
      } catch (eRm) {}
    }
    rows.sort(function (a, b) {
      if (a.isInstr !== b.isInstr) return a.isInstr ? -1 : 1;
      return String(a.name || "").localeCompare(String(b.name || ""));
    });
    return rows;
  }

  function outlinePapersFromEntries(entries) {
    var rows = [];
    (entries || []).forEach(function (e) {
      if (!e || e.dir || e.hidden) return;
      var nm = String(e.name || "");
      if (!/\.md$/i.test(nm)) return;
      var role =
        typeof classifyPaperRole === "function" ? classifyPaperRole(e) : "";
      var isInstr =
        role === "law" ||
        role === "architecture" ||
        (typeof isPcLawMd === "function" && isPcLawMd(nm)) ||
        !!(e.rule || e.pointer || e.instruction);
      rows.push({
        name: nm,
        rel: nm,
        f: e,
        isInstr: isInstr,
      });
    });
    rows.sort(function (a, b) {
      if (a.isInstr !== b.isInstr) return a.isInstr ? -1 : 1;
      return String(a.name || "").localeCompare(String(b.name || ""));
    });
    return rows;
  }

  function outlineOpenMd(plot, fileName, parentRel) {
    if (!plot || !fileName) return;
    var plotPath = String(plot.path || "").replace(/\/+$/, "");
    var sub = parentRel
      ? String(parentRel).replace(/^\/+|\/+$/g, "") + "/" + fileName
      : fileName;
    var abs = plotPath
      ? typeof joinRel === "function"
        ? joinRel(plotPath, sub)
        : plotPath + "/" + sub
      : sub;
    var cityRel =
      typeof cityRelFromAbs === "function" ? cityRelFromAbs(abs) : "";
    var path = cityRel || abs || sub;
    try {
      if (typeof openPaperInSuite === "function") {
        openPaperInSuite(path);
        return;
      }
    } catch (eOp) {}
    try {
      goHref("/read?path=" + encodeURIComponent(path));
    } catch (eGo) {}
  }

  function _renderOutlineMdRows(frag, plot, mdRows, depth, parentRel) {
    if (!frag || !plot || !mdRows || !mdRows.length) return;
    var depthCls = "ol-depth-" + Math.min(depth, 3);
    mdRows.forEach(function (row) {
      if (!row || !row.name) return;
      var name = String(row.name);
      var el = document.createElement("div");
      el.className =
        "ol-row is-md " +
        depthCls +
        (row.isInstr ? " is-instr-md" : "");
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "row");
      el.dataset.md = name;
      el.title =
        name +
        (row.isInstr ? " · Instructions" : " · paper") +
        " · click → read in suite · ⌘-click full page";

      var sp = document.createElement("span");
      sp.className = "ol-expand-spacer";
      el.appendChild(sp);

      var glyph = document.createElement("span");
      glyph.className = "ol-md-glyph";
      glyph.setAttribute("aria-hidden", "true");
      glyph.textContent = "md";
      el.appendChild(glyph);

      var nameEl = document.createElement("span");
      nameEl.className = "ol-name";
      nameEl.textContent = name;
      el.appendChild(nameEl);

      /* Law mark is on the name (is-instr-md) — no per-row Instr. chip.
       * Project row already has the Instr. seat door; stacking chips was noise. */

      (function (capturedPlot, capturedName, capturedParent) {
        function openIt(ev) {
          if (ev && (ev.metaKey || ev.ctrlKey)) {
            var plotPath = String(capturedPlot.path || "").replace(/\/+$/, "");
            var sub = capturedParent
              ? capturedParent + "/" + capturedName
              : capturedName;
            var abs = plotPath
              ? typeof joinRel === "function"
                ? joinRel(plotPath, sub)
                : plotPath + "/" + sub
              : sub;
            var cityRel =
              typeof cityRelFromAbs === "function"
                ? cityRelFromAbs(abs)
                : abs;
            try {
              goHref("/read?path=" + encodeURIComponent(cityRel || abs));
            } catch (eG) {}
            return;
          }
          outlineOpenMd(capturedPlot, capturedName, capturedParent);
        }
        el.addEventListener("click", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          openIt(ev);
        });
        el.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            openIt(ev);
          }
        });
      })(plot, name, parentRel || "");

      frag.appendChild(el);
    });
  }

  function _renderOutlineChildren(frag, plot, entries, parentRel, depth, digTrail, parentOnPath, opts) {
    opts = opts || {};
    var slug = String(plot.slug || plot.name || "").toLowerCase();
    var depthCls = "ol-depth-" + Math.min(depth, 3);
    var digRel = opts.digRel != null ? String(opts.digRel || "") : "";
    /* Trail segment at this depth — for path walking (not multi-You paint) */
    var focusTrailEntry = parentOnPath && digTrail.length > depth ? digTrail[depth] : null;
    var focusName = focusTrailEntry ? String(focusTrailEntry.name || "").toLowerCase() : "";
    var allEntries = opts.fullEntries || entries || [];
    var dirs = (entries || []).filter(function (e) { return e && e.dir && !e.hidden; });
    /*
     * Project-root rows under Expand folders (opsOnly): same membership as Map.
     * Manual chevron dig may pass full listings (opsOnly false).
     */
    var moreN = opts.more != null ? opts.more | 0 : 0;
    if (opts.opsOnly && !parentRel) {
      var split = splitEntriesOpsLayer(dirs);
      dirs = split.ops;
      if (moreN <= 0) moreN = split.rest.length;
    }
    /* Markdown at this level first — BluePrint as MD viewer (before dirs) */
    var mdRows = [];
    try {
      if (parentRel) {
        mdRows = outlinePapersFromEntries(allEntries);
        /* Prefer census when ground listing is thin */
        if (!mdRows.length) {
          mdRows = outlinePapersAtLevel(plot, parentRel);
        }
      } else {
        mdRows = outlinePapersAtLevel(plot, "");
        var fromList = outlinePapersFromEntries(allEntries);
        var seenMd = {};
        mdRows.forEach(function (r) {
          seenMd[String(r.name || "").toLowerCase()] = true;
        });
        fromList.forEach(function (r) {
          var k = String(r.name || "").toLowerCase();
          if (!seenMd[k]) {
            seenMd[k] = true;
            mdRows.push(r);
          }
        });
        mdRows.sort(function (a, b) {
          if (a.isInstr !== b.isInstr) return a.isInstr ? -1 : 1;
          return String(a.name || "").localeCompare(String(b.name || ""));
        });
      }
    } catch (eMd) {}
    if (mdRows.length) {
      _renderOutlineMdRows(frag, plot, mdRows, depth, parentRel || "");
    }
    dirs.forEach(function (e) {
      var name = String(e.name || "");
      if (!name) return;
      var relPath = parentRel ? parentRel + "/" + name : name;
      var isFoundation = window.MapGraph && MapGraph.isDigFoundationDirName
        ? MapGraph.isDigFoundationDirName(name)
        : false;
      var onPath =
        !!(parentOnPath && focusName && name.toLowerCase() === focusName);
      /* You presence = exact dig leaf only (one row, matches Map is-you-here) */
      var isFocused = !!(digRel && relPath === digRel);
      var expKey = _outlineKey(slug, relPath);
      var expState = _outlineExpandState[expKey];
      var isOpen = !!(expState && expState.entries);
      var hasChildren = (e.n == null ? true : e.n > 0);

      var row = document.createElement("div");
      row.className = "ol-row " + depthCls +
        (isFoundation ? " ol-foundation" : "") +
        (isFocused ? " is-focused" : "");
      row.setAttribute("tabindex", "0");
      row.setAttribute("role", "row");
      row.dataset.rel = relPath;

      if (hasChildren) {
        var expBtn = document.createElement("button");
        expBtn.type = "button";
        expBtn.className = "ol-expand" + (isOpen ? " is-open" : "");
        expBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
        expBtn.textContent = isOpen ? "▾" : "▸";
        (function (capturedPlot, capturedSlug, capturedRel) {
          expBtn.addEventListener("click", function (ev) {
            ev.stopPropagation();
            _toggleOutlineExpand(capturedPlot, capturedSlug, capturedRel);
          });
        })(plot, slug, relPath);
        row.appendChild(expBtn);
      } else {
        var spacer = document.createElement("span");
        spacer.className = "ol-expand-spacer";
        row.appendChild(spacer);
      }

      var nameEl = document.createElement("span");
      nameEl.className = "ol-name";
      nameEl.textContent = name;
      row.appendChild(nameEl);

      /* Folder law mark stays on project/seat chips — not a second Instr. stack */

      (function (capturedPlot, capturedName, capturedRel) {
        row.addEventListener("click", function (ev) {
          if (ev.target.classList && ev.target.classList.contains("ol-expand")) return;
          if (ev.metaKey || ev.ctrlKey) {
            if (capturedPlot.path) {
              try { window.open("file://" + capturedPlot.path + "/" + capturedRel); } catch (eO) {}
            }
            return;
          }
          _outlineDigChild(capturedPlot, { name: capturedName, relPath: capturedRel });
        });
        row.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            _outlineDigChild(capturedPlot, { name: capturedName, relPath: capturedRel });
          }
        });
      })(plot, name, relPath);

      frag.appendChild(row);

      if (expState && expState.loading) {
        var ld = document.createElement("div");
        ld.className = "ol-loading " + depthCls;
        ld.textContent = "Loading…";
        frag.appendChild(ld);
      } else if (isOpen && expState.entries) {
        _renderOutlineChildren(
          frag,
          plot,
          expState.entries,
          relPath,
          depth + 1,
          digTrail,
          onPath,
          {
            opsOnly: !!expState.opsOnly && !relPath,
            more: expState.more,
            digRel: digRel,
            fullEntries: expState.fullEntries || expState.entries,
          }
        );
      }
    });
    /* Match Map expand "+N more · dig in" when ops-only layer is showing */
    if (moreN > 0 && !parentRel) {
      var moreRow = document.createElement("div");
      moreRow.className = "ol-row " + depthCls + " ol-more-dig";
      moreRow.setAttribute("role", "note");
      var moreSp = document.createElement("span");
      moreSp.className = "ol-expand-spacer";
      moreRow.appendChild(moreSp);
      var moreNm = document.createElement("span");
      moreNm.className = "ol-name ol-more-label";
      moreNm.textContent = "+" + moreN + " more · dig in";
      moreNm.title = "Domain / non-ops folders — open the project on Map or dig via click";
      moreRow.appendChild(moreNm);
      frag.appendChild(moreRow);
    }
  }

  function _outlineEnterPlot(p, rowEl) {
    if (!mapDigIn || !mapDigIn.plot ||
        String(mapDigIn.plot.slug || "").toLowerCase() !== String(p.slug || p.name || "").toLowerCase()) {
      /* Collapse expand overlay without camera dance */
      if (mapExpandLevel > 0) {
        syncMapViewExpand(0);
        try {
          outlineClearExpandMembership();
          var root = svg && (svg.querySelector("#root") || svg);
          clearExpandOverlay(root, null);
          if (model) model._expandBounds = null;
          if (svg) svg.classList.remove("map-expand-on");
        } catch (eExp) {}
      }
      if (!_preDigCam) _preDigCam = typeof snapshotCamera === "function" ? snapshotCamera() : null;
      mapDigIn = {
        plot: p,
        relPath: "",
        trail: [{ name: p.name || p.slug || "project", relPath: "" }],
        listing: null,
        hubLabel: p.name || p.slug,
      };
      _digEnterFitPending = true;
      syncMapViewDigFromLocal();
      if (model) model._digIn = true;
      try { setDigNestedStageFlag && setDigNestedStageFlag(); } catch (e) {}
      try {
        if (typeof WoTape.getProjectKey() !== "undefined") {
          WoTape.setProjectKey(String(p.slug || p.name || p.product || "").toLowerCase().trim());
          if (global.WoTape) WoTape.bustTape();
          if (global.WoTape) WoTape.bustChips();
          AgentsPanel.setLiveSig("");
        }
      } catch (eWo) {}
      try { mountMapDigTrailChrome && mountMapDigTrailChrome(); } catch (e) {}
      try { paintMapResetFab && paintMapResetFab(); } catch (e) {}
    }
    try { showProjectDetail && showProjectDetail(p, rowEl); } catch (e) {}
    var slug = String(p.slug || p.name || "").toLowerCase();
    var expKey = _outlineKey(slug, "");
    if (!_outlineExpandState[expKey]) {
      _toggleOutlineExpand(p, slug, "");
    } else {
      _outlineSig = ""; renderMapOutline();
    }
  }

  function _outlineDigChild(plot, dirEntry) {
    var pSlug = String(plot.slug || plot.name || "").toLowerCase();
    var digPlotSlug = mapDigIn && mapDigIn.plot
      ? String(mapDigIn.plot.slug || mapDigIn.plot.name || "").toLowerCase()
      : "";
    if (!mapDigIn || digPlotSlug !== pSlug) {
      _outlineEnterPlot(plot, null);
      return;
    }
    var name = String(dirEntry.name || "");
    var nextRel = String(dirEntry.relPath || name);
    var trail = (mapDigIn.trail || []).slice();
    trail.push({ name: name, relPath: nextRel });
    mapDigIn = Object.assign({}, mapDigIn, {
      relPath: nextRel,
      trail: trail,
      hubLabel: trail.map(function (t) { return t.name; }).join(" / "),
    });
    syncMapViewDigFromLocal();
    try { mountMapDigTrailChrome && mountMapDigTrailChrome(); } catch (e) {}
    var expKey = _outlineKey(pSlug, nextRel);
    if (!_outlineExpandState[expKey]) {
      _toggleOutlineExpand(plot, pSlug, nextRel);
    } else {
      _outlineSig = ""; renderMapOutline();
    }
  }

  function _toggleOutlineExpand(plot, slug, relPath) {
    var key = _outlineKey(slug, relPath);
    var st = _outlineExpandState[key];
    /* Open or still loading → close / cancel (in-flight must not re-open) */
    if (st && (st.entries || st.loading)) {
      delete _outlineExpandState[key];
      /* Drop descendant expands under this path (no ghost re-open on re-expand) */
      try {
        var slugPart = String(slug || "") + ":";
        var rel = String(relPath || "");
        Object.keys(_outlineExpandState).forEach(function (k) {
          if (k === key) return;
          if (k.indexOf(slugPart) !== 0) return;
          if (!rel) {
            /* Project root closed → clear every nested key for this slug */
            delete _outlineExpandState[k];
          } else if (k.indexOf(slugPart + rel + "/") === 0) {
            delete _outlineExpandState[k];
          }
        });
      } catch (eNest) {}
      _outlineSig = "";
      renderMapOutline();
      try {
        paintMapExpandFab();
      } catch (eFab0) {}
      return;
    }
    var token = {};
    var expandGen = _outlineExpandGen | 0;
    _outlineExpandState[key] = { loading: true, token: token };
    _outlineSig = "";
    renderMapOutline();
    try {
      paintMapExpandFab();
    } catch (eFab1) {}
    var scope;
    try {
      scope = typeof folderCityRel === "function"
        ? folderCityRel(plot, relPath ? { relPath: relPath } : null)
        : (relPath ? (String(plot.name || plot.slug || "") + "/" + relPath) : String(plot.name || plot.slug || ""));
    } catch (eSc) {
      scope = relPath ? (String(plot.name || plot.slug || "") + "/" + relPath) : String(plot.name || plot.slug || "");
    }
    fetch("/api/ground?scope=" + encodeURIComponent(scope || ""), { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : { entries: [] }; })
      .then(function (data) {
        if (expandGen !== (_outlineExpandGen | 0)) return;
        var cur = _outlineExpandState[key];
        if (!cur || cur.token !== token) return;
        var raw = data.entries || data.listing || [];
        _outlineExpandState[key] = {
          entries: raw,
          fullEntries: raw,
          opsOnly: false,
          token: token,
        };
        _outlineSig = "";
        renderMapOutline();
        try {
          paintMapExpandFab();
        } catch (eFab2) {}
      })
      .catch(function () {
        if (expandGen !== (_outlineExpandGen | 0)) return;
        var cur = _outlineExpandState[key];
        if (!cur || cur.token !== token) return;
        _outlineExpandState[key] = {
          entries: [],
          fullEntries: [],
          token: token,
        };
        _outlineSig = "";
        renderMapOutline();
        try {
          paintMapExpandFab();
        } catch (eFab3) {}
      });
  }

  /* ── end pc-758 ──────────────────────────────────────────────────────────── */

  /** Expand Outline to this project and light the matching seat chip (Map↔Outline glue). */
  function outlineRevealPlot(plot, seatHint) {
    if (!plot || !model) return;
    try {
      /* Prefer Outline projection so chips are visible next to Map */
      if (typeof mapProjectionMode !== "undefined" && mapProjectionMode !== "outline") {
        /* Do not force-switch projection — only expand if already on Outline */
      }
    } catch (e0) {}
    try {
      var slug = String(plot.slug || plot.name || "").toLowerCase();
      var key = typeof _outlineKey === "function" ? _outlineKey(slug, "") : slug;
      if (typeof _outlineExpandState !== "undefined" && !_outlineExpandState[key]) {
        if (typeof _toggleOutlineExpand === "function") {
          _toggleOutlineExpand(plot, slug, "");
        }
      }
      if (typeof paintOutlineTree === "function") paintOutlineTree();
      setTimeout(function () {
        try {
          var row =
            document.querySelector(
              '.ol-row[data-slug="' +
                slug.replace(/"/g, "") +
                '"], .ol-row[data-name="' +
                String(plot.name || "").replace(/"/g, "") +
                '"]'
            ) ||
            document.querySelector(".ol-row.is-here, .ol-row.is-selected");
          if (row && row.scrollIntoView) {
            row.scrollIntoView({ block: "nearest", behavior: "smooth" });
          }
          var chipSel =
            seatHint === "jobs"
              ? ".ol-chip.is-jobs"
              : seatHint === "hands" || seatHint === "agents"
                ? ".ol-chip.is-hands, .ol-chip.is-agents"
                : seatHint === "instr"
                  ? ".ol-chip.is-instr"
                  : ".ol-chip.is-papers";
          var host = row || document;
          var chip = host.querySelector && host.querySelector(chipSel);
          if (chip) {
            chip.classList.add("is-pulse");
            setTimeout(function () {
              try {
                chip.classList.remove("is-pulse");
              } catch (e) {}
            }, 900);
          }
        } catch (eSc) {}
      }, 80);
    } catch (e1) {}
  }

  function bustSig() {
    _outlineSig = "";
  }

  function getExpandState() {
    return _outlineExpandState;
  }

  function wrapPublic(fn) {
    return function () {
      syncFromHost();
      var result;
      try {
        result = fn.apply(this, arguments);
      } finally {
        syncToHost();
      }
      return result;
    };
  }

  var FolderList = {
    init: init,
    paint: wrapPublic(function () {
      renderMapOutlineIfOn();
    }),
    bustSig: bustSig,
    getExpandState: getExpandState,
    outlineClearExpandMembership: wrapPublic(outlineClearExpandMembership),
    outlineTreeHasOpen: wrapPublic(outlineTreeHasOpen),
    outlineCollapseAll: wrapPublic(outlineCollapseAll),
    outlineExpandAllTopProjects: wrapPublic(outlineExpandAllTopProjects),
    outlinePlotsFromModel: wrapPublic(outlinePlotsFromModel),
    renderMapOutlineIfOn: wrapPublic(renderMapOutlineIfOn),
    renderMapOutline: wrapPublic(renderMapOutline),
    outlineWorkspaceHubName: wrapPublic(outlineWorkspaceHubName),
    outlineWorkspaceStaffCounts: wrapPublic(outlineWorkspaceStaffCounts),
    outlineWorkspaceHasL0Instructions: wrapPublic(outlineWorkspaceHasL0Instructions),
    outlinePapersAtLevel: wrapPublic(outlinePapersAtLevel),
    outlinePapersFromEntries: wrapPublic(outlinePapersFromEntries),
    outlineOpenMd: wrapPublic(outlineOpenMd),
    outlineRevealPlot: wrapPublic(outlineRevealPlot),
    splitEntriesOpsLayer: wrapPublic(splitEntriesOpsLayer),
  };

  function init(host) {
    if (!host || typeof host !== "object") return FolderList;
    Object.keys(host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return FolderList;
  }

  global.FolderList = FolderList;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = FolderList;
  }
})(typeof window !== "undefined" ? window : globalThis);

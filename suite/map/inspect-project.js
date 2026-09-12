/*! inspect-project.js — Project inspect panel renderer (pc-1395)
 *
 * Strangler extract from workspace_map_app.js (ARCHITECTURE.md §4).
 * Project overview / Finder / house / open-pile door live here only —
 * host keeps thin wrappers so existing call sites stay put.
 *
 * Browser: window.InspectProject
 * Public: { init, show, finder, house, openWorkOrders }
 *
 * No window.* render negotiation flags.
 */
(function (global) {
  "use strict";

  /** Host hooks — set by init(host). */
  var _host = {
    actorIsJob: null,
    actorIsLive: null,
    actorIsWalking: null,
    actorShortName: null,
    adoptProjectFolder: null,
    bindDoorRunChips: null,
    bindPlaceOpenSectionShared: null,
    bindPlacePulse: null,
    bodySliceToPulseId: null,
    buildPlaceOpenSectionHtml: null,
    cityRelFromPaper: null,
    computePlacePulseCells: null,
    deskProductForPlot: null,
    ensurePlaceBodySurface: null,
    filterMdsByDepth: null,
    folderHasDeskStore: null,
    folderTabFaceCount: null,
    forYouAttItems: null,
    forYouCategoryFromSlip: null,
    forYouProductLabel: null,
    forYouWatchRowModel: null,
    formatRemain: null,
    formatSnoozeUntil: null,
    goldFor: null,
    groupFilesByRole: null,
    groupMdsBySubfolder: null,
    inspectOrbitGroup: null,
    inspectPerson: null,
    instructionSectionLabel: null,
    isProjectRootLayerLaw: null,
    isRequiredPaper: null,
    joinForeignDesk: null,
    joinRel: null,
    listFilterBarHtml: null,
    mapHygieneKindsForPlot: null,
    mapHygieneTeach: null,
    mapMdDepthLabel: null,
    mapMdDepthPref: null,
    mapUnroutedRowsForPlot: null,
    mergePlaceOpenEntries: null,
    nextFireMs: null,
    normKey: null,
    normalizePlaceBodySlice: null,
    normalizePlaceOpenHref: null,
    normalizeWoFilter: null,
    openCount: null,
    openFolderInFinder: null,
    openFolderInSuite: null,
    openMapHygieneTicket: null,
    openPathInFinder: null,
    operateForeignConsumer: null,
    paintInspectKpis: null,
    paperDepth: null,
    paperRelPath: null,
    placeOpenFallbackEntries: null,
    placePulseStripHtml: null,
    placeState: null,
    poll: null,
    postMapHygieneExpected: null,
    prodFromTid: null,
    productSnoozeActive: null,
    projectBriefHref: null,
    projectInstructionStacks: null,
    projectRootPapers: null,
    readPlaceOpenDoorsCache: null,
    readPlaceOpenTeamCache: null,
    readPlaceOpenUserPins: null,
    refreshMapHygieneSurfaces: null,
    remountPlaceOverview: null,
    renderInstructionsSection: null,
    renderWorkingOnNowSection: null,
    rowMatchesWoFilter: null,
    scrollInspectSection: null,
    setPlaceBodySlice: null,
    slipFromApiTask: null,
    slipMatchesListFilter: null,
    softRefreshPlacePulse: null,
    stalledAttItems: null,
    storeOpenRaw: null,
    stuckFaceFromPlaceState: null,
    syncDigInWoToLeftRail: null,
    wireListFilterInput: null,
    workerColor: null,
    workerHomeMatchesPlot: null,
    writePlaceOpenDoorsCache: null,
    writePlaceOpenTeamCache: null,
    youPendingCount: null,
    youSnoozeBarHtml: null,
    getModel: null,
    getLastAtt: null,
    getMapPlaceBodySlice: null,
    getDigOverviewRemount: null,
    setDigOverviewRemount: null,
    getSoftPulseSig: null,
    setSoftPulseSig: null
  };

  function H(name) {
    var fn = _host[name];
    return typeof fn === "function" ? fn : null;
  }

  var model = null;
  var _digOverviewRemount = null;
  var mapPlaceBodySlice = "work";
  var _lastAtt = null;
  var _softPulseSig = "";

  function syncFromHost() {
    var g;
    g = H("getModel");
    model = g ? g() : model;
    g = H("getLastAtt");
    _lastAtt = g ? g() : _lastAtt;
    g = H("getMapPlaceBodySlice");
    mapPlaceBodySlice = g ? g() : mapPlaceBodySlice;
    g = H("getDigOverviewRemount");
    _digOverviewRemount = g ? g() : _digOverviewRemount;
    g = H("getSoftPulseSig");
    if (g) _softPulseSig = g();
  }

  function syncToHost() {
    var s;
    s = H("setDigOverviewRemount");
    if (s) s(_digOverviewRemount);
    s = H("setSoftPulseSig");
    if (s) s(_softPulseSig);
  }

  function actorIsJob() {
    syncToHost();
    var fn = H('actorIsJob');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function actorIsLive() {
    syncToHost();
    var fn = H('actorIsLive');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function actorIsWalking() {
    syncToHost();
    var fn = H('actorIsWalking');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function actorShortName() {
    syncToHost();
    var fn = H('actorShortName');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function adoptProjectFolder() {
    syncToHost();
    var fn = H('adoptProjectFolder');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function bindDoorRunChips() {
    syncToHost();
    var fn = H('bindDoorRunChips');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function bindPlaceOpenSectionShared() {
    syncToHost();
    var fn = H('bindPlaceOpenSectionShared');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function bindPlacePulse() {
    syncToHost();
    var fn = H('bindPlacePulse');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function bodySliceToPulseId() {
    syncToHost();
    var fn = H('bodySliceToPulseId');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function buildPlaceOpenSectionHtml() {
    syncToHost();
    var fn = H('buildPlaceOpenSectionHtml');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function cityRelFromPaper() {
    syncToHost();
    var fn = H('cityRelFromPaper');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function computePlacePulseCells() {
    syncToHost();
    var fn = H('computePlacePulseCells');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function deskProductForPlot() {
    syncToHost();
    var fn = H('deskProductForPlot');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function ensurePlaceBodySurface() {
    syncToHost();
    var fn = H('ensurePlaceBodySurface');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function filterMdsByDepth() {
    syncToHost();
    var fn = H('filterMdsByDepth');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function folderHasDeskStore() {
    syncToHost();
    var fn = H('folderHasDeskStore');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function folderTabFaceCount() {
    syncToHost();
    var fn = H('folderTabFaceCount');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function forYouAttItems() {
    syncToHost();
    var fn = H('forYouAttItems');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function forYouCategoryFromSlip() {
    syncToHost();
    var fn = H('forYouCategoryFromSlip');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function forYouProductLabel() {
    syncToHost();
    var fn = H('forYouProductLabel');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function forYouWatchRowModel() {
    syncToHost();
    var fn = H('forYouWatchRowModel');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function formatRemain() {
    syncToHost();
    var fn = H('formatRemain');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function formatSnoozeUntil() {
    syncToHost();
    var fn = H('formatSnoozeUntil');
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

  function groupFilesByRole() {
    syncToHost();
    var fn = H('groupFilesByRole');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function groupMdsBySubfolder() {
    syncToHost();
    var fn = H('groupMdsBySubfolder');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function inspectOrbitGroup() {
    syncToHost();
    var fn = H('inspectOrbitGroup');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function inspectPerson() {
    syncToHost();
    var fn = H('inspectPerson');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function instructionSectionLabel() {
    syncToHost();
    var fn = H('instructionSectionLabel');
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

  function isRequiredPaper() {
    syncToHost();
    var fn = H('isRequiredPaper');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function joinForeignDesk() {
    syncToHost();
    var fn = H('joinForeignDesk');
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

  function listFilterBarHtml() {
    syncToHost();
    var fn = H('listFilterBarHtml');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function mapHygieneKindsForPlot() {
    syncToHost();
    var fn = H('mapHygieneKindsForPlot');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function mapHygieneTeach() {
    syncToHost();
    var fn = H('mapHygieneTeach');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function mapMdDepthLabel() {
    syncToHost();
    var fn = H('mapMdDepthLabel');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function mapMdDepthPref() {
    syncToHost();
    var fn = H('mapMdDepthPref');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function mapUnroutedRowsForPlot() {
    syncToHost();
    var fn = H('mapUnroutedRowsForPlot');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function mergePlaceOpenEntries() {
    syncToHost();
    var fn = H('mergePlaceOpenEntries');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function nextFireMs() {
    syncToHost();
    var fn = H('nextFireMs');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function normKey() {
    syncToHost();
    var fn = H('normKey');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function normalizePlaceBodySlice() {
    syncToHost();
    var fn = H('normalizePlaceBodySlice');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function normalizePlaceOpenHref() {
    syncToHost();
    var fn = H('normalizePlaceOpenHref');
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

  function openCount() {
    syncToHost();
    var fn = H('openCount');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function openFolderInFinder() {
    syncToHost();
    var fn = H('openFolderInFinder');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function openFolderInSuite() {
    syncToHost();
    var fn = H('openFolderInSuite');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function openMapHygieneTicket() {
    syncToHost();
    var fn = H('openMapHygieneTicket');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function openPathInFinder() {
    syncToHost();
    var fn = H('openPathInFinder');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function operateForeignConsumer() {
    syncToHost();
    var fn = H('operateForeignConsumer');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function paintInspectKpis() {
    syncToHost();
    var fn = H('paintInspectKpis');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function paperDepth() {
    syncToHost();
    var fn = H('paperDepth');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function paperRelPath() {
    syncToHost();
    var fn = H('paperRelPath');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function placeOpenFallbackEntries() {
    syncToHost();
    var fn = H('placeOpenFallbackEntries');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function placePulseStripHtml() {
    syncToHost();
    var fn = H('placePulseStripHtml');
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

  function poll() {
    syncToHost();
    var fn = H('poll');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function postMapHygieneExpected() {
    syncToHost();
    var fn = H('postMapHygieneExpected');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function prodFromTid() {
    syncToHost();
    var fn = H('prodFromTid');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function productSnoozeActive() {
    syncToHost();
    var fn = H('productSnoozeActive');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function projectBriefHref() {
    syncToHost();
    var fn = H('projectBriefHref');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function projectInstructionStacks() {
    syncToHost();
    var fn = H('projectInstructionStacks');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function projectRootPapers() {
    syncToHost();
    var fn = H('projectRootPapers');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function readPlaceOpenDoorsCache() {
    syncToHost();
    var fn = H('readPlaceOpenDoorsCache');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function readPlaceOpenTeamCache() {
    syncToHost();
    var fn = H('readPlaceOpenTeamCache');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function readPlaceOpenUserPins() {
    syncToHost();
    var fn = H('readPlaceOpenUserPins');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function refreshMapHygieneSurfaces() {
    syncToHost();
    var fn = H('refreshMapHygieneSurfaces');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function remountPlaceOverview() {
    syncToHost();
    var fn = H('remountPlaceOverview');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function renderInstructionsSection() {
    syncToHost();
    var fn = H('renderInstructionsSection');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function renderWorkingOnNowSection() {
    syncToHost();
    var fn = H('renderWorkingOnNowSection');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function rowMatchesWoFilter() {
    syncToHost();
    var fn = H('rowMatchesWoFilter');
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

  function setPlaceBodySlice() {
    syncToHost();
    var fn = H('setPlaceBodySlice');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function slipFromApiTask() {
    syncToHost();
    var fn = H('slipFromApiTask');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function slipMatchesListFilter() {
    syncToHost();
    var fn = H('slipMatchesListFilter');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function softRefreshPlacePulse() {
    syncToHost();
    var fn = H('softRefreshPlacePulse');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function stalledAttItems() {
    syncToHost();
    var fn = H('stalledAttItems');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function storeOpenRaw() {
    syncToHost();
    var fn = H('storeOpenRaw');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function stuckFaceFromPlaceState() {
    syncToHost();
    var fn = H('stuckFaceFromPlaceState');
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

  function wireListFilterInput() {
    syncToHost();
    var fn = H('wireListFilterInput');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function workerColor() {
    syncToHost();
    var fn = H('workerColor');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function workerHomeMatchesPlot() {
    syncToHost();
    var fn = H('workerHomeMatchesPlot');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function writePlaceOpenDoorsCache() {
    syncToHost();
    var fn = H('writePlaceOpenDoorsCache');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }

  function writePlaceOpenTeamCache() {
    syncToHost();
    var fn = H('writePlaceOpenTeamCache');
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

  function youSnoozeBarHtml() {
    syncToHost();
    var fn = H('youSnoozeBarHtml');
    var result = typeof fn === "function" ? fn.apply(null, arguments) : undefined;
    syncFromHost();
    return result;
  }


/**
 * Project bubble → ops overview (like hand/job dig-in), not a Finder tree.
 * Folders stay on the map rim; click a folder child for MD library.
 * Overview: live work · hands · jobs · open WOs · law files set for this project.
 */
function showProjectDetail(p, el) {
  if (!p) return;
  _digOverviewRemount = null; /* pc-1231: clear stale ref before building new closure */
  const slug = p.slug || p.name || "";
  const hasStore = folderHasDeskStore(p);
  const st = p.store || {};
  const cityR = String((model.city && model.city.city_root) || "");
  /* pc-1349: live stacks (not a first-paint snapshot of empty root_mds).
   * Light city ships root_entries + deferred root_mds; inventory remount
   * reused this closure and kept inspect at INSTRUCTIONS · PROJECT · 0. */
  function liveInstructionStacks() {
    return projectInstructionStacks(p);
  }
  const hands = (model.workers || []).filter(function (w) {
    return workerHomeMatchesPlot(w, p) && !actorIsJob(w);
  });
  const jobs = (model.workers || []).filter(function (w) {
    return workerHomeMatchesPlot(w, p) && actorIsJob(w);
  });
  /* Dig actors = same home set as placeState (include jobs for fault/live) */
  /*
   * pc-702: cache placeState once per dig paint. digSignal/digGold/digOpen/
   * digStuckFace + buildItems + stats used to re-run placeState many times
   * per mount (and again on every soft remount).
   */
  let _digPlaceCache = null;
  function digPlace() {
    if (!_digPlaceCache) {
      _digPlaceCache = placeState(p, { actors: hands.concat(jobs) });
    }
    return _digPlaceCache;
  }
  function digPlaceInvalidate() {
    _digPlaceCache = null;
  }
  function digSignal() {
    return digPlace().signal;
  }
  function digGold() {
    return digPlace().wo.forYou | 0;
  }
  function digOpen() {
    return digPlace().wo.liveOpen | 0;
  }
  /**
   * Full desk open pile size for this project (pc-836).
   * liveOpen alone is false when For You is deferred/human-gated and
   * heat says live=0 while backlog still has rows — door must not show (0).
   */
  function digStoreOpenRaw() {
    try {
      return storeOpenRaw(p) | 0;
    } catch (e) {
      const st0 = (p && p.store) || {};
      return (
        (st0.backlog | 0) +
        (st0.in_progress | 0) +
        (st0.in_review | 0)
      );
    }
  }
  function digBacklog() {
    const st0 = (p && p.store) || {};
    const psWo = digPlace().wo || {};
    return Math.max(st0.backlog | 0, psWo.ready | 0, 0);
  }
  /**
   * Primary dig door: honest label + filter for the full pile (pc-836).
   * Prefer live open; if only act-now, open for_you pile; if backlog only,
   * still open "open" filter with store count (not digOpen alone).
   */
  function digPrimaryWoDoor() {
    const live = digOpen() | 0;
    const gold = digGold() | 0;
    const stuck = digStuckFace() | 0;
    const storeOpen = digStoreOpenRaw() | 0;
    const backlog = digBacklog() | 0;
    if (digInWoFilter === "for_you") {
      const n = gold || 0;
      return {
        label: "All work orders · for You (" + n + ")",
        filter: "for_you",
        count: n,
      };
    }
    if (digInWoFilter === "stalled") {
      return {
        label: "All stuck (" + (stuck || "…") + ")",
        filter: "stalled",
        count: stuck | 0,
      };
    }
    /* Default "open" pile door */
    if (live > 0) {
      return {
        label:
          "All work orders (" +
          live +
          (gold > 0 ? " · " + gold + " for You" : "") +
          ")",
        filter: "open",
        count: live,
      };
    }
    if (gold > 0) {
      return {
        label:
          "All work orders (" +
          gold +
          " for You" +
          (backlog > 0 ? " · " + backlog + " backlog" : "") +
          ")",
        filter: "for_you",
        count: gold,
      };
    }
    if (storeOpen > 0 || backlog > 0) {
      const n = storeOpen > 0 ? storeOpen : backlog;
      return {
        label: "All work orders (" + n + ")",
        filter: "open",
        count: n,
      };
    }
    if (stuck > 0) {
      return {
        label: "All stuck (" + stuck + ")",
        filter: "stalled",
        count: stuck,
      };
    }
    return {
      label: "All work orders (0)",
      filter: "open",
      count: 0,
    };
  }
  function digStuckFace() {
    return stuckFaceFromPlaceState(digPlace());
  }
  function digCityForYouElse() {
    const city = youPendingCount() | 0;
    const here = digGold();
    return Math.max(0, city - here);
  }
  const live = hands.filter(actorIsLive);
  const walking = hands.filter(actorIsWalking);
  function projectStalledAttItems() {
    const keys = [p.slug, p.name, p.product, deskProductForPlot(p)]
      .filter(Boolean)
      .map(function (k) {
        return normKey(k);
      });
    const out = [];
    try {
      ((_lastAtt && _lastAtt.items) || []).forEach(function (it) {
        if (!it) return;
        const kind = String(it.kind || it.status || "")
          .toLowerCase()
          .replace(/ /g, "_");
        if (kind !== "stalled") return;
        const product = normKey(it.product || it.project || it.store || "");
        if (product && keys.indexOf(product) >= 0) out.push(it);
      });
    } catch (e) {}
    return out;
  }
  function handRow(w, sub) {
    return {
      label: actorShortName(w) || w.display || w.name,
      sub: sub,
      icon: "hand",
      isHand: true,
      name: w.name,
      color:
        w.color ||
        (typeof workerColor === "function" ? workerColor(w.name) : null),
      action: function () {
        inspectPerson(w);
      },
    };
  }

  /* dig-in WO filter: open | for_you | stalled — maps to left rail + map lip */
  let digInWoFilter = "open";
  const deskProd = deskProductForPlot(p) || slug;
  const seedWos = workOrdersForProject(deskProd);
  let cachedWos = seedWos;
  /* pc-692: idle | loading | done | error — never stick on “Loading…” after fetch */
  let deskFetchState = "idle";
  /*
   * pc-702: kick desk open-slips fetch as soon as dig opens (not only in
   * afterOpen). First paint uses seedWos; remount lands when promise settles.
   */
  let deskFetchPromise = null;
  if (hasStore) {
    deskFetchState = "loading";
    deskFetchPromise = fetchProjectOpenSlips(deskProd)
      .then(function (deskWos) {
        /* pc-692: remount even when empty */
        cachedWos = deskWos || [];
        deskFetchState = "done";
        return cachedWos;
      })
      .catch(function () {
        deskFetchState = "error";
        return [];
      });
  }
  const prodSnooze = hasStore ? productSnoozeActive(deskProd) : null;
  /* Skip full dig remount when soft poll only changes timestamps */
  let lastOverviewSig = "";

  const entryPaper = (projectRootPapers(p).all || []).find(function (f) {
    return (
      f &&
      paperDepth(f) <= 1 &&
      String(f.name || "").toLowerCase() === "entry.md"
    );
  });

  const placeOpenSlug = String(slug || "").toLowerCase().trim();
  let pinnedPlaceOpenEntries = readPlaceOpenUserPins(placeOpenSlug);
  /* pc-1228: seed with last-known ENTRY.md chips — no fallback flash. */
  let placeOpenTeamEntries = readPlaceOpenTeamCache(placeOpenSlug);

  function resolvePlaceOpenEntries(entryEntries) {
    const merged = mergePlaceOpenEntries(
      pinnedPlaceOpenEntries,
      entryEntries
    );
    return merged.length ? merged : placeOpenFallbackEntries(placeOpenSlug);
  }

  let placeOpenEntries = resolvePlaceOpenEntries(placeOpenTeamEntries);

  function refreshPlaceOpenEntries() {
    placeOpenEntries = resolvePlaceOpenEntries(placeOpenTeamEntries);
  }

  /** ENTRY.md contract: one simple markdown link per list line. */
  function parsePlaceOpenEntries(content) {
    const entries = [];
    String(content || "")
      .split(/\r?\n/)
      .forEach(function (line) {
        const match = line.match(
          /^\s*-\s+\[([^\]\r\n]+)\]\(([^)\r\n]+)\)\s*$/
        );
        if (!match) return;
        const label = String(match[1] || "").trim();
        const href = normalizePlaceOpenHref(match[2]);
        if (!label || !href) return;
        entries.push({ label: label, href: href });
      });
    return entries;
  }

  let entryFetchPromise = null;
  if (entryPaper) {
    const entryPath = String(
      entryPaper.path ||
        cityRelFromPaper(entryPaper, p.name || p.slug || slug) ||
        ""
    ).trim();
    if (entryPath) {
      entryFetchPromise = fetch(
        "/api/file?path=" + encodeURIComponent(entryPath),
        { cache: "no-store", credentials: "same-origin" }
      )
        .then(function (r) {
          if (!r.ok) return null;
          return r.json();
        })
        .then(function (data) {
          placeOpenTeamEntries = parsePlaceOpenEntries(
            data && data.content != null ? data.content : ""
          );
          writePlaceOpenTeamCache(placeOpenSlug, placeOpenTeamEntries);
          refreshPlaceOpenEntries();
          return placeOpenEntries;
        })
        .catch(function () {
          /* pc-1228: transient fetch error keeps the cached team chips
           * instead of wiping the strip back to the fallback. */
          refreshPlaceOpenEntries();
          return placeOpenEntries;
        });
    }
  }
  if (!entryFetchPromise) {
    refreshPlaceOpenEntries();
  }

  /* pc-1227: fetch doors.json layer for the dig Open strip.
   * pc-1228: seed from the session cache so the first paint is complete;
   * transient fetch errors keep the cached doors. */
  let placeOpenDoors = readPlaceOpenDoorsCache(placeOpenSlug);
  const doorsFetchPromise = fetch(
    "/api/project/" + encodeURIComponent(placeOpenSlug) + "/doors",
    { cache: "no-store", credentials: "same-origin" }
  )
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      placeOpenDoors = (data && Array.isArray(data.doors)) ? data.doors : [];
      writePlaceOpenDoorsCache(placeOpenSlug, placeOpenDoors);
    })
    .catch(function () {});

  function placeOpenSectionHtml() {
    /* Shared chrome — same template as workspace dig */
    return buildPlaceOpenSectionHtml(
      placeOpenSlug,
      pinnedPlaceOpenEntries,
      placeOpenTeamEntries,
      { scopeLabel: "Project entry points", doors: placeOpenDoors, doorSlug: placeOpenSlug }
    );
  }

  function bindPlaceOpenEntries(host) {
    bindPlaceOpenSectionShared(host, placeOpenSlug, function () {
      pinnedPlaceOpenEntries = readPlaceOpenUserPins(placeOpenSlug);
      refreshPlaceOpenEntries();
      lastOverviewSig = "";
      mountProjectOverview(true);
    });
    bindDoorRunChips(host, placeOpenSlug);
  }

  /* pc-610 / pc-703: L1 glance helpers — open/for You only; never done dump. */
  function woIsDoneOrCanceled(r) {
    if (!r) return true;
    const st0 = String(r.status || r.stamp || "")
      .toLowerCase()
      .replace(/ /g, "_");
    return (
      st0 === "done" ||
      st0 === "canceled" ||
      st0 === "cancelled" ||
      !!r.isDone
    );
  }
  function woIsOpenish(r) {
    if (!r || woIsDoneOrCanceled(r)) return false;
    const st0 = String(r.status || "")
      .toLowerCase()
      .replace(/ /g, "_");
    if (
      st0 === "backlog" ||
      st0 === "in_progress" ||
      st0 === "in_review" ||
      st0 === "ready" ||
      !st0
    )
      return true;
    const stamp = String(r.stamp || "").toLowerCase();
    if (stamp.indexOf("done") >= 0 || stamp.indexOf("cancel") >= 0)
      return false;
    return true;
  }

  /* pc-703 / pc-950: For You paper pile (≤5). Open pile never listed on L1. */
  function pushNeedsYouRows(into, wos) {
    const forYouWos = (wos || []).filter(function (r) {
      return r && woIsOpenish(r) && r.isYou;
    });
    /* pc-1201: same row anatomy as You dig — title = focus; meta = id · verb · product */
    forYouWos.slice(0, 5).forEach(function (r) {
      const cat = forYouCategoryFromSlip(r);
      const prod = forYouProductLabel(r.prod || r.focus || r.product || "");
      let focus = String(r.title || "For You")
        .replace(/^Inbox\s*[·•\-–]\s*/i, "")
        .replace(/^FOUNDER\s*[·•\-–]\s*/i, "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 72);
      if (focus && focus === focus.toUpperCase() && focus.length > 4) {
        focus = focus.charAt(0) + focus.slice(1).toLowerCase();
      }
      const verb =
        cat.verb || (cat.face === "read" ? "Mark read" : "Open · decide");
      const meta = [r.tid, verb, prod].filter(Boolean).join(" · ");
      into.push({
        label: focus || r.tid || "For You",
        sub: meta,
        href: r.tid ? "/ticket?id=" + encodeURIComponent(r.tid) : null,
      });
    });
    return forYouWos.length;
  }

  function buildItems(woRows) {
    const items = [];
    const bodySlice = normalizePlaceBodySlice(mapPlaceBodySlice);
    const live = hands.filter(actorIsLive);
    const walking = hands.filter(actorIsWalking);

    /* ── Non-act slices: one body only (pulse nav) — no full ops dump ── */
    if (bodySlice === "structure") {
      const instr = liveInstructionStacks();
      const lawFiles = instr.law;
      const archFiles = instr.architecture;
      renderInstructionsSection(lawFiles, items, "project", {
        managed: !!p.managed,
        projRel: p.name || p.slug || slug,
        architectureFiles: archFiles,
      });
      return items;
    }
    if (bodySlice === "jobs") {
      items.push({
        label: "Jobs · " + jobs.length,
        section: true,
        inert: true,
      });
      if (!jobs.length) {
        items.push({
          label: "No jobs home here",
          sub: "Scheduled automation · map ⏰ seat",
          empty: true,
          inert: true,
        });
      } else {
        jobs.forEach(function (w) {
          const nf = nextFireMs(w);
          items.push({
            label: actorShortName(w) || w.display || w.name,
            sub: isFinite(nf)
              ? "next " + formatRemain(nf - Date.now())
              : w.working
                ? "live"
                : "job",
            icon: "job",
            isJob: true,
            name: w.name,
            action: function () {
              inspectPerson(w);
            },
          });
        });
      }
      return items;
    }
    if (bodySlice === "work") {
      const openNow = digOpen();
      const goldWo = digGold();
      items.push({
        label: "Work orders · this project",
        section: true,
        inert: true,
      });
      items.push({
        label:
          openNow +
          " live open · " +
          goldWo +
          " for You",
        sub: "Full stream on left Work orders rail (scoped)",
        note: true,
        inert: true,
      });
      if (hasStore) {
        items.push({
          label: "Open live pile (left)",
          sub: "Scopes tape · live open excludes deferred",
          action: function () {
            digInWoFilter = "open";
            syncDigInWoToLeftRail(p, "open");
            openProjectWorkOrders(deskProd, p, { filter: "open" });
          },
        });
        if (goldWo > 0) {
          items.push({
            label: "Open For You pile",
            sub: goldWo + " act-now · map gold",
            action: function () {
              digInWoFilter = "for_you";
              syncDigInWoToLeftRail(p, "for_you");
              openProjectWorkOrders(deskProd, p, { filter: "for_you" });
            },
          });
        }
      } else {
        items.push({
          label: "No WorkLane store joined",
          sub: "Work orders need a store",
          empty: true,
          inert: true,
        });
      }
      return items;
    }
    if (bodySlice === "presence") {
      renderWorkingOnNowSection(live, walking, items, {
        maxWalk: 8,
        icon: "hand",
        subFn: function (w, st) {
          return st === "live" ? "live inside" : "on approach";
        },
      });
      if (!live.length && !walking.length) {
        items.push({
          label: "Quiet · no one live here",
          sub: "Idle seats on left Agent activities · On this project",
          note: true,
          inert: true,
        });
      }
      items.push({
        label: "Left rail · Agent activities",
        sub: "On this project · heat order",
        action: function () {
          try {
            const list = document.getElementById("map-live-list");
            if (list)
              list.scrollIntoView({ block: "nearest", behavior: "smooth" });
          } catch (e) {}
        },
      });
      return items;
    }
    if (bodySlice === "roster") {
      items.push({
        label: "Agents · " + hands.length,
        section: true,
        inert: true,
      });
      if (!hands.length) {
        items.push({
          label: "No agents home here",
          sub: "Hire or set homeKey",
          empty: true,
          inert: true,
        });
      } else {
        items.push({
          label: "Full list on left rail",
          sub: hands.length + " seats · left Agent activities",
          note: true,
          inert: true,
        });
        hands.slice(0, 8).forEach(function (w) {
          items.push(
            handRow(
              w,
              w.working
                ? "live"
                : "idle · left rail for heat"
            )
          );
        });
      }
      return items;
    }

    /* ── act (default): For You + Stuck + notices only ── */
    /* Notices density: ≤2 rows per active/expected; snoozed collapsed.
     * Q2: when place is stuck, unrouted rows live under Stuck (not double). */
    const hygieneKinds =
      typeof mapHygieneKindsForPlot === "function"
        ? mapHygieneKindsForPlot(p)
        : [];
    const foldUnroutedToStuck =
      digSignal().id === "stuck" || digStuckFace() > 0;
    if (hygieneKinds.length) {
      const hyActive = [];
      const hyExpected = [];
      const hySnoozed = [];
      let foldedUnrouted = 0;
      hygieneKinds.forEach(function (kind) {
        const k = kind || {};
        if (
          foldUnroutedToStuck &&
          String(k.id || "") === "unrouted" &&
          !k.expected &&
          !k.snoozed
        ) {
          foldedUnrouted++;
          return;
        }
        if (k.expected) hyExpected.push(k);
        else if (k.snoozed) hySnoozed.push(k);
        else hyActive.push(k);
      });
      const hyN =
        hyActive.length + hyExpected.length + hySnoozed.length;
      if (hyN > 0) {
        items.push({
          label:
            "Notices · " +
            hyN +
            (hyActive.length
              ? " · " + hyActive.length + " open"
              : hySnoozed.length
                ? " · " + hySnoozed.length + " hidden"
                : ""),
          section: true,
          inert: true,
        });
        /* pc-860: layer teach — hygiene hide ≠ For You alarm snooze */
        items.push({
          label: "Map pins · browser hide",
          sub:
            "Hide notice mutes hygiene pins only (this browser). " +
            "Alarm clock Snooze For You mutes gold via server — separate store.",
          note: true,
          inert: true,
        });
        if (foldedUnrouted > 0) {
          items.push({
            label: foldedUnrouted + " unrouted in Stuck below",
            sub: "Same red map lip · not listed twice here",
            note: true,
            inert: true,
          });
        }
        hyActive.forEach(function (k) {
          const kid = String(k.id || "");
          const sig = String(k.signature || "");
          const teach = String(k.teach || mapHygieneTeach(kid) || "").slice(
            0,
            96
          );
          if (k.ticket && k.ticket.id) {
            items.push({
              label: k.label || "Ready without a hand",
              sub: teach + " · open work order",
              action: function () {
                openMapHygieneTicket(
                  k.ticket.id,
                  k.ticket.product || k.ticket.store || deskProd || ""
                );
              },
            });
          } else {
            items.push({
              label: k.label || kid || "Notice",
              sub: teach,
              inert: true,
            });
          }
          if (k.canMarkExpected && k.expectedToken) {
            items.push({
              label:
                kid === "quiet"
                  ? "Mark expected · stable"
                  : "Mark expected · planning",
              sub: "Durable on this project · not a browser hide",
              action: function () {
                const patch =
                  kid === "quiet"
                    ? { quiet: "stable" }
                    : { handless: "planning" };
                postMapHygieneExpected(p, patch).catch(function () {});
              },
            });
            /* Timed browser hide as the non-durable alternative */
            items.push({
              label: "Hide notice · 1 day",
              sub:
                "Browser pin only · not For You gold · overview also has Today / 1 week",
              action: function () {
                snoozeMapNotice(kid, sig, "1d");
                refreshMapHygieneSurfaces(p);
              },
            });
          } else {
            /* pc-860: multi-duration Hide notice — not "Snooze" (that word = For You) */
            [
              { token: "today", lab: "Today" },
              { token: "1d", lab: "1 day" },
              { token: "1w", lab: "1 week" },
            ].forEach(function (opt) {
              items.push({
                label: "Hide notice · " + opt.lab,
                sub:
                  "Browser pin mute only · does not clear For You gold or gates",
                action: function () {
                  snoozeMapNotice(kid, sig, opt.token);
                  refreshMapHygieneSurfaces(p);
                },
              });
            });
          }
        });
        hyExpected.forEach(function (k) {
          const kid = String(k.id || "");
          items.push({
            label: k.label || kid || "Expected",
            sub:
              (k.teach || "Marked expected on this project") +
              " · tap to clear",
            action: function () {
              const patch =
                kid === "quiet" ? { quiet: null } : { handless: null };
              postMapHygieneExpected(p, patch).catch(function () {});
            },
          });
        });
        if (hySnoozed.length === 1) {
          const k = hySnoozed[0];
          const untilLabel =
            typeof formatSnoozeUntil === "function"
              ? formatSnoozeUntil(k.snoozeUntil)
              : String(k.snoozeUntil || "").slice(0, 16);
          items.push({
            label: (k.label || k.id || "Notice") + " · hidden",
            sub:
              "Until " +
              (untilLabel || "later") +
              " · browser only · tap to show notice again",
            action: function () {
              unsnoozeMapNotice(String(k.id || ""));
              refreshMapHygieneSurfaces(p);
            },
          });
          items.push({
            label: "Show notice again",
            sub: "Unhide this pin · does not touch For You snooze",
            action: function () {
              unsnoozeMapNotice(String(k.id || ""));
              refreshMapHygieneSurfaces(p);
            },
          });
        } else if (hySnoozed.length > 1) {
          items.push({
            label: hySnoozed.length + " notices hidden",
            sub: "Muted in this browser · tap to restore all pins",
            action: function () {
              hySnoozed.forEach(function (k) {
                unsnoozeMapNotice(String(k.id || ""));
              });
              refreshMapHygieneSurfaces(p);
            },
          });
          items.push({
            label: "Show all notices again",
            sub: "Unhide every hidden pin here · For You gold unchanged",
            action: function () {
              hySnoozed.forEach(function (k) {
                unsnoozeMapNotice(String(k.id || ""));
              });
              refreshMapHygieneSurfaces(p);
            },
          });
        }
      } else if (foldedUnrouted > 0) {
        /* Only unrouted notices — fully owned by Stuck section */
        items.push({
          label: "Notices",
          section: true,
          inert: true,
        });
        items.push({
          label: foldedUnrouted + " unrouted in Stuck below",
          sub: "Same red map lip · not double-listed",
          note: true,
          inert: true,
        });
      }
    }
    /* Open entry chips + place pulse live in formPrefix — not list status rows */

    /* For You inventory only when act-now rows exist (idle → pulse only) */
    const goldNow = digGold();
    const sigNow = digSignal();
    const stuckFace = digStuckFace();
    {
      const fyBuf = [];
      const needsShown = pushNeedsYouRows(fyBuf, woRows || []);
      const stillLoadingNeeds =
        deskFetchState === "idle" || deskFetchState === "loading";
      if (needsShown > 0) {
        items.push({
          label: "For You · " + needsShown,
          section: true,
          inert: true,
        });
        fyBuf.forEach(function (row) {
          items.push(row);
        });
        if (goldNow > 5 || needsShown > 5) {
          items.push({
            label:
              "All work orders · for You (" + needsShown + ")",
            sub: "Overview keeps ≤5",
            action: function () {
              digInWoFilter = "for_you";
              syncDigInWoToLeftRail(p, "for_you");
              openProjectWorkOrders(deskProd, p, { filter: "for_you" });
            },
          });
        }
      } else if (goldNow > 0 && stillLoadingNeeds) {
        items.push({
          label: "For You · " + goldNow,
          section: true,
          inert: true,
        });
        items.push({
          label: "Loading…",
          sub: "Act-now gates",
          empty: true,
          inert: true,
        });
      } else if (goldNow > 0) {
        items.push({
          label: "For You · " + goldNow,
          section: true,
          inert: true,
        });
        items.push({
          label:
            deskFetchState === "error"
              ? "Couldn't load rows"
              : "Open full pile",
          sub: goldNow + " act-now · map gold",
          action: function () {
            digInWoFilter = "for_you";
            syncDigInWoToLeftRail(p, "for_you");
            openProjectWorkOrders(deskProd, p, { filter: "for_you" });
          },
        });
      }
      /* Idle For You (0) → place pulse only, no empty list section */
    }

    /* Stuck — same channel as map red lip (not For You); pulse shows severity */
    if (stuckFace > 0 || (sigNow && sigNow.id === "stuck")) {
      const stalledItems = projectStalledAttItems();
      const unroutedRows =
        typeof mapUnroutedRowsForPlot === "function"
          ? mapUnroutedRowsForPlot(p)
          : [];
      items.push({
        label: "Stuck · " + stuckFace,
        section: true,
        inert: true,
      });
      items.push({
        label: sigNow.label || "Stuck",
        sub:
          (sigNow.reason || "") +
          (sigNow.liveOpen
            ? " · " + sigNow.liveOpen + " live open total"
            : "") +
          " · map lip face " +
          stuckFace,
        note: true,
        inert: true,
      });
      stalledItems.slice(0, 5).forEach(function (it) {
        const tid = String((it && it.id) || "").trim();
        items.push({
          label: tid || "stalled work order",
          sub: String((it && (it.title || it.summary || it.note)) || "stalled").slice(
            0,
            72
          ),
          href: tid ? "/ticket?id=" + encodeURIComponent(tid) : null,
        });
      });
      unroutedRows.slice(0, 5).forEach(function (row) {
        const tid = String((row && row.id) || "").trim();
        if (
          stalledItems.some(function (it) {
            return String((it && it.id) || "") === tid;
          })
        )
          return;
        items.push({
          label: tid || "unrouted work order",
          sub: "No routed hand · open work order",
          action: tid
            ? function () {
                openMapHygieneTicket(tid, deskProd || "");
              }
            : null,
          href: tid ? "/ticket?id=" + encodeURIComponent(tid) : null,
        });
      });
      if (!stalledItems.length && !unroutedRows.length) {
        items.push({
          label: "Open stuck pile on left rail",
          sub: "Stalled / unrouted rows · same filter as map lip",
          action: function () {
            digInWoFilter = "stalled";
            syncDigInWoToLeftRail(p, "stalled");
            openProjectWorkOrders(deskProd, p, { filter: "stalled" });
          },
        });
      } else {
        items.push({
          label: "All stuck on left rail",
          sub: "Scopes Work Orders tape to stalled",
          action: function () {
            digInWoFilter = "stalled";
            syncDigInWoToLeftRail(p, "stalled");
            openProjectWorkOrders(deskProd, p, { filter: "stalled" });
          },
        });
      }
    }

    /*
     * act slice ends here — agents / jobs / WO dump / instructions live on
     * other pulse slices or left rails (one dig grammar with workspace).
     */
    if (!items.length) {
      items.push({
        label: "Nothing to decide here",
        sub: "Pulse → Structure · Work · Presence · left rails for motion",
        note: true,
        inert: true,
      });
    }
    return items;
  }

  function buildProjectStats() {
    const ps = digPlace();
    const sig = ps.signal;
    const wo = ps.wo;
    const openN = wo.liveOpen | 0;
    const goldN = wo.forYou | 0;
    const stuckN = digStuckFace();
    const readyN = wo.ready | 0;
    const defN = wo.deferred | 0;
    /* pc-1083: presence = hands only — jobs shown separately in hands·jobs chip */
    const handLiveN = hands.filter(actorIsLive).length;
    const handWalkN = hands.filter(actorIsWalking).length;
    const busyN = handLiveN + handWalkN;
    const statusLab = handLiveN > 0
      ? "live"
      : handWalkN > 0
        ? "approach"
        : ps.presence.fault
          ? "fault"
          : "status";
    const statusVal = ps.presence.fault
      ? "!"
      : busyN
        ? String(busyN)
        : "quiet";
    const projectStats = [
      {
        id: "presence",
        label: statusLab,
        value: statusVal,
        live: handLiveN > 0,
        stuck: !!ps.presence.fault,
        muted: busyN === 0 && !ps.presence.fault,
        title:
          "Presence · " +
          (ps.presence.ringLabel || "Idle") +
          " · motion: " +
          (ps.motion.grammar || "schedule-walk") +
          " · scroll Working on now",
        action: function () {
          scrollInspectSection("working on now") ||
            scrollInspectSection("agents");
        },
      },
      {
        id: "hands_jobs",
        label: "hands · jobs",
        value: hands.length + " · " + jobs.length,
        muted: hands.length + jobs.length === 0,
        title: "Scroll Agents on this overview",
        action: function () {
          scrollInspectSection("agents");
        },
      },
    ];
    if (!hasStore) {
      projectStats.push({
        label: "store",
        value: "none",
        muted: true,
        title: "No WorkLane store joined",
      });
    } else {
      /* placeState.work ladder → dig KPIs (same as map lip) */
      projectStats.push({
        id: "live_open",
        label: "live open",
        value: String(openN),
        live: digInWoFilter === "open" || digInWoFilter === "live",
        muted:
          openN === 0 &&
          digInWoFilter !== "open" &&
          digInWoFilter !== "live",
        title:
          "Live open (deferred excluded) · same as left-rail live door · map lip face: " +
          (ps.face | 0) +
          " · " +
          (sig.reason || sig.label || ""),
        action: function () {
          if (digInWoFilter !== "open" && digInWoFilter !== "live") {
            digInWoFilter = "open";
            mountProjectOverview(true);
          }
          syncDigInWoToLeftRail(p, "open");
          scrollInspectSection("work orders");
        },
      });
      projectStats.push({
        id: "for_you",
        label: "For You",
        value: String(goldN),
        gold: goldN > 0 || digInWoFilter === "for_you",
        live: digInWoFilter === "for_you",
        muted: goldN === 0 && digInWoFilter !== "for_you",
        title:
          goldN > 0
            ? "Act-now · map gold (For You)"
            : stuckN > 0
              ? "0 For You · map lip is Stuck, not gold"
              : digCityForYouElse() > 0
                ? "0 here · " +
                  digCityForYouElse() +
                  " For You elsewhere (You card)"
                : "No act-now on this project",
        action: function () {
          if (digInWoFilter !== "for_you") {
            digInWoFilter = "for_you";
            mountProjectOverview(true);
          }
          syncDigInWoToLeftRail(p, "for_you");
          scrollInspectSection("for you");
        },
      });
      if (stuckN > 0 || (sig && sig.id === "stuck")) {
        projectStats.push({
          id: "stuck",
          label: "stuck",
          value: String(stuckN || ps.face || 1),
          stuck: true,
          live: digInWoFilter === "stalled",
          muted: false,
          title:
            (sig.reason || "Stuck") +
            " · red map lip · filter stalled",
          action: function () {
            if (digInWoFilter !== "stalled") {
              digInWoFilter = "stalled";
              mountProjectOverview(true);
            }
            syncDigInWoToLeftRail(p, "stalled");
            scrollInspectSection("stuck") ||
              scrollInspectSection("work orders");
          },
        });
      } else if (sig && sig.id === "flowing") {
        projectStats.push({
          id: "flowing",
          label: "flowing",
          value: String(Math.max(handLiveN, wo.inProgress | 0, 1)),
          live: true,
          muted: false,
          title: "Hand working now · green map lip · Working on now",
          action: function () {
            scrollInspectSection("working on now");
          },
        });
      } else if (sig && sig.id === "starved") {
        projectStats.push({
          id: "starved",
          label: "starved",
          value: "0",
          muted: false,
          title:
            (sig.reason || "Scheduled · ready empty") +
            " · hollow map lip",
          action: function () {
            digInWoFilter = "ready";
            syncDigInWoToLeftRail(p, "ready");
            scrollInspectSection("work orders");
          },
        });
      } else if (readyN > 0 && (!sig || sig.id === "queued")) {
        projectStats.push({
          id: "ready",
          label: "ready",
          value: String(readyN),
          live: digInWoFilter === "ready",
          muted: false,
          title: readyN + " ready for a hand · map queued",
          action: function () {
            if (digInWoFilter !== "ready") {
              digInWoFilter = "ready";
              mountProjectOverview(true);
            }
            syncDigInWoToLeftRail(p, "ready");
            scrollInspectSection("work orders");
          },
        });
      }
      if (defN > 0) {
        projectStats.push({
          id: "deferred",
          label: "deferred",
          value: String(defN),
          muted: digInWoFilter !== "deferred",
          live: digInWoFilter === "deferred",
          title:
            defN +
            " iced / deferred · not in live open · left-rail deferred",
          action: function () {
            if (digInWoFilter !== "deferred") {
              digInWoFilter = "deferred";
              mountProjectOverview(true);
            }
            syncDigInWoToLeftRail(p, "deferred");
            openProjectWorkOrders(deskProd, p, { filter: "deferred" });
          },
        });
      }
    }
    const instr = liveInstructionStacks();
    const instrN = instr.law.length + instr.architecture.length;
    projectStats.push({
      id: "instructions",
      label: "instructions",
      value: String(instrN),
      muted: instrN === 0,
      title: "Scroll " + instructionSectionLabel("project"),
      action: function () {
        scrollInspectSection("instructions · project");
      },
    });
    if (prodSnooze && goldN === 0) {
      projectStats.push({
        id: "for_you_muted",
        label: "For You muted",
        value: formatSnoozeUntil(prodSnooze.until) || "on",
        muted: true,
        title:
          "Server For You snooze — gold quiet; human gates still set; not map-pin hide",
      });
    }
    return projectStats;
  }

  function projectOverviewSig(wos) {
    const fy = (wos || [])
      .filter(function (r) {
        return r && r.isYou;
      })
      .map(function (r) {
        return String(r.tid || "");
      })
      .join(",");
    const handBit = hands
      .map(function (w) {
        return String(w.name || "") + ":" + (w.working ? "1" : "0");
      })
      .join(",");
    const openEntries = placeOpenEntries
      .map(function (e) {
        return String(e.label || "") + ":" + String(e.href || "");
      })
      .join(",");
    const personalOpenEntries = pinnedPlaceOpenEntries
      .map(function (e) {
        return String(e.label || "") + ":" + String(e.href || "");
      })
      .join(",");
    /* pc-1229: include doors so sig guard handles skip-if-same after doors fetch */
    const doorsSig = placeOpenDoors
      .map(function (d) {
        return (
          String(d.label || "") +
          ":" +
          String(d.kind || "") +
          ":" +
          String(d.url || d.href || d.path || "")
        );
      })
      .join(",");
    const sig = digSignal();
    const instr = liveInstructionStacks();
    return [
      slug,
      digInWoFilter,
      digOpen(),
      digGold(),
      digStuckFace(),
      sig && sig.id,
      deskFetchState,
      fy,
      handBit,
      instr.law
        .map(function (f) {
          return f.name || "";
        })
        .join(",") +
        ";" +
        instr.architecture
          .map(function (f) {
            return f.name || "";
          })
          .join(","),
      openEntries,
      personalOpenEntries,
      hygieneKindsSig(),
      doorsSig,
    ].join("|");
  }
  function hygieneKindsSig() {
    try {
      if (typeof mapHygieneKindsForPlot !== "function") return "";
      return mapHygieneKindsForPlot(p)
        .map(function (k) {
          return String((k && k.id) || "") + (k && k.snoozed ? "s" : "");
        })
        .join(",");
    } catch (e) {
      return "";
    }
  }

  /* pc-1043: mount uses same builder as soft-poll (no st.backlog-only fork) */
  function digPlacePulseCells() {
    const instr = liveInstructionStacks();
    return computePlacePulseCells("project", p, {
      clickable: true,
      ps: digPlace(),
      structureCount: instr.law.length + instr.architecture.length,
    });
  }

  function digPulseSelect(slice, railFn) {
    setPlaceBodySlice(slice);
    if (typeof railFn === "function") {
      try {
        railFn();
      } catch (eR) {}
    }
    /* Force remount even if content sig matches — body slice changed */
    lastOverviewSig = "";
    remountPlaceOverview();
  }
  function digPulseActions() {
    return {
      for_you: function () {
        digPulseSelect("act", function () {
          digInWoFilter = "for_you";
          syncDigInWoToLeftRail(p, "for_you");
        });
      },
      map_work: function () {
        const sig = digSignal();
        if (sig && sig.id === "stuck") {
          digPulseSelect("act", function () {
            digInWoFilter = "stalled";
            syncDigInWoToLeftRail(p, "stalled");
          });
          return;
        }
        digPulseSelect("work", function () {
          digInWoFilter =
            sig && sig.id === "starved" ? "ready" : "open";
          syncDigInWoToLeftRail(p, digInWoFilter);
        });
      },
      presence: function () {
        digPulseSelect("presence");
      },
      work_orders: function () {
        digPulseSelect("work", function () {
          digInWoFilter = "open";
          syncDigInWoToLeftRail(p, "open");
        });
      },
      jobs: function () {
        digPulseSelect("jobs");
      },
      structure: function () {
        digPulseSelect("structure");
      },
    };
  }

  function mountProjectOverview(replace) {
    syncFromHost();
    /* Fresh placeState once per mount; dig helpers reuse the cache (pc-702). */
    digPlaceInvalidate();
    const handLiveN0 = hands.filter(actorIsLive).length;
    ensurePlaceBodySurface("project:" + String(slug || "").toLowerCase(), {
      forYou: digGold(),
      stuck: digStuckFace(),
      liveN: handLiveN0,
      isWorkspace: false,
    });
    const wos = cachedWos || seedWos;
    const bodySlice = normalizePlaceBodySlice(mapPlaceBodySlice);
    const sig = projectOverviewSig(wos) + "|slice:" + bodySlice;
    /*
     * Soft poll / desk refetch often remounted the whole dig panel → flicker.
     * Same content signature = skip full inspect rebuild.
     */
    if (replace && sig === lastOverviewSig) {
      try {
        const stHost = document.getElementById("inspect-stats");
        if (stHost && typeof paintInspectKpis === "function") {
          paintInspectKpis(stHost, []); /* pulse-only summary */
        }
        softRefreshPlacePulse();
        const formHost = document.getElementById("inspect-form");
        if (formHost) bindPlacePulse(formHost, digPulseActions());
      } catch (eSoft) {}
      return;
    }
    lastOverviewSig = sig;
    _softPulseSig = ""; syncToHost(); /* force soft path to accept fresh strip after remount */
    const instr = liveInstructionStacks();
    const lawN = instr.law.length + instr.architecture.length;
    const pulseHtml = placePulseStripHtml(
      computePlacePulseCells("project", p, {
        clickable: true,
        ps: digPlace(),
        structureCount: lawN,
      }),
      {
        label: "Place pulse",
        aria: "Project place pulse · dig nav",
        selectedId: bodySliceToPulseId(bodySlice),
      }
    );
    const openHtml = placeOpenSectionHtml();
    const snoozeHtml = hasStore
      ? youSnoozeBarHtml({
          id: "map-project-snooze",
          product: deskProd,
          compact: true,
        })
      : "";
    inspectOrbitGroup({
      replace: !!replace,
      el: el || null,
      kind: p.managed
        ? hasStore
          ? "Project · overview"
          : "Project · no store"
        : "Project · unmanaged",
      surface: "project",
      title: p.name || slug || "Project",
      meta:
        "pulse nav · " +
        bodySlice +
        " · left rails = motion" +
        (digStuckFace() || digGold()
          ? " · lip " + folderTabFaceCount(digSignal())
          : "") +
        (prodSnooze && digGold() === 0
          ? " · For You gold quiet (server snooze)"
          : ""),
      skipPaperMeta: true,
      stats: [], /* pulse is the only summary strip (unified with workspace) */
      formPrefix: pulseHtml + openHtml + snoozeHtml,
      items: buildItems(wos),
      doors: hasStore
        ? [
            (function () {
              const door = digPrimaryWoDoor();
              return {
                label: door.label,
                primary: true,
                action: function () {
                  /*
                   * pc-692 / pc-836: scope left rail, then open pile with a
                   * filter that matches the door count (not digOpen alone —
                   * live-only was (0) while For You list had rows).
                   */
                  const filt = door.filter || digInWoFilter || "open";
                  try {
                    digInWoFilter = filt === "open" ? "open" : filt;
                  } catch (eF) {}
                  syncDigInWoToLeftRail(p, filt);
                  openProjectWorkOrders(deskProd, p, {
                    filter: filt,
                    expectedCount: door.count,
                    expectedGold: digGold(),
                    expectedOpen: digOpen(),
                  });
                },
              };
            })(),
          ]
        : [],
      afterOpen: function (host) {
        bindPlaceOpenEntries(host);
        bindPlacePulse(host, digPulseActions());
        if (!hasStore || !deskFetchPromise) return;
        const titleWant = String(p.name || slug);
        /* pc-766: bounded timeout — treat as error after 6s so Loading never sticks */
        const _deskTimer = setTimeout(function () {
          if (deskFetchState !== "loading") return;
          deskFetchState = "error";
          digPlaceInvalidate();
          const title = document.getElementById("inspect-title");
          if (title && String(title.textContent || "") === titleWant) {
            mountProjectOverview(true);
          }
        }, 6000);
        deskFetchPromise
          .then(function () {
            clearTimeout(_deskTimer);
            digPlaceInvalidate();
            const title = document.getElementById("inspect-title");
            if (
              !title ||
              String(title.textContent || "") !== titleWant
            ) {
              return;
            }
            /* pc-692: remount even when empty (deskFetchState already set) */
            mountProjectOverview(true);
          })
          .catch(function () {
            clearTimeout(_deskTimer);
            digPlaceInvalidate();
            const title = document.getElementById("inspect-title");
            if (
              !title ||
              String(title.textContent || "") !== titleWant
            ) {
              return;
            }
            mountProjectOverview(true);
          });
      },
    });
  }

  if (entryFetchPromise) {
    entryFetchPromise.then(function () {
      const title = document.getElementById("inspect-title");
      if (
        title &&
        String(title.textContent || "") === String(p.name || slug)
      ) {
        mountProjectOverview(true);
      }
    });
  }

  /* pc-1227: remount once doors.json layer is ready.
   * pc-1229: no forced sig clear — doorsSig is in projectOverviewSig, so the
   * normal guard skips the rebuild when fetched doors match the cached seed. */
  doorsFetchPromise.then(function () {
    const title = document.getElementById("inspect-title");
    if (title && String(title.textContent || "") === String(p.name || slug)) {
      mountProjectOverview(true);
    }
  });

  _digOverviewRemount = mountProjectOverview; /* pc-1231: expose for inventory callback */
  mountProjectOverview(false);
}

/**
 * Desk-backed open slips for one product (project overview + All door).
 * pc-496: open = backlog + in_progress + in_review per store — not a
 * mixed recent feed (done rows crowd out open at low limits) and not
 * the pulse/transitions fragment.
 */
function fetchProjectTasksByStatus(product, status, limit) {
  const prod = String(product || "").trim();
  if (!prod) return Promise.resolve([]);
  const lim = Math.max(1, Math.min(limit || WoTape.LIST_CAP, WoTape.LIST_CAP));
  const q = new URLSearchParams();
  q.set("product", prod);
  q.set("limit", String(lim));
  if (status) q.set("status", status);
  return fetch("/api/tasks?" + q.toString(), {
    cache: "no-store",
    credentials: "same-origin",
  })
    .then(function (r) {
      return r.json();
    })
    .then(function (d) {
      return (d && d.ok !== false && d.tasks) || [];
    })
    .catch(function () {
      return [];
    });
}

function fetchProjectOpenSlips(product) {
  const prod = String(product || "").trim();
  if (!prod) return Promise.resolve([]);
  const allProducts = prod.toLowerCase() === "all";
  const attIds = {};
  try {
    forYouAttItems((_lastAtt && _lastAtt.items) || []).forEach(function (it) {
      if (!it) return;
      const p = String(it.product || it.project || "").toLowerCase();
      if (
        !allProducts &&
        (p === prod.toLowerCase() || normKey(p) === normKey(prod))
      ) {
        attIds[String(it.id || "")] = true;
      }
      if (allProducts) attIds[String(it.id || "")] = true;
    });
  } catch (e) {}
  const lim = WoTape.LIST_CAP;
  return Promise.all([
    fetchProjectTasksByStatus(prod, "backlog", lim),
    fetchProjectTasksByStatus(prod, "in_progress", lim),
    fetchProjectTasksByStatus(prod, "in_review", lim),
  ])
    .then(function (parts) {
      const seen = {};
      const rows = [];
      (parts[0] || [])
        .concat(parts[1] || [])
        .concat(parts[2] || [])
        .forEach(function (t) {
          const row = slipFromApiTask(t);
          if (!row) return;
          if (row.isDone || row.status === "done" || row.status === "canceled")
            return;
          if (seen[row.tid]) return;
          seen[row.tid] = true;
          if (attIds[row.tid]) row.isYou = true;
          rows.push(row);
        });
      rows.sort(function (a, b) {
        if (a.isYou !== b.isYou) return a.isYou ? -1 : 1;
        return (b.updated || 0) - (a.updated || 0);
      });
      return rows;
    })
    .catch(function () {
      return [];
    });
}

function inspectProjectFinder(p, el) {
  if (!p) return;
  const slug = p.slug || p.name || "";
  const open = openCount(p); /* pc-770: live-only (deferred excluded) when heat loaded */
  const gold = goldFor(p.slug, p.name);
  const cityR = String((model.city && model.city.city_root) || "");
  const entries = (p.root_entries || []).slice();
  const dirs = entries.filter(function (e) {
    return e && (e.kind === "dir" || e.ftype === "folder");
  });
  const files = entries.filter(function (e) {
    return e && e.kind !== "dir" && e.ftype !== "folder";
  });
  const mds = (p.root_mds || []).slice();
  const dMax = mapMdDepthPref();
  /* Required = gold law at project root only (AGENTS / PERIMETER / pointers) */
  const required = mds.filter(function (f) {
    return (
      f &&
      paperDepth(f) <= 1 &&
      (isRequiredPaper(f) || isProjectRootLayerLaw(f, p.path))
    );
  });
  /* Full paper list (pc-663: always all indexed under each project) */
  const otherMd = filterMdsByDepth(mds, dMax).filter(function (f) {
    return f && required.indexOf(f) < 0;
  });
  function mdItem(f, sub) {
    const rel =
      cityRelFromPaper(f, p.name || p.slug || slug) || f.name;
    const lab =
      f && f.depth > 1 && String(rel).indexOf("/") >= 0
        ? String(rel)
        : f.name || rel;
    return {
      label: "📄 " + lab,
      sub:
        sub ||
        (f.pointer
          ? "points agents to the rules"
          : isRequiredPaper(f)
            ? "project rules"
            : "paper"),
      href: rel ? "/read?path=" + encodeURIComponent(rel) : "",
    };
  }
  const items = [];
  /* Next level: folders first — same suite open as map dig-in child */
  dirs.slice(0, 40).forEach(function (d) {
    const abs = String(d.path || "");
    items.push({
      label: "📁 " + (d.name || "folder"),
      sub: "folder · open in suite",
      kind: "folder",
      icon: "folder",
      action: function () {
        openFolderInSuite({
          kind: "inner",
          plot: p,
          dir: {
            name: d.name,
            path: abs || (p.path || "") + "/" + d.name,
            relPath: String(d.name || ""),
          },
        });
      },
    });
  });
  if (required.length) {
    items.push({
      label: instructionSectionLabel("project"),
      sub: required.length + " at project root (gold on papers stack)",
      inert: true,
    });
  }
  required.forEach(function (f) {
    items.push(
      mdItem(f, f.pointer ? "points agents to the rules" : "project rules")
    );
  });
  /* Nested papers: role stacks + subfolder groups (pc-423) */
  const nested = filterMdsByDepth(mds, dMax).filter(function (f) {
    return f && required.indexOf(f) < 0;
  });
  const nestedRoot = nested.filter(function (f) {
    return paperDepth(f) <= 1;
  });
  const nestedDeep = nested.filter(function (f) {
    return paperDepth(f) > 1;
  });
  if (nestedRoot.length) {
    groupFilesByRole(
      nestedRoot.map(function (f) {
        return { f: f, fileName: f.name, rel: f.rel || f.name };
      })
    ).forEach(function (grp) {
      items.push({
        label: grp.label,
        sub: grp.files.length + " at project root · " + grp.sub,
        inert: true,
      });
      grp.files.slice(0, 20).forEach(function (row) {
        items.push(mdItem(row.f, grp.role + " · open"));
      });
    });
  }
  const byFolder = groupMdsBySubfolder(nestedDeep, "", p.path);
  byFolder.forEach(function (bucket) {
    if (bucket.folderKey === ".") return;
    const n =
      (bucket.mdCount != null
        ? bucket.mdCount
        : (bucket.files || []).length) || 0;
    if (!n && !(bucket.files || []).length) return;
    items.push({
      label: "📁 " + (bucket.folderLabel || bucket.folderKey),
      sub: n + " markdown · open in suite",
      kind: "folder",
      icon: "folder",
      action: function () {
        openFolderInSuite({
          kind: "inner",
          plot: p,
          dir: {
            name: bucket.folderKey,
            path: joinRel(
              String(p.path || ""),
              bucket.folderRel || bucket.folderKey
            ),
            relPath: bucket.folderRel || bucket.folderKey,
          },
        });
      },
    });
  });
  /* Flat leftover (depth-filtered) if grouping empty */
  if (!nestedRoot.length && !byFolder.length && otherMd.length) {
    items.push({
      label: "Other papers",
      sub:
        otherMd.length +
        " · depth " +
        mapMdDepthLabel(dMax) +
        " (Settings → Map)",
      inert: true,
    });
    otherMd.slice(0, 40).forEach(function (f) {
      items.push(
        mdItem(
          f,
          paperDepth(f) > 1 ? "nested · open" : "paper at project root"
        )
      );
    });
  }
  files.forEach(function (f) {
    if (f.md || /\.md$/i.test(f.name || "")) return; /* already as md */
    const abs = String(f.path || "");
    const rel = abs.replace(cityR, "").replace(/^\//, "") || f.name;
    items.push({
      label: "· " + (f.name || rel),
      sub: (f.ftype || "file") + " · Finder",
      action: function () {
        openPathInFinder(abs || rel);
      },
    });
  });
  (p.agent_papers || []).slice(0, 12).forEach(function (ap) {
    const rel =
      cityRelFromPaper(ap, p.name || p.slug || slug) ||
      paperRelPath(ap) ||
      "";
    items.push({
      label: "✋ " + (ap.agent || "") + " / " + (ap.file || ap.name || "paper"),
      sub: ap.kind || "hand paper",
      href: rel
        ? "/read?path=" + encodeURIComponent(String(rel).replace(/^\//, ""))
        : null,
    });
  });
  const hands = (model.workers || []).filter(function (w) {
    if (!w || w.kind === "citizen") return false;
    const hk = String(w.homeKey || "").toLowerCase();
    return (
      hk === String(slug).toLowerCase() ||
      hk === String(p.name || "").toLowerCase() ||
      normKey(hk) === normKey(slug)
    );
  });
  hands.forEach(function (w) {
    const job = actorIsJob(w);
    items.push({
      label: w.display || w.name,
      sub: job ? "job on this project" : "hand",
      icon: job ? "job" : "hand",
      isJob: job,
      isHand: !job,
      name: w.name,
      color:
        w.color ||
        (typeof workerColor === "function" ? workerColor(w.name) : null),
      action: function () {
        inspectPerson(w);
      },
    });
  });
  if (!items.length) {
    const foreignEmpty = String(p.zone || "").toLowerCase() === "foreign";
    items.push({
      label: p.managed
        ? "No child folders / papers indexed yet"
        : foreignEmpty
          ? "Upstream-owned · consumer (no adopt required)"
          : "Unmanaged · adopt to add AGENTS.md",
      sub: p.managed
        ? "Rescan workspace"
        : foreignEmpty
          ? "Right-click → Operate · consumer, or Join desk (--force)"
          : "Right-click bubble → Adopt · manage",
      inert: true,
    });
  }
  const doors = [
    {
      label: "Open dig-in · overview",
      primary: true,
      action: function () {
        openFolderInSuite({ kind: "project", plot: p }, el);
      },
    },
    {
      label: "Work orders (" + open + ")",
      action: function () {
        openProjectWorkOrders(slug, p);
      },
    },
    {
      label: "Open in Finder",
      primary: false,
      action: function () {
        openFolderInFinder({ kind: "project", plot: p });
      },
    },
  ];
  if (!p.managed && String(p.zone || "").toLowerCase() === "foreign") {
    doors.unshift({
      label: "Join desk (--force) · origin stays foreign",
      action: function () {
        joinForeignDesk(p);
      },
    });
    doors.unshift({
      label: "Operate · consumer (no adopt)",
      primary: true,
      action: function () {
        operateForeignConsumer(p);
      },
    });
  } else if (!p.managed) {
    doors.unshift({
      label: "Adopt · manage",
      primary: true,
      action: function () {
        adoptProjectFolder(p);
      },
    });
  }
  doors.push({
    label: "Project brief",
    href: projectBriefHref(slug),
  });
  inspectOrbitGroup({
    el: el,
    kind:
      String(p.zone || "").toLowerCase() === "foreign"
        ? p.managed
          ? "Dig-in · upstream-owned"
          : "Dig-in · consumer"
        : p.managed
          ? "Dig-in · project"
          : "Dig-in · unmanaged",
    title: p.name || slug,
    meta:
      "Same open as map folder click · " +
      dirs.length +
      " folders · " +
      mds.length +
      " md · " +
      open +
      " open work" +
      (gold > 0 ? " · " + gold + " for You" : "") +
      (String(p.zone || "").toLowerCase() === "foreign"
        ? p.managed
          ? " · upstream-owned · desk-joined"
          : " · upstream-owned · consumer"
        : p.managed
          ? ""
          : " · not managed yet"),
    items: items,
    doors: doors,
  });
}

/**
 * Work orders for a project — tape (data-focus) + attention seed.
 * Full list comes from fetchProjectOpenSlips (desk) in project overview.
 */
function workOrdersForProject(slug) {
  const sk = String(slug || "").toLowerCase();
  if (!sk) return [];
  const allProducts = sk === "all";
  const rows = [];
  const seen = {};
  function push(row) {
    if (!row || !row.tid) return;
    const k = String(row.tid);
    if (seen[k]) return;
    seen[k] = true;
    rows.push(row);
  }
  const tape = document.getElementById("map-tape-list");
  if (tape) {
    tape.querySelectorAll("button.slip-row").forEach(function (btn) {
      const prod = String(
        btn.getAttribute("data-focus") ||
          btn.getAttribute("data-prod") ||
          ""
      ).toLowerCase();
      const tid = btn.getAttribute("data-tid") || "";
      if (!tid) return;
      if (
        !allProducts &&
        prod &&
        prod !== sk &&
        normKey(prod) !== normKey(sk)
      )
        return;
      /* tid prefix match when focus missing */
      if (!allProducts && !prod) {
        const pref = prodFromTid(tid);
        if (pref && pref !== sk && normKey(pref) !== normKey(sk)) return;
        if (!pref) return;
      }
      push({
        tid: tid,
        title: (btn.querySelector(".slip-title") || {}).textContent || tid,
        stamp: (btn.querySelector(".slip-pill") || {}).textContent || "",
        isYou: btn.classList.contains("is-you"),
      });
    });
  }
  try {
    ((_lastAtt && _lastAtt.items) || []).forEach(function (it) {
      if (!it) return;
      const prod = String(it.product || it.project || "").toLowerCase();
      if (
        !allProducts &&
        prod !== sk &&
        normKey(prod) !== normKey(sk)
      )
        return;
      push({
        tid: String(it.id || "").trim(),
        title: String(it.title || "").slice(0, 96),
        stamp: "for you",
        isYou: true,
      });
    });
  } catch (e) {}
  return rows;
}

/**
 * pc-496: All work orders door — full open pile from desk store
 * (backlog + in_progress + in_review), not attention ∪ transitions.
 * pc-512 / pc-626: opts.filter supports open · live · ready · deferred ·
 * for_you so every compact count opens this same in-Map pile pre-filtered.
 * pc-692: project-scoped opens sync left-rail scope via callers
 * (syncDigInWoToLeftRail) before entering this pile.
 */
function openProjectWorkOrders(slug, p, opts) {
  opts = opts || {};
  /* pc-692: project piles keep left-rail scope in lockstep with dig-in */
  if (opts.scope !== "workspace" && String(slug || "") !== "all" && p) {
    try {
      syncDigInWoToLeftRail(p, opts.filter || "open");
    } catch (eSync) {}
  }
  const requestedPileFilter = String(opts.filter || "open").toLowerCase();
  const initialPileFilter =
    requestedPileFilter === "open"
      ? "open"
      : normalizeWoFilter(requestedPileFilter);
  let pileFilter =
    [
      "open",
      "live",
      "ready",
      "deferred",
      "for_you",
      "stalled",
    ].indexOf(initialPileFilter) >= 0
      ? initialPileFilter
      : "open";
  const initialExpected =
    opts.expectedCount != null ? Number(opts.expectedCount) || 0 : null;
  let pileTextQ = String(opts.textQ || "");
  let pileKeepFocus = false;
  let pileCaret = null;
  let pileFullCache = null;
  const sk = String(slug || (p && (p.slug || p.name)) || "");
  const isWorkspacePile = opts.scope === "workspace" || sk === "all";
  const title =
    String(opts.title || "") ||
    (p && (p.name || p.slug)) ||
    (isWorkspacePile ? "Workspace" : (sk.indexOf("__") === 0 ? "You" : sk)); /* pc-1134: resolve __…__ sentinel before painting */
  const openExpected =
    opts.expectedOpen != null
      ? Number(opts.expectedOpen) || 0
      : p
        ? openCount(p)
        : 0;
  const goldExpected =
    opts.expectedGold != null
      ? Number(opts.expectedGold) || 0
      : p
        ? goldFor(p.slug, p.name)
        : 0;
  const scopeLabel = isWorkspacePile ? "workspace" : (sk.indexOf("__") === 0 ? "You" : sk); /* pc-1134 */
  const collectionLabel = isWorkspacePile
    ? "across all projects"
    : "for this store";

  function pileFilterLabel(filter) {
    if (filter === "for_you") return "for You";
    if (filter === "live") return "live";
    if (filter === "ready") return "ready";
    if (filter === "deferred") return "deferred";
    return "open";
  }

  function applyPileFilter(list) {
    const rows = list || [];
    if (pileFilter === "for_you") {
      return rows.filter(function (r) {
        return r && r.isYou;
      });
    }
    if (pileFilter !== "open") {
      return rows.filter(function (r) {
        return r && rowMatchesWoFilter(r, pileFilter);
      });
    }
    return rows;
  }

  function applyPileText(list) {
    const rows = list || [];
    const q = pileTextQ;
    if (!String(q || "").trim()) return rows;
    return rows.filter(function (r) {
      return slipMatchesListFilter(r, q);
    });
  }

  function rowItems(rows) {
    const list = rows || [];
    /* pc-950 optional: for_you pile groups by face (Decide then Read) */
    /* pc-1076: Watch band (stalled/embargo) appended below Read */
    if (pileFilter === "for_you") {
      if (!list.length && !watchForYouRows.length) return [];
      const sorted = list.slice().sort(function (a, b) {
        const ca = forYouCategoryFromSlip(a);
        const cb = forYouCategoryFromSlip(b);
        if (ca.order !== cb.order) return ca.order - cb.order;
        return String(a.tid || "").localeCompare(String(b.tid || ""));
      });
      const out = [];
      let lastFace = "";
      sorted.forEach(function (row) {
        const cat = forYouCategoryFromSlip(row);
        const faceKey = cat.face || cat.key || "decide";
        if (faceKey !== lastFace) {
          lastFace = faceKey;
          const nIn = sorted.filter(function (r) {
            const c = forYouCategoryFromSlip(r);
            return (c.face || c.key) === faceKey;
          }).length;
          out.push({
            label: cat.label + " · " + nIn,
            sub: cat.sectionSub || "For You face",
            section: true,
            inert: true,
          });
        }
        const st = String(row.stamp || row.status || "open").replace(/_/g, " ");
        const prod = forYouProductLabel(
          row.prod || row.focus || row.product || ""
        );
        const focus = String(row.title || st)
          .replace(/^Inbox\s*[·•\-–]\s*/i, "")
          .replace(/^FOUNDER\s*[·•\-–]\s*/i, "")
          .slice(0, 56);
        const verb =
          cat.verb || (cat.face === "read" ? "Mark read" : "Open · decide");
        out.push({
          label: prod + " · " + cat.label,
          sub: verb + " · " + focus + (row.tid ? " · " + row.tid : ""),
          action: function () {
            if (
              window.SuitePaper &&
              typeof SuitePaper.openTicket === "function"
            ) {
              SuitePaper.openTicket(row.tid);
            }
          },
        });
      });
      if (watchForYouRows.length) {
        out.push({
          label: "Watch · " + watchForYouRows.length,
          sub: "timers · stalled — not gold · Opens {date} on timers",
          section: true,
          inert: true,
        });
        watchForYouRows.forEach(function (it) {
          const wr = forYouWatchRowModel(it);
          const tid = wr.tid;
          out.push({
            label: wr.headline + (wr.opens ? " · " + wr.opens : ""),
            sub:
              (wr.verb ? wr.verb + " · " : "") +
              (wr.focusLine || tid) +
              (tid ? " · " + tid : ""),
            action: function () {
              if (
                window.SuitePaper &&
                typeof SuitePaper.openTicket === "function"
              ) {
                SuitePaper.openTicket(tid);
              }
            },
          });
        });
      }
      return out;
    }
    return list.map(function (row) {
      const st = String(row.stamp || row.status || "open").replace(/_/g, " ");
      if (row.isYou || WoTape.getFilter() === "for_you") {
        const cat = forYouCategoryFromSlip(row);
        const prod = forYouProductLabel(
          row.prod || row.focus || row.product || ""
        );
        const focus = String(row.title || st)
          .replace(/^Inbox\s*[·•\-–]\s*/i, "")
          .replace(/^FOUNDER\s*[·•\-–]\s*/i, "")
          .slice(0, 56);
        const verb =
          cat.verb || (cat.face === "read" ? "Mark read" : "Open · decide");
        return {
          label: prod + " · " + cat.label,
          sub: verb + " · " + focus + (row.tid ? " · " + row.tid : ""),
          action: function () {
            if (
              window.SuitePaper &&
              typeof SuitePaper.openTicket === "function"
            ) {
              SuitePaper.openTicket(row.tid);
            }
          },
        };
      }
      return {
        label: row.tid + (row.isYou ? " · For You" : ""),
        sub:
          ((row.title || "").slice(0, 48) || st) +
          (row.title && st ? " · " + st : ""),
        action: function () {
          if (
            window.SuitePaper &&
            typeof SuitePaper.openTicket === "function"
          ) {
            SuitePaper.openTicket(row.tid);
          }
        },
      };
    });
  }

  function paintPile(allRows, replace) {
    const full = allRows || [];
    pileFullCache = full;
    const statusRows = applyPileFilter(full);
    const rows = applyPileText(statusRows);
    const n = rows.length;
    const nStatus = statusRows.length;
    const nYou = full.filter(function (r) {
      return r && r.isYou;
    }).length;
    const activeLabel = pileFilterLabel(pileFilter);
    const showFilter =
      nStatus >= LIST_FILTER_MIN || !!String(pileTextQ || "").trim();
    let meta =
      pileFilter === "for_you"
        ? nStatus +
          " for You" +
          (openExpected ? " · " + openExpected + " open total" : "") +
          (isWorkspacePile
            ? ". Workspace-wide filter."
            : ". Project pile · left rail scoped to match.") +
          " Click a row → read on Map."
        : pileFilter !== "open"
          ? nStatus +
            " " +
            activeLabel +
            (openExpected ? " · " + openExpected + " open total" : "") +
            (isWorkspacePile
              ? ". Workspace-wide pre-filtered pile."
              : ". Project pre-filtered pile · left rail scoped to match.") +
            " Click a row → read on Map."
        : (full.length +
            " open" +
            (openExpected && openExpected < full.length
              ? " · " + openExpected + " live"
              : "") +
            " " +
            collectionLabel) +
          (isWorkspacePile
            ? ". Full cross-project pile."
            : ". WorkLane store — left rail scoped to this project.") +
          " Click a row → read on Map. For You first when present.";
    if (String(pileTextQ || "").trim()) {
      meta += " · filter: " + n + " of " + nStatus + " match";
    }
    if (pileFilter === "open" && openExpected && full.length < openExpected) {
      meta +=
        " (loaded under open door — check the WorkLane store or raise list cap " +
        WoTape.LIST_CAP +
        ")";
    } else if (full.length >= WoTape.LIST_CAP) {
      meta += " (cap " + WoTape.LIST_CAP + " per status · use filter below)";
    }
    const keepFocus = pileKeepFocus;
    const caret = pileCaret;
    pileKeepFocus = false;
    pileCaret = null;
    const watchForYouRows = pileFilter === "for_you"
      ? stalledAttItems(isWorkspacePile ? null : sk)
      : [];
    const stats = [
      {
        label: "live open",
        value: openExpected ? String(openExpected) : String(full.length),
        live: pileFilter === "open" || pileFilter === "live",
        muted: full.length === 0 && pileFilter !== "open" && pileFilter !== "live",
        title: isWorkspacePile
          ? "Live open across all projects (deferred excluded) · show open pile"
          : "Live open for this store (deferred excluded) · show open pile",
        action: function () {
          if (pileFilter !== "open" && pileFilter !== "live") {
            pileFilter = "open";
            paintPile(full, true);
          }
        },
      },
      {
        label: "For You",
        value: String(nYou || goldExpected),
        gold: nYou > 0 || pileFilter === "for_you",
        live: pileFilter === "for_you",
        muted: nYou === 0 && pileFilter !== "for_you",
        title: isWorkspacePile
          ? "Show only For You rows across all projects"
          : "Show only For You rows for this store",
        action: function () {
          if (pileFilter !== "for_you") {
            pileFilter = "for_you";
            paintPile(full, true);
          }
        },
      },
    ];
    if (
      ["live", "ready", "deferred"].indexOf(initialPileFilter) >= 0
    ) {
      stats.push({
        label: pileFilterLabel(initialPileFilter),
        value: String(
          initialExpected != null
            ? initialExpected
            : full.filter(function (r) {
                return rowMatchesWoFilter(r, initialPileFilter);
              }).length
        ),
        live: pileFilter === initialPileFilter,
        muted: false,
        title: "Return to the " + pileFilterLabel(initialPileFilter) + " pile",
        action: function () {
          if (pileFilter !== initialPileFilter) {
            pileFilter = initialPileFilter;
            paintPile(full, true);
          }
        },
      });
    }
    stats.push({
      label: String(pileTextQ || "").trim() ? "match" : "in pile",
      value: String(n),
      muted: true,
      title:
        "Rows in pile (cap " +
        WoTape.LIST_CAP +
        " per status · live + deferred when filter is open). " +
        (pileFilter === "for_you"
          ? "After for You" +
            (String(pileTextQ || "").trim() ? " + text filter" : " filter")
          : "In " +
            activeLabel +
            " pile" +
            (String(pileTextQ || "").trim() ? " after text filter" : "")),
      action: function () {
        const list = document.querySelector("#inspect-form .inspect-list");
        if (!list) return;
        try {
          list.scrollIntoView({ block: "nearest", behavior: "smooth" });
        } catch (eList) {
          try {
            list.scrollIntoView(true);
          } catch (eListFallback) {}
        }
      },
    });
    inspectOrbitGroup({
      replace: !!replace,
      kind:
        "Work orders · " +
        scopeLabel +
        (pileFilter === "open" ? "" : " · " + activeLabel),
      title: title,
      meta: meta,
      formPrefix: showFilter
        ? listFilterBarHtml("map-pile-filter", pileTextQ, n, nStatus)
        : "",
      stats: stats,
      items: (n || watchForYouRows.length)
        ? rowItems(rows)
        : [
            {
              label: String(pileTextQ || "").trim()
                ? "No rows match filter"
                : pileFilter === "for_you"
                  ? isWorkspacePile
                    ? "Nothing for You across the workspace"
                    : "Nothing for You in this store"
                  : pileFilter !== "open"
                    ? "No " + activeLabel + " work orders in this pile"
                  : isWorkspacePile
                    ? "No open work orders across the workspace"
                    : "No open slips for this store",
              sub: String(pileTextQ || "").trim()
                ? "Clear filter (Esc) or try id / title tokens"
                : pileFilter !== "open"
                  ? "Click open for the full pile"
                  : (isWorkspacePile
                      ? "No backlog / in_progress / in_review rows returned"
                      : "WorkLane returned zero backlog / in_progress / in_review") +
                    (openExpected
                      ? " · open door still shows " + openExpected + " open"
                      : ""),
              inert: true,
            },
          ],
      afterOpen: function (host) {
        if (!showFilter) return;
        wireListFilterInput(host, "map-pile-filter", {
          keepFocus: keepFocus,
          caret: caret,
          onChange: function (q, inputEl) {
            pileTextQ = q || "";
            pileKeepFocus = true;
            pileCaret =
              inputEl && typeof inputEl.selectionStart === "number"
                ? inputEl.selectionStart
                : (q || "").length;
            paintPile(pileFullCache || full, true);
          },
        });
      },
    });
  }

  const seed = applyPileFilter(workOrdersForProject(sk));
  const seedItems = seed.length
    ? rowItems(seed.slice(0, 12))
    : [
        {
          label:
            pileFilter === "for_you"
              ? "Loading for You…"
              : pileFilter !== "open"
                ? "Loading " + pileFilterLabel(pileFilter) + " pile…"
              : "Loading open pile…",
          sub: isWorkspacePile
            ? "All projects · backlog + in progress + in review"
            : "Project · backlog + in progress + in review",
          inert: true,
        },
      ];
  inspectOrbitGroup({
    kind:
      "Work orders · " +
      scopeLabel +
      (pileFilter === "open" ? "" : " · " + pileFilterLabel(pileFilter)),
    title: title,
    meta:
      (pileFilter === "for_you"
        ? "for You · loading…"
        : pileFilter !== "open"
          ? pileFilterLabel(pileFilter) + " · loading pre-filtered pile…"
        : openExpected
          ? openExpected +
            " open · loading full " +
            (isWorkspacePile ? "workspace" : "project") +
            " pile…"
          : "Loading open pile " +
            (isWorkspacePile ? "across all projects" : "for this project") +
            "…") +
      " Click a row → read on Map.",
    items: seedItems,
  });
  fetchProjectOpenSlips(sk).then(function (deskWos) {
    const titleEl = document.getElementById("inspect-title");
    if (titleEl && String(titleEl.textContent || "") !== String(title)) {
      return;
    }
    paintPile(deskWos || [], true);
  });
}

/**
 * Legacy name kept for call sites — same project overview as bubble dig-in.
 * (Old thin house panel retired so tradeOS / socials / … match ProtocolCity.)
 */
function inspectHouse(p, el) {
  if (!p) return;
  showProjectDetail(p, el || null);
}

  function wrapPublic(fn) {
    return function () {
      syncFromHost();
      try {
        return fn.apply(null, arguments);
      } finally {
        syncToHost();
      }
    };
  }

  var InspectProject = {
    init: init,
    show: wrapPublic(showProjectDetail),
    finder: wrapPublic(inspectProjectFinder),
    house: wrapPublic(inspectHouse),
    openWorkOrders: wrapPublic(openProjectWorkOrders),
  };

  function init(host) {
    if (!host || typeof host !== "object") return InspectProject;
    Object.keys(host).forEach(function (k) {
      if (typeof host[k] === "function") _host[k] = host[k];
    });
    return InspectProject;
  }

  global.InspectProject = InspectProject;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = InspectProject;
  }
})(typeof window !== "undefined" ? window : globalThis);

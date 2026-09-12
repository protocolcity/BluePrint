/*! wo-buckets.js — single Work Order bucket-math module (pc-1084 / pc-1090)
 *
 * Predicates + folder/store counts for Map / paper / failsafe.
 * Python mirror: suite/api/wo_gates.py (lint-checked; do not hand-diverge).
 *
 * Usage (browser global):
 *   WoBuckets.isDeferredGate(gateType, gateNote)
 *   WoBuckets.isReady(status, gateType, gateNote)
 *   WoBuckets.isLiveOpen(status, gateType, gateNote)
 *   WoBuckets.storeLiveOpen(store)   // gate-aware when store.ready present
 *   WoBuckets.storeOpenRaw(store)    // backlog+ip+ir (includes ice)
 *   WoBuckets.folderLiveOpen(plot, opts)
 *   WoBuckets.folderDeferred(plot, opts)
 *   WoBuckets.pulseBacklogFromWo(wo, store)
 *   WoBuckets.pulseInMotionFromWo(wo, store)
 *   WoBuckets.normalizeStoreSlug(s)  // pc-1090: one slug + alias normalizer
 *   WoBuckets.storeSlugEquivalents(s)
 *   WoBuckets.normHubKey(s)
 */
(function (global) {
  "use strict";

  /** Open-family statuses (not done/canceled). */
  var OPEN_STATUSES = {
    backlog: true,
    in_progress: true,
    in_review: true,
    "": true,
  };

  var DONE_STATUSES = {
    done: true,
    canceled: true,
    cancelled: true,
  };

  /**
   * Dual-read ice markers (PROCESS §3.9 / wl-257 / pc-547).
   * Keep in lockstep with suite/api/wo_gates.py is_deferred_gate.
   * Marker strings are also asserted by scripts/check_wo_buckets_drift.py.
   */
  var DEFERRED_NOTE_MARKERS = [
    "deferred:",
    "post-northstar",
    "not claimable",
    "withheld from ready",
    "parked:",
    "thaw when",
  ];

  function statusKey(status) {
    return String(status == null ? "" : status)
      .toLowerCase()
      .replace(/\s+/g, "_");
  }

  /**
   * Dual-read deferred: first-class gate_type=deferred OR parked note markers.
   * Parks must not gold For You (wl-257).
   */
  function isDeferredGate(gateType, gateNote) {
    var gt = String(gateType == null ? "" : gateType)
      .toLowerCase()
      .trim();
    var note = String(gateNote == null ? "" : gateNote)
      .toLowerCase()
      .trim();
    if (gt === "deferred") return true;
    if (!gt) return false;
    if (note.indexOf("deferred:") === 0 || note.indexOf("umbrella") === 0) {
      return true;
    }
    for (var i = 0; i < DEFERRED_NOTE_MARKERS.length; i++) {
      if (note.indexOf(DEFERRED_NOTE_MARKERS[i]) >= 0) return true;
    }
    if (note.indexOf("umbrella") >= 0) return true;
    return false;
  }

  /** Map ready: backlog, no ice, empty/missing gate_type. */
  function isReady(status, gateType, gateNote) {
    var st = statusKey(status || "backlog");
    if (st !== "backlog") return false;
    if (isDeferredGate(gateType, gateNote)) return false;
    return gateType == null || String(gateType).trim() === "";
  }

  /** Open without ice — backlog / in_progress / in_review, not deferred. */
  function isLiveOpen(status, gateType, gateNote) {
    var st = statusKey(status);
    if (DONE_STATUSES[st]) return false;
    if (isDeferredGate(gateType, gateNote)) return false;
    return !!OPEN_STATUSES[st];
  }

  /**
   * Gate-aware store live open (pc-765 / pc-1084).
   * When store.ready is present (non-deferred backlog), use ready+ip+ir.
   * Otherwise fall back to backlog+ip+ir (legacy stores without ready).
   */
  function storeLiveOpen(store) {
    var st = store || {};
    if (Object.prototype.hasOwnProperty.call(st, "ready")) {
      return (st.ready | 0) + (st.in_progress | 0) + (st.in_review | 0);
    }
    return (st.backlog | 0) + (st.in_progress | 0) + (st.in_review | 0);
  }

  /** Raw store open (all open statuses) — diagnostics / total pile. */
  function storeOpenRaw(store) {
    var st = store || {};
    return (st.backlog | 0) + (st.in_progress | 0) + (st.in_review | 0);
  }

  function heatRowFromOpts(plot, opts) {
    opts = opts || {};
    if (opts.heat && typeof opts.heat === "object") return opts.heat;
    var heat = opts.folderHeat;
    if (!heat || typeof heat !== "object") return null;
    var cands = opts.keyCandidates;
    if (!cands || !cands.length) {
      cands = [
        plot && plot.slug,
        plot && plot.name,
        plot && plot.product,
      ];
    }
    for (var i = 0; i < cands.length; i++) {
      var k = String(cands[i] || "")
        .toLowerCase()
        .trim();
      if (k && heat[k]) return heat[k];
    }
    return null;
  }

  /**
   * Folder OPEN KPI — live-only when heat row is *sampled* (pc-770 / pc-875).
   * Sampled live=0 stays 0 (ice-correct). Unsampled / cold → storeLiveOpen.
   *
   * opts:
   *   heat — { live, deferred, sampled } for this plot
   *   heatWarm — true when a heat index is considered loaded
   *   folderHeat + keyCandidates — alternate heat lookup
   */
  function folderLiveOpen(plot, opts) {
    opts = opts || {};
    var heatWarm =
      !!opts.heatWarm ||
      !!(
        opts.folderHeat &&
        typeof opts.folderHeat === "object" &&
        (opts.folderHeatAt || Object.keys(opts.folderHeat).length > 0)
      );
    if (heatWarm || opts.heat) {
      var h = heatRowFromOpts(plot, opts);
      if (h && h.sampled) return Math.max(0, h.live | 0);
      /* Unsampled under warm index → store fallback (not silent 0) */
    }
    return storeLiveOpen((plot && plot.store) || {});
  }

  /** Deferred/ice count from sampled heat only (0 when cold). */
  function folderDeferred(plot, opts) {
    opts = opts || {};
    var heatWarm =
      !!opts.heatWarm ||
      !!(
        opts.folderHeat &&
        typeof opts.folderHeat === "object" &&
        (opts.folderHeatAt || Object.keys(opts.folderHeat).length > 0)
      );
    if (!heatWarm && !opts.heat) return 0;
    var h = heatRowFromOpts(plot, opts);
    if (h && h.sampled) return Math.max(0, h.deferred | 0);
    return 0;
  }

  /**
   * map-soft helper: live open for a plot given the soft model (folderHeat).
   */
  function openCountFromPlot(plot, model) {
    var heat = model && model.folderHeat;
    var heatWarm =
      heat &&
      typeof heat === "object" &&
      (model.folderHeatAt || Object.keys(heat).length > 0);
    return folderLiveOpen(plot, {
      folderHeat: heat,
      folderHeatAt: model && model.folderHeatAt,
      heatWarm: !!heatWarm,
      keyCandidates: [plot && plot.slug, plot && plot.name, plot && plot.product],
    });
  }

  function deferredCountFromPlot(plot, model) {
    var heat = model && model.folderHeat;
    if (!heat || typeof heat !== "object") return 0;
    return folderDeferred(plot, {
      folderHeat: heat,
      folderHeatAt: model && model.folderHeatAt,
      heatWarm: true,
      keyCandidates: [plot && plot.slug, plot && plot.name, plot && plot.product],
    });
  }

  /**
   * Backlog for Work-orders pulse cell (pc-1043 / pc-1084).
   * totalOpen · max(live+deferred) · store.backlog floor.
   */
  function pulseBacklogFromWo(wo, store) {
    wo = wo || {};
    store = store || {};
    return Math.max(
      wo.totalOpen | 0,
      (wo.liveOpen | 0) + (wo.deferred | 0),
      store.backlog | 0
    );
  }

  function pulseInMotionFromWo(wo, store) {
    wo = wo || {};
    store = store || {};
    return Math.max(
      wo.inProgress | 0,
      (store.in_progress | 0) + (store.in_review | 0)
    );
  }

  /**
   * pc-1090: one store-slug normalizer (normalize + alias).
   * Map glass / tape dedup / For You counts must key by canonical slug only.
   * Keep lockstep with suite/serve.py _FOLDER_STORE / _normalize_store_slug
   * and workspace_map_app.js fallbacks.
   */
  var STORE_SLUG_ALIASES = {
    ticketingprotocol: "worklane",
    tp: "worklane",
    wl: "worklane",
    register: "oneseo-pos",
    regi: "oneseo-pos",
    "oneseo_pos": "oneseo-pos",
    oc: "workforce",
    blueprint: "protocolcity",
    pc: "protocolcity",
  };

  /** Hyphen-form key: "SE Local HC" / se_local_hc → se-local-hc */
  function normHubKey(k) {
    return String(k || "")
      .trim()
      .toLowerCase()
      .replace(/_/g, "-")
      .replace(/\s+/g, "-");
  }

  /** Canonical WorkLane store slug (aliases applied). */
  function normalizeStoreSlug(s) {
    var k = normHubKey(s);
    if (!k) return "";
    return STORE_SLUG_ALIASES[k] || k;
  }

  /** All slugs that mean the same store (scope checks / dual-read). */
  function storeSlugEquivalents(slug) {
    var canon = normalizeStoreSlug(slug);
    if (!canon) return [];
    var groups = [
      ["worklane", "ticketingprotocol", "tp", "wl"],
      ["oneseo-pos", "register", "regi", "oneseo_pos"],
      ["workforce", "oc"],
      ["protocolcity", "blueprint", "pc"],
    ];
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i];
      if (g.indexOf(canon) >= 0 || g.indexOf(normHubKey(slug)) >= 0) {
        return g.slice();
      }
    }
    return [canon];
  }

  var api = {
    OPEN_STATUSES: OPEN_STATUSES,
    DONE_STATUSES: DONE_STATUSES,
    DEFERRED_NOTE_MARKERS: DEFERRED_NOTE_MARKERS,
    isDeferredGate: isDeferredGate,
    isReady: isReady,
    isLiveOpen: isLiveOpen,
    storeLiveOpen: storeLiveOpen,
    storeOpenRaw: storeOpenRaw,
    folderLiveOpen: folderLiveOpen,
    folderDeferred: folderDeferred,
    openCountFromPlot: openCountFromPlot,
    deferredCountFromPlot: deferredCountFromPlot,
    /* Aliases preferred by Map consumers */
    openCount: openCountFromPlot,
    deferredCount: deferredCountFromPlot,
    pulseBacklogFromWo: pulseBacklogFromWo,
    pulseInMotionFromWo: pulseInMotionFromWo,
    /* pc-1090 store slug */
    STORE_SLUG_ALIASES: STORE_SLUG_ALIASES,
    normHubKey: normHubKey,
    normalizeStoreSlug: normalizeStoreSlug,
    storeSlugEquivalents: storeSlugEquivalents,
  };

  global.WoBuckets = api;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : typeof globalThis !== "undefined" ? globalThis : this);

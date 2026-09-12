/*! graph.js — dig-graph topology helpers (pc-757 · depth ladder pc-774)
 *
 * Pure: folder depth ladder, foundation weight, children@path.
 * No DOM. No global model. Depth is always caller-supplied.
 *
 * Host (workspace_map.html) delegates via MapGraph when available.
 * Spatial projection uses MapGraph directly.
 *
 * Depth ladder (workspace root up to surface children):
 *   0  workspace hub (OneSeo / city folder)
 *   1  managed projects on the ring
 *   2  children of projects (expand-all + dig at project root)
 *   3+ deeper dig (disk)
 *
 * dig-tier-* is SECONDARY weight on depth ≥2 (foundation names), not a
 * parallel color system that fights work/ring on projects.
 */
(function (global) {
  "use strict";

  /*
   * Dig-tier weight: law/ops homes + known product names (deeper dig mute
   * still applies). Heavier paint at the same depth — not expand membership.
   */
  var DIG_FOUNDATION_DIRS = {
    docs: 1,
    suite: 1,
    scripts: 1,
    skills: 1,
    agents: 1,
    ".agents": 1,
    ".claude": 1,
    ".grok": 1,
    ".protocolcity": 1,
    ".github": 1,
    local: 1,
    deploy: 1,
    workers: 1,
    protocolcity: 1,
    worklane: 1,
    workforce: 1,
    presentations: 1,
    socials: 1,
    connector: 1,
    tradeos: 1,
    recipes: 1,
    gridfinity: 1,
    career: 1,
    "oneseo-pos": 1,
  };

  /*
   * Expand-all membership only — BluePrint / ops layers on the project ring
   * (depth 1 → 2). Never product codenames or domain folders (Cisco, talks…).
   * Rest of disk = dig-in, not expand-all.
   */
  var EXPAND_OPS_DIRS = {
    docs: 1,
    suite: 1,
    scripts: 1,
    skills: 1,
    agents: 1,
    workers: 1,
    local: 1,
    deploy: 1,
    tools: 1,
    ".agents": 1,
    ".claude": 1,
    ".grok": 1,
    ".protocolcity": 1,
    ".github": 1,
  };

  function isDigFoundationDirName(name) {
    var n = String(name || "")
      .toLowerCase()
      .replace(/\/+$/, "");
    if (!n) return false;
    if (DIG_FOUNDATION_DIRS[n]) return true;
    if (n === "rules" || n === "law" || n === "charter") return true;
    if (n.indexOf("agents") === 0) return true;
    return false;
  }

  /** Expand-all layer filter — ops/structure only (not dig-tier product names). */
  function isExpandOpsDirName(name) {
    var n = String(name || "")
      .toLowerCase()
      .replace(/\/+$/, "");
    if (!n) return false;
    if (EXPAND_OPS_DIRS[n]) return true;
    if (n === "rules" || n === "law" || n === "charter") return true;
    return false;
  }

  /**
   * Clamp map depth into CSS class map-depth-0 … map-depth-4.
   * Depths >4 share map-depth-4 (deep disk mute).
   */
  function mapDepthClass(depth) {
    var d = depth != null ? depth | 0 : 0;
    if (d < 0) d = 0;
    if (d > 4) d = 4;
    return "map-depth-" + d;
  }

  /**
   * Dig fan child depth: trail length 1 (project root dig) → map depth 2;
   * trail 2 → depth 3; deeper → cap 4.
   */
  function mapDepthForDigChild(trailLen) {
    var t = trailLen != null ? trailLen | 0 : 1;
    if (t < 1) t = 1;
    return Math.min(4, 1 + t);
  }

  /** Expand-all minis are always project children → depth 2. */
  function mapDepthForExpandChild() {
    return 2;
  }

  /**
   * Secondary weight class at a map depth (foundation boost only).
   * digTrailOrDepth: dig trail length when known; for expand pass 1.
   *   foundation — PC-critical / law-ish name (weight, any child depth)
   *   coord      — default child weight (depth 2 family)
   *   deep       — reserved; depth ladder owns mute (kept for back-compat)
   */
  function digTierClassForDir(dirName, digTrailOrDepth) {
    var d = digTrailOrDepth != null ? digTrailOrDepth : 0;
    if (isDigFoundationDirName(dirName)) {
      return "dig-tier-foundation";
    }
    if (d <= 1) return "dig-tier-coord";
    return "dig-tier-deep";
  }

  /**
   * Full class fragment for a child folder at mapDepth:
   * "map-depth-N dig-tier-*".
   */
  function folderLayerClasses(dirName, mapDepth, digTrailForTier) {
    var md = mapDepth != null ? mapDepth : 2;
    var trail =
      digTrailForTier != null
        ? digTrailForTier
        : md <= 2
          ? 1
          : md - 1;
    return mapDepthClass(md) + " " + digTierClassForDir(dirName, trail);
  }

  /**
   * All top-level directory children of a plot (no cap).
   */
  function plotAllDirs(p) {
    var entries = ((p && p.root_entries) || []).slice();
    return entries.filter(function (e) {
      if (!e || e.hidden) return false;
      if (e.dir === true) return true;
      var k = String(e.kind || e.ftype || "").toLowerCase();
      return k === "dir" || k === "folder";
    });
  }

  /**
   * Top-level directory children of a plot (root_entries that are dirs).
   * Capped at 12 to match the dig fan budget.
   */
  function plotTopDirs(p) {
    return plotAllDirs(p).slice(0, 12);
  }

  /**
   * Expand-all membership: **ops layers only** on the same project ring.
   * Never fall back to domain/noise dirs (that felt like a second map dump).
   * Empty ops set → no minis; "+N dig in" still reports full disk remainder.
   *
   * Returns { dirs, total, more, foundationOnly, foundationCount }.
   */
  function plotExpandDirs(p, maxN) {
    var max = maxN != null ? maxN | 0 : 6;
    if (max < 1) max = 1;
    var all = plotAllDirs(p);
    var ops = [];
    for (var i = 0; i < all.length; i++) {
      var e = all[i];
      var nm = (e && (e.name || e.basename)) || "";
      if (isExpandOpsDirName(nm)) ops.push(e);
    }
    var dirs = ops.slice(0, max);
    return {
      dirs: dirs,
      total: all.length,
      more: Math.max(0, all.length - dirs.length),
      foundationOnly: true,
      foundationCount: ops.length,
    };
  }

  global.MapGraph = {
    DIG_FOUNDATION_DIRS: DIG_FOUNDATION_DIRS,
    EXPAND_OPS_DIRS: EXPAND_OPS_DIRS,
    isDigFoundationDirName: isDigFoundationDirName,
    isExpandOpsDirName: isExpandOpsDirName,
    mapDepthClass: mapDepthClass,
    mapDepthForDigChild: mapDepthForDigChild,
    mapDepthForExpandChild: mapDepthForExpandChild,
    digTierClassForDir: digTierClassForDir,
    folderLayerClasses: folderLayerClasses,
    plotAllDirs: plotAllDirs,
    plotTopDirs: plotTopDirs,
    plotExpandDirs: plotExpandDirs,
  };
})(typeof window !== "undefined" ? window : globalThis);

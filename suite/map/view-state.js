/*! view-state.js — one focus + expand state for Map and Outline (pc-844)
 *
 * Dual projection law (pc-756): one workspace truth, two layouts.
 * Both projections MUST read/write this object — not sibling flags.
 *
 *   focus  = dig into a project path (null = workspace hub)
 *   expand = simultaneous ops-layer open (0 = collapsed, 1 = expanded)
 *   projection = "map" | "outline" (layout only; does not own expand/dig)
 */
(function (global) {
  "use strict";

  var state = {
    projection: "map",
    /** 0 = project ring only · 1 = ops layers open (Map minis + Outline rows) */
    expandLevel: 0,
    /**
     * Dig focus — null when at workspace hub.
     * plotSlug / plotName identify the project; relPath is "" at project root.
     * trail: [{ name, relPath }] for back navigation.
     */
    dig: null,
  };

  /* pc-1119: custom ring order — slug array, index = ring/outline rank */
  var _customOrder = [];
  var _onOrderChange = null;

  function cloneDig(d) {
    if (!d) return null;
    var trail = [];
    if (Array.isArray(d.trail)) {
      for (var i = 0; i < d.trail.length; i++) {
        var t = d.trail[i] || {};
        trail.push({
          name: String(t.name || ""),
          relPath: String(t.relPath || ""),
        });
      }
    }
    return {
      plotSlug: String(d.plotSlug || d.slug || "").toLowerCase(),
      plotName: String(d.plotName || d.name || ""),
      relPath: String(d.relPath || ""),
      trail: trail,
    };
  }

  function get() {
    return {
      projection: state.projection,
      expandLevel: state.expandLevel,
      dig: cloneDig(state.dig),
    };
  }

  function getExpandLevel() {
    return state.expandLevel > 0 ? 1 : 0;
  }

  function isExpanded() {
    return state.expandLevel > 0;
  }

  /** Set expand 0|1. Returns new level. Does not paint — host applies visuals. */
  function setExpandLevel(n) {
    state.expandLevel = n > 0 ? 1 : 0;
    return state.expandLevel;
  }

  function getDig() {
    return cloneDig(state.dig);
  }

  function hasDig() {
    return !!(state.dig && (state.dig.plotSlug || state.dig.plotName));
  }

  function digSlug() {
    if (!state.dig) return "";
    return String(state.dig.plotSlug || state.dig.plotName || "").toLowerCase();
  }

  function digRelPath() {
    return state.dig ? String(state.dig.relPath || "") : "";
  }

  /**
   * Set dig focus from host mapDigIn shape or plain fields.
   * Host may pass { plot: {slug,name}, relPath, trail }.
   */
  function setDig(src) {
    if (!src) {
      state.dig = null;
      return null;
    }
    var plot = src.plot || src;
    var slug = String(
      src.plotSlug || src.slug || (plot && (plot.slug || plot.name)) || ""
    ).toLowerCase();
    var name = String(
      src.plotName || src.name || (plot && (plot.name || plot.slug)) || ""
    );
    if (!slug && !name) {
      state.dig = null;
      return null;
    }
    var trail = src.trail;
    if (!Array.isArray(trail) || !trail.length) {
      trail = [{ name: name || slug, relPath: String(src.relPath || "") }];
    }
    state.dig = {
      plotSlug: slug,
      plotName: name || slug,
      relPath: String(src.relPath || ""),
      trail: trail.map(function (t) {
        return {
          name: String((t && t.name) || ""),
          relPath: String((t && t.relPath) || ""),
        };
      }),
    };
    return cloneDig(state.dig);
  }

  function clearDig() {
    state.dig = null;
  }

  function getProjection() {
    return state.projection === "outline" ? "outline" : "map";
  }

  function setProjection(p) {
    state.projection = p === "outline" ? "outline" : "map";
    return state.projection;
  }

  function getCustomOrder() {
    return _customOrder.slice();
  }

  function customOrderSig() {
    return _customOrder.join(",");
  }

  function customOrderRank(slug) {
    return _customOrder.indexOf(String(slug || "").toLowerCase());
  }

  function setCustomOrder(arr, opts) {
    var next = (arr || []).map(function (s) {
      return String(s).toLowerCase();
    });
    var same = next.join(",") === _customOrder.join(",");
    _customOrder = next;
    /* pc-1255: identical order is not a layout event — do not wipe the Map. */
    if (!same && _onOrderChange) {
      try { _onOrderChange(_customOrder.slice()); } catch (e) {}
    }
    if (!same && (!opts || !opts.skipSave)) {
      try {
        fetch("/api/map/layout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ order: _customOrder }),
        });
      } catch (e) {}
    }
  }

  function onOrderChange(fn) {
    _onOrderChange = typeof fn === "function" ? fn : null;
  }

  var _layoutFetch = null;
  function loadCustomOrder(cb) {
    if (!_layoutFetch) {
      try {
        _layoutFetch = fetch("/api/map/layout")
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d && Array.isArray(d.order) && d.order.length) {
              setCustomOrder(d.order, { skipSave: true });
            }
            return _customOrder.slice();
          })
          .catch(function () {
            return _customOrder.slice();
          });
      } catch (e) {
        _layoutFetch = Promise.resolve(_customOrder.slice());
      }
    }
    if (cb) {
      _layoutFetch.then(function (order) {
        try { cb(order || _customOrder.slice()); } catch (eCb) {}
      });
    }
    return _layoutFetch;
  }

  /**
   * Snapshot for debug / soft-poll sig.
   * expand|proj|digSlug|relPath|trailLen
   */
  function sig() {
    var d = state.dig;
    return [
      state.expandLevel > 0 ? 1 : 0,
      state.projection,
      d ? d.plotSlug || "" : "",
      d ? d.relPath || "" : "",
      d && d.trail ? d.trail.length : 0,
    ].join("|");
  }

  global.MapViewState = {
    get: get,
    getExpandLevel: getExpandLevel,
    isExpanded: isExpanded,
    setExpandLevel: setExpandLevel,
    getDig: getDig,
    hasDig: hasDig,
    digSlug: digSlug,
    digRelPath: digRelPath,
    setDig: setDig,
    clearDig: clearDig,
    getProjection: getProjection,
    setProjection: setProjection,
    sig: sig,
    getCustomOrder: getCustomOrder,
    customOrderSig: customOrderSig,
    customOrderRank: customOrderRank,
    setCustomOrder: setCustomOrder,
    onOrderChange: onOrderChange,
    loadCustomOrder: loadCustomOrder,
  };

  /* pc-1255: start the layout fetch during parse so first paint often
   * already has ring order — avoids a second full SVG wipe a few seconds later. */
  try {
    loadCustomOrder();
  } catch (eBoot) {}
})(typeof window !== "undefined" ? window : globalThis);

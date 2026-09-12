/*! live.js — city-data overlay seam for pollLight (pc-757)
 *
 * Pure: shallow city clone + tp-scene store overlay.
 * No DOM. No fetch. No side effects beyond mutating the cloned city object.
 *
 * Host (workspace_map.html) delegates via MapLive when available.
 * Spatial projection uses MapLive directly.
 */
(function (global) {
  "use strict";

  /* Local copy — matches host normHubKey exactly (pc-559). */
  function normHubKey(k) {
    return String(k || "")
      .trim()
      .toLowerCase()
      .replace(/_/g, "-")
      .replace(/\s+/g, "-");
  }

  /**
   * Shallow folder-level clone before store overlay (pollLight).
   * Avoids JSON deep-clone of the whole ~0.3–0.8MB city every heartbeat.
   */
  function cloneCityForStoreOverlay(city) {
    if (!city || typeof city !== "object") return city;
    var next = Object.assign({}, city);
    var key = city.folders ? "folders" : "neighborhoods";
    var list = city.folders || city.neighborhoods || [];
    next[key] = list.map(function (f) {
      return f && typeof f === "object" ? Object.assign({}, f) : f;
    });
    return next;
  }

  /**
   * Overlay tp-scene store counts onto a (cloned) city object.
   * Marks f._storeFromScene so sticky-preserve never freezes a closed queue.
   */
  function overlayStoresFromScene(city, scene) {
    if (!city || !scene || !scene.stores || !scene.stores.length) return city;
    var by = {};
    scene.stores.forEach(function (s) {
      if (!s || !s.slug) return;
      /* pc-559: normHubKey so "SE Local HC" / se-local-hc / se_local_hc match */
      by[normHubKey(s.slug)] = s;
    });
    (city.folders || city.neighborhoods || []).forEach(function (f) {
      if (!f) return;
      f._storeFromScene = false;
      var keys = [f.slug, f.name, f.product]
        .filter(Boolean)
        .map(function (k) {
          return normHubKey(k);
        });
      var s = null;
      for (var i = 0; i < keys.length; i++) {
        if (by[keys[i]]) {
          s = by[keys[i]];
          break;
        }
      }
      if (!s) return;
      f.store = {
        backlog: s.backlog | 0,
        in_progress: s.in_progress | 0,
        in_review: s.in_review | 0,
        done: s.done_total | 0,
        urgent_backlog: 0,
        ready: s.ready | 0,
      };
      f._storeFromScene = true;
      if (!f.product && s.slug) f.product = s.slug;
    });
    return city;
  }

  global.MapLive = {
    normHubKey: normHubKey,
    cloneCityForStoreOverlay: cloneCityForStoreOverlay,
    overlayStoresFromScene: overlayStoresFromScene,
  };
})(typeof window !== "undefined" ? window : globalThis);
